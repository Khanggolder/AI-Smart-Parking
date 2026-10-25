from io import BytesIO
from dataclasses import replace
import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from PIL import Image
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.model_loader import Settings
from src.service import create_app


class FakeLoader:
    def __init__(self, settings):
        self.settings = settings
        self.device = torch.device("cpu")
        self.threshold = .9
        self.model_version = "fake-v1"

    def predict(self, batch):
        return torch.tensor([[.7,.3]] * len(batch))


def payload(spots=None):
    im = Image.new("RGB", (80,60), "white")
    buf = BytesIO()
    im.save(buf, format="JPEG")
    if spots is None:
        spots = [{"spot_id":"P01","polygon":[[.1,.1],[.5,.1],[.5,.5],[.1,.5]]}]
    return {"image": ("scene.jpg", buf.getvalue(), "image/jpeg")}, {"camera_id":"CAM01","spots_json":json.dumps(spots)}


def test_health_ready_and_infer_schema():
    with TestClient(create_app(loader_factory=FakeLoader)) as client:
        assert client.get("/health").json() == {"status":"alive"}
        assert client.get("/ready").json()["device"] == "cpu"
        files, data = payload()
        result = client.post("/v1/infer", files=files, data=data)
        assert result.status_code == 200
        body = result.json()
        assert body["camera_id"] == "CAM01" and body["model_version"] == "fake-v1"
        assert body["threshold"] == .9 and body["processing_time_ms"] >= 0
        assert body["predictions"][0]["spot_id"] == "P01"
        assert body["predictions"][0]["raw_label"] == "empty"
        assert body["predictions"][0]["label"] == "unknown"
        assert set(body["predictions"][0]["scores"]) == {"empty","occupied"}


def test_invalid_requests():
    with TestClient(create_app(loader_factory=FakeLoader)) as client:
        files, data = payload()
        assert client.post("/v1/infer", files=files, data={}).status_code == 422
        assert client.post("/v1/infer", files={"image":("x.txt",b"text","text/plain")}, data=data).status_code == 415
        assert client.post("/v1/infer", files={"image":("x.jpg",b"","image/jpeg")}, data=data).json()["error"]["code"] == "EMPTY_IMAGE"
        assert client.post("/v1/infer", files={"image":("x.jpg",b"bad","image/jpeg")}, data=data).json()["error"]["code"] == "INVALID_IMAGE"
        data["spots_json"] = "not json"
        assert client.post("/v1/infer", files=files, data=data).json()["error"]["code"] == "INVALID_SPOTS_JSON"
        files, data = payload([{"spot_id":"A","polygon":[[0,0],[1,0],[1,1]]}] * 2)
        assert client.post("/v1/infer", files=files, data=data).json()["error"]["code"] == "DUPLICATE_SPOT_ID"
        files, data = payload([{"spot_id":"A","polygon":[[0,0],[1,1],[0,1],[1,0]]}])
        assert client.post("/v1/infer", files=files, data=data).json()["error"]["code"] == "INVALID_POLYGON"


def test_unavailable_model():
    def broken(settings):
        raise FileNotFoundError("missing checkpoint")
    with TestClient(create_app(loader_factory=broken)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        files, data = payload()
        assert client.post("/v1/infer", files=files, data=data).json()["error"]["code"] == "MODEL_UNAVAILABLE"


def test_upload_limit_and_inference_error():
    settings = replace(Settings.load(), max_upload_bytes=10)
    with TestClient(create_app(settings=settings, loader_factory=FakeLoader)) as client:
        files, data = payload()
        response = client.post("/v1/infer", files=files, data=data)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"

    class BrokenLoader(FakeLoader):
        def predict(self, batch):
            raise RuntimeError("private model error")
    with TestClient(create_app(loader_factory=BrokenLoader)) as client:
        files, data = payload()
        response = client.post("/v1/infer", files=files, data=data)
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INFERENCE_ERROR"
        assert "private" not in response.text
