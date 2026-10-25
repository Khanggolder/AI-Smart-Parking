"""Capture and compare the W7 validation HTTP response without test labels."""
from __future__ import annotations

import argparse
import csv
import json
from math import isclose
from pathlib import Path
import sys

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
from src.service import create_app
from sample_snapshot import sample_snapshot


def capture() -> dict:
    image, spots, image_path = sample_snapshot()
    assert len(spots) == 37 and len({spot["spot_id"] for spot in spots}) == 37
    with TestClient(create_app()) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        response = client.post(
            "/v1/infer",
            data={"camera_id": "UFPR04-DEMO", "spots_json": json.dumps(spots)},
            files={"image": ("snapshot.jpg", image, "image/jpeg")},
        )
        invalid_polygon = client.post(
            "/v1/infer",
            data={"camera_id": "UFPR04-DEMO", "spots_json": json.dumps([
                {"spot_id": "BAD", "polygon": [[0, 0], [1, 1], [0, 1], [1, 0]]},
            ])},
            files={"image": ("snapshot.jpg", image, "image/jpeg")},
        )
        invalid_image = client.post(
            "/v1/infer",
            data={"camera_id": "UFPR04-DEMO", "spots_json": json.dumps(spots[:1])},
            files={"image": ("bad.jpg", b"bad", "image/jpeg")},
        )
        with (SERVICE_ROOT / "runs/mobilenetv3_gpu/confidence/val_predictions.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            low_score = next(row for row in csv.DictReader(handle) if row["is_unknown"] == "True")
        crop_path = SERVICE_ROOT.parent / low_score["crop_path"]
        unknown = client.post(
            "/v1/infer",
            data={"camera_id": "UFPR04-DEMO", "spots_json": json.dumps([
                {"spot_id": "LOW-SCORE-DEV", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]},
            ])},
            files={"image": (crop_path.name, crop_path.read_bytes(), "image/jpeg")},
        )
    for result in (health, ready, response, invalid_polygon, invalid_image, unknown):
        if result.status_code not in (200, 422):
            raise AssertionError(f"Unexpected status: {result.status_code} {result.text}")
    body = response.json()
    if [prediction["spot_id"] for prediction in body["predictions"]] != [spot["spot_id"] for spot in spots]:
        raise AssertionError("37 spot IDs or order changed")
    if unknown.json()["predictions"][0]["label"] != "unknown":
        raise AssertionError("Development low-confidence crop did not abstain")
    body.pop("processing_time_ms")
    unknown_body = unknown.json()
    unknown_body.pop("processing_time_ms")
    return {
        "image": image_path,
        "health": [health.status_code, health.json()],
        "ready": [ready.status_code, ready.json()],
        "infer": [response.status_code, body],
        "unknown": [unknown.status_code, unknown_body],
        "invalid_polygon": [invalid_polygon.status_code, invalid_polygon.json()],
        "invalid_image": [invalid_image.status_code, invalid_image.json()],
    }


def equivalent(before: object, after: object, path: str = "response") -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        if before.keys() != after.keys():
            raise AssertionError(f"{path}: keys changed")
        for key in before:
            equivalent(before[key], after[key], f"{path}.{key}")
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            raise AssertionError(f"{path}: length changed")
        for index, (left, right) in enumerate(zip(before, after, strict=True)):
            equivalent(left, right, f"{path}[{index}]")
    elif isinstance(before, float) and isinstance(after, float):
        if not isclose(before, after, rel_tol=1e-6, abs_tol=1e-6):
            raise AssertionError(f"{path}: {before} != {after}")
    elif before != after:
        raise AssertionError(f"{path}: {before!r} != {after!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    actual = capture()
    if args.compare:
        equivalent(json.loads(args.compare.read_text(encoding="utf-8")), actual)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "MATCH" if args.compare else "CAPTURED",
                      "spots": len(actual["infer"][1]["predictions"]),
                      "device": actual["ready"][1]["device"],
                      "model_version": actual["ready"][1]["model_version"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
