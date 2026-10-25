"""Compare saved W1 JPEG crops with direct W4 crops on validation data only."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import cv2
import numpy as np
import torch
from PIL import Image

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
sys.path.insert(0, str(SERVICE_ROOT))
from src.confidence_utils import decide
from src.dataset import ParkingSpotDataset
from src.model_loader import ModelLoader, Settings
from src.preprocessing import polygon_pixels, preprocess
from src.w1_crop import make_crop


def main():
    data = ParkingSpotDataset(SERVICE_ROOT / "manifests/val.csv", REPO_ROOT, train=False)
    selected = [data.rows[i * len(data) // 100] for i in range(100)]
    loader = ModelLoader(Settings.load())
    metadata_cache, image_cache = {}, {}
    w1_tensors, w4_tensors, rows = [], [], []
    for row in selected:
        source = row["source_json"]
        if source not in metadata_cache:
            doc = json.loads((REPO_ROOT / "data/metapklot" / source).read_text(encoding="utf-8"))
            metadata_cache[source] = {str(a["id"]): a for a in doc["annotations"]}
        ann = metadata_cache[source][row["annotation_id"]]
        if len(ann["segmentation"]) != 1:
            raise RuntimeError("Validation consistency sample includes multipart polygon")
        image_file = row["image_file"]
        if image_file not in image_cache:
            image_cache[image_file] = cv2.imread(str(REPO_ROOT / "data/metapklot" / image_file))
        scene = image_cache[image_file]
        if scene is None:
            raise FileNotFoundError(image_file)
        height, width = scene.shape[:2]
        flat = ann["segmentation"][0]
        w1_pixels = np.asarray(flat, dtype=np.int32).reshape(-1,2)
        normalized = [[float(x)/(width-1), float(y)/(height-1)] for x,y in w1_pixels]
        w4_pixels = polygon_pixels(normalized, width, height)
        geometry_match = bool(np.array_equal(w1_pixels, w4_pixels))
        direct = make_crop(scene, [w4_pixels], 224, "mask")
        saved = cv2.imread(str(REPO_ROOT / row["crop_path"]))
        if saved is None or saved.shape != (224,224,3):
            raise RuntimeError("Missing or incorrect W1 JPEG crop")
        diff = np.abs(saved.astype(np.int16) - direct.astype(np.int16))
        with Image.open(REPO_ROOT / row["crop_path"]) as saved_pil:
            w1_tensors.append(data.transform(saved_pil.convert("RGB")))
        w4_tensors.append(preprocess(scene, [{"spot_id":"DEV", "polygon":normalized}])[0])
        rows.append({"crop_path":row["crop_path"], "image_file":image_file,
                     "annotation_id":row["annotation_id"], "date":row["date"],
                     "geometry_match":geometry_match,
                     "pixel_mae":float(diff.mean()), "pixel_max_abs":int(diff.max()),
                     "pixel_fraction_changed":float((diff != 0).mean())})
    p1, p4 = [], []
    for start in range(0,len(rows),loader.settings.batch_size):
        p1.extend(loader.predict(torch.stack(w1_tensors[start:start+loader.settings.batch_size])).tolist())
        p4.extend(loader.predict(torch.stack(w4_tensors[start:start+loader.settings.batch_size])).tolist())
    for row, a, b in zip(rows,p1,p4,strict=True):
        d1, d4 = decide(*a,loader.threshold), decide(*b,loader.threshold)
        row.update({"w1_raw":d1["raw_label"],"w4_raw":d4["raw_label"],
                    "w1_final":d1["label"],"w4_final":d4["label"],
                    "w1_confidence":d1["confidence"],"w4_confidence":d4["confidence"],
                    "confidence_abs_delta":abs(d1["confidence"]-d4["confidence"])})
    report = {"split":"val", "samples":len(rows), "selection":"100 equally spaced rows from 720 validation manifest rows",
              "geometry_mismatch_count":sum(not r["geometry_match"] for r in rows),
              "mean_pixel_mae":sum(r["pixel_mae"] for r in rows)/len(rows),
              "max_pixel_abs":max(r["pixel_max_abs"] for r in rows),
              "mean_confidence_abs_delta":sum(r["confidence_abs_delta"] for r in rows)/len(rows),
              "max_confidence_abs_delta":max(r["confidence_abs_delta"] for r in rows),
              "raw_label_change_count":sum(r["w1_raw"]!=r["w4_raw"] for r in rows),
              "final_label_change_count":sum(r["w1_final"]!=r["w4_final"] for r in rows),
              "rows":rows}
    output = SERVICE_ROOT / "runs/mobilenetv3_gpu/w5_evaluation/preprocessing_consistency_val.json"
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="rows"},indent=2))


if __name__ == "__main__":
    main()
