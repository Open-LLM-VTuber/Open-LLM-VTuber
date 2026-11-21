"""Book extraction and sequential speech endpoints for the browser reader."""

import asyncio
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

MAX_SIZE = 30 * 1024 * 1024


def extract_book(data: bytes, suffix: str) -> list[str]:
    if suffix == ".txt":
        for encoding in ("utf-8-sig", "utf-16", "gb18030"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeError:
                continue
        else:
            raise ValueError("无法识别 TXT 编码，请转换为 UTF-8")
    elif suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("请先解密 PDF")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".epub":
        import posixpath

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
                raise ValueError("EPUB 解压后过大")
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            package_path = next(
                e.attrib["full-path"]
                for e in container.iter()
                if e.tag.endswith("}rootfile")
            )
            package = ET.fromstring(archive.read(package_path))
            manifest = {
                e.attrib["id"]: e.attrib
                for e in package.iter()
                if e.tag.endswith("}item")
            }
            parts = []
            for entry in package.iter():
                if not entry.tag.endswith("}itemref"):
                    continue
                item = manifest[entry.attrib["idref"]]
                if item.get("media-type") != "application/xhtml+xml":
                    continue
                path = posixpath.normpath(
                    posixpath.join(
                        posixpath.dirname(package_path), item["href"].split("#")[0]
                    )
                )
                root = ET.fromstring(archive.read(path))
                body = next((e for e in root.iter() if e.tag.endswith("}body")), root)
                parts.append(" ".join(body.itertext()))
            text = "\n".join(parts)
    else:
        raise ValueError("仅支持 PDF、EPUB、TXT")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError("未提取到文字；扫描版 PDF 需要先进行 OCR")
    # Bound synthesis requests even when a book has no punctuation.
    chunks = []
    for sentence in re.split(r"(?<=[。！？.!?；;])", text):
        sentence = sentence.strip()
        while sentence:
            chunks.append(sentence[:240])
            sentence = sentence[240:]
    return chunks


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=240)


def init_book_routes(context) -> APIRouter:
    router = APIRouter()
    speech_lock = asyncio.Lock()

    @router.get("/reader")
    async def reader():
        return FileResponse(Path(__file__).with_name("reader.html"))

    @router.post("/api/reader/import")
    async def import_book(file: UploadFile = File(...)):
        from .broadcast import LIVE
        if LIVE:
            raise HTTPException(403, "直播模式不开放临时书籍导入")
        try:
            data = await file.read(MAX_SIZE + 1)
            if len(data) > MAX_SIZE:
                raise HTTPException(413, "书籍不能超过 30 MB")
            chunks = await asyncio.to_thread(
                extract_book, data, Path(file.filename or "").suffix.lower()
            )
            return {"title": file.filename, "chunks": chunks}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(400, f"无法读取书籍：{exc}") from exc
        finally:
            await file.close()

    @router.post("/api/reader/speech")
    async def speech(request: SpeechRequest):
        from .broadcast import LIVE
        if LIVE:
            raise HTTPException(403, "直播模式请通过获准书库阅读")
        async with speech_lock:
            engine = context.tts_engine
            path = await engine.async_generate_audio(
                request.text, file_name_no_ext=f"reader_{uuid4().hex}"
            )
            if not path or not Path(path).is_file():
                raise HTTPException(502, "语音生成失败")
            try:
                audio = await asyncio.to_thread(Path(path).read_bytes)
                suffix = Path(path).suffix.lower()
            except BaseException:
                engine.remove_file(path)
                raise
            return Response(
                audio,
                media_type={
                    ".wav": "audio/wav",
                    ".mp3": "audio/mpeg",
                    ".ogg": "audio/ogg",
                }.get(suffix, "application/octet-stream"),
                background=BackgroundTask(engine.remove_file, path),
            )

    return router
