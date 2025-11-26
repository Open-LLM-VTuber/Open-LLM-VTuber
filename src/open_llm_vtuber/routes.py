import os
import json
from uuid import uuid4
import numpy as np
from datetime import datetime
from fastapi import APIRouter, WebSocket, UploadFile, File, Response, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect
from loguru import logger
from .service_context import ServiceContext
from .websocket_handler import WebSocketHandler
from .conversations.direct_control import speak_text
from .proxy_handler import ProxyHandler


def init_client_ws_route(ws_handler: WebSocketHandler) -> APIRouter:
    """
    Create and return API routes for handling the `/client-ws` WebSocket connections.

    Args:
        default_context_cache: Default service context cache for new sessions.

    Returns:
        APIRouter: Configured router with WebSocket endpoint.
    """

    router = APIRouter()

    @router.websocket("/client-ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for client connections"""
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


def init_proxy_route(server_url: str) -> APIRouter:
    """
    Create and return API routes for handling proxy connections.

    Args:
        server_url: The WebSocket URL of the actual server

    Returns:
        APIRouter: Configured router with proxy WebSocket endpoint
    """
    router = APIRouter()
    proxy_handler = ProxyHandler(server_url)

    @router.websocket("/proxy-ws")
    async def proxy_endpoint(websocket: WebSocket):
        """WebSocket endpoint for proxy connections"""
        try:
            await proxy_handler.handle_client_connection(websocket)
        except Exception as e:
            logger.error(f"Error in proxy connection: {e}")
            raise

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


def init_direct_control_routes(
    ws_handler: WebSocketHandler, default_context_cache: ServiceContext
) -> APIRouter:
    """REST API for direct control over the active chat session."""

    router = APIRouter()

    class CommonTarget(BaseModel):
        client_uid: str | None = Field(
            default=None, description="Target client UID; default last active"
        )
        apply_to_all: bool = Field(
            default=False, description="Apply to all connected sessions"
        )

    class SpeakRequest(CommonTarget):
        text: str = Field(..., description="Text for the avatar to speak")

    class SpeakResponse(BaseModel):
        status: str
        targets: list[str]
        message: str

    @router.get(
        "/v1/sessions",
        response_model=list[str],
        summary="List connected session UIDs",
        tags=["sessions"],
    )
    async def list_sessions():
        handler = ws_handler
        if not handler:
            return []
        return list(handler.client_connections.keys())

    def _resolve_targets(handler: WebSocketHandler, req: CommonTarget) -> list[str]:
        if not handler or not handler.client_connections:
            raise HTTPException(status_code=409, detail="No active chat session")

        if req.apply_to_all:
            return list(handler.client_connections.keys())

        if req.client_uid:
            if req.client_uid not in handler.client_connections:
                raise HTTPException(status_code=404, detail="client_uid not connected")
            return [req.client_uid]

        # Default: last active session, then fallback to last connected
        last_active = getattr(handler, "last_active_client_uid", None)
        if last_active and last_active in handler.client_connections:
            return [last_active]

        keys = list(handler.client_connections.keys())
        return [keys[-1]]

    def _sync_memory(context) -> None:
        if not context or not context.history_uid:
            return
        try:
            context.agent_engine.set_memory_from_history(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
            )
        except Exception as e:
            logger.warning(f"Failed to sync memory from history: {e}")

    @router.post(
        "/v1/control/speak",
        response_model=SpeakResponse,
        summary="Speak text (TTS-only, no memory)",
        tags=["control"],
    )
    async def speak(req: SpeakRequest):
        handler = ws_handler
        targets = _resolve_targets(handler, req)

        delivered: list[str] = []
        for uid in targets:
            websocket = handler.client_connections.get(uid)
            if not websocket:
                continue

            context = handler.client_contexts.get(uid)
            if not context:
                continue

            async def ws_send(payload: str):
                await websocket.send_text(payload)
            await speak_text(
                context,
                ws_send,
                req.text,
            )
            delivered.append(uid)

        return SpeakResponse(status="ok", targets=delivered, message="Speech delivered")

    class SystemRequest(CommonTarget):
        text: str = Field(
            ..., description="Invisible instruction to apply to the agent"
        )
        mode: str = Field(
            default="append", description="append | prepend | reset"
        )

    class SystemResponse(BaseModel):
        status: str
        targets: list[str]
        message: str

    @router.post(
        "/v1/control/system",
        response_model=SystemResponse,
        summary="Apply invisible system instruction",
        tags=["control"],
    )
    async def system_message(req: SystemRequest):
        handler = ws_handler
        targets = _resolve_targets(handler, req)

        applied: list[str] = []
        for uid in targets:
            context = handler.client_contexts.get(uid)
            if not context:
                continue

            if not hasattr(context, "_original_system_prompt") or not context._original_system_prompt:
                context._original_system_prompt = context.system_prompt or ""

            current = context.system_prompt or ""
            instruction = req.text or ""
            mode = (req.mode or "append").lower()

            if mode == "reset":
                new_system = context._original_system_prompt
            elif mode == "prepend":
                new_system = f"{instruction}\n\n{current}" if instruction else current
            else:
                new_system = f"{current}\n\n{instruction}" if instruction else current

            context.system_prompt = new_system
            if hasattr(context.agent_engine, "set_system"):
                try:
                    context.agent_engine.set_system(new_system)
                except Exception as e:
                    logger.warning(f"Failed applying system prompt to agent: {e}")

            applied.append(uid)

        return SystemResponse(
            status="ok",
            targets=applied,
            message=("system prompt updated" if req.mode != "reset" else "system prompt reset"),
        )

    class RespondRequest(CommonTarget):
        text: str = Field(
            ..., description="User-style message to trigger an agent response"
        )

    class RespondResponse(BaseModel):
        status: str
        targets: list[str]
        message: str

    @router.post(
        "/v1/control/respond",
        response_model=RespondResponse,
        summary="Trigger LLM response (remembered)",
        tags=["control"],
    )
    async def respond(req: RespondRequest):
        handler = ws_handler
        targets = _resolve_targets(handler, req)

        triggered: list[str] = []
        for uid in targets:
            websocket = handler.client_connections.get(uid)
            if not websocket:
                continue
            # Ensure agent memory is synced with current history before LLM turn
            context = handler.client_contexts.get(uid)
            _sync_memory(context)
            data = {"type": "text-input", "text": req.text}
            await handler._handle_conversation_trigger(websocket, uid, data)
            triggered.append(uid)

        return RespondResponse(status="ok", targets=triggered, message="Agent response triggered")

    return router
