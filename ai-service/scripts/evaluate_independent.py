"""Freeze an evaluation protocol, then make one official held-out test pass.

Commands, from repository root:
  python ai-service/scripts/evaluate_independent.py --freeze-only
  python ai-service/scripts/evaluate_independent.py --run-test
The second command refuses to overwrite any existing official result.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
sys.path.insert(0, str(SERVICE_ROOT))
from src.baseline_utils import CLASSES, assert_safe_splits, metrics_from_predictions, save_confusion_png
from src.confidence_utils import decide, selective_summary
from src.dataset import ParkingSpotDataset
from src.model_loader import MEAN, STD, ModelLoader, Settings

OUTPUT = SERVICE_ROOT / "runs/mobilenetv3_gpu/w5_evaluation"
FROZEN = OUTPUT / "frozen_evaluation_config.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_protocol() -> dict:
    settings = Settings.load()
    stats = assert_safe_splits(SERVICE_ROOT / "manifests")
    checkpoint = torch.load(settings.checkpoint, map_location="cpu", weights_only=True)
    saved = checkpoint.get("split_stats")
    if not isinstance(saved, dict) or any(saved[k]["sha256"] != stats[k]["sha256"] for k in ("train", "val", "test")):
        raise RuntimeError("Current split hashes differ from the W2 checkpoint")
    candidate = json.loads(settings.threshold_config.read_text(encoding="utf-8"))
    if candidate.get("val_manifest_sha256") != stats["val"]["sha256"]:
        raise RuntimeError("W3 validation manifest hash differs")
    loader = ModelLoader(settings)
    if loader.threshold != .9 or tuple(CLASSES) != ("empty", "occupied"):
        raise RuntimeError("Expected frozen W3 threshold 0.90 and class order")
    if stats["test"]["rows"] != 740:
        raise RuntimeError("Expected 740 held-out test crops")
    return {
        "protocol": "W5 independent held-out evaluation v1",
        "split": "test", "test_passes_planned": 1,
        "checkpoint_path": str(settings.checkpoint.resolve()),
        "checkpoint_sha256": loader.checkpoint_sha256,
        "threshold_config_path": str(settings.threshold_config.resolve()),
        "threshold_config_sha256": sha256(settings.threshold_config),
        "inference_yaml_sha256": sha256(SERVICE_ROOT / "configs/inference.yaml"),
        "manifest_stats": stats,
        "architecture": "mobilenet_v3_small", "model_version": loader.model_version,
        "class_order": list(CLASSES), "selected_epoch": checkpoint["selected_epoch"],
        "image_size": 224, "crop_mode": "mask", "input_source": "W1 saved JPEG crops",
        "normalization": {"mean": list(MEAN), "std": list(STD)},
        "unknown_threshold": loader.threshold,
        "unknown_rule": "max_softmax_probability < threshold",
        "batch_size": settings.batch_size, "device": str(loader.device),
        "torch_version": torch.__version__,
    }


def freeze() -> None:
    if FROZEN.exists():
        raise FileExistsError(f"Protocol already frozen: {FROZEN}")
    protocol = prepare_protocol()
    protocol["frozen_utc"] = datetime.now(timezone.utc).isoformat()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with FROZEN.open("x", encoding="utf-8") as handle:
        json.dump(protocol, handle, indent=2)
    print(f"FROZEN {FROZEN}")
    print(f"checkpoint={protocol['checkpoint_sha256']} test_manifest={protocol['manifest_stats']['test']['sha256']}")


def evaluate() -> None:
    if not FROZEN.is_file():
        raise RuntimeError("Freeze configuration before touching the test images")
    targets = [OUTPUT / x for x in ("test_predictions.csv", "test_metrics.json", "unknown_metrics.json", "test_confusion_matrix.png")]
    if any(x.exists() for x in targets):
        raise FileExistsError("Official test output exists; refusing a second test pass")
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    current = prepare_protocol()
    if any(current[k] != frozen[k] for k in current):
        raise RuntimeError("Frozen evaluation protocol differs from current inputs or settings")
    settings = Settings.load()
    loader = ModelLoader(settings)
    dataset = ParkingSpotDataset(SERVICE_ROOT / "manifests/test.csv", REPO_ROOT, train=False, size=224)
    dataloader = DataLoader(dataset, batch_size=frozen["batch_size"], shuffle=False, num_workers=0)
    probabilities = []
    # Dataset labels are carried for metrics only; ModelLoader.predict receives images alone.
    for images, _labels in dataloader:
        probabilities.extend(loader.predict(images).tolist())
    if len(probabilities) != 740:
        raise RuntimeError("Inference did not return all 740 samples")
    truth = [CLASSES.index(row["label"]) for row in dataset.rows]
    probs = np.asarray(probabilities, dtype=np.float64)
    raw = probs.argmax(1).tolist()
    metrics = metrics_from_predictions(truth, raw)
    metrics.update({
        "split": "test", "manifest_sha256": frozen["manifest_stats"]["test"]["sha256"],
        "checkpoint_sha256": loader.checkpoint_sha256,
        "macro_precision": sum(metrics["by_class"][c]["precision"] for c in CLASSES) / 2,
        "macro_recall": sum(metrics["by_class"][c]["recall"] for c in CLASSES) / 2,
        "false_empty": metrics["confusion_matrix"][1][0],
        "false_occupied": metrics["confusion_matrix"][0][1],
    })
    by_day = {}
    for day in sorted({row["date"] for row in dataset.rows}):
        indices = [i for i, row in enumerate(dataset.rows) if row["date"] == day]
        by_day[day] = metrics_from_predictions([truth[i] for i in indices], [raw[i] for i in indices])
    metrics["by_day"] = by_day
    threshold = frozen["unknown_threshold"]
    selective = selective_summary(truth, probs, threshold)
    cm = selective["confusion_matrix_true_rows_predicted_cols_empty_occupied_unknown"]
    selective.update({
        "unknown_rate": selective["unknown"] / len(truth),
        "accepted_error_count": cm[0][1] + cm[1][0],
        "accepted_error_rate_among_accepted": ((cm[0][1] + cm[1][0]) / selective["accepted"] if selective["accepted"] else None),
        "accepted_error_rate_all_samples": (cm[0][1] + cm[1][0]) / len(truth),
        "empty_recall_counting_unknown_as_miss": cm[0][0] / sum(cm[0]),
        "occupied_recall_counting_unknown_as_miss": cm[1][1] / sum(cm[1]),
    })
    rows = []
    for row, actual, pair in zip(dataset.rows, truth, probs, strict=True):
        choice = decide(float(pair[0]), float(pair[1]), threshold)
        accepted = choice["label"] != "unknown"
        rows.append({
            "crop_path": row["crop_path"], "image_file": row["image_file"],
            "date": row["date"], "camera": row["camera"], "annotation_id": row["annotation_id"],
            "true_label": CLASSES[actual], "raw_label": choice["raw_label"],
            "empty_score": float(pair[0]), "occupied_score": float(pair[1]),
            "confidence": choice["confidence"], "final_label": choice["label"],
            "accepted": accepted, "raw_correct": choice["raw_label"] == CLASSES[actual],
            "accepted_error": accepted and choice["raw_label"] != CLASSES[actual],
        })
    with targets[0].open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    targets[1].write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    targets[2].write_text(json.dumps(selective, indent=2), encoding="utf-8")
    save_confusion_png(metrics["confusion_matrix"], targets[3], "W5 independent test, raw classifier")
    print(json.dumps({"raw": {k: metrics[k] for k in ("accuracy", "macro_f1", "macro_precision", "macro_recall", "confusion_matrix", "false_empty", "false_occupied")},
                      "occupied": metrics["by_class"]["occupied"], "unknown": selective}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze-only", action="store_true")
    action.add_argument("--run-test", action="store_true")
    args = parser.parse_args()
    if args.freeze_only:
        freeze()
    else:
        evaluate()


if __name__ == "__main__":
    main()
