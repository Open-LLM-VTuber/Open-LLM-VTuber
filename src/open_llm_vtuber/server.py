"""
Open-LLM-VTuber Server
========================
This module contains the WebSocket server for Open-LLM-VTuber, which handles
the WebSocket connections, serves static files, and manages the web tool.
It uses FastAPI for the server and Starlette for static file serving.
"""

import os
import shutil
import re
from pathlib import Path
from fastapi.responses import HTMLResponse, FileResponse

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from .routes import init_client_ws_route, init_webtool_routes, init_proxy_route
from .book_reader import init_book_routes
from .media_library import init_media_routes
from .extensions import init_extension_routes
from .computer_use.service import CONTROL, init_control_routes
from .service_context import ServiceContext
from .config_manager.utils import Config


# Create a custom StaticFiles class that adds CORS headers
class CORSStaticFiles(StarletteStaticFiles):
    """
    Static files handler that adds CORS headers to all responses.
    Needed because Starlette StaticFiles might bypass standard middleware.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        # Add CORS headers to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"

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

        # Add global CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include routes, passing the context instance
        # The context will be populated during the initialize step
        self.app.include_router(
            init_client_ws_route(default_context_cache=self.default_context_cache),
        )
        self.app.include_router(
            init_webtool_routes(default_context_cache=self.default_context_cache),
        )

        # Initialize and include proxy routes if proxy is enabled
        system_config = config.system_config
        if hasattr(system_config, "enable_proxy") and system_config.enable_proxy:
            # Construct the server URL for the proxy
            host = system_config.host
            port = system_config.port
            server_url = f"ws://{host}:{port}/client-ws"
            self.app.include_router(
                init_proxy_route(server_url=server_url),
            )

        self.app.include_router(init_book_routes(self.default_context_cache))
        self.app.include_router(init_extension_routes(self.default_context_cache))
        self.app.include_router(init_control_routes())
        self.app.add_event_handler("shutdown", CONTROL.close)

        self.app.include_router(init_media_routes(self.default_context_cache))

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

        @self.app.get("/api/broadcast/status")
        async def broadcast_status():
            from .broadcast import LIVE, STOP
            return {"enabled": LIVE, "stopped": LIVE and STOP.exists()}

        @self.app.get("/subtitle-sync.js")
        async def subtitle_sync_script():
            return FileResponse(Path(__file__).with_name("subtitle_sync.js"), media_type="application/javascript")

        @self.app.get("/interface.css")
        async def interface_styles():
            return FileResponse(Path(__file__).with_name("interface.css"), media_type="text/css")

        @self.app.get("/live2d-actions.js")
        async def live2d_actions_script():
            return FileResponse(
                Path(__file__).with_name("live2d_actions.js"),
                media_type="application/javascript",
            )

        @self.app.get("/live2d-stage.js")
        async def live2d_stage_script():
            return FileResponse(
                Path(__file__).with_name("live2d_stage.js"),
                media_type="application/javascript",
            )

        @self.app.get("/")
        @self.app.get("/index.html")
        async def frontend_index():
            frontend_root = Path("frontend/dist/web") if Path("frontend/dist/web/index.html").is_file() else Path("frontend")
            html = (frontend_root / "index.html").read_text(encoding="utf-8")
            # Bundled filenames stay unchanged for local patches; invalidate browser caches.
            def version_asset(match):
                asset = frontend_root / match.group(2)
                version = asset.stat().st_mtime_ns if asset.is_file() else 0
                return f'{match.group(1)}"./{match.group(2)}?v={version}"'
            html = re.sub(r'(src=|href=)"\./(assets/[^"?]+)"', version_asset, html)
            # Source HTML includes adapters for Vite dev; inject them once in production.
            html = re.sub(r'<script src="/(?:subtitle-sync|live2d-stage|live2d-actions)\.js"></script>', '', html)
            html = re.sub(r'<link rel="stylesheet" href="/interface\.css">', '', html)
            language = self.config.system_config.default_language
            language_script = (
                f'<script>(()=>{{const language="{language}";'
                "document.documentElement.lang=language;"
                'try{const key="vtuberDefaultLanguage";'
                'if(localStorage.getItem(key)!==language || !localStorage.getItem("i18nextLng"))'
                'localStorage.setItem("i18nextLng",language);'
                "localStorage.setItem(key,language);"
                "}catch{}})();</script>"
            )
            html = html.replace(
                "<head>",
                '<head><script src="/subtitle-sync.js"></script><link rel="stylesheet" href="/interface.css?v=3">' + language_script + '<script src="/live2d-stage.js?v=4"></script>'
                '<script src="/live2d-actions.js"></script>',
                1,
            )
            return HTMLResponse(html, headers={"Cache-Control": "no-store"})

        # Mount main frontend last (as catch-all)
        self.app.mount(
            "/",
            CORSStaticFiles(directory="frontend/dist/web" if Path("frontend/dist/web/index.html").is_file() else "frontend", html=True),
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
