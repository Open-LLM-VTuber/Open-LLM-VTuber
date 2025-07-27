import asyncio
import http.cookies
import random
import traceback
import json
from typing import Callable, Dict, Any, List, Optional
from loguru import logger
import aiohttp
import websockets
import sys
import os

from .live_interface import LivePlatformInterface

# Import the blivedm library
try:
    # Add project root to path to enable imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

    sys.path.insert(0, os.path.join(project_root, "blivedm"))

    import blivedm
    from blivedm.models import web as web_models
    from blivedm.handlers import BaseHandler

    BLIVEDM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"blivedm import failed: {e}")
    logger.warning("BiliBili live functionality will not be available.")
    BLIVEDM_AVAILABLE = False


class BiliBiliLivePlatform(LivePlatformInterface):
    """
    Implementation of LivePlatformInterface for BiliBili Live platform.
    Connects to a BiliBili live room and forwards danmaku messages to the VTuber.
    """

    def __init__(self, room_ids: List[int], sessdata: str = ""):
        """
        Initialize the BiliBili Live platform client.

        Args:
            room_ids: List of room IDs to monitor
            sessdata: Optional SESSDATA cookie value for authentication
        """
        if not BLIVEDM_AVAILABLE:
            raise ImportError(
                "blivedm library is required for BiliBili live functionality"
            )

        self._room_ids = room_ids
        self._sessdata = sessdata
        self._session: Optional[aiohttp.ClientSession] = None
        self._client: Optional[blivedm.BLiveClient] = None
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._running = False
        self._message_handlers: List[Callable[[Dict[str, Any]], None]] = []
        self._conversation_active = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to the proxy server."""
        try:
            if hasattr(self._websocket, "closed"):
                return (
                    self._connected and self._websocket and not self._websocket.closed
                )
            elif hasattr(self._websocket, "open"):
                return self._connected and self._websocket and self._websocket.open
            else:
                return self._connected and self._websocket is not None
        except Exception:
            return False

    def _init_session(self):
        """Initialize HTTP session with cookies if provided."""
        cookies = http.cookies.SimpleCookie()
        if self._sessdata:
            cookies["SESSDATA"] = self._sessdata
            cookies["SESSDATA"]["domain"] = "bilibili.com"

        self._session = aiohttp.ClientSession()
        self._session.cookie_jar.update_cookies(cookies)

    async def connect(self, proxy_url: str) -> bool:
        """
        Connect to the proxy WebSocket server.

        Args:
            proxy_url: The WebSocket URL of the proxy

        Returns:
            bool: True if connection successful
        """
        try:
            # Connect to the proxy WebSocket
            self._websocket = await websockets.connect(
                proxy_url, ping_interval=20, ping_timeout=10, close_timeout=5
            )
            self._connected = True
            logger.info(f"Connected to proxy at {proxy_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to proxy: {e}")
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from the proxy server and stop the BiliBili client.
        """
        self._running = False

        # Stop BiliBili client if running
        if self._client:
            try:
                await self._client.stop_and_close()
                self._client = None
            except Exception as e:
                logger.warning(f"Error while stopping BiliBili client: {e}")

        # Close WebSocket connection
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error while closing WebSocket: {e}")

        # Close HTTP session
        if self._session:
            try:
                await self._session.close()
                self._session = None
            except Exception as e:
                logger.warning(f"Error while closing HTTP session: {e}")

        self._connected = False
        logger.info("Disconnected from BiliBili Live and proxy server")

    async def send_message(self, text: str) -> bool:
        """
        Send a text message to the VTuber through the proxy.
        Not used for BiliBili Live as we only receive messages, not send them.

        Args:
            text: The message text

        Returns:
            bool: True if sent successfully
        """
        # BiliBili Live platform only receives messages, doesn't send them back to the live room
        logger.warning(
            "BiliBili Live platform doesn't support sending messages back to the live room"
        )
        return False

    async def register_message_handler(
        self, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a callback for handling incoming messages.

        Args:
            handler: Function to call when a message is received
        """
        self._message_handlers.append(handler)
        logger.debug("Registered new message handler")

    async def _handle_danmaku(self, danmaku_text: str):
        """
        Process received danmaku message and forward it to VTuber.

        Args:
            danmaku_text: The danmaku text received from BiliBili
        """
        try:
            # Send danmaku directly to proxy
            await self._send_to_proxy(danmaku_text)
        except Exception as e:
            logger.error(f"Error forwarding danmaku to proxy: {e}")

    async def _send_to_proxy(self, text: str) -> bool:
        """
        Send danmaku text to the proxy.

        Args:
            text: The danmaku text to send

        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected:
            logger.error("Cannot send message: Not connected to proxy")
            return False

        try:
            message = {"type": "text-input", "text": text}
            await self._websocket.send(json.dumps(message))
            logger.info(f"Sent danmaku to VTuber: {text}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to proxy: {e}")
            self._connected = False
            return False

    async def start_receiving(self) -> None:
        """
        Start receiving messages from the proxy WebSocket.
        This runs in the background to receive messages from the VTuber.
        """
        if not self.is_connected:
            logger.error("Cannot start receiving: Not connected to proxy")
            return

        try:
            logger.info("Started receiving messages from proxy")
            while self._running and self.is_connected:
                try:
                    message = await self._websocket.recv()
                    data = json.loads(message)

                    # Log received message (truncate audio data for readability)
                    if "audio" in data:
                        log_data = data.copy()
                        log_data["audio"] = (
                            f"[Audio data, length: {len(data['audio'])}]"
                        )
                        logger.debug(f"Received message from VTuber: {log_data}")
                    else:
                        logger.debug(f"Received message from VTuber: {data}")

                    # Process the message
                    await self.handle_incoming_messages(data)

                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed by server")
                    self._connected = False
                    break
                except Exception as e:
                    logger.error(f"Error receiving message from proxy: {e}")
                    await asyncio.sleep(1)

            logger.info("Stopped receiving messages from proxy")
        except Exception as e:
            logger.error(f"Error in message receiving loop: {e}")

    async def handle_incoming_messages(self, message: Dict[str, Any]) -> None:
        """
        Process messages received from the VTuber.

        Args:
            message: The message received from the VTuber
        """
        # Process the message with all registered handlers
        for handler in self._message_handlers:
            try:
                await asyncio.to_thread(handler, message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    class VtuberHandler(BaseHandler):
        """
        Handler for BiliBili Live danmaku messages.
        """

        def __init__(self, platform):
            super().__init__()
            self.platform = platform

        def _on_danmaku(
            self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage
        ):
            """
            Handle danmaku message from BiliBili Live.

            Args:
                client: The BiliBili Live client
                message: The danmaku message
            """
            logger.debug(f"[Room {client.room_id}] {message.uname}: {message.msg}")
            asyncio.create_task(self.platform._handle_danmaku(message.msg))

        def _on_heartbeat(
            self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage
        ):
            """
            Handle heartbeat packet from BiliBili Live.

            Args:
                client: The BiliBili Live client
                message: The heartbeat message
            """
            logger.debug(
                f"[Room {client.room_id}] Heartbeat, popularity: {message.popularity}"
            )

    async def run(self) -> None:
        """
        Main entry point for running the BiliBili Live platform client.
        Connects to BiliBili Live rooms and the proxy, and starts monitoring danmaku.
        """
        proxy_url = "ws://localhost:12393/proxy-ws"

        try:
            self._running = True

            # Initialize HTTP session
            self._init_session()

            # Connect to the proxy
            if not await self.connect(proxy_url):
                logger.error("Failed to connect to proxy, exiting")
                return

            # Start background task for receiving messages from the proxy
            receive_task = asyncio.create_task(self.start_receiving())

            # Randomly select a room ID if multiple are provided
            room_id = random.choice(self._room_ids)

            # Create and start the BiliBili Live client
            self._client = blivedm.BLiveClient(room_id, session=self._session)
            handler = self.VtuberHandler(self)
            self._client.set_handler(handler)
            self._client.start()

            logger.info(f"Connected to BiliBili Live room {room_id}")

            # Wait until stopped
            try:
                await self._client.join()
            finally:
                await self._client.stop_and_close()

            # Clean up receive task if necessary
            if not receive_task.done():
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Error in BiliBili Live run loop: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Ensure clean disconnect
            await self.disconnect()
