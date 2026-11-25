from pathlib import Path

import pytest
from fastapi import HTTPException
from PIL import Image

from app.services.business_listing_service import _validate_and_sanitize_file


def test_valid_jpeg_without_n_frames_attribute_is_accepted(tmp_path: Path) -> None:
    image_path = tmp_path / "photo.jpg"
    Image.new("RGB", (16, 16), color="red").save(image_path, format="JPEG")

    _validate_and_sanitize_file(image_path, ".jpg", "image/jpeg")

    with Image.open(image_path) as image:
        assert image.format == "JPEG"
        assert image.size == (16, 16)


def test_animated_webp_is_rejected(tmp_path: Path) -> None:
    image_path = tmp_path / "animated.webp"
    frames = [Image.new("RGB", (8, 8), color=color) for color in ("red", "blue")]
    frames[0].save(image_path, format="WEBP", save_all=True, append_images=frames[1:])

    with pytest.raises(HTTPException) as error:
        _validate_and_sanitize_file(image_path, ".webp", "image/webp")

    assert error.value.status_code == 415