from pathlib import Path
import sys

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.inference import InferenceEngine
from src.model_loader import Settings


class FakeLoader:
    def __init__(self):
        self.settings = Settings.load()
        self.device = torch.device("cpu")
        self.threshold = .9
        self.model_version = "test"
        self.calls = []

    def predict(self, batch):
        self.calls.append(len(batch))
        return torch.tensor([[.8,.2], [.09,.91], [.05,.95]][:len(batch)])


def test_batch_order_and_unknown(monkeypatch):
    import src.inference as inference
    monkeypatch.setattr(inference, "decode_image", lambda data, max_pixels: object())
    monkeypatch.setattr(inference, "preprocess", lambda image, spots: torch.zeros(len(spots),3,224,224))
    loader = FakeLoader()
    result = InferenceEngine(loader).infer(b"image", [{"spot_id":s,"polygon":[]} for s in ("Z","A","B")])
    assert loader.calls == [3]
    assert [x["spot_id"] for x in result.predictions] == ["Z","A","B"]
    assert [x["label"] for x in result.predictions] == ["unknown","occupied","occupied"]
    assert result.predictions[0]["raw_label"] == "empty"
    assert result.predictions[0]["scores"] == {"empty": .8, "occupied": .2} or abs(result.predictions[0]["scores"]["empty"]-.8)<1e-6
