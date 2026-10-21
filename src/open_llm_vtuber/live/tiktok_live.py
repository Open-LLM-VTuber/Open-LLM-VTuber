import asyncio
import contextlib
import json
import os
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from loguru import logger
import websockets

from .live_interface import LivePlatformInterface
from ..utils.donations import (
    PendingDonors,
    build_donor_draw_payload,
    build_gift_thanks,
)
from ..utils.tarot_commands import is_tarot_command

try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, FollowEvent, GiftEvent

    TIKTOKLIVE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TikTokLive import failed: {e}")
    logger.warning("TikTok live functionality will not be available.")
    TIKTOKLIVE_AVAILABLE = False


def _env_client_options() -> Dict[str, Any]:
    """Optional TikTokLive knobs, taken from the environment.

    TikTokLive 7 has no ``region`` argument: it picks a random browser
    location preset at import time and delegates the signed WebSocket to Euler
    Stream. These variables (all optional, read on every connector restart)
    cover the cases a room abroad needs:

    * ``TIKTOKLIVE_REGION``: ISO country code (``FR``) sent as ``region`` and
      ``priority_region`` in the webcast parameters.
    * ``TIKTOKLIVE_SIGN_API_KEY``: Euler Stream key; raises the free signing
      rate limit (HTTP 429) that otherwise blocks reconnects.
    * ``TIKTOKLIVE_PROXY``: HTTP/SOCKS proxy URL used for both the HTTP and the
      WebSocket leg, e.g. ``http://user:pass@eu-proxy:3128``.

    Returns:
        dict: Keyword arguments for ``TikTokLiveClient`` (empty by default).
    """

    options: Dict[str, Any] = {}

    def warn(name: str, error: Exception) -> None:
        logger.warning(f"{name} ignored: {error}")

    region = os.environ.get("TIKTOKLIVE_REGION", "").strip().upper()
    if region:
        try:
            from TikTokLive.client.web.web_settings import WebDefaults

            WebDefaults.web_client_params["region"] = region
            WebDefaults.web_client_params["priority_region"] = region
            logger.info(f"TikTokLive webcast region forced to {region}")
        except Exception as e:  # pragma: no cover - depends on the library
            warn("TIKTOKLIVE_REGION", e)

    sign_key = os.environ.get("TIKTOKLIVE_SIGN_API_KEY", "").strip()
    if sign_key:
        try:
            from TikTokLive.client.web.web_settings import WebDefaults

            WebDefaults.tiktok_sign_api_key = sign_key
            logger.info("TikTokLive signing API key configured")
        except Exception as e:  # pragma: no cover - depends on the library
            warn("TIKTOKLIVE_SIGN_API_KEY", e)

    proxy_url = os.environ.get("TIKTOKLIVE_PROXY", "").strip()
    if proxy_url:
        try:
            import httpx

            proxy = httpx.Proxy(proxy_url)
            options["web_proxy"] = proxy
            options["ws_proxy"] = proxy
            logger.info("TikTokLive will use the configured proxy")
        except Exception as e:
            warn("TIKTOKLIVE_PROXY", e)

    return options


