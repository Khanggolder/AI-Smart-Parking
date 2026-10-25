"""W5 local engine and real HTTP benchmark with a full-scene validation image."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import gc
import json
import os
import platform
from pathlib import Path
import socket
import subprocess
import sys
from time import perf_counter, sleep

import httpx
from PIL import Image
import torch
import torchvision

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
sys.path.insert(0, str(SERVICE_ROOT))
from src.inference import InferenceEngine
from src.model_loader import ModelLoader, Settings
from sample_snapshot import sample_snapshot


def quantile(values: list[float], q: float) -> float:
    sorted_values = sorted(values)
    at = (len(sorted_values) - 1) * q
    low = int(at)
    return sorted_values[low] + (sorted_values[min(low + 1, len(values) - 1)] - sorted_values[low]) * (at - low)


def summary(values: list[float]) -> dict:
    return {"p50_ms": quantile(values, .5), "p95_ms": quantile(values, .95),
            "max_ms": max(values)}


def spots_for(source: list[dict], count: int) -> list[dict]:
    return [{"spot_id": f"BENCH-{i+1:03d}", "polygon": source[i % len(source)]["polygon"]}
            for i in range(count)]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, choices=("cpu", "cuda"))
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runs < 2 or args.warmup < 1:
        parser.error("runs >= 2 and warmup >= 1 required")
    settings = replace(Settings.load(), device=args.device)
    data, source_spots, image_path = sample_snapshot()
    if len(source_spots) != 37:
        raise RuntimeError("Expected 37 distinct source polygons in the reference image")
    with Image.open(image_path) as image:
        image_size = [image.width, image.height]
    count_list = (1, 10, 37, 50, 100)
    t0 = perf_counter()
    loader = ModelLoader(settings)
    model_load_ms = (perf_counter() - t0) * 1000
    engine = InferenceEngine(loader)
    engine_results = {}
    for count in count_list:
        spots = spots_for(source_spots, count)
        for _ in range(args.warmup):
            engine.infer(data, spots)
        if args.device == "cuda":
            torch.cuda.reset_peak_memory_stats(loader.device)
        measured = [engine.infer(data, spots) for _ in range(args.runs)]
        engine_results[str(count)] = {
            "workload": "real_distinct_polygons" if count <= 37 else "synthetic_workload_repeated_polygons",
            "preprocessing": summary([x.preprocess_ms for x in measured]),
            "model": summary([x.model_ms for x in measured]),
            "total": summary([x.total_ms for x in measured]),
            "peak_gpu_allocated_bytes": (torch.cuda.max_memory_allocated(loader.device) if args.device == "cuda" else None),
        }
    del engine, loader
    gc.collect()
    if args.device == "cuda":
        torch.cuda.empty_cache()

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["AI_DEVICE"] = args.device
    command = [sys.executable, "-m", "uvicorn", "src.service:app", "--app-dir", "ai-service",
               "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--log-level", "error"]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    startup = perf_counter()
    server = subprocess.Popen(command, cwd=REPO_ROOT, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              creationflags=creationflags)
    try:
        with httpx.Client(timeout=30) as client:
            for _ in range(600):
                if server.poll() is not None:
                    raise RuntimeError(f"Uvicorn exited early with code {server.returncode}")
                try:
                    ready = client.get(base + "/ready")
                    if ready.status_code == 200:
                        break
                except httpx.RequestError:
                    pass
                sleep(.1)
            else:
                raise TimeoutError("Uvicorn readiness timed out")
            server_ready_ms = (perf_counter() - startup) * 1000
            if ready.json()["device"] != args.device:
                raise RuntimeError("Server selected the wrong device")

            def request(spots: list[dict]) -> tuple[float, float]:
                t = perf_counter()
                response = client.post(base + "/v1/infer",
                    data={"camera_id":"UFPR04-BENCH", "spots_json":json.dumps(spots)},
                    files={"image":("scene.jpg",data,"image/jpeg")})
                wall = (perf_counter()-t)*1000
                response.raise_for_status()
                body = response.json()
                if [x["spot_id"] for x in body["predictions"]] != [x["spot_id"] for x in spots]:
                    raise RuntimeError("HTTP response lost spot order")
                return wall, body["processing_time_ms"]

            http_results = {}
            for count in count_list:
                spots = spots_for(source_spots, count)
                for _ in range(args.warmup):
                    request(spots)
                measured = [request(spots) for _ in range(args.runs)]
                http_results[str(count)] = {
                    "workload": "real_distinct_polygons" if count <= 37 else "synthetic_workload_repeated_polygons",
                    "client_wall": summary([x[0] for x in measured]),
                    "server_handler": summary([x[1] for x in measured]),
                }
            concurrency = {}
            spots = spots_for(source_spots, 37)
            for workers in (1, 2, 4):
                for _ in range(args.warmup):
                    request(spots)
                started = perf_counter()
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    times = list(pool.map(lambda _: request(spots)[0], range(20)))
                elapsed = perf_counter() - started
                concurrency[str(workers)] = {"request_count":20, "client_latency":summary(times),
                                            "wall_ms":elapsed*1000, "throughput_requests_per_second":20/elapsed}
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    report = {
        "source_image":image_path, "image_size":image_size,
        "real_polygon_count":len(source_spots), "device":args.device,
        "cpu":platform.processor(),
        "gpu":torch.cuda.get_device_name(0) if args.device=="cuda" else None,
        "torch":torch.__version__, "torchvision":torchvision.__version__,
        "batch_size":settings.batch_size, "warmup_per_case":args.warmup,
        "measured_runs_per_case":args.runs,
        "model_loader_ms":model_load_ms, "server_start_to_ready_ms":server_ready_ms,
        "engine":engine_results, "http":http_results,
        "concurrency_37_real_spots":concurrency,
    }
    output = args.output or SERVICE_ROOT / f"runs/mobilenetv3_gpu/w5_evaluation/benchmark_{args.device}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
