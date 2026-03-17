"""Image upload endpoint — stores files locally and returns URL."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "application/pdf",
}


@router.post("/upload")
async def upload_file(file: UploadFile):
    """Upload an image file. Returns the URL path."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "png"
    filename = f"{uuid.uuid4()}.{ext}"
    path = UPLOAD_DIR / filename
    path.write_bytes(data)

    logger.info("Uploaded %s (%d bytes)", filename, len(data))
    return {"url": f"/uploads/{filename}"}
