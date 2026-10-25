"""W1 polygon mask, bounding box and letterbox crop shared by dataset and inference."""
from __future__ import annotations

import cv2
import numpy as np


def make_crop(img: np.ndarray, polygons: list[np.ndarray], size: int, mode: str) -> np.ndarray:
    """Polygon mask + axis-aligned crop, letterboxed without shape distortion."""
    pts = np.concatenate(polygons, axis=0)
    x, y, w, h = cv2.boundingRect(pts)
    if w < 3 or h < 3:
        raise ValueError("Degenerate crop bounding box")
    region = img[y:y+h, x:x+w].copy()
    if mode == "mask":
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.fillPoly(mask, polygons, 255)
        inner = mask[y:y+h, x:x+w]
        region[inner == 0] = (114, 114, 114)
    scale = min(size / w, size / h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = cv2.resize(region, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    dst = np.full((size, size, 3), 114, dtype=np.uint8)
    ox, oy = (size - nw)//2, (size - nh)//2
    dst[oy:oy+nh, ox:ox+nw] = resized
    return dst
