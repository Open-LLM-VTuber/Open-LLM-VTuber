import asyncio
import re
from typing import Optional, Union, Any, List, Dict
import numpy as np
import json
from loguru import logger

from ..message_handler import message_handler
from ..metrics import OUTCOME_COMPLETED, turn_metrics
from .types import WebSocketSend, BroadcastContext
from .tts_manager import TTSTaskManager
from ..agent.output_types import SentenceOutput, AudioOutput
from ..agent.input_types import BatchInput, TextData, ImageData, TextSource, ImageSource
from ..asr.asr_interface import ASRInterface
from ..live2d_model import Live2dModel
from ..tts.tts_interface import TTSInterface
from ..utils.stream_audio import prepare_audio_payload


# --------------------------------------------------------------------------- #
# A22 / §5.3: turn metrics
# --------------------------------------------------------------------------- #
#: Payload types that carry synthesised audio ("time to first audio").
_AUDIO_MESSAGE_TYPES = frozenset({"audio"})


def _decode_message(payload: str) -> Dict[str, Any]:
    """Best-effort decode of an outgoing payload (never raises)."""
    try:
        message = json.loads(payload)
    except (TypeError, ValueError):
        return {}
    return message if isinstance(message, dict) else {}


def instrument_websocket_send(
    websocket_send: WebSocketSend, client_uid: str
) -> WebSocketSend:
    """Wrap ``websocket_send`` so the turn metrics see audio and the turn end.

    Every payload of an individual turn goes through the wrapped sender, which
    is the cheapest place to timestamp "first audio" and "chain end" without
    touching the agent, TTS or proxy code (audit §5.3). Decoding failures are
    swallowed on purpose: telemetry must never be able to abort a turn.
    """

    async def send(payload: str) -> None:
        await websocket_send(payload)

        if not isinstance(payload, str) or '"type"' not in payload:
            return

        message = _decode_message(payload)
        message_type = message.get("type")
        if message_type in _AUDIO_MESSAGE_TYPES:
            turn_metrics.first_audio(client_uid)
        elif (
            message_type == "control"
            and message.get("text") == "conversation-chain-end"
        ):
            turn_metrics.end_turn(client_uid, OUTCOME_COMPLETED)

    return send


