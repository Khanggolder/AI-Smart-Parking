"""Build and verify the frozen, self-contained W6 inference release."""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import torch

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
VERSION = "v0.1.0-rc2"
RELEASE = ROOT / "releases" / VERSION
ZIP = ROOT / "releases" / f"ai-smart-parking-model-{VERSION}.zip"
EXPECTED_CHECKPOINT = "488ed38efe016ad9a6aea42973909b77372f7331b13da7cb9d4d81c23608dada"
EXPECTED_MANIFESTS = {
    "train": "4835afb024738106588075d771bf59acdd006ffe798d9705a74a39004a7c506b",
    "val": "7316e508ae876e275c4a6276e6e34b3670b74e7ca307b74871655f27d8651ecc",
    "test": "684b8a49e82b7e2c2a9b22f4d97d1ca85c663a26e4e2fbacc69ddabed2cb4e9b",
}
SOURCE = (
    "baseline_utils.py", "confidence_utils.py", "inference.py", "model_loader.py",
    "model_runtime.py", "preprocessing.py", "service.py", "w1_crop.py",
)
DIRECT_DEPENDENCIES = (
    "torch", "torchvision", "numpy", "opencv-python", "Pillow", "PyYAML",
    "fastapi", "uvicorn", "python-multipart", "httpx",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit() -> tuple[Path, Path, dict]:
    checkpoint_path = ROOT / "runs/mobilenetv3_gpu/best.pt"
    threshold_path = ROOT / "runs/mobilenetv3_gpu/confidence/threshold_candidate.json"
    frozen_path = ROOT / "runs/mobilenetv3_gpu/w5_evaluation/frozen_evaluation_config.json"
    for path in (checkpoint_path, threshold_path, frozen_path):
        if not path.is_file():
            raise FileNotFoundError(f"Release input missing: {path}")
    if sha(checkpoint_path) != EXPECTED_CHECKPOINT:
        raise ValueError("Checkpoint SHA-256 mismatch")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    threshold = json.loads(threshold_path.read_text(encoding="utf-8"))
    if frozen["checkpoint_sha256"] != EXPECTED_CHECKPOINT or frozen["threshold_config_sha256"] != sha(threshold_path):
        raise ValueError("W5 frozen checkpoint/threshold mismatch")
    if frozen["inference_yaml_sha256"] != sha(ROOT / "configs/inference.yaml"):
        raise ValueError("W5 inference configuration changed")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if checkpoint["class_names"] != ["empty", "occupied"] or frozen["class_order"] != checkpoint["class_names"]:
        raise ValueError("Class order mismatch")
    if threshold["unknown_threshold"] != 0.90 or threshold["status"] != "candidate_not_production_validated":
        raise ValueError("Candidate threshold/status changed")
    if threshold["checkpoint_sha256"] != EXPECTED_CHECKPOINT:
        raise ValueError("Threshold references another checkpoint")
    for split, expected in EXPECTED_MANIFESTS.items():
        if sha(ROOT / "manifests" / f"{split}.csv") != expected:
            raise ValueError(f"{split} manifest changed")
        if checkpoint["split_stats"][split]["sha256"] != expected or frozen["manifest_stats"][split]["sha256"] != expected:
            raise ValueError(f"{split} manifest metadata mismatch")
    return checkpoint_path, threshold_path, frozen


def build() -> None:
    checkpoint_path, threshold_path, frozen = audit()
    if RELEASE.exists() or ZIP.exists():
        raise FileExistsError("Release already exists; refusing to overwrite it")
    RELEASE.mkdir(parents=True)
    (RELEASE / "model").mkdir()
    (RELEASE / "configs").mkdir()
    (RELEASE / "src").mkdir()
    shutil.copy2(checkpoint_path, RELEASE / "model/best.pt")
    shutil.copy2(threshold_path, RELEASE / "threshold_candidate.json")
    for name in SOURCE:
        shutil.copy2(ROOT / "src" / name, RELEASE / "src" / name)
    for name in ("MODEL_CARD.md", "BACKEND_HANDOVER.md", "FRONTEND_HANDOVER.md", "DEMO_RUNBOOK.md"):
        shutil.copy2(ROOT / "docs" / name, RELEASE / name)
    shutil.copy2(ROOT / "docs/AI_API_CONTRACT.md", RELEASE / "AI_API_CONTRACT.md")
    shutil.copy2(ROOT / "docs/RELEASE_README.md", RELEASE / "README.md")
    shutil.copy2(ROOT / "scripts/verify_release.py", RELEASE / "verify_release.py")
    shutil.copy2(ROOT / "scripts/ai_http_client.py", RELEASE / "client_example.py")
    (RELEASE / "configs/inference.yaml").write_text(
        "checkpoint: model/best.pt\nthreshold_config: threshold_candidate.json\n"
        "device: auto\nbatch_size: 32\nmax_spots: 100\nmax_upload_bytes: 10485760\n"
        "max_image_pixels: 20000000\nport: 8001\n", encoding="utf-8")
    versions = {name: metadata.version(name) for name in DIRECT_DEPENDENCIES}
    (RELEASE / "requirements-demo.txt").write_text(
        "# Install the matching torch/torchvision CPU or CUDA pair first; see README.md.\n"
        + "".join(f"{name}=={versions[name]}\n" for name in DIRECT_DEPENDENCIES if name not in ("torch", "torchvision")),
        encoding="utf-8",
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    manifest = {
        "release_version": VERSION,
        "release_status": "release_candidate_not_production_validated",
        "model_version": frozen["model_version"],
        "source_commit": commit,
        "source_snapshot": "src/ (copied from uncommitted W7 source; hashes in checksums.sha256)",
        "checkpoint_sha256": EXPECTED_CHECKPOINT,
        "source_threshold_sha256": sha(threshold_path),
        "dataset_manifest_sha256": EXPECTED_MANIFESTS,
        "class_order": ["empty", "occupied"],
        "architecture": "mobilenet_v3_small",
        "selected_epoch": 2,
        "input_size": [224, 224],
        "unknown_threshold": 0.90,
        "threshold_status": "candidate_not_production_validated",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "dependency_versions": versions,
        "validated_platform": "Windows 64-bit, RTX 3050 Laptop GPU, CUDA 12.8 runtime",
        "w5_test_passes": 1,
    }
    (RELEASE / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    paths = sorted(path for path in RELEASE.rglob("*") if path.is_file())
    (RELEASE / "checksums.sha256").write_text(
        "".join(f"{sha(path)}  {path.relative_to(RELEASE).as_posix()}\n" for path in paths),
        encoding="utf-8",
    )
    with ZipFile(ZIP, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(path for path in RELEASE.rglob("*") if path.is_file()):
            archive.write(path, arcname=f"{VERSION}/{path.relative_to(RELEASE).as_posix()}")
    print(json.dumps({"release": str(RELEASE), "zip": str(ZIP), "zip_sha256": sha(ZIP),
                      "model_version": manifest["model_version"]}, indent=2))


if __name__ == "__main__":
    build()
