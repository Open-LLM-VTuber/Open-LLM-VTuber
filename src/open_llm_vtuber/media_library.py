"""Read-only media library and timestamped audio transcription."""

import asyncio
from .broadcast import allowed
from collections import OrderedDict
from pathlib import Path
import os
import tempfile
import shutil
import subprocess

import numpy as np
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

MEDIA_TYPES = {
    "music": {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".opus"},
    "videos": {".mp4", ".webm", ".mov", ".m4v", ".ogv"},
}


def list_media(root=Path("media")):
    root = root.resolve()
    result = {}
    for kind, extensions in MEDIA_TYPES.items():
        folder = root / kind
        result[kind] = [
            {"title": path.stem, "path": path.relative_to(folder).as_posix()}
            for path in sorted(folder.rglob("*"))
            if allowed(kind, path.relative_to(folder).as_posix())
            and folder.resolve().is_relative_to(root)
            and path.suffix.lower() in extensions
            and path.is_file()
            and path.resolve().is_relative_to(folder.resolve())
        ]
    return result


def init_media_routes(context, root=Path("media")) -> APIRouter:
    router = APIRouter(prefix="/api/media")
    root = root.resolve()
    lock = asyncio.Lock()
    cache = OrderedDict()

    def entries(kind):
        if kind not in MEDIA_TYPES:
            raise HTTPException(404, "未知媒体类型")
        folder = root / kind
        folder.mkdir(parents=True, exist_ok=True)
        if not folder.resolve().is_relative_to(root):
            raise HTTPException(404, "媒体目录不可用")
        return folder, MEDIA_TYPES[kind]

    def resolve(kind, filename):
        folder, extensions = entries(kind)
        path = (folder / filename).resolve()
        if (
            not allowed(kind, filename)
            or not path.is_relative_to(folder.resolve())
            or path.suffix.lower() not in extensions
            or not path.is_file()
        ):
            raise HTTPException(404, "媒体文件不存在")
        return path

    # Keep the existing playback catalog stable; resources also include books/images.
    resource_types = {**MEDIA_TYPES,
                      "images": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"},
                      "books": {".pdf", ".epub", ".txt"}}

    def resource_folder(kind):
        if kind not in resource_types:
            raise HTTPException(404, "未知资源类型")
        folder = (Path(os.environ.get("VTUBER_BOOKS_DIR", str(root / "books")))
                  .expanduser().resolve() if kind == "books" else root / kind)
        folder.mkdir(parents=True, exist_ok=True)
        if kind != "books" and not folder.resolve().is_relative_to(root):
            raise HTTPException(400, "资源目录不可用")
        return folder

    @router.get("/resources")
    def resources():
        result = []
        for kind, extensions in resource_types.items():
            folder = resource_folder(kind)
            for path in sorted(folder.rglob("*")):
                name = path.relative_to(folder).as_posix()
                if (path.is_file() and path.suffix.lower() in extensions
                        and path.resolve().is_relative_to(folder.resolve())
                        and allowed(kind, name)):
                    result.append({"kind": kind, "path": name, "title": path.name,
                                   "size": path.stat().st_size})
        return result

    @router.post("/resources/{kind}")
    async def import_resource(kind: str, filename: str, request: Request):
        from .broadcast import LIVE
        if LIVE:
            raise HTTPException(403, "请在非直播模式下导入资源")
        folder = resource_folder(kind)
        if (not filename or filename in {".", ".."} or "/" in filename
                or "\\" in filename or any(ord(c) < 32 for c in filename)
                or len(filename.encode("utf-8")) > 220
                or Path(filename).suffix.lower() not in resource_types[kind]):
            raise HTTPException(400, "文件名或格式不支持")
        limit = (30 if kind == "books" else 500) * 1024 * 1024
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=folder, suffix=".upload", delete=False) as out:
                temp = Path(out.name)
                size = 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(413, f"文件不能超过 {limit // 1024 // 1024} MB")
                    out.write(chunk)
            if not size:
                raise HTTPException(400, "不能导入空文件")
            target = folder / filename
            index = 1
            while True:
                try:
                    os.link(temp, target)
                    break
                except FileExistsError:
                    target = folder / f"{Path(filename).stem} ({index}){Path(filename).suffix}"
                    index += 1
            return {"kind": kind, "path": target.name, "title": target.name, "size": size}
        finally:
            if temp:
                temp.unlink(missing_ok=True)

    @router.get("/resources/file/{kind}/{filename:path}")
    def resource_file(kind: str, filename: str):
        folder = resource_folder(kind)
        path = (folder / filename).resolve()
        if (not path.is_relative_to(folder.resolve()) or not path.is_file()
                or path.suffix.lower() not in resource_types[kind]
                or not allowed(kind, filename)):
            raise HTTPException(404, "资源不存在")
        return FileResponse(path)

    @router.get("/library")
    def library():
        return list_media(root)

    @router.get("/file/{kind}/{filename:path}")
    def media_file(kind: str, filename: str):
        return FileResponse(resolve(kind, filename))

    @router.get("/lyrics/{filename:path}")
    async def lyrics(filename: str):
        path = resolve("music", filename)
        engine = context.asr_engine
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg or not engine:
            raise HTTPException(503, "需要 FFmpeg 和可用的语音识别引擎")
        stat = path.stat()
        key = (path, stat.st_mtime_ns, stat.st_size, id(engine))
        async with lock:
            if key in cache:
                cache.move_to_end(key)
                return cache[key]
            try:
                pcm = await asyncio.to_thread(decode_audio, ffmpeg, path)
                result = []
                samples = np.frombuffer(pcm, dtype="<i2")
                window = 16000 * 10
                for offset in range(0, samples.size, window):
                    chunk = samples[offset : offset + window].astype(np.float32) / 32768
                    text = (await engine.async_transcribe_np(chunk)).strip()
                    if text:
                        result.append(
                            {
                                "start": offset / 16000,
                                "end": min(offset + window, samples.size) / 16000,
                                "text": text,
                            }
                        )
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                raise HTTPException(422, "无法转写音轨") from exc
            cache[key] = result
            if len(cache) > 16:
                cache.popitem(last=False)
            return result

    return router


def decode_audio(ffmpeg, path):
    return subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-t",
            "600",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "s16le",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=45,
    ).stdout
