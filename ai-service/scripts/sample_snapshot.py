"""Read one W1 validation snapshot for W4 smoke and load benchmarking only."""
from __future__ import annotations

import csv
import json
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent


def sample_snapshot() -> tuple[bytes, list[dict], str]:
    with (SERVICE_ROOT / "manifests/val.csv").open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    source = REPO_ROOT / "data/metapklot" / row["source_json"]
    metadata = json.loads(source.read_text(encoding="utf-8"))
    image = next(item for item in metadata["images"] if str(item["id"]) == row["image_id"])
    width, height = image["width"], image["height"]
    spots = []
    for ann in metadata["annotations"]:
        if ann["image_id"] != image["id"] or len(ann.get("segmentation", [])) != 1:
            continue
        flat = ann["segmentation"][0]
        polygon = [[flat[i] / (width - 1), flat[i + 1] / (height - 1)] for i in range(0, len(flat), 2)]
        # Demo IDs identify test inputs only; inference never sees annotation IDs or labels.
        spots.append({"spot_id": f"DEMO-{len(spots)+1:03d}", "polygon": polygon})
    path = REPO_ROOT / "data/metapklot" / image["file_name"]
    return path.read_bytes(), spots, str(path)
