"""
File Management API for Open-LLM-VTuber
========================================
Provides REST API endpoints for uploading, downloading, and managing files
between your local PC and RunPod deployment.
"""

import os
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger
import shutil

# Create router
router = APIRouter(prefix="/api/files", tags=["files"])

# Allowed directories for file operations (security)
ALLOWED_DIRS = {
    "characters": "characters",
    "chat_history": "chat_history",
    "cache": "cache",
    "avatars": "avatars",
    "backgrounds": "backgrounds",
    "configs": ".",  # Root for config files
}

# Max file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024


def is_safe_path(base_dir: str, filename: str) -> bool:
    """Check if the path is safe (no directory traversal)."""
    base = Path(base_dir).resolve()
    target = (base / filename).resolve()
    return str(target).startswith(str(base))


@router.get("/list/{directory}")
async def list_files(directory: str, subdirectory: Optional[str] = None):
    """
    List files in a directory.

    Examples:
    - GET /api/files/list/characters
    - GET /api/files/list/chat_history?subdirectory=user1
    """
    if directory not in ALLOWED_DIRS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to '{directory}' not allowed"
        )

    base_dir = ALLOWED_DIRS[directory]
    target_dir = Path(base_dir)

    if subdirectory:
        target_dir = target_dir / subdirectory
        if not is_safe_path(base_dir, subdirectory):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid path"
            )

    if not target_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Directory not found"
        )

    try:
        files = []
        for item in target_dir.iterdir():
            files.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": item.stat().st_mtime,
            })

        return JSONResponse({
            "directory": str(target_dir),
            "files": sorted(files, key=lambda x: (x["type"] != "directory", x["name"]))
        })
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/upload/{directory}")
async def upload_file(
    directory: str,
    file: UploadFile = File(...),
    subdirectory: Optional[str] = None
):
    """
    Upload a file to RunPod.

    Examples:
    - POST /api/files/upload/characters
    - POST /api/files/upload/chat_history?subdirectory=user1

    Usage:
        curl -X POST -F "file=@myconfig.yaml" \
            https://[POD-ID]-12393.proxy.runpod.net/api/files/upload/characters
    """
    if directory not in ALLOWED_DIRS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to '{directory}' not allowed"
        )

    base_dir = ALLOWED_DIRS[directory]
    target_dir = Path(base_dir)

    if subdirectory:
        target_dir = target_dir / subdirectory
        if not is_safe_path(base_dir, subdirectory):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid path"
            )

    # Create directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)"
        )

    # Save file
    file_path = target_dir / file.filename

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"File uploaded: {file_path}")

        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "path": str(file_path),
            "size": file_size
        })
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/download/{directory}/{filename}")
async def download_file(directory: str, filename: str, subdirectory: Optional[str] = None):
    """
    Download a file from RunPod.

    Examples:
    - GET /api/files/download/characters/mychar.yaml
    - GET /api/files/download/chat_history/log.json?subdirectory=user1

    Usage:
        curl -O https://[POD-ID]-12393.proxy.runpod.net/api/files/download/characters/mychar.yaml
    """
    if directory not in ALLOWED_DIRS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to '{directory}' not allowed"
        )

    base_dir = ALLOWED_DIRS[directory]
    target_dir = Path(base_dir)

    if subdirectory:
        target_dir = target_dir / subdirectory

    file_path = target_dir / filename

    if not is_safe_path(base_dir, str(file_path.relative_to(base_dir))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path"
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    logger.info(f"File downloaded: {file_path}")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@router.delete("/delete/{directory}/{filename}")
async def delete_file(directory: str, filename: str, subdirectory: Optional[str] = None):
    """
    Delete a file from RunPod.

    Examples:
    - DELETE /api/files/delete/characters/oldchar.yaml

    Usage:
        curl -X DELETE https://[POD-ID]-12393.proxy.runpod.net/api/files/delete/characters/oldchar.yaml
    """
    if directory not in ALLOWED_DIRS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to '{directory}' not allowed"
        )

    base_dir = ALLOWED_DIRS[directory]
    target_dir = Path(base_dir)

    if subdirectory:
        target_dir = target_dir / subdirectory

    file_path = target_dir / filename

    if not is_safe_path(base_dir, str(file_path.relative_to(base_dir))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path"
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    try:
        if file_path.is_file():
            file_path.unlink()
        else:
            shutil.rmtree(file_path)

        logger.info(f"File deleted: {file_path}")

        return JSONResponse({
            "status": "success",
            "message": f"Deleted {filename}"
        })
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/info")
async def get_info():
    """Get information about available directories and disk usage."""
    info = {
        "allowed_directories": list(ALLOWED_DIRS.keys()),
        "max_file_size_mb": MAX_FILE_SIZE // 1024 // 1024,
    }

    try:
        # Get disk usage
        import shutil as sh
        total, used, free = sh.disk_usage("/")
        info["disk"] = {
            "total_gb": total // (2**30),
            "used_gb": used // (2**30),
            "free_gb": free // (2**30),
            "percent_used": round((used / total) * 100, 1)
        }
    except:
        pass

    return JSONResponse(info)
