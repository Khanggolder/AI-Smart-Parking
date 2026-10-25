"""Model construction and device selection shared by inference and research CLI tools."""
from __future__ import annotations

import torch
from torch import nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

CLASSES = ("empty", "occupied")


def create_model(pretrained: bool = False, freeze_features: bool = False) -> nn.Module:
    """Build the W2 MobileNetV3-Small architecture with its two output classes."""
    weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    try:
        model = mobilenet_v3_small(weights=weights)
    except Exception as exc:
        if pretrained:
            raise RuntimeError(
                'Unable to download pretrained MobileNetV3 weights. Check internet, '
                'then retry. Use --weights none ONLY to smoke-test the code.'
            ) from exc
        raise
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, len(CLASSES))
    for param in model.features.parameters():
        param.requires_grad = not freeze_features
    return model


def select_device(name: str) -> torch.device:
    """Resolve auto/cpu/cuda using the existing W2 device policy."""
    if name == 'auto':
        name = 'cuda' if torch.cuda.is_available() else 'cpu'
    if name == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; use --device cpu or --device auto')
    return torch.device(name)
