"""End-to-end smoke test for the live pipeline (no browser needed).

It plays the role of the OBS overlay and of the live connector at the same
time, so it exercises the real chain: text-input -> LLM -> TTS -> audio ->
playback ack -> turn end.  Use it before every show and after any change in
the conversation code.

Usage::

    uv run python scripts/smoke_test.py
    uv run python scripts/smoke_test.py --url http://127.0.0.1:12393 \
        --text "Di hola en una frase."

Exit code 0 means the pipeline answered with audio and closed the turn.

Notes:
    * It connects to ``/proxy-ws`` (not ``/client-ws``) because that is the
      socket the overlay uses during a show (audit A1).
    * It *must* answer ``frontend-playback-complete``; without that ack the
      backend waits ``PLAYBACK_ACK_TIMEOUT`` before closing the turn.
"""

import argparse
import asyncio
import base64
import json
import os
import sys
from typing import Optional
from urllib.parse import quote

import httpx
import websockets

#: Shared handshake token (audit A22); unset means the local show has no auth.
TOKEN_ENV = "VTUBER_WS_TOKEN"


def _with_token(url: str, token: Optional[str]) -> str:
    """Append ``?token=`` to a WebSocket/HTTP URL (no-op without a token).

    Mirrors ``security.with_token``; kept local so the smoke test stays a
    standalone script that runs without the service package importable.
    """
    if not token:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}token={quote(token, safe='')}"


class Result:
    def __init__(self) -> None:
        self.audio_chunks = 0
        self.audio_bytes = 0
        self.texts: list[str] = []
        self.turn_started = False
        self.turn_ended = False
        self.acked = 0
        self.error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.audio_bytes > 0 and self.turn_ended and not self.error


def _audio_size(payload: str) -> int:
    """Decoded size of a base64 payload; 0 if it is not valid base64."""
    try:
        return len(base64.b64decode(payload, validate=False))
    except Exception:
        return 0


async def _overlay(ws_url: str, result: Result, ready: asyncio.Event) -> None:
    """Connected client that consumes audio and confirms playback."""
    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
        ready.set()
        while not result.turn_ended:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")
            if msg_type == "audio":
                result.audio_chunks += 1
                result.audio_bytes += _audio_size(message.get("audio", ""))
                text = message.get("display_text")
                if text:
                    # ``display_text`` is a dict (name/text/emotion), but older
                    # backends send a plain string; accept both.
                    if isinstance(text, dict):
                        text = text.get("text") or json.dumps(text, ensure_ascii=False)
                    result.texts.append(str(text))
            elif msg_type == "control":
                text = message.get("text")
                if text == "conversation-chain-start":
                    result.turn_started = True
                elif text == "conversation-chain-end":
                    result.turn_ended = True
            elif msg_type == "backend-synth-complete":
                # This is what use-audio-task.ts does once the queue drains
                await ws.send(json.dumps({"type": "frontend-playback-complete"}))
                result.acked += 1
            elif msg_type == "error":
                result.error = message.get("message", "unknown backend error")
                result.turn_ended = True


async def _sender(ws_url: str, text: str, result: Result) -> None:
    """Connected client that injects one text turn, like the live connector."""
    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
        # Give the proxy a moment to forward the init config
        await asyncio.sleep(0.5)
        await ws.send(json.dumps({"type": "text-input", "text": text}))
        # Keep the socket open; closing it would drop the turn
        while not result.turn_ended:
            await asyncio.sleep(0.2)


async def run(
    url: str, text: str, timeout: float, token: Optional[str] = None
) -> Result:
    base = url.rstrip("/")
    ws_url = base.replace("http://", "ws://").replace("https://", "wss://")
    proxy_url = _with_token(f"{ws_url}/proxy-ws", token)
    result = Result()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base}/")
    except Exception as e:
        result.error = f"server unreachable at {base}: {type(e).__name__}"
        return result
    if response.status_code != 200:
        result.error = f"GET / returned {response.status_code}"
        return result
    print(f"ok  web {base}/ -> 200")

    ready = asyncio.Event()
    tasks = [
        asyncio.create_task(_overlay(proxy_url, result, ready)),
        asyncio.create_task(_sender(proxy_url, text, result)),
    ]
    try:
        await asyncio.wait_for(ready.wait(), timeout=10)
        print("ok  overlay connected to /proxy-ws")
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
    except asyncio.TimeoutError:
        result.error = result.error or f"no turn end within {timeout:.0f}s"
    except Exception as e:  # connection refused, TLS error, ...
        result.error = result.error or f"{type(e).__name__}: {e}"
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    return result


def _print_metrics(url: str, token: Optional[str]) -> None:
    """Best-effort dump of ``GET /api/metrics`` (audit §5.3 acceptance p95)."""
    metrics_url = _with_token(f"{url.rstrip('/')}/api/metrics", token)
    try:
        response = httpx.get(metrics_url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"metrics      : unavailable ({type(e).__name__})")
        return

    turns = data.get("turn_seconds") or {}
    first_audio = data.get("first_audio_seconds") or {}
    queue = (data.get("queue") or {}).get("wait_seconds") or {}
    targets = data.get("targets") or {}
    print(
        "turn p95     : "
        f"{turns.get('p95')} s (n={turns.get('count')}, "
        f"first audio p95={first_audio.get('p95')} s, "
        f"queue wait p95={queue.get('p95')} s)"
    )
    print(
        f"p95 target   : <{targets.get('p95_turn_seconds')} s -> "
        f"{targets.get('p95_ok')}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Live pipeline smoke test")
    parser.add_argument(
        "--url", default="http://127.0.0.1:12393", help="server base URL"
    )
    parser.add_argument(
        "--text",
        default="Di hola en una frase corta, en español.",
        help="prompt sent as a text turn",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="seconds to wait for conversation-chain-end (default: 120)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get(TOKEN_ENV, ""),
        help="shared WS token (default: $VTUBER_WS_TOKEN)",
    )
    args = parser.parse_args()

    try:
        result = asyncio.run(run(args.url, args.text, args.timeout, args.token))
    except KeyboardInterrupt:
        return 130

    print()
    print(f"audio chunks : {result.audio_chunks}")
    print(f"audio bytes  : {result.audio_bytes}")
    print(f"playback ack : {result.acked}")
    print(f"chain start  : {result.turn_started}")
    print(f"chain end    : {result.turn_ended}")
    if result.texts:
        preview = " ".join(result.texts)[:200]
        print(f"said         : {preview}")
    _print_metrics(args.url, args.token)

    if result.ok:
        print("\nSMOKE TEST PASSED")
        return 0

    print(f"\nSMOKE TEST FAILED: {result.error or 'no audio produced'}")
    print(
        "Check: proxy enabled (enable_proxy), TTS reachable, and that no other\n"
        "client is holding the turn (only one turn per client at a time)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
