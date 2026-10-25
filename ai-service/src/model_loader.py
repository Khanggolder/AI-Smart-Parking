"""Load the frozen W2 model and validate it against the W3 candidate config."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

import torch
import yaml

from .model_runtime import CLASSES, create_model, select_device
from .confidence_utils import _validate_threshold

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


@dataclass(frozen=True)
class Settings:
    checkpoint: Path
    threshold_config: Path
    device: str = "auto"
    batch_size: int = 32
    max_spots: int = 100
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 20_000_000
    port: int = 8001

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or SERVICE_ROOT / "configs/inference.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Invalid inference configuration")
        def setting(key: str, env: str):
            return os.environ.get(env, raw[key])
        def local_path(value: str) -> Path:
            p = Path(value)
            return p if p.is_absolute() else SERVICE_ROOT / p
        settings = cls(
            checkpoint=local_path(setting("checkpoint", "AI_CHECKPOINT_PATH")),
            threshold_config=local_path(setting("threshold_config", "AI_THRESHOLD_CONFIG")),
            device=str(setting("device", "AI_DEVICE")),
            batch_size=int(setting("batch_size", "AI_BATCH_SIZE")),
            max_spots=int(setting("max_spots", "AI_MAX_SPOTS")),
            max_upload_bytes=int(setting("max_upload_bytes", "AI_MAX_UPLOAD_BYTES")),
            max_image_pixels=int(setting("max_image_pixels", "AI_MAX_IMAGE_PIXELS")),
            port=int(setting("port", "AI_PORT")),
        )
        if settings.device not in ("auto", "cpu", "cuda"):
            raise ValueError("Device must be auto, cpu or cuda")
        if not 1 <= settings.max_spots <= 100 or min(settings.batch_size, settings.max_upload_bytes, settings.max_image_pixels) < 1 or not 1 <= settings.port <= 65535:
            raise ValueError("Invalid positive limits, port, or max_spots > 100")
        return settings


class ModelLoader:
    def __init__(self, settings: Settings):
        self.settings = settings
        path = settings.checkpoint
        if not path.is_file():
            raise FileNotFoundError(f"Checkpoint missing: {path}")
        if not settings.threshold_config.is_file():
            raise FileNotFoundError(f"Threshold configuration missing: {settings.threshold_config}")
        config = json.loads(settings.threshold_config.read_text(encoding="utf-8"))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha.lower() != str(config.get("checkpoint_sha256", "")).lower():
            raise ValueError("Checkpoint SHA-256 differs from W3 configuration")
        if config.get("architecture") != "mobilenet_v3_small" or config.get("class_order") != list(CLASSES) or config.get("image_size") != 224 or config.get("crop_mode") != "mask":
            raise ValueError("W3 architecture, class order, image size, or crop mode mismatch")
        norm = config.get("normalization", {})
        if norm.get("mean") != list(MEAN) or norm.get("std") != list(STD):
            raise ValueError("W3 normalization mismatch")
        if config.get("unknown_rule") != "max_softmax_probability < threshold":
            raise ValueError("W3 UNKNOWN rule mismatch")
        self.threshold = _validate_threshold(config["unknown_threshold"])
        self.device = select_device(settings.device)
        try:
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        except Exception as exc:
            raise ValueError(f"Cannot read checkpoint: {exc}") from exc
        if not isinstance(checkpoint, dict) or checkpoint.get("architecture") != "mobilenet_v3_small" or checkpoint.get("num_classes") != 2 or checkpoint.get("class_names") != list(CLASSES) or checkpoint.get("image_size") != 224 or checkpoint.get("preprocess") != "W1 ParkingSpotDataset ImageNet normalize":
            raise ValueError("Incompatible W2 checkpoint metadata")
        if checkpoint.get("weights_source") != "pretrained" or checkpoint.get("selected_epoch") != config.get("selected_epoch"):
            raise ValueError("Unexpected checkpoint source or epoch")
        model = create_model(pretrained=False)
        try:
            model.load_state_dict(checkpoint["model_state"], strict=True)
        except (KeyError, RuntimeError) as exc:
            raise ValueError(f"Incompatible model state: {exc}") from exc
        self.model = model.to(self.device).eval()
        self.model_version = f"mobilenetv3-small-w2-{sha[:12]}"
        self.checkpoint_sha256 = sha

    def predict(self, batch: torch.Tensor) -> torch.Tensor:
        if batch.ndim != 4 or batch.shape[1:] != (3, 224, 224) or batch.shape[0] < 1:
            raise ValueError("Expected nonempty N x 3 x 224 x 224 tensor")
        with torch.inference_mode():
            logits = self.model(batch.to(self.device))
            if logits.shape != (len(batch), 2) or not torch.isfinite(logits).all():
                raise RuntimeError("Invalid model logits")
            return torch.softmax(logits, dim=1).cpu()
