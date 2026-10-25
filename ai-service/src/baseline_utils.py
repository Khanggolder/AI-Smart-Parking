"""Utilities shared between baseline training and held-out evaluation."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

# W1-W3 scripts import this module directly from src/; W4+ uses src.baseline_utils.
# Keep both entrypoints while runtime imports only the small model module.
if __package__:
    from .model_runtime import CLASSES, create_model, select_device
else:
    from model_runtime import CLASSES, create_model, select_device


def metrics_from_predictions(y_true: list[int], y_pred: list[int]) -> dict:
    if not y_true or len(y_true) != len(y_pred):
        raise ValueError('Empty/mismatched predictions')
    cm = np.zeros((2, 2), dtype=np.int64)
    for actual, predicted in zip(y_true, y_pred):
        if actual not in (0, 1) or predicted not in (0, 1):
            raise ValueError('Labels must be 0 or 1')
        cm[actual, predicted] += 1
    by_class = {}
    for cls_id, name in enumerate(CLASSES):
        tp = int(cm[cls_id, cls_id])
        fp = int(cm[:, cls_id].sum() - tp)
        fn = int(cm[cls_id, :].sum() - tp)
        precision = tp/(tp+fp) if tp+fp else 0.0
        recall = tp/(tp+fn) if tp+fn else 0.0
        f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
        by_class[name] = {'support': int(cm[cls_id, :].sum()), 'precision': precision, 'recall': recall, 'f1': f1}
    return {
        'accuracy': float(np.trace(cm)/cm.sum()),
        'macro_f1': float(sum(by_class[x]['f1'] for x in CLASSES)/2),
        'by_class': by_class,
        'confusion_matrix': cm.tolist(),
        'class_order': list(CLASSES),
        'total': int(cm.sum()),
    }


def manifest_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_safe_splits(manifest_dir: Path) -> dict:
    """Reject same day/image/crop appearing in multiple train/val/test manifests."""
    contents = {}
    for split in ('train','val','test'):
        p = manifest_dir / f'{split}.csv'
        if not p.exists():
            raise FileNotFoundError(f'Missing {p}')
        with p.open(newline='', encoding='utf-8') as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            raise ValueError(f'{p} has no rows')
        required = {'crop_path', 'label', 'date', 'image_file'}
        if not required.issubset(rows[0]):
            raise ValueError(f'{p} missing columns {sorted(required-set(rows[0]))}')
        if any(r['label'] not in CLASSES for r in rows):
            raise ValueError(f'{p} contains invalid labels')
        paths=[r['crop_path'] for r in rows]
        if len(paths)!=len(set(paths)):
            raise ValueError(f'{p} contains duplicate crop_path')
        contents[split] = rows
    for i, x in enumerate(('train','val','test')):
        for y in ('train','val','test')[i+1:]:
            for key in ('date','image_file','crop_path'):
                overlap = {r[key] for r in contents[x]} & {r[key] for r in contents[y]}
                if overlap:
                    raise ValueError(f'DATA LEAKAGE: {x}/{y} overlap for {key}: {sorted(overlap)[:3]}')
    return {
        split: {'rows':len(rows), 'days':len({r['date'] for r in rows}),
                'labels':dict(Counter(r['label'] for r in rows)),
                'sha256': manifest_sha256(manifest_dir/f'{split}.csv')}
        for split, rows in contents.items()
    }


def save_confusion_png(matrix: list[list[int]], output: Path, title: str) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5.1, 4.4))
    arr = np.asarray(matrix, dtype=int)
    im=ax.imshow(arr, cmap='Blues')
    fig.colorbar(im, ax=ax, fraction=.046, pad=.04)
    ax.set(xticks=[0,1], yticks=[0,1], xticklabels=CLASSES, yticklabels=CLASSES,
           xlabel='Predicted label', ylabel='Ground-truth label', title=title)
    for i in range(2):
        for j in range(2):
            ax.text(j,i,str(arr[i,j]),ha='center',va='center',fontsize=15,
                    color='white' if arr[i,j]>arr.max()/2 else 'black')
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def dump_json(output: Path, content: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')


def predict_all(model: nn.Module, loader: torch.utils.data.DataLoader,
                device: torch.device, criterion: nn.Module | None = None) -> tuple[list[int], list[int], float | None]:
    model.eval()
    truths, predictions, total_loss, n = [], [], 0.0, 0
    with torch.inference_mode():
        for xb, yb in loader:
            logits = model(xb.to(device))
            yb = yb.to(device)
            if criterion is not None:
                total_loss += float(criterion(logits, yb).item())*len(yb)
                n += len(yb)
            truths.extend(yb.cpu().tolist())
            predictions.extend(logits.argmax(1).cpu().tolist())
    return truths, predictions, total_loss/n if n else None
