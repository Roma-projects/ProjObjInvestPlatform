"""Safe storage helpers for user-uploaded profile pictures."""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_AVATAR_PIXELS = 20_000_000
AVATAR_SIZE = (512, 512)
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def store_avatar(content: bytes, root: Path) -> str:
    """Decode and re-encode supported raster images to strip active content/metadata."""
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in ALLOWED_FORMATS:
                raise HTTPException(status_code=415, detail="Avatar must be a JPEG, PNG or WebP image")
            if image.width * image.height > MAX_AVATAR_PIXELS:
                raise HTTPException(status_code=413, detail="Avatar image dimensions are too large")
            image.verify()

        with Image.open(io.BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(AVATAR_SIZE, Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            output = io.BytesIO()
            image.save(output, format="PNG", optimize=True)
    except HTTPException:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, Image.DecompressionBombError):
            raise HTTPException(status_code=413, detail="Avatar image dimensions are too large") from exc
        raise HTTPException(status_code=415, detail="Invalid or unsupported avatar image") from exc

    root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    target = (root / filename).resolve()
    if target.parent != root.resolve():
        raise HTTPException(status_code=500, detail="Avatar storage path is invalid")
    target.write_bytes(output.getvalue())
    return f"/public/avatars/{filename}"


def delete_avatar(public_path: str, root: Path) -> None:
    """Remove only a generated avatar file located directly in the configured folder."""
    prefix = "/public/avatars/"
    if not public_path.startswith(prefix):
        return
    filename = public_path.removeprefix(prefix)
    if not filename or Path(filename).name != filename:
        return
    root_resolved = root.resolve()
    target = (root_resolved / filename).resolve()
    if target.parent == root_resolved:
        target.unlink(missing_ok=True)