"""Minimal OBS Studio WebSocket v5 client (scene switching + stream control).

``websockets`` is already a project dependency, so the client speaks the OBS
protocol directly instead of adding ``obsws-python``: a new dependency would
require regenerating ``uv.lock`` and break the ``uv sync --frozen`` Docker
build.

Only what the show needs is implemented: switch the program scene, start/stop
the stream and list the scenes for the startup log. Every public method is
failure-tolerant -- a closed OBS instance must never take the show down.
"""

import asyncio
import base64
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional

import websockets
from loguru import logger
from websockets.exceptions import ConnectionClosed

OP_HELLO = 0
OP_IDENTIFY = 1
OP_IDENTIFIED = 2
OP_REQUEST = 6
OP_REQUEST_RESPONSE = 7
RPC_VERSION = 1


class OBSProtocolError(Exception):
    """The peer did not speak the OBS WebSocket v5 protocol."""


class OBSAuthError(OBSProtocolError):
    """OBS requires a password, or the configured one is wrong."""


class OBSRequestError(Exception):
    """OBS answered a request with ``requestStatus.result == false``."""


def build_auth_string(password: str, salt: str, challenge: str) -> str:
    """Return the ``authentication`` value expected by OBS v5.

    OBS documents the algorithm as::

        secret = base64(sha256(password + salt))
        auth   = base64(sha256(secret + challenge))
    """
    secret = base64.b64encode(
        hashlib.sha256((password + salt).encode("utf-8")).digest()
    )
    return base64.b64encode(
        hashlib.sha256(secret + challenge.encode("utf-8")).digest()
    ).decode("ascii")


class OBSController:
    """Async OBS WebSocket v5 client with reconnect-on-demand."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4455,
        password: str = "",
        timeout: float = 3.0,
    ):
        """Store the connection settings; nothing is opened until ``connect``."""
        self._url = f"ws://{host}:{port}"
        self._host = host
        self._port = port
        self._password = password or ""
        self._timeout = max(0.5, float(timeout))
        self._ws: Optional[Any] = None
        self._connected = False

    @property
    def connected(self) -> bool:
        """True once OBS accepted the Identify message."""
        return self._connected

    async def connect(self) -> bool:
        """Open the socket and identify. Returns False instead of raising."""
        await self.close()
        try:
            self._ws = await websockets.connect(
                self._url,
                open_timeout=self._timeout,
                close_timeout=2,
            )
            hello = await self._recv()
            if hello.get("op") != OP_HELLO:
                raise OBSProtocolError(f"expected Hello, got {hello!r}")

            data = hello.get("d") or {}
            identify: Dict[str, Any] = {
                "rpcVersion": RPC_VERSION,
                # No events: the client only needs request/response pairs.
                "eventSubscriptions": 0,
            }
            auth = data.get("authentication")
            if auth:
                if not self._password:
                    raise OBSAuthError(
                        "OBS requires a password; set scheduler_config.obs.password"
                    )
                identify["authentication"] = build_auth_string(
                    self._password,
                    str(auth.get("salt", "")),
                    str(auth.get("challenge", "")),
                )

            await self._ws.send(json.dumps({"op": OP_IDENTIFY, "d": identify}))
            reply = await self._recv()
            if reply.get("op") != OP_IDENTIFIED:
                raise OBSAuthError(
                    f"OBS rejected the Identify message (wrong password?): {reply!r}"
                )

            self._connected = True
            logger.info(
                f"OBS connected at {self._url} "
                f"(obs-websocket {data.get('obsWebSocketVersion', '?')})"
            )
            return True

        except Exception as e:  # OBS down/misconfigured must not crash startup
            logger.warning(f"OBS connection to {self._url} failed: {e}")
            await self.close()
            return False

    async def _recv(self) -> Dict[str, Any]:
        """Receive one JSON message, honouring the configured timeout."""
        if self._ws is None:
            raise OBSProtocolError("not connected")
        raw = await asyncio.wait_for(self._ws.recv(), timeout=self._timeout)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise OBSProtocolError("expected a JSON object")
        return message

    async def _send_request(
        self, request_type: str, request_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send one request and wait for its matching response."""
        if self._ws is None:
            raise OBSProtocolError("not connected")

        request_id = uuid.uuid4().hex
        await self._ws.send(
            json.dumps(
                {
                    "op": OP_REQUEST,
                    "d": {
                        "requestType": request_type,
                        "requestId": request_id,
                        "requestData": request_data or {},
                    },
                }
            )
        )

        while True:
            reply = await self._recv()
            if reply.get("op") != OP_REQUEST_RESPONSE:
                continue
            data = reply.get("d") or {}
            if data.get("requestId") != request_id:
                continue
            status = data.get("requestStatus") or {}
            if not status.get("result"):
                raise OBSRequestError(
                    f"{request_type} failed (code {status.get('code')}): "
                    f"{status.get('comment', '')}".rstrip()
                )
            return data.get("responseData") or {}

    async def _request(
        self, request_type: str, request_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a request, reconnecting once if OBS dropped the socket."""
        for attempt in (1, 2):
            if not self._connected or self._ws is None:
                if not await self.connect():
                    raise OBSRequestError(f"not connected to {self._url}")
            try:
                return await self._send_request(request_type, request_data)
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                await self.close()
                if attempt == 2:
                    raise OBSRequestError(
                        f"{request_type} lost the connection: {e}"
                    ) from e
                logger.info(f"OBS connection lost during {request_type}; reconnecting")

        raise OBSRequestError(f"{request_type} failed")  # unreachable, typing guard

    # --------------------------------------------------------------- actions
    async def set_scene(self, scene_name: str) -> bool:
        """Switch the program scene. Returns False when OBS rejects it."""
        if not scene_name:
            return False
        try:
            await self._request("SetCurrentProgramScene", {"sceneName": scene_name})
            logger.info(f"OBS scene switched to '{scene_name}'")
            return True
        except OBSRequestError as e:
            logger.warning(f"OBS could not switch to scene '{scene_name}': {e}")
            return False

    async def start_stream(self) -> bool:
        """Start the OBS stream (logs a warning when already streaming)."""
        try:
            await self._request("StartStream")
            logger.info("OBS stream started")
            return True
        except OBSRequestError as e:
            logger.warning(f"OBS could not start the stream: {e}")
            return False

    async def stop_stream(self) -> bool:
        """Stop the OBS stream."""
        try:
            await self._request("StopStream")
            logger.info("OBS stream stopped")
            return True
        except OBSRequestError as e:
            logger.warning(f"OBS could not stop the stream: {e}")
            return False

    async def list_scenes(self) -> List[str]:
        """Return the scene names, for the startup log and manual checks."""
        try:
            data = await self._request("GetSceneList")
        except OBSRequestError as e:
            logger.warning(f"OBS could not list the scenes: {e}")
            return []

        scenes = data.get("scenes") or []
        return [
            str(scene.get("sceneName"))
            for scene in scenes
            if isinstance(scene, dict) and scene.get("sceneName")
        ]

    async def close(self) -> None:
        """Close the socket; safe to call when never connected."""
        ws, self._ws = self._ws, None
        self._connected = False
        if ws is None:
            return
        try:
            await ws.close()
        except Exception as e:
            logger.debug(f"OBS socket already closed: {e}")
