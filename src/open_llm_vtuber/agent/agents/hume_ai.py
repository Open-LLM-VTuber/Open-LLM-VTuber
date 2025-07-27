import asyncio
import base64
from typing import AsyncIterator, Optional
import json
import websockets
from loguru import logger
from pathlib import Path

from .agent_interface import AgentInterface
from ..output_types import AudioOutput, Actions, DisplayText
from ..input_types import BatchInput
from ...chat_history_manager import get_metadata, update_metadate


class HumeAIAgent(AgentInterface):
    """
    Hume AI Agent that handles text input and audio output.
    Uses AudioOutput type to provide audio responses with transcripts.
    """

    AGENT_TYPE = "hume_ai_agent"

    def __init__(
        self,
        api_key: str,
        host: str = "api.hume.ai",
        config_id: Optional[str] = None,
        idle_timeout: int = 15,
    ):
        """
        Initialize Hume AI agent

        Args:
            api_key: Hume AI API key
            host: API host
            config_id: Optional configuration ID
            idle_timeout: Connection idle timeout in seconds
        """
        self.api_key = api_key
        self.host = host
        self.config_id = config_id
        self.idle_timeout = idle_timeout
        self._ws = None
        self._current_text = None
        self._current_id = None
        self._connected = False
        self._chat_group_id = None
        self._idle_timer = None
        self._current_conf_uid = None
        self._current_history_uid = None

        # Create cache directory if it doesn't exist
        self.cache_dir = Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)

    async def connect(self, resume_chat_group_id: Optional[str] = None):
        """
        Establish WebSocket connection with optional chat group resumption

        Args:
            resume_chat_group_id: Optional chat group ID to resume
        """
        if self._ws:
            await self._ws.close()
            self._ws = None
            self._connected = False

        # Build URL with query parameters
        socket_url = f"wss://{self.host}/v0/evi/chat?api_key={self.api_key}"

        if self.config_id:
            socket_url += f"&config_id={self.config_id}"

        if resume_chat_group_id:
            logger.info(f"Resuming chat group: {resume_chat_group_id}")
            socket_url += f"&resumed_chat_group_id={resume_chat_group_id}"
            self._chat_group_id = resume_chat_group_id

        logger.info(f"Connecting to EVI with config_id: {self.config_id}")

        self._ws = await websockets.connect(socket_url)
        self._connected = True

        async for message in self._ws:
            data = json.loads(message)
            if data.get("type") == "chat_metadata":
                new_chat_group_id = data.get("chat_group_id")

                if not resume_chat_group_id and self._current_history_uid:
                    update_metadate(
                        self._current_conf_uid,
                        self._current_history_uid,
                        {"resume_id": new_chat_group_id, "agent_type": self.AGENT_TYPE},
                    )

                self._chat_group_id = new_chat_group_id
                logger.info(
                    f"{'Resumed' if resume_chat_group_id else 'Created new'} "
                    f"chat group: {self._chat_group_id}"
                )
                break

    def _reset_idle_timer(self):
        """Reset the idle timer"""
        if self._idle_timer:
            self._idle_timer.cancel()

        async def disconnect_after_timeout():
            await asyncio.sleep(self.idle_timeout)
            if self._ws and self._connected:
                logger.info("Idle timeout reached, disconnecting...")
                await self._ws.close()
                self._connected = False

        self._idle_timer = asyncio.create_task(disconnect_after_timeout())

    async def _ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        if not self._connected or not self._ws or self._ws.closed:
            await self.connect(self._chat_group_id)

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """
        Set chat group ID based on history

        Args:
            conf_uid: Configuration ID
            history_uid: History ID
        """
        self._current_conf_uid = conf_uid
        self._current_history_uid = history_uid

        metadata = get_metadata(conf_uid, history_uid)

        agent_type = metadata.get("agent_type")
        if agent_type and agent_type != self.AGENT_TYPE:
            logger.warning(
                f"Incompatible agent type in history: {agent_type}. "
                f"Expected: {self.AGENT_TYPE} or empty. Memory will not be set."
            )
            self._chat_group_id = None
            return

        resume_id = metadata.get("resume_id")
        if resume_id:
            self._chat_group_id = resume_id
            logger.info(f"Using resume_id from metadata: {resume_id}")
        else:
            self._chat_group_id = None
            logger.info("No resume_id found in metadata, will create new chat group")

        # Force reconnection on next chat
        if self._ws:
            asyncio.create_task(self._ws.close())
            self._connected = False

    async def chat(self, batch_input: BatchInput) -> AsyncIterator[AudioOutput]:
        """
        Chat with Hume AI and get audio response

        Args:
            batch_input: BatchInput containing text and optional media

        Returns:
            AsyncIterator[AudioOutput]: Stream of AudioOutput objects
        """
        try:
            self._reset_idle_timer()
            await self._ensure_connection()

            # Extract main text from BatchInput
            input_text = batch_input.texts[0].content if batch_input.texts else ""

            # Hume AI doesn't support image input, log warning if images present
            if batch_input.images:
                logger.warning(
                    "Hume AI does not support image input. Images will be ignored."
                )

            message = {
                "type": "user_input",
                "text": input_text,
            }
            await self._ws.send(json.dumps(message))

            async for message in self._ws:
                self._reset_idle_timer()
                logger.debug(f"Received message: {message}")
                try:
                    response_data = json.loads(message)
                    msg_type = response_data.get("type")
                    msg_id = response_data.get("id")

                    if msg_type == "assistant_message":
                        self._current_text = response_data["message"]["content"]
                        self._current_id = msg_id

                    elif msg_type == "audio_output":
                        if msg_id == self._current_id and self._current_text:
                            audio_data = base64.b64decode(response_data["data"])
                            cache_file = self.cache_dir / f"evi_audio_{msg_id}.wav"

                            with open(cache_file, "wb") as f:
                                f.write(audio_data)
                                logger.debug(f"Saved audio to cache file: {cache_file}")

                            # Create AudioOutput with DisplayText
                            yield AudioOutput(
                                audio_path=str(cache_file),
                                display_text=DisplayText(text=self._current_text),
                                transcript=self._current_text,
                                actions=Actions(),
                            )

                            self._current_text = None
                            self._current_id = None

                    elif msg_type == "assistant_end":
                        break

                    elif msg_type == "tool_error_message":
                        logger.error(f"Tool error: {response_data.get('error')}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response JSON: {e}")
                    continue

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Connection closed: {e}, attempting to reconnect...")
            self._connected = False
            await self._ensure_connection()
            async for result in self.chat(batch_input):
                yield result

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise

    def handle_interrupt(self, heard_response: str) -> None:
        """Handle user interruption (not implemented for Hume AI)"""
        pass

    def __del__(self):
        """Cleanup WebSocket connection and cache files"""
        if self._idle_timer:
            self._idle_timer.cancel()

        if self._ws:
            self._ws.close()

        # Clean up cache files
        try:
            for file in self.cache_dir.glob("evi_audio_*.wav"):
                file.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up cache files: {e}")