# Convert class methods to standalone functions
def create_batch_input(
    input_text: str,
    images: Optional[List[Dict[str, Any]]],
    from_name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> BatchInput:
    """Create batch input for agent processing"""
    return BatchInput(
        texts=[
            TextData(source=TextSource.INPUT, content=input_text, from_name=from_name)
        ],
        images=[
            ImageData(
                source=ImageSource(img["source"]),
                data=img["data"],
                mime_type=img["mime_type"],
            )
            for img in (images or [])
        ]
        if images
        else None,
        metadata=metadata,
    )


async def process_agent_output(
    output: Union[AudioOutput, SentenceOutput],
    character_config: Any,
    live2d_model: Live2dModel,
    tts_engine: TTSInterface,
    websocket_send: WebSocketSend,
    tts_manager: TTSTaskManager,
    translate_engine: Optional[Any] = None,
) -> str:
    """Process agent output with character information and optional translation"""
    output.display_text.name = character_config.character_name
    output.display_text.avatar = character_config.avatar

    full_response = ""
    try:
        if isinstance(output, SentenceOutput):
            full_response = await handle_sentence_output(
                output,
                live2d_model,
                tts_engine,
                websocket_send,
                tts_manager,
                translate_engine,
            )
        elif isinstance(output, AudioOutput):
            full_response = await handle_audio_output(output, websocket_send)
        else:
            logger.warning(f"Unknown output type: {type(output)}")
    except Exception as e:
        logger.error(f"Error processing agent output: {e}")
        await websocket_send(
            json.dumps(
                {"type": "error", "message": f"Error processing response: {str(e)}"}
            )
        )

    return full_response


async def handle_sentence_output(
    output: SentenceOutput,
    live2d_model: Live2dModel,
    tts_engine: TTSInterface,
    websocket_send: WebSocketSend,
    tts_manager: TTSTaskManager,
    translate_engine: Optional[Any] = None,
) -> str:
    """Handle sentence output type with optional translation support"""
    full_response = ""
    async for display_text, tts_text, actions in output:
        logger.debug(f"🏃 Processing output: '''{tts_text}'''...")

        if translate_engine:
            if len(re.sub(r'[\s.,!?，。！？\'"』」）】\s]+', "", tts_text)):
                tts_text = translate_engine.translate(tts_text)
            logger.info(f"🏃 Text after translation: '''{tts_text}'''...")
        else:
            logger.debug("🚫 No translation engine available. Skipping translation.")

        full_response += display_text.text
        await tts_manager.speak(
            tts_text=tts_text,
            display_text=display_text,
            actions=actions,
            live2d_model=live2d_model,
            tts_engine=tts_engine,
            websocket_send=websocket_send,
        )
    return full_response


async def handle_audio_output(
    output: AudioOutput,
    websocket_send: WebSocketSend,
) -> str:
    """Process and send AudioOutput directly to the client"""
    full_response = ""
    async for audio_path, display_text, transcript, actions in output:
        full_response += transcript
        audio_payload = prepare_audio_payload(
            audio_path=audio_path,
            display_text=display_text,
            actions=actions.to_dict() if actions else None,
        )
        await websocket_send(json.dumps(audio_payload))
    return full_response


async def send_conversation_start_signals(websocket_send: WebSocketSend) -> None:
    """Send initial conversation signals"""
    await websocket_send(
        json.dumps(
            {
                "type": "control",
                "text": "conversation-chain-start",
            }
        )
    )
    await websocket_send(json.dumps({"type": "full-text", "text": "Thinking..."}))


async def process_user_input(
    user_input: Union[str, np.ndarray],
    asr_engine: ASRInterface,
    websocket_send: WebSocketSend,
) -> str:
    """Process user input, converting audio to text if needed"""
    if isinstance(user_input, np.ndarray):
        logger.info("Transcribing audio input...")
        input_text = await asr_engine.async_transcribe_np(user_input)
        await websocket_send(
            json.dumps({"type": "user-input-transcription", "text": input_text})
        )
        return input_text
    return user_input


# A18: a turn must always end, even if the overlay never confirms playback.
# Without these timeouts a backgrounded OBS browser source leaves the turn
# hanging forever and the TikTok connector never advances its queue.
PLAYBACK_ACK_TIMEOUT = 180  # s; a long tarot reading fits comfortably
SYNTH_TIMEOUT = 120  # s; if TTS stalls, don't block the turn end


async def finalize_conversation_turn(
    tts_manager: TTSTaskManager,
    websocket_send: WebSocketSend,
    client_uid: str,
    broadcast_ctx: Optional[BroadcastContext] = None,
) -> None:
    """Finalize a conversation turn, always signalling the turn end."""
    try:
        if tts_manager.task_list:
            try:
                # return_exceptions: one failed sentence must not kill the turn
                await asyncio.wait_for(
                    asyncio.gather(*tts_manager.task_list, return_exceptions=True),
                    timeout=SYNTH_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"TTS still running after {SYNTH_TIMEOUT}s; closing the turn anyway"
                )

            await websocket_send(json.dumps({"type": "backend-synth-complete"}))

            response = await message_handler.wait_for_response(
                client_uid,
                "frontend-playback-complete",
                timeout=PLAYBACK_ACK_TIMEOUT,
            )
            if not response:
                logger.warning(
                    f"No playback completion from {client_uid}; closing the turn anyway"
                )
                # NOTE: no early return - the turn must be closed below.

        await websocket_send(json.dumps({"type": "force-new-message"}))

        if broadcast_ctx and broadcast_ctx.broadcast_func:
            await broadcast_ctx.broadcast_func(
                broadcast_ctx.group_members,
                {"type": "force-new-message"},
                broadcast_ctx.current_client_uid,
            )
    finally:
        # Last line of the turn: whatever happened, unblock proxy and connector.
        await send_conversation_end_signal(websocket_send, broadcast_ctx)


async def send_conversation_end_signal(
    websocket_send: WebSocketSend,
    broadcast_ctx: Optional[BroadcastContext],
    session_emoji: str = "😊",
) -> None:
    """Send conversation chain end signal"""
    chain_end_msg = {
        "type": "control",
        "text": "conversation-chain-end",
    }

    await websocket_send(json.dumps(chain_end_msg))

    if broadcast_ctx and broadcast_ctx.broadcast_func and broadcast_ctx.group_members:
        await broadcast_ctx.broadcast_func(
            broadcast_ctx.group_members,
            chain_end_msg,
        )

    logger.info(f"😎👍✅ Conversation Chain {session_emoji} completed!")


#: Text of the frame that tells every overlay to drop its audio queue (A20).
INTERRUPT_SIGNAL_TEXT = "conversation-interrupted"


def build_interrupt_signal() -> Dict[str, str]:
    """Build the ``interrupt-signal`` frame sent when a turn is cancelled.

    Kept next to the other control frames so the payload has a single source of
    truth: ``conversation_handler`` broadcasts it and
    ``scripts/export_overlay_fixtures.py`` exports it to the overlay fixtures.
    """
    return {"type": "interrupt-signal", "text": INTERRUPT_SIGNAL_TEXT}


def cleanup_conversation(tts_manager: TTSTaskManager, session_emoji: str) -> None:
    """Clean up conversation resources"""
    tts_manager.clear()
    logger.debug(f"🧹 Clearing up conversation {session_emoji}.")


EMOJI_LIST = [
    "🐶",
    "🐱",
    "🐭",
    "🐹",
    "🐰",
    "🦊",
    "🐻",
    "🐼",
    "🐨",
    "🐯",
    "🦁",
    "🐮",
    "🐷",
    "🐸",
    "🐵",
    "🐔",
    "🐧",
    "🐦",
    "🐤",
    "🐣",
    "🐥",
    "🦆",
    "🦅",
    "🦉",
    "🦇",
    "🐺",
    "🐗",
    "🐴",
    "🦄",
    "🐝",
    "🌵",
    "🎄",
    "🌲",
    "🌳",
    "🌴",
    "🌱",
    "🌿",
    "☘️",
    "🍀",
    "🍂",
    "🍁",
    "🍄",
    "🌾",
    "💐",
    "🌹",
    "🌸",
    "🌛",
    "🌍",
    "⭐️",
    "🔥",
    "🌈",
    "🌩",
    "⛄️",
    "🎃",
    "🎄",
    "🎉",
    "🎏",
    "🎗",
    "🀄️",
    "🎭",
    "🎨",
    "🧵",
    "🪡",
    "🧶",
    "🥽",
    "🥼",
    "🦺",
    "👔",
    "👕",
    "👜",
    "👑",
]
