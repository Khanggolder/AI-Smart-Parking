"""Validate normalized spot polygons and apply the original W1 crop pipeline."""
from __future__ import annotations

from io import BytesIO

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
import torch
from torchvision import transforms

from .model_loader import MEAN, STD
from .w1_crop import make_crop


class InputError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=MEAN, std=STD),
])


def decode_image(data: bytes, max_pixels: int) -> np.ndarray:
    if not data:
        raise InputError("EMPTY_IMAGE", "Image file is empty")
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in ("JPEG", "PNG"):
                raise InputError("INVALID_IMAGE", "Only JPEG and PNG images are supported")
            width, height = image.size
            if width < 3 or height < 3 or width * height > max_pixels:
                raise InputError("IMAGE_DIMENSIONS", "Image dimensions are unsupported or exceed the pixel limit")
            # W1 reads original snapshots with OpenCV, so keep BGR channel order here.
            decoded = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if decoded is None or decoded.shape[:2] != (height, width):
                raise InputError("INVALID_IMAGE", "Could not decode image")
            return decoded
    except (UnidentifiedImageError, OSError, cv2.error) as exc:
        raise InputError("INVALID_IMAGE", "Could not decode JPEG/PNG image") from exc


def _orient(a, b, c):
    return (b[0]-a[0]) * (c[1]-a[1]) - (b[1]-a[1]) * (c[0]-a[0])


def _on_segment(a, b, c):
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def _intersect(a, b, c, d):
    o1, o2, o3, o4 = _orient(a,b,c), _orient(a,b,d), _orient(c,d,a), _orient(c,d,b)
    if (o1 > 0 > o2 or o2 > 0 > o1) and (o3 > 0 > o4 or o4 > 0 > o3):
        return True
    return any((o == 0 and _on_segment(x,y,z)) for o,x,y,z in ((o1,a,b,c),(o2,a,b,d),(o3,c,d,a),(o4,c,d,b)))


def polygon_pixels(polygon: object, width: int, height: int) -> np.ndarray:
    if not isinstance(polygon, list) or not 3 <= len(polygon) <= 50:
        raise InputError("INVALID_POLYGON", "Polygon needs 3 to 50 points")
    try:
        if any(not isinstance(p, (list, tuple)) or len(p) != 2 or any(isinstance(v, bool) or not isinstance(v, (int,float)) for v in p) for p in polygon):
            raise ValueError()
        points = np.asarray(polygon, dtype=np.float64)
        if not np.isfinite(points).all() or (points < 0).any() or (points > 1).any():
            raise ValueError()
    except (ValueError, TypeError):
        raise InputError("INVALID_POLYGON", "Polygon coordinates must be finite numbers in [0, 1]")
    if abs(float(np.dot(points[:, 0], np.roll(points[:, 1], -1)) -
                 np.dot(points[:, 1], np.roll(points[:, 0], -1)))) <= 1e-10:
        raise InputError("INVALID_POLYGON", "Polygon has degenerate area")
    # [0, 1] maps to the first and last pixels of each axis.
    pixels = np.rint(points * [width - 1, height - 1]).astype(np.int32)
    coords = [tuple(p) for p in pixels.tolist()]
    if len(set(coords)) != len(coords):
        raise InputError("INVALID_POLYGON", "Polygon has repeated points after pixel conversion")
    n = len(coords)
    for i in range(n):
        a, b = coords[i], coords[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or j == (i + 1) % n or i == (j + 1) % n:
                continue
            if _intersect(a, b, coords[j], coords[(j + 1) % n]):
                raise InputError("INVALID_POLYGON", "Polygon self-intersects")
    if cv2.contourArea(pixels) <= 1:
        raise InputError("INVALID_POLYGON", "Polygon has degenerate pixel area")
    x,y,w,h = cv2.boundingRect(pixels)
    if w < 3 or h < 3:
        raise InputError("INVALID_POLYGON", "Polygon bounding box is too small")
    return pixels


def validate_spots(spots: object, max_spots: int) -> list[dict]:
    if not isinstance(spots, list) or not 1 <= len(spots) <= max_spots:
        raise InputError("INVALID_SPOTS", f"Expected 1 to {max_spots} spots")
    seen = set()
    for spot in spots:
        if not isinstance(spot, dict) or not isinstance(spot.get("spot_id"), str) or not spot["spot_id"].strip() or len(spot["spot_id"]) > 128:
            raise InputError("INVALID_SPOTS", "Every spot needs a nonempty spot_id of at most 128 characters")
        if spot["spot_id"] in seen:
            raise InputError("DUPLICATE_SPOT_ID", f"Duplicate spot_id: {spot['spot_id']}")
        seen.add(spot["spot_id"])
        if "polygon" not in spot:
            raise InputError("INVALID_POLYGON", f"Missing polygon for {spot['spot_id']}")
    return spots


def preprocess(image_bgr: np.ndarray, spots: list[dict]) -> torch.Tensor:
    height, width = image_bgr.shape[:2]
    polygons = [polygon_pixels(spot["polygon"], width, height) for spot in spots]
    tensors = []
    for polygon in polygons:
        crop_bgr = make_crop(image_bgr, [polygon], size=224, mode="mask")
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        tensors.append(TRANSFORM(Image.fromarray(crop_rgb)))
    return torch.stack(tensors)
