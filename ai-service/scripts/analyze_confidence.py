"""W3: analyze VAL softmax scores and candidate UNKNOWN threshold for MobileNetV3.

Does NOT touch the held-out TEST split, train model, or modify a checkpoint.
Usage from repo root:
  python ai-service/scripts/analyze_confidence.py --checkpoint ai-service/runs/mobilenetv3_gpu/best.pt --threshold 0.90 --device cuda
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
import torch
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / 'src'))
from dataset import LABEL_TO_ID, ParkingSpotDataset
from baseline_utils import assert_safe_splits, create_model, select_device
from confidence_utils import CLASSES, decide, selective_summary, expected_calibration_error


def make_gallery(rows, repo_root, output, limit=24):
    subset = sorted(rows, key=lambda x: x['confidence'])[:limit]
    size, caption, columns = 184, 56, 6
    height = (len(subset) + columns - 1) // columns
    image = Image.new('RGB', (columns * size, max(1, height) * (size + caption)), '#eeeeee')
    draw = ImageDraw.Draw(image)
    for i, record in enumerate(subset):
        fp = repo_root / record['crop_path']
        try:
            with Image.open(fp) as src:
                thumb = src.convert('RGB').resize((size-8, size-8))
        except (OSError, ValueError):
            continue
        x = (i % columns) * size + 4
        y = (i // columns) * (size + caption) + 4
        image.paste(thumb, (x, y))
        draw.text((x, y + size-2), f"True: {record['true_label']}", fill='#222222')
        draw.text((x, y + size+14), f"Pred: {record['raw_label']}", fill='#222222')
        draw.text((x, y + size+30), f"Score: {record['confidence']:.3f} | {record['predicted_label']}", fill='#222222')
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def make_plot(probs: np.ndarray, threshold: float, path: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    c = probs.max(axis=1)
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ax.hist(c, bins=np.linspace(.5, 1.0, 26), edgecolor='white')
    ax.axvline(threshold, ls='--', lw=2, label=f'candidate UNKNOWN threshold = {threshold:.2f}')
    ax.set(xlabel='max softmax probability (not calibrated)', ylabel='Number of validation crops',
           title='UFPR04 validation confidence distribution')
    ax.legend()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def describe_confidence(values: np.ndarray) -> dict:
    return {
        'count': int(len(values)),
        'min': float(np.min(values)),
        'median': float(np.median(values)),
        'max': float(np.max(values)),
        'p05': float(np.quantile(values, .05)),
        'p25': float(np.quantile(values, .25)),
        'p75': float(np.quantile(values, .75)),
        'p95': float(np.quantile(values, .95)),
    }


class SyntheticValidationDataset(Dataset):
    """Apply an in-memory perturbation to VAL crops; source files remain untouched."""

    def __init__(self, base: ParkingSpotDataset, variant: str):
        self.base = base
        self.variant = variant

    def __len__(self):
        return len(self.base)

    def __getitem__(self, index):
        row = self.base.rows[index]
        with Image.open(self.base.repo_root / row['crop_path']) as source:
            image = source.convert('RGB')
        if self.variant == 'brightness_0.6':
            image = ImageEnhance.Brightness(image).enhance(.6)
        elif self.variant == 'contrast_0.5':
            image = ImageEnhance.Contrast(image).enhance(.5)
        elif self.variant == 'center_occlusion_35pct':
            width, height = image.size
            side_x, side_y = int(width * .35), int(height * .35)
            x, y = (width-side_x)//2, (height-side_y)//2
            ImageDraw.Draw(image).rectangle((x, y, x+side_x-1, y+side_y-1), fill=(127, 127, 127))
        else:
            raise ValueError(f'Unknown synthetic variant: {self.variant}')
        return self.base.transform(image), LABEL_TO_ID[row['label']]


def synthetic_sensitivity(model, base, device, batch_size, threshold, output):
    results = []
    for variant in ('brightness_0.6', 'contrast_0.5', 'center_occlusion_35pct'):
        loader = DataLoader(SyntheticValidationDataset(base, variant), batch_size=batch_size,
                            shuffle=False, num_workers=0, pin_memory=device.type == 'cuda')
        truths, chunks = [], []
        with torch.inference_mode():
            for images, labels in loader:
                chunks.append(torch.softmax(model(images.to(device)), dim=1).cpu().numpy())
                truths.extend(labels.tolist())
        values = np.concatenate(chunks)
        summary = selective_summary(truths, values, threshold)
        summary['variant'] = variant
        summary['raw_accuracy'] = float(np.mean(values.argmax(axis=1) == np.asarray(truths)))
        results.append(summary)
    report = {
        'purpose': 'Synthetic corruption sensitivity on validation crop copies; not real-world or test performance',
        'source_split': 'val',
        'source_files_modified': False,
        'threshold': threshold,
        'variants': results,
    }
    (output / 'synthetic_sensitivity_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    for row in results:
        print(f"SYNTHETIC {row['variant']}: raw_accuracy={row['raw_accuracy']:.4f} "
              f"coverage={row['coverage']:.4f} unknown={row['unknown']}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', default='ai-service/runs/mobilenetv3_gpu/best.pt')
    p.add_argument('--threshold', type=float, default=0.90)
    p.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    p.add_argument('--batch-size', type=int, default=32)
    p.add_argument('--output', default='ai-service/runs/mobilenetv3_gpu/confidence')
    p.add_argument('--synthetic-sensitivity', action='store_true',
                   help='Evaluate in-memory brightness, contrast and occlusion copies of VAL crops')
    args = p.parse_args()
    if not np.isfinite(args.threshold) or not (0.5 <= args.threshold <= 1.0) or args.batch_size < 1:
        p.error('Expected 0.5 <= --threshold <= 1.0, batch-size >= 1')
    stats = assert_safe_splits(ROOT / 'manifests')
    checkpoint_path = (REPO_ROOT / args.checkpoint).resolve()
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    ckpt = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    if ckpt.get('architecture') != 'mobilenet_v3_small' or ckpt.get('class_names') != list(CLASSES):
        raise RuntimeError('Unexpected checkpoint model/label order')
    if ckpt.get('image_size') != 224:
        raise RuntimeError('This W3 script expects 224x224 crops')
    if ckpt.get('weights_source') != 'pretrained':
        raise RuntimeError('W3 requires the trained pretrained baseline, not a smoke-test checkpoint')
    trained_split = ckpt.get('split_stats')
    if not trained_split or any(trained_split[s]['sha256'] != stats[s]['sha256'] for s in stats):
        raise RuntimeError('Manifest changed from checkpoint training. Refuse confidence analysis.')
    device = select_device(args.device)
    model = create_model(pretrained=False)
    model.load_state_dict(ckpt['model_state'], strict=True)
    model.to(device).eval()
    data = ParkingSpotDataset(ROOT / 'manifests/val.csv', REPO_ROOT, train=False)
    loader = DataLoader(data, batch_size=args.batch_size, shuffle=False, num_workers=0,
                        pin_memory=(device.type == 'cuda'))
    truth, chunks = [], []
    with torch.inference_mode():
        for xb, yb in loader:
            prob = torch.softmax(model(xb.to(device)), dim=1).cpu().numpy()
            chunks.append(prob)
            truth.extend(yb.cpu().tolist())
    probs = np.concatenate(chunks, axis=0)
    if len(probs) != len(data.rows):
        raise RuntimeError('Prediction and manifest rows mismatched')
    raw_preds = np.argmax(probs, axis=1)
    raw_accuracy = float(np.mean(raw_preds == np.asarray(truth)))
    out = (REPO_ROOT / args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for row, y, pair in zip(data.rows, truth, probs):
        d = decide(float(pair[0]), float(pair[1]), args.threshold)
        records.append({
            'crop_path': row['crop_path'],
            'image_file': row['image_file'],
            'date': row['date'],
            'annotation_id': row.get('annotation_id', ''),
            'true_label': CLASSES[y],
            'prob_empty': float(pair[0]),
            'prob_occupied': float(pair[1]),
            'raw_label': d['raw_label'],
            'predicted_label': d['label'],
            'confidence': d['confidence'],
            'raw_correct': d['raw_label'] == CLASSES[y],
            'is_unknown': d['label'] == 'unknown',
        })
    with (out / 'val_predictions.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    thresholds = sorted(set([0.5, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, args.threshold]))
    comparison = [selective_summary(truth, probs, t) for t in thresholds]
    selected = selective_summary(truth, probs, args.threshold)
    checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    confidence = probs.max(axis=1)
    bin_edges = np.linspace(.5, 1.0, 26)
    bin_counts, _ = np.histogram(confidence, bins=bin_edges)
    lowest = sorted(records, key=lambda x: x['confidence'])[:24]
    summary = {
        'purpose': 'Validation-only descriptive analysis; not a test benchmark',
        'split': 'val',
        'sample_count': len(truth),
        'candidate_threshold': args.threshold,
        'raw_accuracy_val': raw_accuracy,
        'raw_errors_val': int((raw_preds != np.asarray(truth)).sum()),
        'ece_val_10_bins_descriptive': expected_calibration_error(truth, probs),
        'min_confidence_val': float(confidence.min()),
        'median_confidence_val': float(np.median(confidence)),
        'confidence_overall': describe_confidence(confidence),
        'confidence_by_true_class': {
            name: describe_confidence(confidence[np.asarray(truth) == index])
            for index, name in enumerate(CLASSES)
        },
        'confidence_histogram': {'bin_edges': bin_edges.tolist(), 'counts': bin_counts.tolist()},
        'lowest_confidence_samples': [
            {k: row[k] for k in ('crop_path', 'true_label', 'raw_label', 'predicted_label',
                                   'confidence', 'raw_correct')}
            for row in lowest
        ],
        'selected': selected,
        'threshold_comparison_on_val': comparison,
        'limits': ['Perfect validation accuracy cannot validate UNKNOWN effectiveness on errors or OOD images.',
                   'Softmax probability is not a guarantee of correctness/calibration.',
                   'Do not optimize threshold on held-out test data.'],
    }
    (out / 'val_confidence_report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    config = {
        'status': 'candidate_not_production_validated',
        'architecture': 'mobilenet_v3_small',
        'class_order': list(CLASSES),
        'image_size': 224,
        'crop_mode': (data.rows[0].get('crop_mode') or 'unknown'),
        'normalization': {'mean': [0.485, 0.456, 0.406], 'std': [0.229, 0.224, 0.225]},
        'unknown_rule': 'max_softmax_probability < threshold',
        'unknown_threshold': args.threshold,
        'checkpoint_path': str(checkpoint_path),
        'checkpoint_sha256': checkpoint_sha,
        'val_manifest_sha256': stats['val']['sha256'],
        'selected_epoch': ckpt.get('selected_epoch'),
        'model_version': ckpt.get('created_utc'),
        'weights_source': ckpt.get('weights_source'),
        'preprocess': ckpt.get('preprocess'),
    }
    (out / 'threshold_candidate.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    make_plot(probs, args.threshold, out / 'val_confidence_distribution.png')
    make_gallery(records, REPO_ROOT, out / 'lowest_confidence_crops.jpg')
    if args.synthetic_sensitivity:
        synthetic_sensitivity(model, data, device, args.batch_size, args.threshold, out)
    print(f"VAL: n={len(truth)} raw_accuracy={raw_accuracy:.4f} raw_errors={summary['raw_errors_val']}")
    print(f"Threshold={args.threshold:.3f} | accepted={selected['accepted']} | unknown={selected['unknown']} | coverage={selected['coverage']:.4f}")
    print(f"Accepted accuracy={selected['accepted_accuracy']} | ECE (descriptive)={summary['ece_val_10_bins_descriptive']:.5f}")
    if summary['raw_errors_val'] == 0:
        print('NOTE: VAL has no errors => UNKNOWN ability to reject model mistakes is UNTESTED.')
    else:
        print('NOTE: UNKNOWN effectiveness is estimated on VAL only; check challenging samples separately.')
    print(f'[PASS] W3 validation analysis saved to: {out}')

if __name__ == '__main__':
    main()
