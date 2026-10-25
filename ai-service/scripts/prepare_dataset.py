"""Prepare MetaPKLot UFPR04 polygon crops and leakage-safe day-wise CSV splits.

Run from AI-Smart-Parking repository root:
    python ai-service/scripts/prepare_dataset.py --max-days 12 --per-day 10

W0's inspect_ufpr04.py must be in the same scripts/ folder.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import random
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.w1_crop import make_crop

from inspect_ufpr04 import (
    ARCHIVE_PATH,
    annotation_polygons,
    download_one,
    extract_jsons,
    safe_repo_path,
)

FIELDNAMES = [
    "crop_path", "label", "category_id", "camera", "date", "weather",
    "image_file", "image_id", "annotation_id", "source_json",
    "crop_mode", "width", "height",
]


def normalized_image_path(file_name: str) -> str:
    rel = safe_repo_path(file_name)
    parts = PurePosixPath(rel).parts
    if parts[0] == "PKLot":
        parts = parts[1:]
    if not parts or parts[0].upper() != "UFPR04":
        raise ValueError(f"Expected UFPR04 image: {file_name!r}")
    return str(PurePosixPath("PKLot", *parts))


def image_day(img: dict, image_file: str) -> str:
    parts = PurePosixPath(image_file).parts
    for p in parts:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p):
            return p
    d = img.get("date")
    if isinstance(d, list) and len(d) == 3:
        return f"{int(d[0]):04d}-{int(d[1]):02d}-{int(d[2]):02d}"
    raise ValueError("Image has no reliable shooting date; cannot split safely")


def image_weather(image_file: str) -> str:
    parts = PurePosixPath(image_file).parts
    return parts[2] if len(parts) >= 5 else "unknown"


def collect_records(json_files: list[Path]) -> tuple[dict[str, list[dict]], Counter]:
    """Each JSON has its own image_id namespace; never join IDs across JSONs."""
    by_day = defaultdict(list)
    seen_paths: set[str] = set()
    problems = Counter()
    for json_path in json_files:
        try:
            doc = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict) or not isinstance(doc.get("images"), list) or not isinstance(doc.get("annotations"), list):
                problems["invalid_json_schema"] += 1
                continue
        except (ValueError, UnicodeError, OSError):
            problems["unreadable_json"] += 1
            continue
        anno_by_image = defaultdict(list)
        for a in doc["annotations"]:
            if not isinstance(a, dict):
                problems["invalid_annotation"] += 1
                continue
            anno_by_image[a.get("image_id")].append(a)
        for img in doc["images"]:
            if not isinstance(img, dict):
                problems["invalid_image_record"] += 1
                continue
            try:
                image_file = normalized_image_path(img["file_name"])
                day = image_day(img, image_file)
            except (KeyError, ValueError, TypeError):
                problems["invalid_image_metadata"] += 1
                continue
            anns = anno_by_image.get(img.get("id"), [])
            if not anns:
                problems["image_without_annotations"] += 1
                continue
            if image_file in seen_paths:
                problems["duplicate_image_file"] += 1
                continue
            seen_paths.add(image_file)
            by_day[day].append({"image_file": image_file, "image": img, "annotations": anns, "source_json": str(json_path)})
    return by_day, problems


def split_days(days: list[str], seed: int) -> dict[str, set[str]]:
    if len(days) < 3:
        raise RuntimeError("Need at least 3 distinct dates for train/val/test; increase --max-days")
    days = sorted(days)
    random.Random(seed).shuffle(days)
    n = len(days)
    n_test = max(1, round(n * 0.15))
    n_val = max(1, round(n * 0.15))
    if n_test + n_val >= n:
        raise RuntimeError("Not enough dates to leave at least one training day")
    return {"test": set(days[:n_test]), "val": set(days[n_test:n_test+n_val]), "train": set(days[n_test+n_val:])}


def save_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def save_preview(rows: list[dict], repo_root: Path, out_path: Path, limit: int = 24) -> None:
    canvas = np.full((4 * 180, 6 * 170, 3), 246, dtype=np.uint8)
    chosen = rows[:limit]
    for i, item in enumerate(chosen):
        fp = repo_root / item["crop_path"]
        crop = cv2.imread(str(fp), cv2.IMREAD_COLOR)
        if crop is None:
            continue
        thumb = cv2.resize(crop, (152, 152))
        x, y = (i % 6) * 170 + 9, (i // 6) * 180 + 5
        canvas[y:y+152, x:x+152] = thumb
        tag = f"{item['label']} | {item['date']}"
        cv2.putText(canvas, tag, (x, y + 166), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (20, 20, 20), 1, cv2.LINE_AA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_path), canvas):
        raise RuntimeError(f"Cannot save preview: {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-days", type=int, default=12)
    p.add_argument("--per-day", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--size", type=int, default=224)
    p.add_argument("--mode", choices=["mask", "bbox"], default="mask")
    p.add_argument("--data-dir", default="data/metapklot")
    p.add_argument("--manifests-dir", default="ai-service/manifests")
    p.add_argument("--reports-dir", default="ai-service/reports")
    args = p.parse_args()
    if args.max_days < 3 or args.per_day < 1 or not (32 <= args.size <= 1024):
        p.error("Require --max-days >= 3, --per-day >= 1 and 32 <= --size <= 1024")
    root = Path.cwd().resolve()
    data_root = Path(args.data_dir)
    if not data_root.is_absolute():
        data_root = root / data_root
    data_root = data_root.resolve()
    try:
        relative_data_root = data_root.relative_to(root)
    except ValueError as exc:
        raise ValueError("--data-dir must be inside the Git repository (paths in CSV are repo-relative)") from exc
    manifests_dir = root / args.manifests_dir
    reports_dir = root / args.reports_dir

    archive = download_one(ARCHIVE_PATH, data_root)
    jsons = extract_jsons(archive, data_root / "extracted" / "ufpr04_spots")
    by_day, errors = collect_records(jsons)
    if len(by_day) < 3:
        raise RuntimeError(f"Only {len(by_day)} days in annotations; inspect the JSON files")

    # Randomized but reproducible subset; never split crops from one date across sets.
    selected_days = sorted(by_day)
    random.Random(args.seed).shuffle(selected_days)
    selected_days = selected_days[:args.max_days]
    assignment = split_days(selected_days, args.seed)
    day_to_split = {day: part for part, dates in assignment.items() for day in dates}
    rows_by_split: dict[str, list[dict]] = {k: [] for k in ("train", "val", "test")}
    day_image_counts = Counter()
    all_image_assignments = {}

    print(f"[INFO] {len(jsons)} JSON file(s), {len(by_day)} available dates, {len(selected_days)} selected dates")
    for day in sorted(selected_days):
        part = day_to_split[day]
        records = sorted(by_day[day], key=lambda r: r["image_file"])
        rng = random.Random(f"{args.seed}:{day}")
        rng.shuffle(records)
        records = records[:args.per_day]
        print(f"[{part.upper()}] {day}: {len(records)} image(s)")
        for record in records:
            fn = record["image_file"]
            if fn in all_image_assignments and all_image_assignments[fn] != part:
                raise RuntimeError(f"LEAKAGE: {fn} is in multiple splits")
            all_image_assignments[fn] = part
            try:
                source_path = download_one(fn, data_root)
                img = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("unreadable image")
                h, w = img.shape[:2]
                expected = (record["image"].get("width"), record["image"].get("height"))
                if (w, h) != expected:
                    raise ValueError(f"image dimension mismatch: expected={expected}, actual={(w,h)}")
            except Exception as exc:
                errors["missing_or_invalid_image"] += 1
                print(f"  [SKIP IMAGE] {fn}: {exc}")
                continue
            day_image_counts[day] += 1
            for ann in record["annotations"]:
                category = ann.get("category_id")
                if category not in (0, 1):
                    errors["unknown_label"] += 1
                    continue
                polygons, issues = annotation_polygons(ann, w, h)
                errors["invalid_contour"] += len(issues)
                if issues or not polygons:
                    # Strict QA: don't train on partially broken segmentation.
                    errors["invalid_annotation_skipped"] += 1
                    continue
                try:
                    crop = make_crop(img, polygons, args.size, args.mode)
                    ann_id = str(ann.get("id", "unknown"))
                    fingerprint = hashlib.sha1(f"{record['source_json']}|{fn}|{ann_id}".encode()).hexdigest()[:14]
                    relative = relative_data_root / "crops" / "ufpr04" / day / f"{fingerprint}.jpg"
                    destination = root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if not cv2.imwrite(str(destination), crop):
                        raise RuntimeError("cv2.imwrite returned False")
                    rows_by_split[part].append({
                        "crop_path": relative.as_posix(),
                        "label": "empty" if category == 0 else "occupied",
                        "category_id": category,
                        "camera": "UFPR04",
                        "date": day,
                        "weather": image_weather(fn),
                        "image_file": fn,
                        "image_id": record["image"].get("id"),
                        "annotation_id": ann_id,
                        "source_json": str(Path(record["source_json"]).relative_to(data_root).as_posix()),
                        "crop_mode": args.mode,
                        "width": args.size,
                        "height": args.size,
                    })
                except Exception as exc:
                    errors["crop_write_failure"] += 1
                    print(f"  [SKIP CROP] {fn}, annotation={ann.get('id')}: {exc}")

    for part, rows in rows_by_split.items():
        if not rows:
            raise RuntimeError(f"Split {part} has 0 usable crops. Increase --max-days/--per-day")
        save_manifest(manifests_dir / f"{part}.csv", rows)

    # Postcondition: dates and file names must be disjoint across splits.
    for a in rows_by_split:
        for b in rows_by_split:
            if a >= b:
                continue
            assert not ({r["date"] for r in rows_by_split[a]} & {r["date"] for r in rows_by_split[b]})
            assert not ({r["image_file"] for r in rows_by_split[a]} & {r["image_file"] for r in rows_by_split[b]})

    stats = {}
    lines = [
        "# W1 – UFPR04 prepared dataset", "",
        f"- Crop mode: `{args.mode}` (polygon mask + bbox when `mask`); letterbox to {args.size} x {args.size}.",
        f"- Seed: `{args.seed}`; source images per selected day: at most `{args.per_day}`.",
        "- Split unit: **calendar date** for UFPR04; no date or source panorama shared across splits.",
        "- These are samples for the preparation pipeline, not the final model benchmark.",
        "- `annotation_id` is an identifier in source annotation, not stable production spot_id.",
        "- For a final training dataset, increase days/images and recheck split distribution.", "",
        "| Split | Days | Panoramas | Empty | Occupied | Crops |", "|---|---:|---:|---:|---:|---:|",
    ]
    for part, rows in rows_by_split.items():
        c = Counter(r["label"] for r in rows)
        dates = sorted(assignment[part])
        n_images = len(set(r["image_file"] for r in rows))
        stats[part] = {"dates": dates, "panorama_images_with_crops": n_images, "empty": c["empty"], "occupied": c["occupied"], "crops": len(rows)}
        if c["empty"] == 0 or c["occupied"] == 0:
            errors[f"split_{part}_missing_one_class"] += 1
            print(f"[WARNING] {part} split missing empty or occupied. Sample more days/images before training.")
        lines.append(f"| {part} | {len(dates)} | {n_images} | {c['empty']} | {c['occupied']} | {len(rows)} |")
    lines.extend(["", "## Skipped items / anomalies", ""])
    lines.extend([f"- `{name}`: {num}" for name, num in sorted(errors.items())] or ["- None encountered in selected subset."])
    lines.extend(["", "## Dataset source", "", "- MetaPKLot: https://github.com/DSBD-Research/MetaPKLot-Dataset", "- PKLot images are CC BY 4.0; preserve attribution and review derivative distribution terms.", ""])
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "dataset_preparation.md").write_text("\n".join(lines), encoding="utf-8")
    (reports_dir / "dataset_split_stats.json").write_text(json.dumps({"config": vars(args), "splits": stats, "anomalies": dict(errors)}, ensure_ascii=False, indent=2), encoding="utf-8")
    save_preview([*rows_by_split["train"], *rows_by_split["val"], *rows_by_split["test"]], root, reports_dir / "crops_preview.jpg")
    print("\n[RESULT] W1 preparation finished:")
    for split, info in stats.items():
        print(f"  {split}: {len(info['dates'])} days, {info['panorama_images_with_crops']} images, {info['crops']} crops (E={info['empty']}, O={info['occupied']})")
    print(f"  CSV manifests: {manifests_dir}")
    print(f"  Preview: {reports_dir / 'crops_preview.jpg'}")
    print(f"  Report: {reports_dir / 'dataset_preparation.md'}")
    print("[CHECK] Manually inspect preview for ROI alignment and labels before model training.")

if __name__ == "__main__":
    main()
