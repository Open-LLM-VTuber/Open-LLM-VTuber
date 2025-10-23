import os
import re
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Optional, List

import numpy as np
import yaml
from fastapi import (
    APIRouter,
    WebSocket,
    UploadFile,
    File,
    Response,
    HTTPException,
    Form,
)
from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect
from loguru import logger

from .service_context import ServiceContext
from .websocket_handler import WebSocketHandler
from .proxy_handler import ProxyHandler
from .config_manager.utils import read_yaml


SAFE_NAME_PATTERN = re.compile(r"[^a-z0-9_-]+")


def _sanitize_name(value: str, fallback: str = "character") -> str:
    """
    Sanitize a string to create a filesystem-safe, lowercase identifier.
    Allowed characters: a-z, 0-9, hyphen, underscore.
    """
    if value is None:
        value = ""
    sanitized = SAFE_NAME_PATTERN.sub("-", value.lower()).strip("-_")
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    if not sanitized:
        return fallback
    return sanitized


def _ensure_unique_basename(base: str, directory: Path, extension: str) -> str:
    """
    Ensure the basename is unique within the directory by appending numeric suffixes.
    Returns the basename without extension.
    """
    candidate = base
    counter = 2
    while (directory / f"{candidate}{extension}").exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _load_model_dict(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError("model_dict.json not found")

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc

    if not isinstance(data, list):
        raise ValueError("model_dict.json must contain a list")
    return data


def _collect_existing_conf_uids(characters_dir: Path) -> set:
    """
    Collect existing conf_uid values from conf.yaml and characters directory.
    """
    conf_uids = set()
    candidate_files: List[Path] = []
    root_conf = Path("conf.yaml")
    if root_conf.exists():
        candidate_files.append(root_conf)
    candidate_files.extend(characters_dir.glob("*.yaml"))

    for file_path in candidate_files:
        try:
            config = read_yaml(str(file_path))
            uid = (
                config.get("character_config", {})
                if isinstance(config, dict)
                else {}
            ).get("conf_uid")
            if uid:
                conf_uids.add(str(uid))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to read config '{file_path}': {exc}")
    return conf_uids


def _generate_conf_uid(conf_name: str, characters_dir: Path) -> str:
    """
    Generate a unique conf_uid in the format <conf_name>_<NNN>.
    """
    existing = _collect_existing_conf_uids(characters_dir)
    counter = 1
    while True:
        candidate = f"{conf_name}_{counter:03d}"
        if candidate not in existing:
            return candidate
        counter += 1


def _validate_model_name(model_name: str, model_dict_path: Path) -> None:
    models = _load_model_dict(model_dict_path)
    available_names = {entry.get("name") for entry in models}
    if model_name not in available_names:
        raise ValueError(
            f"Model '{model_name}' not found in model_dict.json. "
            f"Available models: {', '.join(sorted(filter(None, available_names)))}"
        )


class CharacterCreatePayload(BaseModel):
    character_name: Optional[str] = None
    persona_prompt: str
    live2d_model_name: str
    avatar: Optional[str] = ""
    human_name: Optional[str] = "Human"



def init_client_ws_route(default_context_cache: ServiceContext) -> APIRouter:
    """
    Create and return API routes for handling the `/client-ws` WebSocket connections.

    Args:
        default_context_cache: Default service context cache for new sessions.

    Returns:
        APIRouter: Configured router with WebSocket endpoint.
    """

    router = APIRouter()
    ws_handler = WebSocketHandler(default_context_cache)

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

    @router.get("/api/live2d/models")
    async def get_live2d_models():
        """Return the entries defined in model_dict.json"""
        model_dict_path = Path("model_dict.json")
        try:
            models = _load_model_dict(model_dict_path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="model_dict.json not found")
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return {"models": models}

    @router.post("/api/avatars/upload")
    async def upload_avatar(
        file: UploadFile = File(...),
        base_name: Optional[str] = Form(None),
    ):
        """Save an uploaded PNG avatar to the avatars directory."""
        if file.content_type not in {"image/png"}:
            raise HTTPException(
                status_code=400, detail="Only PNG avatar uploads are supported"
            )

        avatars_dir = Path("avatars")
        avatars_dir.mkdir(parents=True, exist_ok=True)

        suggested_base = base_name or Path(file.filename or "").stem or "avatar"
        sanitized_base = _sanitize_name(suggested_base, fallback="avatar")
        unique_base = _ensure_unique_basename(sanitized_base, avatars_dir, ".png")
        target_path = avatars_dir / f"{unique_base}.png"

        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded avatar is empty")

        try:
            with target_path.open("wb") as avatar_file:
                avatar_file.write(contents)
        except OSError as exc:
            logger.error(f"Failed to save avatar: {exc}")
            raise HTTPException(
                status_code=500, detail="Failed to save avatar file"
            ) from exc

        return {"filename": target_path.name}

    @router.post("/api/characters/create")
    async def create_character(payload: CharacterCreatePayload):
        """Create a new character YAML configuration file."""
        if not payload.persona_prompt or not payload.persona_prompt.strip():
            raise HTTPException(status_code=400, detail="persona_prompt is required")

        if not payload.live2d_model_name:
            raise HTTPException(
                status_code=400, detail="live2d_model_name is required"
            )

        model_dict_path = Path("model_dict.json")
        try:
            _validate_model_name(payload.live2d_model_name, model_dict_path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        characters_dir = Path("characters")
        characters_dir.mkdir(parents=True, exist_ok=True)

        suggested_name = payload.character_name or ""
        sanitized_name = _sanitize_name(suggested_name, fallback="character")
        unique_base = _ensure_unique_basename(sanitized_name, characters_dir, ".yaml")
        conf_name = unique_base

        conf_uid = _generate_conf_uid(conf_name, characters_dir)

        avatar_filename = (payload.avatar or "").strip()
        if avatar_filename:
            avatar_path = Path("avatars") / avatar_filename
            if not avatar_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Avatar '{avatar_filename}' not found in avatars directory",
                )

        persona_prompt = payload.persona_prompt.rstrip()
        character_name = payload.character_name or conf_name
        human_name = payload.human_name or "Human"

        yaml_payload = {
            "character_config": {
                "conf_name": conf_name,
                "conf_uid": conf_uid,
                "live2d_model_name": payload.live2d_model_name,
                "character_name": character_name,
                "avatar": avatar_filename,
                "human_name": human_name,
                "persona_prompt": persona_prompt,
            }
        }

        target_path = characters_dir / f"{unique_base}.yaml"
        try:
            with target_path.open("w", encoding="utf-8") as yaml_file:
                yaml.safe_dump(
                    yaml_payload,
                    yaml_file,
                    allow_unicode=True,
                    sort_keys=False,
                    width=80,
                )
        except yaml.YAMLError as exc:
            logger.error(f"Failed to serialize character YAML: {exc}")
            raise HTTPException(
                status_code=500, detail="Failed to serialize character YAML"
            ) from exc
        except OSError as exc:
            logger.error(f"Failed to write character YAML: {exc}")
            raise HTTPException(
                status_code=500, detail="Failed to write character file"
            ) from exc

        return {
            "ok": True,
            "filename": target_path.name,
            "conf_name": conf_name,
            "conf_uid": conf_uid,
        }

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
