"""End-to-end check of the tarot feature against a **live** server.

It plays the OBS overlay (connects to ``/proxy-ws``) and the operator (HTTP
calls), so it exercises the real chain:

    POST /api/tarot/draw -> stage-update with /bg/cards/*.jpg
                         -> (speak) ai-speak-signal -> TTS -> audio
                         -> frontend-playback-complete -> conversation-chain-end
    GET  /api/tarot      -> last draw with asker and question

Usage::

    uv run python scripts/tarot_smoke.py
    uv run python scripts/tarot_smoke.py --url http://127.0.0.1:12393 \\
        --count 3 --asker pepe --question "¿me cambiaré de trabajo?"

Exit code 0 means: cards reached the overlay, the API reports the draw and the
spoken turn closed. Run it with no other client connected (the connector would
be "first" and would receive the speech instead of this socket).

Notes:
    * It must answer ``frontend-playback-complete``; without that ack the
      backend waits ``PLAYBACK_ACK_TIMEOUT`` before closing the turn (A18).
    * ``--no-speak`` only checks the cards and the API, which needs no TTS.
    * The draw waits for the overlay session to be ready (``set-model-and-conf``
      / ``start-mic``). A cold proxy opens ``/client-ws`` on the first client and
      initialises MCP servers there, which takes tens of seconds; drawing before
      that ends up with ``delivered=0`` and no cards on screen.
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
    """Append ``?token=`` to a WebSocket/HTTP URL (no-op without a token)."""
    if not token:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}token={quote(token, safe='')}"


def _audio_size(payload: str) -> int:
    """Decoded size of a base64 payload; 0 if it is not valid base64."""
    try:
        return len(base64.b64decode(payload, validate=False))
    except Exception:
        return 0


class Result:
    """What the overlay saw and what the API returned."""

    def __init__(self) -> None:
        self.stage_updates: list[dict] = []
        self.audio_chunks = 0
        self.audio_bytes = 0
        self.acked = 0
        self.turn_ended = False
        self.draw: Optional[dict] = None
        self.stage_seen = asyncio.Event()
        self.turn_done = asyncio.Event()
        #: Set when the proxy forwards the session handshake, i.e. when the
        #: internal ``/client-ws`` socket is registered and a draw can reach us.
        self.ready = asyncio.Event()
        #: Ignore stage updates replayed from the *previous* draw until here.
        self.armed = False
        #: Only a chain-end after this flag closes the spoken turn (a stale
        #: broadcast from an earlier turn must not end this test early).
        self.awaiting_turn = False
        self.error: Optional[str] = None


async def _overlay(ws_url: str, result: Result) -> None:
    """Consume the socket like ``web_tool/overlay.html`` does."""
    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
        while not result.turn_ended:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")
            if msg_type == "control" and message.get("text") == "start-mic":
                # Last frame of the session handshake: the proxy already
                # registered its ``/client-ws`` socket, and the cached stage
                # (if any) was replayed *before* this message.
                result.ready.set()
            if msg_type == "stage-update":
                if result.armed:
                    result.stage_updates.append(message)
                    if isinstance(message.get("props"), list):
                        result.stage_seen.set()
            elif msg_type == "audio":
                result.audio_chunks += 1
                result.audio_bytes += _audio_size(message.get("audio") or "")
            elif msg_type == "backend-synth-complete":
                # Same reply as the real overlay: one ack per synthesis end.
                await ws.send(json.dumps({"type": "frontend-playback-complete"}))
                result.acked += 1
            elif (
                msg_type == "control"
                and message.get("text") == "conversation-chain-end"
                and result.awaiting_turn
            ):
                result.turn_ended = True
                result.turn_done.set()


async def _draw(client: httpx.AsyncClient, url: str, token: str, body: dict) -> dict:
    """POST /api/tarot/draw and return the parsed response."""
    response = await client.post(_with_token(f"{url}/api/tarot/draw", token), json=body)
    if response.status_code != 200:
        raise RuntimeError(
            f"draw -> HTTP {response.status_code}: {response.text[:200]}"
        )
    return response.json()


def _check_cards(payload: dict, expected: int) -> Optional[str]:
    """Validate one ``stage-update``; returns an error message or ``None``."""
    props = payload.get("props")
    if not isinstance(props, list) or len(props) != expected:
        return f"expected {expected} props, got {props!r}"
    for index, prop in enumerate(props, start=1):
        if prop.get("id") != f"card_{index}":
            return f"prop {index} has id {prop.get('id')!r}"
        src = prop.get("src")
        if not isinstance(src, str) or not src.startswith("/bg/cards/major_"):
            return f"prop {index} src is {src!r}"
        if not src.endswith(".jpg"):
            return f"prop {index} does not use the JPEG deck: {src}"
        if prop.get("rot") not in (0, 180, 0.0, 180.0):
            return f"prop {index} has rot {prop.get('rot')!r}"
    return None


async def run(
    url: str,
    token: str,
    count: int,
    asker: str,
    question: str,
    timeout: float,
    speak: bool,
    ready_timeout: float = 180.0,
    stage_timeout: float = 60.0,
) -> Result:
    """Open the overlay socket, wait for the session, draw and check both."""
    result = Result()
    ws_base = url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = _with_token(f"{ws_base}/proxy-ws", token)

    overlay_task = asyncio.create_task(_overlay(ws_url, result))

    try:
        # A cold proxy only opens /client-ws now, and its first session loads
        # the MCP servers; drawing before that finishes reaches 0 overlays.
        await asyncio.wait_for(result.ready.wait(), timeout=ready_timeout)
        print("ok  overlay session ready")
        result.armed = True

        async with httpx.AsyncClient(timeout=30.0) as client:
            silent = await _draw(
                client,
                url,
                token,
                {"count": count, "asker": asker, "question": question, "seed": 2026},
            )
            await asyncio.wait_for(result.stage_seen.wait(), timeout=stage_timeout)
            print(f"ok  cards delivered ({silent.get('delivered')} overlay(s))")

            response = await client.get(_with_token(f"{url}/api/tarot", token))
            result.draw = response.json().get("draw")
            if not result.draw:
                result.error = "GET /api/tarot returned no draw"
            elif result.draw.get("asker") != asker:
                result.error = (
                    f"asker is {result.draw.get('asker')!r}, expected {asker!r}"
                )
            elif len(result.draw.get("cards") or []) != count:
                result.error = "GET /api/tarot returned a different number of cards"
            if result.error:
                raise RuntimeError(result.error)
            print(f"ok  GET /api/tarot reports asker={asker!r} with {count} card(s)")

            if speak:
                result.awaiting_turn = True
                await _draw(
                    client,
                    url,
                    token,
                    {
                        "count": 1,
                        "asker": asker,
                        "question": question,
                        "speak": True,
                    },
                )
                await asyncio.wait_for(result.turn_done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        if not result.ready.is_set():
            result.error = (
                result.error or f"overlay session not ready within {ready_timeout:.0f}s"
            )
        elif not result.stage_seen.is_set():
            result.error = (
                result.error or f"no stage-update within {stage_timeout:.0f}s"
            )
        else:
            result.error = result.error or f"no turn end within {timeout:.0f}s"
    except Exception as e:  # connection refused, HTTP error, ...
        result.error = result.error or f"{type(e).__name__}: {e}"
    finally:
        result.turn_ended = True
        overlay_task.cancel()
        await asyncio.gather(overlay_task, return_exceptions=True)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Live tarot end-to-end check")
    parser.add_argument(
        "--url", default="http://127.0.0.1:12393", help="server base URL"
    )
    parser.add_argument(
        "--count", type=int, default=3, help="cards in the spread (1-3)"
    )
    parser.add_argument("--asker", default="smoke-test", help="donor name for the draw")
    parser.add_argument(
        "--question", default="¿me cambiaré de trabajo?", help="question for the LLM"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="seconds to wait for the spoken turn",
    )
    parser.add_argument(
        "--ready-timeout",
        type=float,
        default=180.0,
        help="seconds to wait for the overlay session (cold MCP start)",
    )
    parser.add_argument(
        "--stage-timeout",
        type=float,
        default=60.0,
        help="seconds to wait for stage-update after the draw",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get(TOKEN_ENV, ""),
        help="shared token (default: env)",
    )
    parser.add_argument(
        "--no-speak",
        action="store_true",
        help="only check cards + API (no TTS needed)",
    )
    args = parser.parse_args()

    try:
        result = asyncio.run(
            run(
                args.url,
                args.token,
                args.count,
                args.asker,
                args.question,
                args.timeout,
                speak=not args.no_speak,
                ready_timeout=args.ready_timeout,
                stage_timeout=args.stage_timeout,
            )
        )
    except KeyboardInterrupt:
        return 130

    cards_ok = bool(result.stage_updates)
    for payload in result.stage_updates:
        problem = _check_cards(payload, args.count)
        if problem:
            result.error = result.error or problem
            cards_ok = False
            break

    print()
    print(f"stage updates: {len(result.stage_updates)}")
    print(f"cards valid  : {cards_ok}")
    if result.draw:
        cards = result.draw.get("cards") or []
        print(f"api draw     : asker={result.draw.get('asker')!r} cards={len(cards)}")
    if not args.no_speak:
        print(f"audio chunks : {result.audio_chunks}")
        print(f"audio bytes  : {result.audio_bytes}")
        print(f"playback ack : {result.acked}")
        print(f"chain end    : {result.turn_ended}")

    ok = (
        cards_ok
        and result.draw
        and not result.error
        and (args.no_speak or result.turn_ended)
    )
    if ok:
        print("\nTAROT SMOKE PASSED")
        return 0

    print(f"\nTAROT SMOKE FAILED: {result.error or 'cards or turn missing'}")
    print(
        "Check: server up, enable_proxy is true, the deck exists under\n"
        "backgrounds/cards/*.jpg and no other client is holding the turn."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
