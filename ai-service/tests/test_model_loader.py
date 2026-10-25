from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.model_loader import ModelLoader, Settings


def test_real_checkpoint_and_mapping():
    loader = ModelLoader(replace(Settings.load(), device="cpu"))
    assert loader.model.training is False
    assert loader.threshold == .9
    assert loader.model_version.startswith("mobilenetv3-small-w2-488ed38efe01")
    assert loader.model.classifier[-1].out_features == 2
    result = loader.predict(torch.zeros(2, 3, 224, 224))
    assert result.shape == (2, 2)
    assert torch.allclose(result.sum(1), torch.ones(2), atol=1e-5)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_real_cuda_inference():
    loader = ModelLoader(replace(Settings.load(), device="cuda"))
    assert loader.device.type == "cuda"
    assert loader.predict(torch.zeros(1, 3, 224, 224)).shape == (1, 2)


def test_missing_and_mismatched_checkpoint(tmp_path):
    settings = Settings.load()
    with pytest.raises(FileNotFoundError, match="Checkpoint missing"):
        ModelLoader(replace(settings, checkpoint=tmp_path / "missing.pt"))
    config = json.loads(settings.threshold_config.read_text(encoding="utf-8"))
    config["checkpoint_sha256"] = "0" * 64
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        ModelLoader(replace(settings, threshold_config=path))
