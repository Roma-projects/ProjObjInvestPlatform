"""Для чего нужен этот файл:
Проверяет и сохраняет загруженные файлы, чтобы приложение могло использовать их после завершения запроса.
"""

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_BYTES = 10 * 1024 * 1024


async def save_upload(file: UploadFile, listing_id: int) -> str:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Unsupported content type: {file.content_type}")

    upload_root = Path(settings.upload_dir)
    listing_dir = upload_root / str(listing_id)
    listing_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "photo.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{suffix}"
    dest = listing_dir / filename

    size = 0
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 64):
            size += len(chunk)
            if size > MAX_SIZE_BYTES:
                dest.unlink(missing_ok=True)
                raise ValueError("File too large (max 10MB)")
            await out.write(chunk)

    relative = f"/uploads/{listing_id}/{filename}"
    logger.info("Saved upload %s (%s bytes)", relative, size)
    return relative
