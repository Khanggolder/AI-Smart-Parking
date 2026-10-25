"""Pure helper functions for parking occupancy selective classification."""
from __future__ import annotations

from collections import Counter
import numpy as np

CLASSES = ('empty', 'occupied')


def _validate_threshold(threshold: float) -> float:
    value = float(threshold)
    if not np.isfinite(value) or not 0.5 <= value <= 1.0:
        raise ValueError('Threshold must be finite and between 0.5 and 1.0')
    return value


def _validate_probabilities(probs: np.ndarray) -> np.ndarray:
    values = np.asarray(probs, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(CLASSES) or not len(values):
        raise ValueError('Expected a nonempty Nx2 probability array')
    if (not np.all(np.isfinite(values)) or np.any(values < 0) or
            np.any(values > 1) or
            not np.all(np.isclose(values.sum(axis=1), 1.0, rtol=0, atol=1e-4))):
        raise ValueError('Invalid class probabilities')
    return values


def decide(prob_empty: float, prob_occupied: float, threshold: float) -> dict:
    """Predict label with abstention. Always expose winning probability even if unknown.

    `confidence` is max softmax probability, NOT calibrated confidence.
    """
    threshold = _validate_threshold(threshold)
    probs = _validate_probabilities([[prob_empty, prob_occupied]])[0]
    index = int(np.argmax(probs))
    conf = float(probs[index])
    return {'raw_label': CLASSES[index],
            'label': CLASSES[index] if conf >= threshold else 'unknown',
            'confidence': conf}


def selective_summary(truth: list[int], probs: np.ndarray, threshold: float) -> dict:
    threshold = _validate_threshold(threshold)
    probs = _validate_probabilities(probs)
    if len(truth) != len(probs):
        raise ValueError('Expected a nonempty Nx2 probability array matching truth')
    preds = np.argmax(probs, axis=1)
    confidence = np.max(probs, axis=1)
    accepted = confidence >= threshold
    t = np.asarray(truth, dtype=int)
    if not np.all(np.isin(t, (0, 1))):
        raise ValueError('Invalid labels')
    cm = np.zeros((2, 3), dtype=int)  # 0 empty, 1 occupied, 2 unknown
    for a, b, accept in zip(t, preds, accepted):
        cm[a, b if accept else 2] += 1
    n_accepted = int(accepted.sum())
    return {
        'threshold': float(threshold),
        'total': len(t),
        'accepted': n_accepted,
        'unknown': int((~accepted).sum()),
        'coverage': float(accepted.mean()),
        'accepted_accuracy': (float((preds[accepted] == t[accepted]).mean()) if n_accepted else None),
        'unknown_by_true_class': {CLASSES[c]: int(((t == c) & ~accepted).sum()) for c in (0, 1)},
        'confusion_matrix_true_rows_predicted_cols_empty_occupied_unknown': cm.tolist(),
        'prediction_counts': dict(Counter(CLASSES[p] if a else 'unknown' for p, a in zip(preds, accepted))),
    }


def expected_calibration_error(truth: list[int], probs: np.ndarray, bins: int = 10) -> float:
    """Descriptive metric only; cannot validate unknown handling on a no-error split."""
    p = _validate_probabilities(probs)
    labels = np.asarray(truth)
    if len(labels) != len(p) or not np.all(np.isin(labels, (0, 1))) or bins < 1:
        raise ValueError('Invalid ECE inputs')
    conf = p.max(axis=1)
    correct = p.argmax(axis=1) == labels
    edges = np.linspace(0, 1, bins + 1)
    total = 0.
    for k in range(bins):
        mask = (conf >= edges[k]) & (conf <= edges[k + 1] if k == bins-1 else conf < edges[k + 1])
        if mask.any():
            total += mask.mean() * abs(float(correct[mask].mean()) - float(conf[mask].mean()))
    return float(total)
