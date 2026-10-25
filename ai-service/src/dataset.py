"""PyTorch Dataset for W1 UFPR04 parking spot crops."""
from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms

LABEL_TO_ID = {"empty": 0, "occupied": 1}


class ParkingSpotDataset(Dataset):
    def __init__(self, csv_path: str | Path, repo_root: str | Path, train: bool = False, size: int = 224):
        self.csv_path = Path(csv_path)
        self.repo_root = Path(repo_root)
        with self.csv_path.open(newline="", encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f))
        if not self.rows:
            raise ValueError(f"Empty CSV manifest: {self.csv_path}")
        for item in self.rows:
            if item.get("label") not in LABEL_TO_ID:
                raise ValueError(f"Invalid label {item.get('label')}")
        effects = []
        if train:
            effects = [transforms.RandomHorizontalFlip(p=0.5), transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.08)]
        self.transform = transforms.Compose([
            transforms.Resize((size, size)),
            *effects,
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        entry = self.rows[idx]
        path = self.repo_root / Path(entry["crop_path"])
        with Image.open(path) as im:
            tensor = self.transform(im.convert("RGB"))
        return tensor, LABEL_TO_ID[entry["label"]]
