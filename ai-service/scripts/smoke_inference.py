"""Run the frozen checkpoint against one actual W1 validation full-scene image."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
from src.service import create_app
from sample_snapshot import sample_snapshot


def main():
    data, spots, path = sample_snapshot()
    with TestClient(create_app()) as client:
        ready = client.get("/ready")
        ready.raise_for_status()
        response = client.post("/v1/infer", data={"camera_id": "UFPR04-DEMO", "spots_json": json.dumps(spots)},
                               files={"image": ("snapshot.jpg", data, "image/jpeg")})
        response.raise_for_status()
        result = response.json()
    print(json.dumps({"image": path, "image_bytes": len(data), "device": ready.json()["device"],
                      "model_version": result["model_version"], "threshold": result["threshold"],
                      "spot_count": len(spots), "processing_time_ms": result["processing_time_ms"],
                      "label_counts": dict(Counter(x["label"] for x in result["predictions"])),
                      "predictions": result["predictions"][:5]}, indent=2))


if __name__ == "__main__":
    main()
