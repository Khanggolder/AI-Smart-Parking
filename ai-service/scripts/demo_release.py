"""Exercise the extracted W6 ZIP through actual localhost HTTP endpoints."""
from __future__ import annotations

from collections import Counter
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from zipfile import ZipFile

import cv2
import httpx
import numpy as np

from ai_http_client import infer
from sample_snapshot import sample_snapshot
from verify_release import verify

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v0.1.0-rc1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=("v0.1.0-rc1", "v0.1.0-rc2"), default=VERSION)
    args = parser.parse_args()
    version = args.version
    zip_path = ROOT / "releases" / f"ai-smart-parking-model-{version}.zip"
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    data, spots, image_path = sample_snapshot()
    if len(spots) != 37 or len({s["spot_id"] for s in spots}) != 37:
        raise ValueError("Expected 37 distinct validation polygons")
    picture = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    height, width = picture.shape[:2]
    for spot in spots:
        pts = np.rint(np.asarray(spot["polygon"]) * [width - 1, height - 1]).astype(np.int32)
        cv2.polylines(picture, [pts], True, (0, 255, 255), 2)
    output_dir = ROOT / ("runs/w6_demo" if version == VERSION else "runs/w7_demo")
    overlay_path = output_dir / "roi_overlay.jpg"
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(overlay_path), picture)
    with tempfile.TemporaryDirectory(prefix="ai-release-") as temp:
        temp_root = Path(temp)
        with ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP CRC error")
            archive.extractall(temp_root)
        release = temp_root / version
        verified = verify(release)
        source_hash = hashlib.sha256((release / "model/best.pt").read_bytes()).hexdigest()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, AI_DEVICE="cuda")
        command = [sys.executable, "-m", "uvicorn", "src.service:app", "--app-dir", str(release),
                   "--host", "127.0.0.1", "--port", str(port)]
        server = subprocess.Popen(command, cwd=release, env=env, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        url = f"http://127.0.0.1:{port}"
        try:
            with httpx.Client(timeout=5) as client:
                deadline = time.monotonic() + 30
                while True:
                    if server.poll() is not None:
                        raise RuntimeError(f"Release server exited: {server.stderr.read().decode(errors='replace')}")
                    try:
                        health = client.get(url + "/health")
                        ready = client.get(url + "/ready")
                        if health.status_code == 200 and ready.status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        raise TimeoutError("Release server did not become ready")
                    time.sleep(.2)
                manifest = json.loads((release / "release_manifest.json").read_text(encoding="utf-8"))
                if ready.json()["model_version"] != manifest["model_version"] or ready.json()["threshold"] != .9:
                    raise ValueError("Readiness release identity mismatch")
                with tempfile.TemporaryDirectory(prefix="ai-input-") as input_temp:
                    image_file = Path(input_temp) / "snapshot.jpg"
                    spots_file = Path(input_temp) / "spots.json"
                    image_file.write_bytes(data)
                    spots_file.write_text(json.dumps(spots), encoding="utf-8")
                    result = infer(url, image_file, spots_file, "UFPR04-DEMO", 15)
                if len(result["predictions"]) != 37 or result["model_version"] != manifest["model_version"]:
                    raise ValueError("37-spot response mismatch")
                invalid = client.post(url + "/v1/infer", data={"camera_id": "UFPR04-DEMO", "spots_json": json.dumps([
                    {"spot_id": "BAD", "polygon": [[0, 0], [1, 1], [0, 1], [1, 0]]}])},
                    files={"image": ("snapshot.jpg", data, "image/jpeg")})
                if invalid.status_code != 422 or invalid.json()["error"]["code"] != "INVALID_POLYGON":
                    raise ValueError("Invalid polygon did not return expected 422")
                with (ROOT / "runs/mobilenetv3_gpu/confidence/val_predictions.csv").open(newline="", encoding="utf-8") as handle:
                    low_score = next(row for row in csv.DictReader(handle) if row["is_unknown"] == "True")
                # Development crop only. Full-frame polygon passes its 224x224 saved JPEG to the same model path.
                crop_path = ROOT.parent / low_score["crop_path"]
                unknown = client.post(url + "/v1/infer", data={"camera_id": "UFPR04-DEMO",
                    "spots_json": json.dumps([{"spot_id": "LOW-SCORE-DEV", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]}])},
                    files={"image": (crop_path.name, crop_path.read_bytes(), "image/jpeg")})
                if unknown.status_code != 200 or unknown.json()["predictions"][0]["label"] != "unknown":
                    raise ValueError("Development low-score crop did not produce UNKNOWN")
                broken_image = client.post(url + "/v1/infer", data={"camera_id": "UFPR04-DEMO", "spots_json": json.dumps(spots[:1])},
                    files={"image": ("bad.jpg", b"bad", "image/jpeg")})
                if broken_image.status_code != 422 or broken_image.json()["error"]["code"] != "INVALID_IMAGE":
                    raise ValueError("Malformed image was not rejected with 422")
                if hashlib.sha256((release / "model/best.pt").read_bytes()).hexdigest() != source_hash:
                    raise ValueError("Checkpoint changed during service run")
                report = {"release": version, "zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
                          "verified_files": verified["files"], "checkpoint_sha256": source_hash,
                          "health": health.json(), "ready": ready.json(), "camera_id": result["camera_id"],
                          "image": image_path, "spot_count": len(result["predictions"]),
                          "spot_ids_preserved": [p["spot_id"] for p in result["predictions"]] == [s["spot_id"] for s in spots],
                          "response_fields": sorted(result),
                          "prediction_fields": sorted(result["predictions"][0]),
                          "label_counts": dict(Counter(p["label"] for p in result["predictions"])),
                          "processing_time_ms": result["processing_time_ms"],
                          "invalid_polygon_status": invalid.status_code,
                          "invalid_polygon_code": invalid.json()["error"]["code"],
                          "unknown_dev_crop": low_score["crop_path"],
                          "unknown_prediction": unknown.json()["predictions"][0],
                          "invalid_image_status": broken_image.status_code,
                          "invalid_image_code": broken_image.json()["error"]["code"],
                          "roi_overlay": str(overlay_path)}
                (output_dir / "smoke_result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(report, indent=2))
        finally:
            server.terminate()
            try:
                server.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.communicate(timeout=10)


if __name__ == "__main__":
    main()
