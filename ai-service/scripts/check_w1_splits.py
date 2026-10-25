"""Run this check before fitting any model."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from baseline_utils import assert_safe_splits

if __name__ == '__main__':
    summary = assert_safe_splits(ROOT/'manifests')
    for split, info in summary.items():
        print(f"{split:5}: {info['rows']:5} crops | {info['days']:2} days | labels={info['labels']}")
        if set(info['labels']) != {'empty','occupied'}:
            raise RuntimeError(f'{split} does not contain both classes; review split before training.')
    print('[PASS] No day, image or crop overlaps between splits.')
