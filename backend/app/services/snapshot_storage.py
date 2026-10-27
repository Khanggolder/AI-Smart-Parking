"""Immutable, private snapshot storage with validated server-owned paths."""
import os
from pathlib import Path
from uuid import UUID, uuid4
from app.core.config import get_settings
from app.core.errors import APIError


def save_snapshot(snapshot_id: UUID, data: bytes, extension: str) -> tuple[str, Path]:
    root = get_settings().snapshot_image_root
    key = f"{snapshot_id.hex}/{uuid4().hex}{extension}"
    final = root / key
    tmp = final.parent / (".upload-" + uuid4().hex)
    try:
        final.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("xb") as stream:
            stream.write(data)
        os.replace(tmp, final)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise APIError(500, "SNAPSHOT_STORAGE_ERROR", "Unable to store snapshot") from None
    return key, final


def locate_snapshot(snapshot_id: UUID, key: str) -> Path:
    from re import fullmatch
    if not fullmatch(rf"{snapshot_id.hex}/[0-9a-f]{{32}}\.(jpg|png)", key):
        raise ValueError("Unsafe snapshot storage key")
    root = get_settings().snapshot_image_root
    path = (root / key).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise FileNotFoundError("Snapshot file missing")
    return path


def load_snapshot(snapshot_id: UUID, key: str) -> tuple[bytes, str]:
    path = locate_snapshot(snapshot_id, key)
    return path.read_bytes(), "image/jpeg" if path.suffix == ".jpg" else "image/png"
