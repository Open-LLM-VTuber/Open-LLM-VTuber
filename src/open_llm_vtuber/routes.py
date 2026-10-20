import os
import json
from typing import Optional
from uuid import uuid4
import numpy as np
from datetime import datetime
from fastapi import APIRouter, Request, WebSocket, UploadFile, File, Response
from starlette.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect
from loguru import logger
from .metrics import turn_metrics
from .security import enforce_ws_token, http_token_allowed
from .service_context import ServiceContext
from .websocket_handler import WebSocketHandler
from .proxy_handler import ProxyHandler
from .utils.stage import build_stage_payload
from .utils.tarot_commands import MAX_CARDS, MAX_QUESTION


def init_client_ws_route(
    default_context_cache: ServiceContext,
    ws_handler: WebSocketHandler | None = None,
    token: Optional[str] = None,
) -> APIRouter:
    """
    Create and return API routes for handling the `/client-ws` WebSocket connections.

    Args:
        default_context_cache: Default service context cache for new sessions.
        ws_handler: Optional handler shared with the rest of the application
            (the scheduler needs it to reach connected clients).
        token: Shared handshake token (audit A22). ``None`` reads
            ``VTUBER_WS_TOKEN`` from the environment; empty means no auth.

    Returns:
        APIRouter: Configured router with WebSocket endpoint.
    """

    router = APIRouter()
    ws_handler = ws_handler or WebSocketHandler(default_context_cache)

    @router.websocket("/client-ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for client connections"""
        # A22: reject the handshake before accept() so an unauthenticated peer
        # never reaches the service context.
        if not await enforce_ws_token(websocket, token):
            return

        await websocket.accept()
        client_uid = str(uuid4())

        try:
            await ws_handler.handle_new_connection(websocket, client_uid)
            await ws_handler.handle_websocket_communication(websocket, client_uid)
        except WebSocketDisconnect:
            await ws_handler.handle_disconnect(client_uid)
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            await ws_handler.handle_disconnect(client_uid)
            raise

    return router


def init_proxy_route(server_url: str, token: Optional[str] = None) -> APIRouter:
    """
    Create and return API routes for handling proxy connections.

    Args:
        server_url: The WebSocket URL of the actual server
        token: Shared handshake token (audit A22); same rules as `/client-ws`.

    Returns:
        APIRouter: Configured router with proxy WebSocket endpoint
    """
    router = APIRouter()
    proxy_handler = ProxyHandler(server_url)

    @router.websocket("/proxy-ws")
    async def proxy_endpoint(websocket: WebSocket):
        """WebSocket endpoint for proxy connections"""
        if not await enforce_ws_token(websocket, token):
            return

        try:
            await proxy_handler.handle_client_connection(websocket)
        except Exception as e:
            logger.error(f"Error in proxy connection: {e}")
            raise

    return router


def init_metrics_route(token: Optional[str] = None) -> APIRouter:
    """
    Create and return the `/api/metrics` route (A22 / audit §5.3).

    The payload is the in-memory window kept by ``metrics.turn_metrics``: turn
    duration (p50/p95), time to first audio and proxy queue depth/wait. It is
    read-only and never touches the conversation state, so it is safe to poll
    during a show:

        curl -s http://127.0.0.1:12393/api/metrics | jq .turn_seconds

    Args:
        token: Shared token (audit A22). Same rules as the WebSockets: when it
            is set, the request needs ``?token=`` or a bearer header.

    Returns:
        APIRouter: Configured router with the metrics endpoint.
    """
    router = APIRouter()

    @router.get("/api/metrics")
    async def get_metrics(request: Request):
        if not http_token_allowed(request, token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return JSONResponse(turn_metrics.snapshot())

    return router


def init_stage_route(
    ws_handler: WebSocketHandler, token: Optional[str] = None
) -> APIRouter:
    """Create the ``/api/stage`` route (Ruta B, audit §2.4).

    Lets the operator change the overlay scene without waiting for a scheduled
    job, which is also the quickest way to test a custom overlay:

        curl -X POST http://127.0.0.1:12393/api/stage \\
             -H 'Content-Type: application/json' \\
             -d '{"stage": "tarot_main", "background": "/bg/tarot_table.png"}'

    Args:
        ws_handler: Shared handler; it owns the ``current_stage`` cache and the
            client sockets.
        token: Shared token (audit A22). Same rules as ``/api/metrics``.

    Returns:
        APIRouter: ``GET`` returns the last payload, ``POST`` broadcasts a new
        one and reports how many overlays received it.
    """
    router = APIRouter()

    @router.get("/api/stage")
    async def get_stage(request: Request):
        if not http_token_allowed(request, token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return JSONResponse({"stage": ws_handler.current_stage})

    @router.post("/api/stage")
    async def set_stage(request: Request):
        if not http_token_allowed(request, token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "expected a JSON object"}, status_code=400)

        try:
            payload = build_stage_payload(
                stage=str(body.get("stage", "")),
                background=str(body.get("background", "")),
                props=body.get("props"),
                transition=str(body.get("transition", "fade")),
                duration_ms=body.get("duration_ms", 800),
            )
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

        delivered = await ws_handler.broadcast_stage_update(
            payload, str(body.get("target", "first"))
        )
        return JSONResponse(
            {"status": "ok", "delivered": delivered, "payload": payload}
        )

    return router


def init_tarot_route(
    ws_handler: WebSocketHandler, token: Optional[str] = None
) -> APIRouter:
    """Create ``/api/tarot`` and ``/api/tarot/draw`` (audit §4.6).

    Lets the operator draw without waiting for a cron job:

        curl -X POST http://127.0.0.1:12393/api/tarot/draw \\
             -H 'Content-Type: application/json' \\
             -d '{"count": 3, "question": "¿Cambio de trabajo?", "speak": true}'

    ``GET /api/tarot`` returns the last draw, which is what an operator HUD
    needs to show what is already on screen.

    Args:
        ws_handler: Shared handler; it owns the overlay sockets, the stage cache
            and ``current_draw``.
        token: Shared token (audit A22). Same rules as ``/api/metrics``.

    Returns:
        APIRouter: ``GET`` last draw, ``POST /api/tarot/draw`` a new one.
    """
    router = APIRouter()

    @router.get("/api/tarot")
    async def get_tarot(request: Request):
        if not http_token_allowed(request, token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        current = ws_handler.current_draw
        return JSONResponse({"draw": current.summary() if current else None})

    @router.post("/api/tarot/draw")
    async def draw_tarot(request: Request):
        if not http_token_allowed(request, token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        try:
            body = await request.json()
        except Exception:
            body = {}
        if body is None:
            body = {}
        if not isinstance(body, dict):
            return JSONResponse({"error": "expected a JSON object"}, status_code=400)

        count = body.get("count", 1)
        if isinstance(count, bool) or not isinstance(count, int):
            return JSONResponse({"error": "count must be an integer"}, status_code=400)
        if count < 1 or count > MAX_CARDS:
            return JSONResponse(
                {"error": f"count must be between 1 and {MAX_CARDS}"}, status_code=400
            )

        seed = body.get("seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            return JSONResponse({"error": "seed must be an integer"}, status_code=400)

        try:
            result = await ws_handler.draw_tarot(
                count=count,
                question=str(body.get("question", ""))[:MAX_QUESTION],
                seed=seed,
                target_client=str(body.get("target", "first")),
                speak=bool(body.get("speak", False)),
                asker=str(body.get("asker", "")),
            )
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

        return JSONResponse(
            {
                "status": "ok",
                "delivered": result.delivered,
                "spoken": result.spoken,
                "draw": result.summary(),
                "payload": result.payload,
            }
        )

    return router


def init_webtool_routes(default_context_cache: ServiceContext) -> APIRouter:
    """
    Create and return API routes for handling web tool interactions.

    Args:
        default_context_cache: Default service context cache for new sessions.

    Returns:
        APIRouter: Configured router with WebSocket endpoint.
    """

    router = APIRouter()

    @router.get("/web-tool")
    async def web_tool_redirect():
        """Redirect /web-tool to /web_tool/index.html"""
        return Response(status_code=302, headers={"Location": "/web-tool/index.html"})

    @router.get("/web_tool")
    async def web_tool_redirect_alt():
        """Redirect /web_tool to /web_tool/index.html"""
        return Response(status_code=302, headers={"Location": "/web-tool/index.html"})

    @router.get("/live2d-models/info")
    async def get_live2d_folder_info():
        """Get information about available Live2D models"""
        live2d_dir = "live2d-models"
        if not os.path.exists(live2d_dir):
            return JSONResponse(
                {"error": "Live2D models directory not found"}, status_code=404
            )

        valid_characters = []
        supported_extensions = [".png", ".jpg", ".jpeg"]

        for entry in os.scandir(live2d_dir):
            if entry.is_dir():
                folder_name = entry.name.replace("\\", "/")
                model3_file = os.path.join(
                    live2d_dir, folder_name, f"{folder_name}.model3.json"
                ).replace("\\", "/")

                if os.path.isfile(model3_file):
                    # Find avatar file if it exists
                    avatar_file = None
                    for ext in supported_extensions:
                        avatar_path = os.path.join(
                            live2d_dir, folder_name, f"{folder_name}{ext}"
                        )
                        if os.path.isfile(avatar_path):
                            avatar_file = avatar_path.replace("\\", "/")
                            break

                    valid_characters.append(
                        {
                            "name": folder_name,
                            "avatar": avatar_file,
                            "model_path": model3_file,
                        }
                    )
        return JSONResponse(
            {
                "type": "live2d-models/info",
                "count": len(valid_characters),
                "characters": valid_characters,
            }
        )

    @router.post("/asr")
    async def transcribe_audio(file: UploadFile = File(...)):
        """
        Endpoint for transcribing audio using the ASR engine
        """
        logger.info(f"Received audio file for transcription: {file.filename}")

        try:
            contents = await file.read()

            # Validate minimum file size
            if len(contents) < 44:  # Minimum WAV header size
                raise ValueError("Invalid WAV file: File too small")

            # Decode the WAV header and get actual audio data
            wav_header_size = 44  # Standard WAV header size
            audio_data = contents[wav_header_size:]

            # Validate audio data size
            if len(audio_data) % 2 != 0:
                raise ValueError("Invalid audio data: Buffer size must be even")

            # Convert to 16-bit PCM samples to float32
            try:
                audio_array = (
                    np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                    / 32768.0
                )
            except ValueError as e:
                raise ValueError(
                    f"Audio format error: {str(e)}. Please ensure the file is 16-bit PCM WAV format."
                )

            # Validate audio data
            if len(audio_array) == 0:
                raise ValueError("Empty audio data")

            text = await default_context_cache.asr_engine.async_transcribe_np(
                audio_array
            )
            logger.info(f"Transcription result: {text}")
            return {"text": text}

        except ValueError as e:
            logger.error(f"Audio format error: {e}")
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=400,
                media_type="application/json",
            )
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return Response(
                content=json.dumps(
                    {"error": "Internal server error during transcription"}
                ),
                status_code=500,
                media_type="application/json",
            )

    @router.websocket("/tts-ws")
    async def tts_endpoint(websocket: WebSocket):
        """WebSocket endpoint for TTS generation"""
        await websocket.accept()
        logger.info("TTS WebSocket connection established")

        try:
            while True:
                data = await websocket.receive_json()
                text = data.get("text")
                if not text:
                    continue

                logger.info(f"Received text for TTS: {text}")

                # Split text into sentences
                sentences = [s.strip() for s in text.split(".") if s.strip()]

                try:
                    # Generate and send audio for each sentence
                    for sentence in sentences:
                        sentence = sentence + "."  # Add back the period
                        file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
                        audio_path = (
                            await default_context_cache.tts_engine.async_generate_audio(
                                text=sentence, file_name_no_ext=file_name
                            )
                        )
                        logger.info(
                            f"Generated audio for sentence: {sentence} at: {audio_path}"
                        )

                        await websocket.send_json(
                            {
                                "status": "partial",
                                "audioPath": audio_path,
                                "text": sentence,
                            }
                        )

                    # Send completion signal
                    await websocket.send_json({"status": "complete"})

                except Exception as e:
                    logger.error(f"Error generating TTS: {e}")
                    await websocket.send_json({"status": "error", "message": str(e)})

        except WebSocketDisconnect:
            logger.info("TTS WebSocket client disconnected")
        except Exception as e:
            logger.error(f"Error in TTS WebSocket connection: {e}")
            await websocket.close()

    return router
