"""
Open-LLM-VTuber Server
========================
This module contains the WebSocket server for Open-LLM-VTuber, which handles
the WebSocket connections, serves static files, and manages the web tool.
It uses FastAPI for the server and Starlette for static file serving.
"""

import os
import shutil

from fastapi import FastAPI
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from .routes import (
    init_client_ws_route,
    init_metrics_route,
    init_webtool_routes,
    init_proxy_route,
)
from .scheduler.service import SchedulerService
from .security import (
    build_cors_settings,
    get_ws_token,
    static_cors_headers,
    with_token,
)
from .service_context import ServiceContext
from .utils.stream_audio import configure_audio_export
from .websocket_handler import WebSocketHandler
from .config_manager.scheduler import SchedulerConfig
from .config_manager.utils import Config


# Create a custom StaticFiles class that adds CORS headers
class CORSStaticFiles(StarletteStaticFiles):
    """
    Static files handler that adds CORS headers to all responses.
    Needed because Starlette StaticFiles might bypass standard middleware.

    The origins are injected by ``WebSocketServer`` (``cors_origins`` /
    ``cors_origin_regex``) so an allowed origin is echoed back instead of a
    blanket ``*`` (audit A22).
    """

    cors_origins = []
    cors_origin_regex = None

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        for header, value in static_cors_headers(
            scope, self.cors_origins, self.cors_origin_regex
        ).items():
            response.headers[header] = value

        if path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"

        return response


class AvatarStaticFiles(CORSStaticFiles):
    """
    Avatar files handler with security restrictions and CORS headers
    """

    async def get_response(self, path: str, scope):
        allowed_extensions = (".jpg", ".jpeg", ".png", ".gif", ".svg")
        if not any(path.lower().endswith(ext) for ext in allowed_extensions):
            return Response("Forbidden file type", status_code=403)
        response = await super().get_response(path, scope)
        return response


class WebSocketServer:
    """
    API server for Open-LLM-VTuber. This contains the websocket endpoint for the client, hosts the web tool, and serves static files.

    Creates and configures a FastAPI app, registers all routes
    (WebSocket, web tools, proxy) and mounts static assets with CORS.

    Args:
        config (Config): Application configuration containing system settings.
        default_context_cache (ServiceContext, optional):
            Pre‑initialized service context for sessions' service context to reference to.
            **If omitted, `initialize()` method needs to be called to load service context.**

    Notes:
        - If default_context_cache is omitted, call `await initialize()` to load service context cache.
        - Use `clean_cache()` to clear and recreate the local cache directory.
    """

    def __init__(self, config: Config, default_context_cache: ServiceContext = None):
        self.app = FastAPI(title="Open-LLM-VTuber Server")  # Added title for clarity
        self.config = config
        self.default_context_cache = (
            default_context_cache or ServiceContext()
        )  # Use provided context or initialize a new empty one waiting to be loaded
        # It will be populated during the initialize method call

        # Add global CORS middleware. A22: an explicit allow-list (loopback +
        # configured host + VTUBER_CORS_ORIGINS) instead of "*" combined with
        # allow_credentials=True, which browsers reject as invalid.
        host = getattr(config.system_config, "host", "127.0.0.1")
        port = getattr(config.system_config, "port", 12393)
        self.cors_settings = build_cors_settings(host, port)
        self.app.add_middleware(CORSMiddleware, **self.cors_settings)
        CORSStaticFiles.cors_origins = list(self.cors_settings["allow_origins"])
        CORSStaticFiles.cors_origin_regex = self.cors_settings["allow_origin_regex"]

        # A22: shared handshake token. Empty (the default) keeps the local show
        # behaviour; when set, every WS handshake and /api/metrics must present
        # ?token=... (or Authorization: Bearer ...).
        self.ws_token = get_ws_token()
        if self.ws_token:
            logger.info(
                "WebSocket token auth enabled (VTUBER_WS_TOKEN is set); "
                "clients must append ?token=... to /client-ws and /proxy-ws"
            )

        # Include routes, passing the context instance
        # The context will be populated during the initialize step.
        # The handler is created here so the scheduler can reuse it.
        self.ws_handler = WebSocketHandler(self.default_context_cache)
        self.app.include_router(
            init_client_ws_route(
                default_context_cache=self.default_context_cache,
                ws_handler=self.ws_handler,
                token=self.ws_token,
            ),
        )
        self.app.include_router(
            init_webtool_routes(default_context_cache=self.default_context_cache),
        )
        # Turn/queue metrics (audit §5.3). Read-only JSON, no heavy imports.
        self.app.include_router(init_metrics_route(token=self.ws_token))

        # Initialize and include proxy routes if proxy is enabled
        system_config = config.system_config

        # A23: container used for every TTS payload. WAV by default (LAN); switch
        # to MP3 when the overlay runs on another machine or through a tunnel.
        audio_export = getattr(system_config, "audio_export", None)
        try:
            audio_format = configure_audio_export(
                getattr(audio_export, "audio_format", "wav"),
                getattr(audio_export, "bitrate", "64k"),
            )
        except ValueError as e:
            logger.warning(f"Invalid system_config.audio_export ({e}); using wav")
            audio_format = configure_audio_export("wav")
        if audio_format != "wav":
            logger.info(
                f"Audio export format: {audio_format} "
                f"({getattr(audio_export, 'bitrate', '64k')})"
            )

        if hasattr(system_config, "enable_proxy") and system_config.enable_proxy:
            # Construct the server URL for the proxy. The proxy connects to its
            # own /client-ws, so it has to carry the token when auth is on.
            server_url = with_token(f"ws://{host}:{port}/client-ws", self.ws_token)
            self.app.include_router(
                init_proxy_route(server_url=server_url, token=self.ws_token),
            )

        # Scripted segments (start, breaks, closing). Disabled by default.
        scheduler_config = (
            getattr(config, "scheduler_config", None) or SchedulerConfig()
        )
        self.scheduler = SchedulerService(self.ws_handler, scheduler_config)
        self.app.add_event_handler("startup", self.scheduler.start)
        self.app.add_event_handler("shutdown", self.scheduler.shutdown)

        # Mount cache directory first (to ensure audio file access)
        if not os.path.exists("cache"):
            os.makedirs("cache")
        self.app.mount(
            "/cache",
            CORSStaticFiles(directory="cache"),
            name="cache",
        )

        # Mount static files with CORS-enabled handlers
        self.app.mount(
            "/live2d-models",
            CORSStaticFiles(directory="live2d-models"),
            name="live2d-models",
        )
        self.app.mount(
            "/bg",
            CORSStaticFiles(directory="backgrounds"),
            name="backgrounds",
        )
        self.app.mount(
            "/avatars",
            AvatarStaticFiles(directory="avatars"),
            name="avatars",
        )

        # Mount web tool directory separately from frontend
        self.app.mount(
            "/web-tool",
            CORSStaticFiles(directory="web_tool", html=True),
            name="web_tool",
        )

        # Mount main frontend last (as catch-all)
        self.app.mount(
            "/",
            CORSStaticFiles(directory="frontend", html=True),
            name="frontend",
        )

    async def initialize(self):
        """Asynchronously load the service context from config.
        Calling this function is needed if default_context_cache was not provided to the constructor."""
        await self.default_context_cache.load_from_config(self.config)

    @staticmethod
    def clean_cache():
        """Clean the cache directory by removing and recreating it."""
        cache_dir = "cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
