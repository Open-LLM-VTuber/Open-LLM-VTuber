"""PWA (Progressive Web App) support for Open-LLM-VTuber."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse


def create_pwa_router(www_dir: str = "www") -> APIRouter:
    """Create PWA router with static file serving."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def pwa_index(request: Request):
        """Serve PWA shell."""
        index_path = os.path.join(www_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {
            "type": "pwa",
            "message": "Open-LLM-VTuber PWA",
            "install": "Access the PWA install prompt from your browser menu",
        }

    @router.get("/sw.js")
    async def pwa_sw():
        """Serve service worker."""
        sw_path = os.path.join(www_dir, "sw.js")
        if os.path.exists(sw_path):
            return FileResponse(
                sw_path, media_type="application/javascript"
            )
        return {"error": "Service worker not found"}

    @router.get("/manifest.json")
    async def pwa_manifest():
        """Serve PWA manifest."""
        manifest_path = os.path.join(www_dir, "manifest.json")
        if os.path.exists(manifest_path):
            return FileResponse(manifest_path, media_type="application/json")
        return {
            "name": "Open-LLM-VTuber",
            "short_name": "VTuber",
            "display": "standalone",
        }

    @router.get("/{path:path}")
    async def pwa_static(path: str):
        """Serve static files from www directory."""
        file_path = os.path.join(www_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index for SPA routing
        index_path = os.path.join(www_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Not found"}

    return router