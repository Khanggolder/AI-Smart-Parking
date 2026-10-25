"""Measure real full-scene preprocessing and batched inference latency."""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import sys

import torch
from PIL import Image
from io import BytesIO

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
from src.inference import InferenceEngine
from src.model_loader import ModelLoader, Settings
from sample_snapshot import sample_snapshot


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    low = int(pos)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (pos - low)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="auto")
    parser.add_argument("--output", type=Path, default=SERVICE_ROOT / "runs/mobilenetv3_gpu/w4_benchmark.json")
    args = parser.parse_args()
    if args.runs < 2 or args.warmup < 1:
        parser.error("--runs must be >= 2 and --warmup >= 1")
    import dataclasses
    settings = dataclasses.replace(Settings.load(), device=args.device)
    engine = InferenceEngine(ModelLoader(settings))
    data, source_spots, source_path = sample_snapshot()
    with Image.open(BytesIO(data)) as reference:
        image_size = f"{reference.width}x{reference.height}"
    if not source_spots:
        raise RuntimeError("Reference snapshot has no polygons")
    results = {}
    for count in (1, 10, 50, 100):
        spots = [{"spot_id": f"BENCH-{i+1:03d}", "polygon": source_spots[i % len(source_spots)]["polygon"]} for i in range(count)]
        if engine.loader.device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(engine.loader.device)
        for _ in range(args.warmup):
            engine.infer(data, spots)
        measured = [engine.infer(data, spots) for _ in range(args.runs)]
        results[str(count)] = {
            "preprocess_p50_ms": percentile([x.preprocess_ms for x in measured], .5),
            "model_p50_ms": percentile([x.model_ms for x in measured], .5),
            "total_p50_ms": percentile([x.total_ms for x in measured], .5),
            "total_p95_ms": percentile([x.total_ms for x in measured], .95),
            "max_total_ms": max(x.total_ms for x in measured),
            "peak_gpu_allocated_bytes": (torch.cuda.max_memory_allocated(engine.loader.device) if engine.loader.device.type == "cuda" else None),
        }
    report = {"source_image": source_path, "reference_image_size": image_size,
              "source_polygon_count": len(source_spots),
              "method": "50/100 load cases cycle available validation polygons with unique benchmark IDs",
              "runs_per_case": args.runs, "warmup_per_case": args.warmup,
              "device": str(engine.loader.device), "cpu": platform.processor(),
              "gpu": torch.cuda.get_device_name(engine.loader.device) if engine.loader.device.type == "cuda" else None,
              "torch": torch.__version__, "batch_size": settings.batch_size,
              "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
