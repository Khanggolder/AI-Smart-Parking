"""W0 MetaPKLot UFPR04 dataset inspection (no model training).

Run from the AI-Smart-Parking repository root:
    python ai-service/scripts/inspect_ufpr04.py --count 5
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path, PurePosixPath
import tarfile
from urllib.request import urlretrieve

import cv2
import numpy as np
from huggingface_hub import hf_hub_download


REPO_ID = "DSBD-Research/MetaPKLot-Dataset"
ARCHIVE_PATH = "annotations/original/spots/PKLot/ufpr04_spots.tar.xz"
GH_RAW_BASE = "https://raw.githubusercontent.com/DSBD-Research/MetaPKLot-Dataset/main/"
LABELS = {0: "empty", 1: "occupied"}
COLORS = {0: (50, 180, 50), 1: (50, 50, 230)}  # OpenCV BGR


def safe_repo_path(filename: str) -> str:
    parts = PurePosixPath(filename.replace("\\", "/")).parts
    if not parts or any(p in {".", "..", ""} for p in parts) or filename.startswith(("/", "\\")):
        raise ValueError(f"Unsafe relative file name: {filename!r}")
    return str(PurePosixPath(*parts))


def download_one(filename: str, target_root: Path) -> Path:
    filename = safe_repo_path(filename)
    dest = target_root.joinpath(*PurePosixPath(filename).parts)
    if dest.is_file() and dest.stat().st_size > 0:
        print(f"[CACHE] {filename}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[DOWNLOAD] {filename}")
    try:
        result = hf_hub_download(
            repo_id=REPO_ID, repo_type="dataset", filename=filename,
            local_dir=str(target_root),
        )
        return Path(result)
    except Exception as err:
        print(f"  Hugging Face unavailable ({type(err).__name__}); trying GitHub.")
        urlretrieve(GH_RAW_BASE + filename, dest)
        return dest


def extract_jsons(archive: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, mode="r:xz") as tf:
        json_members = [m for m in tf.getmembers() if m.isfile() and m.name.lower().endswith(".json")]
        if not json_members:
            raise RuntimeError("The annotation archive contains no JSON file.")
        for member in json_members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"Unsafe archive member: {member.name}")
            target = out_dir.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tf.extractfile(member)
            if src is None:
                continue
            with src, target.open("wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
    return sorted(out_dir.rglob("*.json"))


def annotation_polygons(ann: dict, width: int, height: int) -> tuple[list[np.ndarray], list[str]]:
    errors: list[str] = []
    polygons: list[np.ndarray] = []
    segmentation = ann.get("segmentation")
    if not isinstance(segmentation, list):
        return [], ["segmentation is missing or not a polygon list"]
    for index, contour in enumerate(segmentation):
        if not isinstance(contour, list) or len(contour) < 6 or len(contour) % 2:
            errors.append(f"contour {index}: fewer than 3 points or odd coordinate count")
            continue
        try:
            coords = np.asarray(contour, dtype=np.float64).reshape(-1, 2)
            if not np.isfinite(coords).all():
                raise ValueError("non-finite coordinate")
            if (coords[:, 0] < 0).any() or (coords[:, 0] >= width).any() or (coords[:, 1] < 0).any() or (coords[:, 1] >= height).any():
                errors.append(f"contour {index}: some points outside image")
                continue
            pts = np.rint(coords).astype(np.int32)
            if cv2.contourArea(pts) <= 1:
                errors.append(f"contour {index}: zero or near-zero area")
                continue
            polygons.append(pts)
        except (ValueError, TypeError) as err:
            errors.append(f"contour {index}: {err}")
    if not polygons and not errors:
        errors.append("empty polygon list")
    return polygons, errors


def draw_overlay(image_path: Path, image_info: dict, anns: list[dict], output: Path) -> dict:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"OpenCV cannot read {image_path}")
    h, w = image.shape[:2]
    expected_wh = (image_info.get("width"), image_info.get("height"))
    issues: list[str] = []
    if expected_wh != (w, h):
        issues.append(f"image dimensions mismatch: JSON={expected_wh}, actual={(w, h)}")

    transparent = image.copy()
    validated = []
    counts = Counter()
    for ann in anns:
        category = ann.get("category_id")
        if category not in LABELS:
            issues.append(f"annotation {ann.get('id')}: category_id={category} unexpected")
            continue
        polygons, errors = annotation_polygons(ann, w, h)
        for err in errors:
            issues.append(f"annotation {ann.get('id')}: {err}")
        if not polygons:
            continue
        color = COLORS[category]
        cv2.fillPoly(transparent, polygons, color)
        validated.append((ann, polygons, color))
        counts[LABELS[category]] += 1

    visual = cv2.addWeighted(transparent, 0.28, image, 0.72, 0)
    for ann, polygons, color in validated:
        cv2.polylines(visual, polygons, isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)
        moments = cv2.moments(polygons[0])
        if moments["m00"]:
            x = int(moments["m10"] / moments["m00"])
            y = int(moments["m01"] / moments["m00"])
        else:
            x, y = polygons[0][0]
            x, y = int(x), int(y)
        # Annotation IDs are for W0 inspection only, not stable physical spot IDs.
        label = f"{ann.get('id', '?')}:{'E' if ann['category_id'] == 0 else 'O'}"
        x, y = max(0, min(x, w - 80)), max(12, min(y, h - 4))
        cv2.putText(visual, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(visual, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)

    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), visual):
        raise RuntimeError(f"Cannot save {output}")
    return {
        "file_name": image_info.get("file_name"),
        "image_id": image_info.get("id"),
        "annotation_total": len(anns),
        "drawn_total": len(validated),
        "empty": counts["empty"],
        "occupied": counts["occupied"],
        "issues": issues,
        "overlay": str(output),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5, help="Number of panorama images (default: 5)")
    parser.add_argument("--data-dir", default="data/metapklot", help="Cache root (gitignored)")
    parser.add_argument("--out-dir", default="ai-service/reports", help="Report and overlay directory")
    args = parser.parse_args()
    if args.count < 1 or args.count > 20:
        parser.error("--count must be from 1 to 20 to keep the download small.")
    data_root = Path(args.data_dir)
    output_dir = Path(args.out_dir)

    archive = download_one(ARCHIVE_PATH, data_root)
    json_files = extract_jsons(archive, data_root / "extracted" / "ufpr04_spots")
    print(f"[ANNOTATIONS] {len(json_files)} JSON file(s) found.")
    records = []
    for js in json_files:
        try:
            doc = json.loads(js.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as e:
            print(f"[SKIP] {js}: {e}")
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("images"), list) or not isinstance(doc.get("annotations"), list):
            print(f"[SKIP] {js}: not a COCO image+annotation document")
            continue
        categories = {c.get("id"): c.get("name") for c in doc.get("categories", [])}
        print(f"[JSON] {js.name}: {len(doc['images'])} images, {len(doc['annotations'])} annotations; categories={categories}")
        anns_by_img = defaultdict(list)
        for ann in doc["annotations"]:
            anns_by_img[ann.get("image_id")].append(ann)
        for img in doc["images"]:
            linked = anns_by_img.get(img.get("id"), [])
            if linked and isinstance(img.get("file_name"), str):
                records.append((img, linked, js))

    if not records:
        raise RuntimeError("No images linked to parking-spot annotations. Inspect the JSON schema.")

    # Choose distinct recording days first, then fill to --count.
    records.sort(key=lambda rec: str(rec[0].get("file_name", "")))
    selected = []
    selected_names = set()
    seen_day = set()
    for img, anns, js in records:
        parts = PurePosixPath(img["file_name"].replace("\\", "/")).parts
        key = tuple(parts[1:3]) if len(parts) >= 4 else tuple(parts[:-1])
        if key not in seen_day:
            selected.append((img, anns, js))
            selected_names.add(img["file_name"])
            seen_day.add(key)
            if len(selected) == args.count:
                break
    if len(selected) < args.count:
        for rec in records:
            if rec[0]["file_name"] not in selected_names:
                selected.append(rec)
                selected_names.add(rec[0]["file_name"])
                if len(selected) == args.count:
                    break

    output_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for idx, (img, anns, js) in enumerate(selected, start=1):
        filename = safe_repo_path(img["file_name"])
        remote_img = filename if filename.startswith("PKLot/") else f"PKLot/{filename}"
        print(f"[IMAGE {idx}/{len(selected)}] {remote_img} (image_id={img['id']}, annotations={len(anns)})")
        try:
            image_path = download_one(remote_img, data_root)
            file_out = output_dir / ("sample_overlay.png" if idx == 1 else f"sample_overlay_{idx:02}.png")
            result = draw_overlay(image_path, img, anns, file_out)
            result["annotation_source"] = str(js)
            reports.append(result)
            print(f"  -> drawn={result['drawn_total']}, E={result['empty']}, O={result['occupied']}; saved {file_out}")
        except Exception as err:
            reports.append({"file_name":filename,"annotation_total":len(anns),"issues":[f"download/draw error: {err}"]})
            print(f"  [ERROR] {err}")

    lines = [
        "# W0 – MetaPKLot UFPR04 dataset inspection",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "- Source: https://github.com/DSBD-Research/MetaPKLot-Dataset",
        "- Download: https://huggingface.co/datasets/DSBD-Research/MetaPKLot-Dataset",
        f"- Annotation archive: `{ARCHIVE_PATH}`",
        "- PKLot images: CC BY 4.0 (attribute PKLot and MetaPKLot). Other component licenses differ.",
        "- IDs rendered on the overlays refer to annotation `id`, NOT guaranteed stable physical `spot_id`.",
        "- A missing annotation outside an `annotationsRectangle` must not be interpreted as an empty spot.",
        "",
        "| Image | image_id | Annotated spots | Drawn spots | Empty | Occupied | Issues |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in reports:
        lines.append(f"| `{r['file_name']}` | {r.get('image_id', 'N/A')} | {r['annotation_total']} | {r.get('drawn_total', 0)} | {r.get('empty', 0)} | {r.get('occupied', 0)} | {len(r['issues'])} |")
    lines.extend(["", "## Issues and validation observations", ""])
    for r in reports:
        lines.append(f"### {r['file_name']}")
        if r.get("overlay"):
            lines.append(f"Overlay: `{Path(r['overlay']).name}`")
        if r["issues"]:
            lines.extend(f"- {problem}" for problem in r["issues"][:20])
            if len(r["issues"]) > 20:
                lines.append(f"- ... and {len(r['issues']) - 20} other issues")
        else:
            lines.append("- No issues detected by automated checks. Manual visual inspection is still required.")
        lines.append("")
    report_path = output_dir / "dataset_inspection.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[DONE] Report saved at {report_path}")
    print("IMPORTANT: Open the overlays manually and compare all spot polygons with the scene.")


if __name__ == "__main__":
    main()
