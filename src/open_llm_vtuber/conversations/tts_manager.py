import asyncio
import json
import re
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Union
from loguru import logger

from ..agent.output_types import DisplayText, Actions
from ..live2d_model import Live2dModel
from ..tts.tts_interface import TTSInterface
from ..utils.stream_audio import (
    prepare_audio_payload,
    prepare_stream_start_payload,
    prepare_stream_chunk_payload,
    prepare_stream_end_payload,
)
from .types import WebSocketSend


class _StreamHandle:
    """
    A streamed-audio sentence occupying one sequence slot in the ordered
    sender. Chunk payloads are produced by the TTS task and consumed by the
    sender once this handle's sequence number is up; a ``None`` sentinel
    marks the end of the stream.
    """

    def __init__(self, start_payload: Dict) -> None:
        self.start_payload = start_payload
        self.stream_id: str = start_payload["stream_id"]
        self.chunks: asyncio.Queue[Optional[Dict]] = asyncio.Queue()

    def finish(self) -> None:
        """Signal that no more chunks will be produced."""
        self.chunks.put_nowait(None)


class TTSTaskManager:
    """Manages TTS tasks and ensures ordered delivery to frontend while allowing parallel TTS generation"""

    def __init__(self) -> None:
        self.task_list: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
        # Queue to store ordered payloads (complete dicts or _StreamHandles)
        self._payload_queue: asyncio.Queue[Union[Dict, _StreamHandle]] = asyncio.Queue()
        # Task to handle sending payloads in order
        self._sender_task: Optional[asyncio.Task] = None
        # Counter for maintaining order
        self._sequence_counter = 0
        self._next_sequence_to_send = 0

    async def speak(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        websocket_send: WebSocketSend,
    ) -> None:
        """
        Queue a TTS task while maintaining order of delivery.

        Args:
            tts_text: Text to synthesize
            display_text: Text to display in UI
            actions: Live2D model actions
            live2d_model: Live2D model instance
            tts_engine: TTS engine instance
            websocket_send: WebSocket send function
        """
        if len(re.sub(r'[\s.,!?，。！？\'"』」）】\s]+', "", tts_text)) == 0:
            logger.debug("Empty TTS text, sending silent display payload")
            # Get current sequence number for silent payload
            current_sequence = self._sequence_counter
            self._sequence_counter += 1

            # Start sender task if not running
            if not self._sender_task or self._sender_task.done():
                self._sender_task = asyncio.create_task(
                    self._process_payload_queue(websocket_send)
                )

            await self._send_silent_payload(display_text, actions, current_sequence)
            return

        logger.debug(
            f"🏃Queuing TTS task for: '''{tts_text}''' (by {display_text.name})"
        )

        # Get current sequence number
        current_sequence = self._sequence_counter
        self._sequence_counter += 1

        # Start sender task if not running
        if not self._sender_task or self._sender_task.done():
            self._sender_task = asyncio.create_task(
                self._process_payload_queue(websocket_send)
            )

        # Create and queue the TTS task
        task = asyncio.create_task(
            self._process_tts(
                tts_text=tts_text,
                display_text=display_text,
                actions=actions,
                live2d_model=live2d_model,
                tts_engine=tts_engine,
                sequence_number=current_sequence,
            )
        )
        self.task_list.append(task)

    async def _process_payload_queue(self, websocket_send: WebSocketSend) -> None:
        """
        Process and send payloads in correct order.
        Runs continuously until all payloads are processed.
        """
        buffered_payloads: Dict[int, Union[Dict, _StreamHandle]] = {}

        while True:
            try:
                # Get payload from queue
                payload, sequence_number = await self._payload_queue.get()
                buffered_payloads[sequence_number] = payload

                # Send payloads in order
                while self._next_sequence_to_send in buffered_payloads:
                    next_payload = buffered_payloads.pop(self._next_sequence_to_send)
                    if isinstance(next_payload, _StreamHandle):
                        await self._send_stream(next_payload, websocket_send)
                    else:
                        await websocket_send(json.dumps(next_payload))
                    self._next_sequence_to_send += 1

                self._payload_queue.task_done()

            except asyncio.CancelledError:
                break

    async def _send_stream(
        self, handle: _StreamHandle, websocket_send: WebSocketSend
    ) -> None:
        """
        Send one streamed sentence: start payload, then chunks as they become
        available from the TTS task, then the end payload. Blocks the ordered
        sender until this stream completes, which keeps wire order strictly
        sequential (later sentences keep synthesizing concurrently — their
        chunks simply buffer in their own handles meanwhile).
        """
        await websocket_send(json.dumps(handle.start_payload))
        while True:
            chunk_payload = await handle.chunks.get()
            if chunk_payload is None:
                break
            await websocket_send(json.dumps(chunk_payload))
        await websocket_send(json.dumps(prepare_stream_end_payload(handle.stream_id)))

    async def _send_silent_payload(
        self,
        display_text: DisplayText,
        actions: Optional[Actions],
        sequence_number: int,
    ) -> None:
        """Queue a silent audio payload"""
        audio_payload = prepare_audio_payload(
            audio_path=None,
            display_text=display_text,
            actions=actions,
        )
        await self._payload_queue.put((audio_payload, sequence_number))

    async def _process_tts(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        sequence_number: int,
    ) -> None:
        """Process TTS generation and queue the result for ordered delivery"""
        if callable(getattr(tts_engine, "async_generate_audio_streaming", None)):
            await self._process_tts_streaming(
                tts_text=tts_text,
                display_text=display_text,
                actions=actions,
                tts_engine=tts_engine,
                sequence_number=sequence_number,
            )
            return

        audio_file_path = None
        try:
            audio_file_path = await self._generate_audio(tts_engine, tts_text)
            payload = prepare_audio_payload(
                audio_path=audio_file_path,
                display_text=display_text,
                actions=actions,
            )
            # Queue the payload with its sequence number
            await self._payload_queue.put((payload, sequence_number))

        except Exception as e:
            logger.error(f"Error preparing audio payload: {e}")
            # Queue silent payload for error case
            payload = prepare_audio_payload(
                audio_path=None,
                display_text=display_text,
                actions=actions,
            )
            await self._payload_queue.put((payload, sequence_number))

        finally:
            if audio_file_path:
                tts_engine.remove_file(audio_file_path)
                logger.debug("Audio cache file cleaned.")

    async def _process_tts_streaming(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        tts_engine: TTSInterface,
        sequence_number: int,
    ) -> None:
        """
        Stream TTS audio chunk by chunk instead of waiting for a full file.

        The stream handle is enqueued at this sentence's sequence slot only
        once the first chunk arrives (the sample rate is known then, and the
        subtitle appears when audio is actually ready). If the engine fails
        before producing any audio, fall back to a silent display payload.
        """
        stream_id = str(uuid.uuid4())
        handle: Optional[_StreamHandle] = None
        start_time = time.perf_counter()

        logger.debug(f"🏃Streaming audio for '''{tts_text}'''...")
        try:
            async for chunk in tts_engine.async_generate_audio_streaming(tts_text):
                chunk_payload, sample_rate = prepare_stream_chunk_payload(
                    stream_id, chunk
                )
                if handle is None:
                    logger.debug(
                        f"First TTS chunk after {time.perf_counter() - start_time:.2f}s "
                        f"for '''{tts_text}'''"
                    )
                    start_payload = prepare_stream_start_payload(
                        stream_id=stream_id,
                        sample_rate=sample_rate,
                        display_text=display_text,
                        actions=actions,
                    )
                    handle = _StreamHandle(start_payload)
                    await self._payload_queue.put((handle, sequence_number))
                handle.chunks.put_nowait(chunk_payload)

        except Exception as e:
            logger.error(f"Error streaming TTS audio: {e}")
            if handle is None:
                # Nothing was streamed — show the text silently so the
                # sentence isn't lost and the sequence slot is filled.
                payload = prepare_audio_payload(
                    audio_path=None,
                    display_text=display_text,
                    actions=actions,
                )
                await self._payload_queue.put((payload, sequence_number))
                return

        finally:
            # Always unblock the sender, including on mid-stream errors and
            # task cancellation — otherwise it would wait for chunks forever.
            if handle is not None:
                handle.finish()

    async def _generate_audio(self, tts_engine: TTSInterface, text: str) -> str:
        """Generate audio file from text"""
        logger.debug(f"🏃Generating audio for '''{text}'''...")
        return await tts_engine.async_generate_audio(
            text=text,
            file_name_no_ext=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}",
        )

    def clear(self) -> None:
        """Clear all pending tasks and reset state"""
        # Cancel in-flight TTS tasks before dropping the references —
        # otherwise a task from an interrupted turn keeps running and
        # enqueues its (stale) payload into the replaced queue below,
        # leaking a sentence from the previous turn into the next one.
        for task in self.task_list:
            task.cancel()
        self.task_list.clear()
        if self._sender_task:
            self._sender_task.cancel()
        self._sequence_counter = 0
        self._next_sequence_to_send = 0
        # Create a new queue to clear any pending items
        self._payload_queue = asyncio.Queue()
