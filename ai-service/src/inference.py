"""Batch inference without annotations, persistence, or business status logic."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import torch

from .confidence_utils import decide
from .model_loader import ModelLoader
from .preprocessing import decode_image, preprocess, validate_spots


@dataclass
class InferenceResult:
    predictions: list[dict]
    preprocess_ms: float
    model_ms: float
    total_ms: float


class InferenceEngine:
    def __init__(self, loader: ModelLoader):
        self.loader = loader

    def infer(self, image: bytes, spots: object) -> InferenceResult:
        start = perf_counter()
        settings = self.loader.settings
        spots = validate_spots(spots, settings.max_spots)
        image_bgr = decode_image(image, settings.max_image_pixels)
        batch = preprocess(image_bgr, spots)
        preprocessed = perf_counter()
        probabilities = []
        for part in batch.split(settings.batch_size):
            probabilities.extend(self.loader.predict(part).tolist())
        if self.loader.device.type == "cuda":
            torch.cuda.synchronize(self.loader.device)
        predicted = perf_counter()
        output = []
        for spot, (empty, occupied) in zip(spots, probabilities, strict=True):
            choice = decide(empty, occupied, self.loader.threshold)
            output.append({"spot_id": spot["spot_id"], **choice,
                           "scores": {"empty": float(empty), "occupied": float(occupied)}})
        end = perf_counter()
        return InferenceResult(output, (preprocessed-start)*1000, (predicted-preprocessed)*1000, (end-start)*1000)
