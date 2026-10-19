import asyncio
import contextlib
import json
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from loguru import logger
import websockets

from .live_interface import LivePlatformInterface

try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, FollowEvent, GiftEvent

    TIKTOKLIVE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TikTokLive import failed: {e}")
    logger.warning("TikTok live functionality will not be available.")
    TIKTOKLIVE_AVAILABLE = False


class TikTokLivePlatform(LivePlatformInterface):
    """
    Implementation of LivePlatformInterface for TikTok Live.

    Forwards comments, gifts and follows to the VTuber proxy. Only one
    conversation runs at a time: the worker sends a ``text-input`` and waits
    for the ``control/conversation-chain-end`` signal before sending the next
    one, so the LLM and the TTS are never overloaded.
    """

    # Priority levels (higher is served first)
    PRIORITY_GIFT = 2
    PRIORITY_QUESTION = 1
    PRIORITY_COMMENT = 0

    # Watchdog: if the turn-end signal never arrives, keep the stream alive
    TURN_TIMEOUT = 90  # seconds

    def __init__(
        self,
        unique_id: str,
        proxy_url: str = "ws://127.0.0.1:12393/proxy-ws",
        max_queue: int = 5,
        cooldown_seconds: float = 6.0,
        min_gift_coins: int = 1,
        reply_to_gifts: bool = True,
        reply_to_follows: bool = True,
    ):
        """
        Initialize the TikTok Live platform client.

        Args:
            unique_id: TikTok username of the account that is live (with or
                without a leading ``@``)
            proxy_url: WebSocket URL of the VTuber proxy
            max_queue: Maximum number of pending events (gifts are dropped last)
            cooldown_seconds: Minimum time between two turns
            min_gift_coins: Gifts cheaper than this are ignored
            reply_to_gifts: React to gifts
            reply_to_follows: Greet new followers
        """
        if not TIKTOKLIVE_AVAILABLE:
            raise ImportError(
                "TikTokLive is required for TikTok live functionality "
                "(pip install 'TikTokLive>=7,<8')"
            )

        self._unique_id = unique_id.lstrip("@").lower()
        self._proxy_url = proxy_url
        self._max_gift_coins = min_gift_coins
        self._reply_to_gifts = reply_to_gifts
        self._reply_to_follows = reply_to_follows
        self._cooldown = max(0.0, cooldown_seconds)
        self._last_reply = 0.0

        self._queues: Dict[int, Deque[str]] = {
            self.PRIORITY_GIFT: deque(),
            self.PRIORITY_QUESTION: deque(),
            self.PRIORITY_COMMENT: deque(),
        }
        self._max_queue = max(1, max_queue)
        self._queued = 0
        self._wakeup = asyncio.Event()  # wakes the worker when something arrives
        self._turn_done = asyncio.Event()
        self._turn_done.set()
        self._connected = False
        self._running = False
        self._websocket = None
        self._client: Optional[Any] = None
        self._handlers: List[Callable[[Dict[str, Any]], None]] = []

    # --- LivePlatformInterface -----------------------------------------
    @property
    def is_connected(self) -> bool:
        """Check if connected to the proxy server."""
        try:
            if self._websocket is None:
                return False
            return self._connected and not self._websocket.closed
        except Exception:
            return False

    async def connect(self, proxy_url: Optional[str] = None) -> bool:
        """Connect to the VTuber proxy WebSocket."""
        try:
            self._websocket = await websockets.connect(
                proxy_url or self._proxy_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            logger.info(f"TikTok connector connected to proxy {self._proxy_url}")
            # The connector never plays audio: ask the proxy to skip it.
            await self._websocket.send(json.dumps({"type": "connector-hello"}))
            return True
        except Exception as e:
            logger.error(f"Failed to connect to proxy: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the proxy server and stop the worker."""
        self._running = False
        self._wakeup.set()  # unblock the worker waiting for events
        self._turn_done.set()  # unblock the worker waiting mid-turn
        if self._websocket is not None:
            with contextlib.suppress(Exception):
                await self._websocket.close()
        self._connected = False

    async def send_message(self, text: str) -> bool:
        """Send a message from the live platform to the VTuber."""
        try:
            if self._websocket is None:
                return False
            await self._websocket.send(json.dumps({"type": "text-input", "text": text}))
            return True
        except Exception as e:
            logger.error(f"Error sending to proxy: {e}")
            self._connected = False
            return False

    async def register_message_handler(
        self, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Register a callback for VTuber responses."""
        self._handlers.append(handler)

    async def handle_incoming_messages(self, message: Dict[str, Any]) -> None:
        """Process one message received from the VTuber server."""
        for handler in self._handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    async def start_receiving(self) -> None:
        """
        Receive messages from the proxy until the connection closes.

        The connector does not need the audio: 5.2.4 makes the proxy skip it,
        and the string check stays as a fallback if that patch is missing.
        """
        try:
            async for raw in self._websocket:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="ignore")
                if '"audio"' in raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if (
                    data.get("type") == "control"
                    and data.get("text") == "conversation-chain-end"
                ):
                    self._turn_done.set()
                await self.handle_incoming_messages(data)
        except websockets.ConnectionClosed:
            logger.warning("Proxy WebSocket closed; the launcher will restart")
        finally:
            self._connected = False
            self._turn_done.set()

    async def run(self) -> None:
        """Run the connector: proxy WS plus TikTok stream, one turn at a time."""
        self._running = True
        if not await self.connect():
            return

        self._client = TikTokLiveClient(unique_id=f"@{self._unique_id}")
        client = self._client

        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent) -> None:
            # TikTokLive 7.x exposes `content`; `comment` is its legacy alias.
            raw = getattr(event, "content", None) or getattr(event, "comment", "") or ""
            text = " ".join(raw.split())[:200]
            if text:
                level = (
                    self.PRIORITY_QUESTION
                    if "?" in text or "¿" in text
                    else self.PRIORITY_COMMENT
                )
                self._enqueue(f'{self._username(event)} dice: "{text}"', level)

        @client.on(GiftEvent)
        async def on_gift(event: GiftEvent) -> None:
            if not self._reply_to_gifts:
                return
            if getattr(event, "streaking", False):  # gift streak: wait for its end
                return
            gift = getattr(event, "gift", None)
            if gift is None:
                return
            coins = getattr(gift, "diamond_count", None)
            # If this version does not expose the price, do not filter by value.
            if coins is not None and coins < self._max_gift_coins:
                return
            gift_name = getattr(gift, "name", None) or "un regalo"
            count = getattr(event, "repeat_count", 1) or 1
            self._enqueue(
                f"{self._username(event)} te envió {gift_name} x{count}. "
                "Dale las gracias en una frase y sigue con la lectura.",
                self.PRIORITY_GIFT,
            )

        @client.on(FollowEvent)
        async def on_follow(event: FollowEvent) -> None:
            if self._reply_to_follows:
                self._enqueue(
                    f"{self._username(event)} acaba de seguirte. Salúdale.",
                    self.PRIORITY_GIFT,
                )

        receive_task = asyncio.create_task(self.start_receiving())
        worker_task = asyncio.create_task(self._worker())
        try:
            # `client.connect()` blocks until the stream ends; `start()` (7.x)
            # connects and returns the stream task so the proxy WS runs in parallel.
            stream_task = await client.start()

            # The connector lives while both the proxy and the stream are alive;
            # if either ends, run() returns and the launcher restarts it.
            await asyncio.wait(
                {receive_task, stream_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if stream_task.done() and not stream_task.cancelled():
                exc = stream_task.exception()
                if exc is not None:
                    logger.error(f"TikTokLive ended with an error: {exc!r}")
                    raise exc  # let the launcher restart the connector
        finally:
            worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker_task
            if not receive_task.done():
                receive_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await receive_task
            with contextlib.suppress(Exception):
                await client.disconnect(close_client=True)  # TikTok WS + HTTP
            await self.disconnect()

    # --- Helpers --------------------------------------------------------
    @staticmethod
    def _username(event: Any) -> str:
        """Return the viewer's unique_id, tolerating missing user data."""
        user = getattr(event, "user", None)
        unique_id = getattr(user, "unique_id", None) if user is not None else None
        return unique_id or "alguien"

    # --- One-turn-at-a-time queue, with priority -----------------------
    def _enqueue(self, text: str, level: int = PRIORITY_COMMENT) -> None:
        """Queue an event. Synchronous: TikTokLive handlers must not block."""
        if self._queued >= self._max_queue:
            # Drop the oldest item of the lowest non-empty level, so a gift is
            # only dropped when the queue is full of gifts.
            for candidate in (
                self.PRIORITY_COMMENT,
                self.PRIORITY_QUESTION,
                self.PRIORITY_GIFT,
            ):
                if self._queues[candidate]:
                    dropped = self._queues[candidate].popleft()
                    self._queued -= 1
                    logger.warning(f"Queue full: dropped «{dropped[:60]}»")
                    break
        self._queues[level].append(text)
        self._queued += 1
        self._wakeup.set()

    def _next(self) -> Optional[str]:
        for level in (self.PRIORITY_GIFT, self.PRIORITY_QUESTION, self.PRIORITY_COMMENT):
            if self._queues[level]:
                self._queued -= 1
                return self._queues[level].popleft()
        return None

    async def _worker(self) -> None:
        """Send queued events one turn at a time, honouring the cooldown."""
        while self._running:
            text = self._next()
            if text is None:
                self._wakeup.clear()
                # Timeout so disconnect() can end the worker.
                try:
                    await asyncio.wait_for(self._wakeup.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                continue
            # Minimum rhythm between turns without dropping the message.
            wait = self._cooldown - (time.monotonic() - self._last_reply)
            if wait > 0:
                await asyncio.sleep(wait)
            self._turn_done.clear()
            sent = await self.send_message(text)
            self._last_reply = time.monotonic()
            if not sent:
                logger.warning("Turn not delivered to the proxy; skipping its wait")
                continue
            try:
                await asyncio.wait_for(self._turn_done.wait(), timeout=self.TURN_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning(
                    "Turn without 'conversation-chain-end'; continuing anyway"
                )
                self._turn_done.set()
            await asyncio.sleep(0.5)
