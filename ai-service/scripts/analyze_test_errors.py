"""Summarize the single frozen W5 test prediction CSV; never reruns the model."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
OUT = SERVICE_ROOT / "runs/mobilenetv3_gpu/w5_evaluation"


def main():
    source = OUT / "test_predictions.csv"
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 740:
        raise ValueError("Expected the one official 740-row test CSV")
    raw_errors = [r for r in rows if r["raw_correct"] == "False"]
    false_empty = [r for r in raw_errors if r["raw_label"] == "empty"]
    false_occupied = [r for r in raw_errors if r["raw_label"] == "occupied"]
    unknown = [r for r in rows if r["accepted"] == "False"]
    low = sorted(rows, key=lambda r: float(r["confidence"]))[:20]
    high_wrong = sorted((r for r in raw_errors if r["accepted"] == "True"),
                        key=lambda r: -float(r["confidence"]))
    groups = [("FALSE EMPTY", false_empty), ("FALSE OCCUPIED", false_occupied),
              ("UNKNOWN", unknown), ("LOW CONFIDENCE", low),
              ("ACCEPTED ERRORS", high_wrong)]
    summary = {
        "source": str(source), "raw_error_count": len(raw_errors),
        "false_empty_count": len(false_empty), "false_occupied_count": len(false_occupied),
        "unknown_count": len(unknown), "accepted_error_count": len(high_wrong),
        "accepted_fraction_of_raw_errors": len(high_wrong) / len(raw_errors) if raw_errors else None,
        "raw_errors": [{k: r[k] for k in ("crop_path", "date", "camera", "true_label",
                      "raw_label", "confidence", "final_label", "accepted")}
                       for r in raw_errors],
        "gallery_groups": {name: len(items) for name, items in groups},
    }
    (OUT / "error_analysis.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    tile_w, tile_h, header_h, columns = 174, 180, 30, 6
    total_height = sum(header_h + ((len(items) + columns - 1) // columns) * tile_h for _, items in groups)
    canvas = Image.new("RGB", (columns * tile_w, total_height), "#ffffff")
    draw = ImageDraw.Draw(canvas)
    cursor = 0
    for title, items in groups:
        draw.rectangle((0,cursor,canvas.width,cursor+header_h-1), fill="#e9eef4")
        draw.text((12,cursor+8), f"{title} ({len(items)})", fill="#111111")
        cursor += header_h
        for i, row in enumerate(items):
            x = (i % columns) * tile_w
            y = cursor + (i // columns) * tile_h
            with Image.open(REPO_ROOT / row["crop_path"]) as im:
                thumb = ImageOps.contain(im.convert("RGB"), (164, 142))
            canvas.paste(thumb, (x + (tile_w-thumb.width)//2, y+2))
            draw.text((x+4,y+145), f"{row['date']} {row['true_label']}->{row['raw_label']}", fill="#111111")
            draw.text((x+4,y+161), f"score={float(row['confidence']):.3f} {row['final_label']}", fill="#111111")
        cursor += ((len(items) + columns - 1) // columns) * tile_h
    canvas.save(OUT / "error_gallery.jpg", quality=90)
    print(json.dumps({k:v for k,v in summary.items() if k != "raw_errors"}, indent=2))


if __name__ == "__main__":
    main()
