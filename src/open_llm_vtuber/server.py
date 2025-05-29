import os
import shutil

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from .routes import init_client_ws_route, init_webtool_routes
from .service_context import ServiceContext
from .config_manager.utils import Config


class CustomStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        return response


class AvatarStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        allowed_extensions = (".jpg", ".jpeg", ".png", ".gif", ".svg")
        if not any(path.lower().endswith(ext) for ext in allowed_extensions):
            return Response("Forbidden file type", status_code=403)
        return await super().get_response(path, scope)


class WebSocketServer:
    def __init__(self, config: Config):
        self.app = FastAPI()

        # Add CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Load configurations and initialize the default context cache
        default_context_cache = ServiceContext()
        default_context_cache.load_from_config(config)

        # Include routes
        self.app.include_router(
            init_client_ws_route(default_context_cache=default_context_cache),
        )
        self.app.include_router(
            init_webtool_routes(default_context_cache=default_context_cache),
        )

        # Mount cache directory first (to ensure audio file access)
        if not os.path.exists("cache"):
            os.makedirs("cache")
        self.app.mount(
            "/cache",
            StaticFiles(directory="cache"),
            name="cache",
        )

        # Mount static files
        self.app.mount(
            "/live2d-models",
            StaticFiles(directory="live2d-models"),
            name="live2d-models",
        )
        self.app.mount(
            "/bg",
            StaticFiles(directory="backgrounds"),
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
            CustomStaticFiles(directory="web_tool", html=True),
            name="web_tool",
        )

        # Mount experimental three.js frontend
        if os.path.isdir("frontend_threejs"):
            self.app.mount(
                "/threejs-demo",
                CustomStaticFiles(directory="frontend_threejs", html=True),
                name="threejs-demo",
            )

        # Mount main frontend last (as catch-all)
        self.app.mount(
            "/",
            CustomStaticFiles(directory="frontend", html=True),
            name="frontend",
        )

    def run(self):
        pass

    @staticmethod
    def clean_cache():
        """Clean the cache directory by removing and recreating it."""
        cache_dir = "cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