class TikTokLivePlatform(LivePlatformInterface):
    """
    Implementation of LivePlatformInterface for TikTok Live.

    Forwards comments, gifts and follows to the VTuber proxy. Only one
    conversation runs at a time: the worker sends a frame and waits for the
    ``control/conversation-chain-end`` signal before sending the next one, so
    the LLM and the TTS are never overloaded.

    A gift is answered in two steps: the connector thanks the donor and asks
    what they need, remembers the donor for ten minutes, and turns that donor's
    next comment into a ``tarot-draw`` frame addressed to them.
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
        gift_reading: bool = True,
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
            gift_reading: Ask the donor what they need and read the cards for
                them; ``False`` only thanks the donor
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
        self._gift_reading = gift_reading
        self._cooldown = max(0.0, cooldown_seconds)
        self._last_reply = 0.0

        self._queues: Dict[int, Deque[Dict[str, Any]]] = {
            self.PRIORITY_GIFT: deque(),
            self.PRIORITY_QUESTION: deque(),
            self.PRIORITY_COMMENT: deque(),
        }
        # Donors who were asked "what do you need?" and still owe the answer.
        self._donors = PendingDonors()
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
        return await self.send_payload({"type": "text-input", "text": text})

    async def send_payload(self, payload: Dict[str, Any]) -> bool:
        """Send a ready-made frame to the proxy (``text-input``, ``tarot-draw``)."""
        try:
            if self._websocket is None:
                return False
            await self._websocket.send(json.dumps(payload))
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

        # Region / signing key / proxy are optional and come from the env
        # (see _env_client_options). Without them the defaults are unchanged.
        self._client = TikTokLiveClient(
            unique_id=f"@{self._unique_id}", **_env_client_options()
        )
        client = self._client

        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent) -> None:
            # TikTokLive 7.x exposes `content`; `comment` is its legacy alias.
            raw = getattr(event, "content", None) or getattr(event, "comment", "") or ""
            text = " ".join(raw.split())[:200]
            if not text:
                return

            username = self._username(event)
            donor = self._donors.consume(username)
            if donor is not None:
                # The donor is answering "what do you need?": draw for them and
                # let the server address the reading to their name.
                logger.info(f"Donor {username} asks for a reading: {text[:60]}")
                self._enqueue(
                    build_donor_draw_payload(username, text),
                    self.PRIORITY_GIFT,
                )
                return

            level = (
                self.PRIORITY_QUESTION
                if is_tarot_command(text) or "?" in text or "¿" in text
                else self.PRIORITY_COMMENT
            )
            self._enqueue(
                {"type": "text-input", "text": f'{username} dice: "{text}"'},
                level,
            )

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
            username = self._username(event)

            if self._gift_reading:
                # Thank the donor and ask what they need; the reading comes
                # when they answer, so it is about *their* question (audit §4.6).
                self._donors.remember(username, gift=gift_name, coins=coins or 0)
                text = build_gift_thanks(username, gift_name, count, coins or 0)
            else:
                # gift_reading is off: only thank, nothing is armed, so a later
                # comment from this donor is a normal comment.
                text = build_gift_thanks(
                    username, gift_name, count, coins or 0, ask_question=False
                )

            self._enqueue({"type": "text-input", "text": text}, self.PRIORITY_GIFT)

        @client.on(FollowEvent)
        async def on_follow(event: FollowEvent) -> None:
            if self._reply_to_follows:
                self._enqueue(
                    {
                        "type": "text-input",
                        "text": f"{self._username(event)} acaba de seguirte. Salúdale.",
                    },
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
    @staticmethod
    def _describe(payload: Dict[str, Any]) -> str:
        """Short label for logs: the text if there is one, else the frame type."""
        text = payload.get("text")
        if isinstance(text, str) and text:
            return text[:60]
        return str(payload.get("type", "frame"))

    def _enqueue(self, payload: Dict[str, Any], level: int = PRIORITY_COMMENT) -> None:
        """Queue an event. Synchronous: TikTokLive handlers must not block.

        The queue stores whole frames, because a donor's answer is not a
        ``text-input``: it is a ``tarot-draw`` that the server turns into cards
        plus a reading.
        """
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
                    logger.warning(f"Queue full: dropped «{self._describe(dropped)}»")
                    break
        self._queues[level].append(payload)
        self._queued += 1
        self._wakeup.set()

    def _next(self) -> Optional[Dict[str, Any]]:
        for level in (
            self.PRIORITY_GIFT,
            self.PRIORITY_QUESTION,
            self.PRIORITY_COMMENT,
        ):
            if self._queues[level]:
                self._queued -= 1
                return self._queues[level].popleft()
        return None

    async def _worker(self) -> None:
        """Send queued events one turn at a time, honouring the cooldown."""
        while self._running:
            payload = self._next()
            if payload is None:
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
            sent = await self.send_payload(payload)
            self._last_reply = time.monotonic()
            if not sent:
                logger.warning("Turn not delivered to the proxy; skipping its wait")
                continue
            try:
                await asyncio.wait_for(
                    self._turn_done.wait(), timeout=self.TURN_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Turn without 'conversation-chain-end'; continuing anyway"
                )
                self._turn_done.set()
            await asyncio.sleep(0.5)
