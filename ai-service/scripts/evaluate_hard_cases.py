"""Descriptive synthetic sensitivity on validation crops only; no test selection."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageEnhance
import numpy as np
import torch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
sys.path.insert(0, str(SERVICE_ROOT))
from src.baseline_utils import CLASSES, metrics_from_predictions
from src.confidence_utils import selective_summary
from src.dataset import ParkingSpotDataset
from src.model_loader import ModelLoader, Settings


def transform(image: Image.Image, scenario: str) -> Image.Image:
    if scenario == "original_validation_jpeg":
        return image
    if scenario == "synthetic_low_light_0.5":
        return ImageEnhance.Brightness(image).enhance(.5)
    if scenario == "synthetic_low_contrast_0.5":
        return ImageEnhance.Contrast(image).enhance(.5)
    if scenario == "synthetic_shadow_left_half":
        layer = Image.new("RGBA", image.size, (0,0,0,0))
        draw = ImageDraw.Draw(layer)
        draw.polygon([(0,0),(int(image.width*.55),0),(int(image.width*.35),image.height),(0,image.height)], fill=(0,0,0,140))
        return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")
    if scenario == "synthetic_center_occlusion_35pct":
        result = image.copy()
        draw = ImageDraw.Draw(result)
        dx, dy = int(image.width*.35/2), int(image.height*.35/2)
        x, y = image.width//2, image.height//2
        draw.rectangle((x-dx,y-dy,x+dx,y+dy), fill=(114,114,114))
        return result
    raise ValueError(scenario)


def main():
    loader = ModelLoader(Settings.load())
    data = ParkingSpotDataset(SERVICE_ROOT / "manifests/val.csv", REPO_ROOT, train=False)
    truth = [CLASSES.index(row["label"]) for row in data.rows]
    scenarios = ("original_validation_jpeg", "synthetic_low_light_0.5",
                 "synthetic_low_contrast_0.5", "synthetic_shadow_left_half",
                 "synthetic_center_occlusion_35pct")
    results = {}
    for scenario in scenarios:
        probs = []
        for start in range(0, len(data), loader.settings.batch_size):
            batch = []
            for row in data.rows[start:start+loader.settings.batch_size]:
                with Image.open(REPO_ROOT / row["crop_path"]) as source:
                    image = source.convert("RGB")
                batch.append(data.transform(transform(image, scenario)))
            probs.extend(loader.predict(torch.stack(batch)).tolist())
        array = np.asarray(probs)
        raw = metrics_from_predictions(truth, array.argmax(1).tolist())
        selective = selective_summary(truth, array, loader.threshold)
        cm = selective["confusion_matrix_true_rows_predicted_cols_empty_occupied_unknown"]
        results[scenario] = {
            "sample_count": len(data), "raw_accuracy": raw["accuracy"],
            "raw_errors": len(data) - sum(raw["confusion_matrix"][i][i] for i in (0,1)),
            "unknown_count": selective["unknown"],
            "unknown_rate": selective["unknown"] / len(data),
            "accepted_errors": cm[0][1] + cm[1][0],
            "accepted_accuracy": selective["accepted_accuracy"],
        }
    output = SERVICE_ROOT / "runs/mobilenetv3_gpu/w5_evaluation/hard_cases_synthetic_val.json"
    output.write_text(json.dumps({"split":"val", "method":"in-memory deterministic transformations of original W1 JPEG crops; source files unchanged", "threshold":loader.threshold, "results":results}, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
