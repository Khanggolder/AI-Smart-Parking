"""Private camera reference-image validation and storage helpers."""

from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4
import os

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import APIError

MAX_PIXELS = 20_000_000  # Matches the AI service image size limit.
MIME_TO_FORMAT = {"image/jpeg": ("JPEG", ".jpg"), "image/png": ("PNG", ".png")}


def validate_reference_image(data: bytes, declared_type: str | None) -> tuple[int, int, str]:
    settings = get_settings()
    if settings.upload_max_mb < 1 or settings.upload_max_mb > 100:
        raise APIError(503, "UPLOAD_NOT_CONFIGURED", "Invalid upload size limit")
    if not data:
        raise APIError(422, "INVALID_IMAGE", "Image is empty")
    if len(data) > settings.upload_max_mb * 1024 * 1024:
        raise APIError(413, "IMAGE_TOO_LARGE", "Image exceeds upload size limit")
    if declared_type not in MIME_TO_FORMAT:
        raise APIError(415, "UNSUPPORTED_IMAGE_TYPE", "Only JPEG and PNG are supported")
    expected_format, extension = MIME_TO_FORMAT[declared_type]
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != expected_format:
                raise APIError(415, "IMAGE_TYPE_MISMATCH", "Image content does not match Content-Type")
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                raise APIError(422, "INVALID_IMAGE_DIMENSIONS", "Image dimensions exceed 20 million pixels")
            image.verify()
        # Decoding the pixel data catches truncated files that pass header checks.
        with Image.open(BytesIO(data)) as image:
            image.load()
    except APIError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise APIError(422, "INVALID_IMAGE", "Image cannot be decoded") from None
    return width, height, extension


def save_reference_image(camera_id: UUID, data: bytes, extension: str) -> tuple[str, Path]:
    """Store immutable bytes under an unguessable key, never a client filename."""
    root = get_settings().reference_image_root
    directory = root / camera_id.hex
    key = f"{camera_id.hex}/{uuid4().hex}{extension}"
    final = root / key
    tmp = directory / (".upload-" + uuid4().hex)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tmp.open("xb") as handle:
            handle.write(data)
        os.replace(tmp, final)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise APIError(500, "IMAGE_STORAGE_ERROR", "Could not store reference image") from None
    return key, final


def locate_reference_image(camera_id: UUID, key: str | None) -> Path:
    """Reject traversal and data paths not generated for this camera."""
    if key is None:
        raise APIError(404, "REFERENCE_IMAGE_NOT_FOUND", "Camera has no reference image")
    from re import fullmatch
    if not fullmatch(rf"{camera_id.hex}/[0-9a-f]{{32}}\.(jpg|png)", key):
        raise APIError(404, "REFERENCE_IMAGE_NOT_FOUND", "Reference image is unavailable")
    root = get_settings().reference_image_root
    path = (root / key).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise APIError(404, "REFERENCE_IMAGE_NOT_FOUND", "Reference image is unavailable")
    return path
