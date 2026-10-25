"""Audit frozen W5 artifacts without making another test inference pass."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/mobilenetv3_gpu/w5_evaluation"


def read_results():
    frozen = json.loads((OUT / "frozen_evaluation_config.json").read_text(encoding="utf-8"))
    with (OUT / "test_predictions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    raw = json.loads((OUT / "test_metrics.json").read_text(encoding="utf-8"))
    selective = json.loads((OUT / "unknown_metrics.json").read_text(encoding="utf-8"))
    return frozen, rows, raw, selective


def test_frozen_sources_and_test_rows():
    frozen, rows, raw, selective = read_results()
    assert frozen["test_passes_planned"] == 1
    assert frozen["unknown_threshold"] == .9
    assert frozen["class_order"] == ["empty", "occupied"]
    assert frozen["manifest_stats"]["test"]["sha256"] == hashlib.sha256((ROOT / "manifests/test.csv").read_bytes()).hexdigest()
    assert frozen["checkpoint_sha256"] == hashlib.sha256((ROOT / "runs/mobilenetv3_gpu/best.pt").read_bytes()).hexdigest()
    assert len(rows) == 740 == raw["total"] == selective["total"]
    assert len({r["crop_path"] for r in rows}) == 740
    assert {r["date"] for r in rows} == {"2012-12-21", "2012-12-24"}


def test_threshold_and_metrics_reconcile_without_model_execution():
    frozen, rows, raw, selective = read_results()
    for row in rows:
        scores = [float(row["empty_score"]), float(row["occupied_score"])]
        assert sum(scores) == pytest.approx(1, abs=1e-5)
        assert max(scores) == pytest.approx(float(row["confidence"]), abs=1e-7)
        assert row["raw_label"] == frozen["class_order"][scores.index(max(scores))]
        assert row["final_label"] == (row["raw_label"] if max(scores) >= .9 else "unknown")
        assert (row["accepted"] == "True") == (row["final_label"] != "unknown")
        assert (row["raw_correct"] == "True") == (row["true_label"] == row["raw_label"])
    assert sum(r["raw_correct"] == "False" for r in rows) == raw["false_empty"] + raw["false_occupied"]
    assert sum(r["accepted"] == "False" for r in rows) == selective["unknown"]
    assert sum(r["accepted_error"] == "True" for r in rows) == selective["accepted_error_count"]
    assert sum(sum(line) for line in raw["confusion_matrix"]) == 740
    assert sum(sum(line) for line in selective["confusion_matrix_true_rows_predicted_cols_empty_occupied_unknown"]) == 740


def test_inference_ignores_supplied_annotation_label(monkeypatch):
    import sys
    import torch
    sys.path.insert(0, str(ROOT))
    import src.inference as inference
    from src.model_loader import Settings
    monkeypatch.setattr(inference, "decode_image", lambda data, limit: object())
    monkeypatch.setattr(inference, "preprocess", lambda image, spots: torch.zeros(len(spots),3,224,224))

    class FixedModel:
        settings = Settings.load()
        device = torch.device("cpu")
        threshold = .9
        model_version = "fixed"

        def predict(self, batch):
            return torch.tensor([[.05,.95]] * len(batch))

    engine = inference.InferenceEngine(FixedModel())
    spot = {"spot_id":"A", "polygon":[]}
    original = engine.infer(b"image", [spot]).predictions
    injected = engine.infer(b"image", [{**spot, "label":"empty", "ground_truth":"empty"}]).predictions
    assert injected == original
    assert injected[0]["label"] == "occupied"
