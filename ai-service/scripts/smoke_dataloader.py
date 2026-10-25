"""Read one PyTorch DataLoader batch; no model training."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import torch
from torch.utils.data import DataLoader

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))
from dataset import ParkingSpotDataset  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--batch-size", type=int, default=16)
    args = p.parse_args()
    repo_root = SERVICE_ROOT.parent
    ds = ParkingSpotDataset(SERVICE_ROOT / "manifests" / "train.csv", repo_root=repo_root, train=True)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    xb, yb = next(iter(loader))
    print(f"train records: {len(ds)}")
    print(f"images: shape={tuple(xb.shape)}, dtype={xb.dtype}")
    print(f"labels: shape={tuple(yb.shape)}, values={sorted(set(yb.tolist()))}")
    assert xb.ndim == 4 and xb.shape[1:] == (3, 224, 224)
    assert yb.dtype == torch.int64 and set(yb.tolist()).issubset({0, 1})
    assert torch.isfinite(xb).all()
    print("[PASS] DataLoader batch is valid. Ready for W2 baseline (not trained yet).")

if __name__ == "__main__":
    main()
