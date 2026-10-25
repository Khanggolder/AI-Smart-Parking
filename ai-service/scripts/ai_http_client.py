"""Example backend-side HTTP client using a real snapshot and configured polygons."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def infer(url: str, image_path: Path, spots_path: Path, camera_id: str, timeout: float) -> dict:
    spots = json.loads(spots_path.read_text(encoding="utf-8"))
    if not isinstance(spots, list) or not spots:
        raise ValueError("Spots file must be a nonempty JSON array")
    requested_ids = [s["spot_id"] for s in spots]
    if len(set(requested_ids)) != len(requested_ids):
        raise ValueError("Duplicate spot IDs in input")
    content_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(image_path.suffix.lower())
    if content_type is None:
        raise ValueError("Image must be JPEG or PNG")
    with image_path.open("rb") as image, httpx.Client(timeout=timeout) as client:
        response = client.post(
            url.rstrip("/") + "/v1/infer",
            data={"camera_id": camera_id, "spots_json": json.dumps(spots)},
            files={"image": (image_path.name, image, content_type)},
        )
    response.raise_for_status()
    body = response.json()
    if body.get("camera_id") != camera_id or [p.get("spot_id") for p in body.get("predictions", [])] != requested_ids:
        raise ValueError("AI response camera/spot mapping mismatch")
    if not body.get("model_version") or body.get("threshold") is None:
        raise ValueError("AI response missing version/threshold")
    for prediction in body["predictions"]:
        if prediction.get("label") not in ("empty", "occupied", "unknown") or prediction.get("raw_label") not in ("empty", "occupied"):
            raise ValueError("AI response has unexpected label")
        if not isinstance(prediction.get("confidence"), (int, float)) or set(prediction.get("scores", {})) != {"empty", "occupied"}:
            raise ValueError("AI response has missing confidence/scores")
    return body


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--spots", type=Path, required=True)
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    print(json.dumps(infer(args.url, args.image, args.spots, args.camera_id, args.timeout), indent=2))
