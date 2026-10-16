import asyncio
import ssl
import re
import time
from typing import Callable, Optional, Dict, Any, List
from loguru import logger
from .live_interface import LivePlatformInterface

class TwitchLivePlatform(LivePlatformInterface):
    """
    Anonymous zero-cost Twitch Chat listener.
    Connects to Twitch IRC over TLS without requiring API keys or OAuth tokens.
    """
    def __init__(self, channel_name: str, message_cooldown: float = 3.0):
        self.channel_name = channel_name.lower().lstrip('#')
        self.message_cooldown = message_cooldown
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._running = False
        self._last_message_time = 0.0
        self._message_handlers: List[Callable[[Dict[str, Any]], None]] = []

    async def connect(self, proxy_url: str = "") -> bool:
        """Connect to Twitch IRC server."""
        try:
            ssl_context = ssl.create_default_context()
            self._reader, self._writer = await asyncio.open_connection(
                'irc.chat.twitch.tv', 6697, ssl=ssl_context
            )
            # Authenticate with anonymous JustInFan token
            self._writer.write(b"PASS oauth:justinfan12345\r\n")
            self._writer.write(b"NICK justinfan12345\r\n")
            self._writer.write(f"JOIN #{self.channel_name}\r\n".encode('utf-8'))
            await self._writer.drain()

            self._connected = True
            self._running = True
            logger.info(f"Connected to Twitch IRC anonymously. Joined #{self.channel_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Twitch IRC: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        self._running = False
        self._connected = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        logger.info(f"Disconnected from Twitch #{self.channel_name}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def send_message(self, text: str) -> bool:
        # Anonymous users cannot write back to Twitch chat (read-only)
        logger.debug(f"Twitch send_message (read-only mode): {text}")
        return True

    def register_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._message_handlers.append(handler)

    async def start_receiving(self) -> None:
        """Receive and parse Twitch IRC messages."""
        msg_regex = re.compile(r'^:(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)$')

        while self._running and self._reader:
            try:
                line_bytes = await self._reader.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode('utf-8', errors='ignore').strip()

                # Handle PING/PONG keepalive
                if line.startswith('PING'):
                    self._writer.write(b'PONG :tmi.twitch.tv\r\n')
                    await self._writer.drain()
                    continue

                # Match user messages
                match = msg_regex.match(line)
                if match:
                    username, text = match.group(1), match.group(2).strip()

                    # Filter bot commands and system bots
                    if text.startswith('!') or username.lower() in ['nightbot', 'streamlabs', 'streamelements']:
                        continue

                    now = time.time()
                    if now - self._last_message_time >= self.message_cooldown:
                        self._last_message_time = now
                        msg_payload = {
                            "type": "chat_message",
                            "platform": "twitch",
                            "username": username,
                            "message": text,
                            "formatted_prompt": f"[Twitch Viewer @{username}]: {text}"
                        }
                        logger.info(f"[Twitch #{self.channel_name}] @{username}: {text}")
                        for handler in self._message_handlers:
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(msg_payload)
                                else:
                                    handler(msg_payload)
                            except Exception as e:
                                logger.error(f"Error in Twitch message handler: {e}")

            except Exception as e:
                logger.warning(f"Twitch receiver exception: {e}")
                await asyncio.sleep(1.0)

    async def run(self) -> None:
        if await self.connect():
            await self.start_receiving()

    async def handle_incoming_messages(self, message: Dict[str, Any]) -> None:
        pass
