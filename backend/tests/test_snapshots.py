"""W4 pipeline integration tests: fake AI HTTP transport, real SQLite and files."""
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path
import uuid
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Snapshot, SpotPrediction, Camera, ParkingSpot, User
from app.services import ai_client, snapshot_jobs

PASSWORD = "Another-Strong-LocalPassword-123"
POLYGON = [{"x": .1, "y": .2}, {"x": .6, "y": .2}, {"x": .6, "y": .7}, {"x": .1, "y": .7}]


def image_bytes(size=(40, 20)):
    stream = BytesIO()
    Image.new("RGB", size, (42, 60, 75)).save(stream, format="PNG")
    return stream.getvalue()


def mock_ai_payload(spot_id, camera_id, confidence=.95, label="occupied"):
    return {
        "camera_id": camera_id,
        "model_version": "mobilenetv3-small-w2-488ed38efe01",
        "threshold": .90,
        "predictions": [{"spot_id": spot_id, "raw_label": "occupied",
                         "label": label, "confidence": confidence,
                         "scores": {"empty": 1 - confidence, "occupied": confidence}}],
        "processing_time_ms": 19.75,
    }


@pytest.fixture()
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-W4-signature-never-use-for-production")
    monkeypatch.setenv("REFERENCE_IMAGE_DIR", str(tmp_path / "reference"))
    monkeypatch.setenv("SNAPSHOT_IMAGE_DIR", str(tmp_path / "snapshots"))
    monkeypatch.setenv("AI_SERVICE_URL", "http://127.0.0.1:8001")
    get_settings.cache_clear()
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def fk(raw, _):
        raw.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(snapshot_jobs, "get_session_factory", lambda: factory)
    with factory() as db:
        db.add_all([User(username="w4-admin", password_hash=hash_password(PASSWORD), role="admin"),
                    User(username="w4-operator", password_hash=hash_password(PASSWORD), role="operator")])
        db.commit()

    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            def login(name):
                r = client.post("/api/v1/auth/login", json={"username": name, "password": PASSWORD})
                assert r.status_code == 200, r.text
                return {"Authorization": "Bearer " + r.json()["access_token"]}
            yield client, login("w4-admin"), login("w4-operator"), factory, tmp_path, monkeypatch
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        get_settings.cache_clear()


def make_camera(c, admin, with_reference=True, with_spot=True):
    lot = c.post("/api/v1/parking-lots", headers=admin, json={"name": "W4 lot"})
    assert lot.status_code == 201, lot.text
    cam = c.post("/api/v1/cameras", headers=admin, json={
        "name": "W4 cam", "parking_lot_id": lot.json()["id"]})
    assert cam.status_code == 201, cam.text
    cam = cam.json()
    if with_reference:
        up = c.put(f"/api/v1/cameras/{cam['id']}/reference-image", headers=admin,
                   data={"expected_camera_config_version": "1"},
                   files={"image": ("reference.png", image_bytes(), "image/png")})
        assert up.status_code == 200, up.text
        cam = up.json()
    if with_spot:
        res = c.post(f"/api/v1/cameras/{cam['id']}/spots", headers=admin,
                     json={"spot_code": "P01", "polygon": POLYGON,
                           "expected_camera_config_version": cam["config_version"]})
        assert res.status_code == 201, res.text
        cam["spot"] = res.json()
        cam["config_version"] = res.json()["camera_config_version"]
    return cam


def snapshot(c, user, camera_id, image=None, captured_at=None):
    dt = captured_at or datetime.now(timezone.utc).isoformat()
    return c.post("/api/v1/snapshots", headers=user,
                  data={"camera_id": camera_id, "captured_at": dt},
                  files={"image": ("snapshot.png", image_bytes() if image is None else image, "image/png")})


def set_ai(ctx, handler):
    monkeypatch = ctx[-1]
    monkeypatch.setattr(ai_client, "create_http_client", lambda timeout:
                        httpx.Client(transport=httpx.MockTransport(handler)))


def test_snapshot_success_real_db_and_mock_http_ai(ctx):
    c, admin, op, factory, tmp, _ = ctx
    cam = make_camera(c, admin)
    spot_id = cam["spot"]["id"]
    def fake_ai(req):
        assert req.url.path == "/v1/infer"
        assert req.method == "POST"
        content = req.content.decode("utf-8", errors="replace")
        assert 'name="spots_json"' in content
        assert 'name="camera_id"' in content
        assert str(spot_id) in content
        assert "[[0.1,0.2],[0.6,0.2],[0.6,0.7],[0.1,0.7]]" in content
        return httpx.Response(200, json=mock_ai_payload(spot_id, cam["id"]))
    set_ai(ctx, fake_ai)
    result = snapshot(c, op, cam["id"])
    assert result.status_code == 202, result.text
    assert result.json()["job_status"] == "queued"
    assert result.json()["camera_config_version"] == cam["config_version"]
    uid = result.json()["id"]
    view = c.get(f"/api/v1/snapshots/{uid}", headers=op)
    assert view.status_code == 200, view.text
    body = view.json()
    assert body["job_status"] == "completed" and body["error_code"] is None
    assert body["ai_threshold"] == .9
    assert body["ai_model_version"] == "mobilenetv3-small-w2-488ed38efe01"
    assert body["ai_processing_time_ms"] == 19.75
    assert body["summary"] == {"total": 1, "empty": 0, "occupied": 1, "unknown": 0,
                                "occupancy_rate": 100.0, "full": True, "status": "FULL"}
    assert body["predictions"][0]["parking_spot_id"] == spot_id
    assert body["predictions"][0]["raw_label"] == "occupied"
    assert body["predictions"][0]["scores"]["occupied"] == .95
    assert body["predictions"][0]["polygon"] == POLYGON
    assert body["is_stale"] is False
    got_image = c.get(f"/api/v1/snapshots/{uid}/image", headers=op)
    assert got_image.status_code == 200 and got_image.content == image_bytes()
    assert got_image.headers["cache-control"] == "private, no-store"
    paged = c.get(f"/api/v1/snapshots?camera_id={cam['id']}&job_status=completed", headers=op)
    assert paged.status_code == 200 and paged.json()["total"] == 1
    with factory() as db:
        stored = db.get(Snapshot, uuid.UUID(uid))
        assert stored.spots_at_capture[0]["id"] == spot_id
        assert db.scalar(select(func.count()).select_from(SpotPrediction)) == 1
        assert (tmp / "snapshots" / stored.image_path).is_file()


def test_ai_unknown_remains_unknown_and_not_full(ctx):
    c, admin, _, _, _, _ = ctx
    cam = make_camera(c, admin)
    set_ai(ctx, lambda req: httpx.Response(200, json=mock_ai_payload(cam["spot"]["id"], cam["id"], .74, "unknown")))
    response = snapshot(c, admin, cam["id"])
    body = c.get(f"/api/v1/snapshots/{response.json()['id']}", headers=admin).json()
    assert body["predictions"][0]["predicted_label"] == "unknown"
    assert body["predictions"][0]["raw_label"] == "occupied"
    assert body["summary"]["status"] == "UNDETERMINED"
    assert body["summary"]["full"] is False
    assert body["summary"]["occupancy_rate"] == 0


@pytest.mark.parametrize("status,expected", [(503,"AI_UNAVAILABLE"), (422,"AI_REJECTED_INPUT"),
                                            (500,"AI_HTTP_ERROR")])
def test_ai_http_failure_creates_failed_job_not_fake_predictions(ctx, status, expected):
    c, admin, _, factory, _, _ = ctx
    cam = make_camera(c, admin)
    set_ai(ctx, lambda req: httpx.Response(status, json={"error":{"code":"X","message":"error"}}))
    response = snapshot(c, admin, cam["id"])
    assert response.status_code == 202
    row = c.get(f"/api/v1/snapshots/{response.json()['id']}", headers=admin).json()
    assert row["job_status"] == "failed"
    assert row["error_code"] == expected
    assert row["predictions"] == [] and row["summary"] is None
    assert row["is_stale"] is None
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(SpotPrediction)) == 0


def test_ai_timeout_records_failed(ctx):
    c, admin, _, _, _, _ = ctx
    cam = make_camera(c, admin)
    def timeout(req):
        raise httpx.ReadTimeout("read timed out", request=req)
    set_ai(ctx, timeout)
    resp = snapshot(c, admin, cam["id"])
    assert resp.status_code == 202
    row = c.get(f"/api/v1/snapshots/{resp.json()['id']}", headers=admin).json()
    assert row["error_code"] == "AI_TIMEOUT"


@pytest.mark.parametrize("tamper,expected", [
    (lambda p: p.update(camera_id="another-camera"), "AI_RESPONSE_MISMATCH"),
    (lambda p: p["predictions"][0].update(spot_id="fake-spot"), "AI_RESPONSE_MISMATCH"),
    (lambda p: p["predictions"].clear(), "AI_RESPONSE_MISMATCH"),
    (lambda p: p["predictions"][0].update(confidence=1.5), "AI_INVALID_RESPONSE"),
    (lambda p: p["predictions"][0].update(label="empty"), "AI_INVALID_RESPONSE"),
    (lambda p: p["predictions"][0]["scores"].update(empty=.9), "AI_INVALID_RESPONSE"),
])
def test_invalid_ai_reply_fails_atomically(ctx, tamper, expected):
    c, admin, _, factory, _, _ = ctx
    cam = make_camera(c, admin)
    result = mock_ai_payload(cam["spot"]["id"], cam["id"])
    tamper(result)
    set_ai(ctx, lambda req: httpx.Response(200, json=result))
    resp = snapshot(c, admin, cam["id"])
    row = c.get(f"/api/v1/snapshots/{resp.json()['id']}", headers=admin).json()
    assert row["job_status"] == "failed" and row["error_code"] == expected
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(SpotPrediction)) == 0


def test_missing_reference_and_spots_rejected_before_storage(ctx):
    c, admin, _, factory, tmp, _ = ctx
    cam = make_camera(c, admin, with_reference=False, with_spot=False)
    res = snapshot(c, admin, cam["id"])
    assert res.status_code == 409 and res.json()["error"]["code"] == "CAMERA_NOT_CONFIGURED"
    up = c.put(f"/api/v1/cameras/{cam['id']}/reference-image", headers=admin,
               data={"expected_camera_config_version": "1"},
               files={"image": ("reference.png", image_bytes(), "image/png")})
    assert up.status_code == 200
    res = snapshot(c, admin, cam["id"])
    assert res.status_code == 409 and res.json()["error"]["code"] == "NO_ACTIVE_SPOTS"
    assert not (tmp / "snapshots").exists()


def test_bad_dimensions_timezone_and_missing_camera(ctx):
    c, admin, _, factory, tmp, _ = ctx
    cam = make_camera(c, admin)
    res = snapshot(c, admin, cam["id"], image=image_bytes((41, 20)))
    assert res.status_code == 422 and res.json()["error"]["code"] == "IMAGE_DIMENSIONS_MISMATCH"
    res = snapshot(c, admin, cam["id"], captured_at="2026-10-27T02:00:00")
    assert res.status_code == 422 and res.json()["error"]["code"] == "INVALID_CAPTURED_AT"
    res = snapshot(c, admin, str(uuid.uuid4()))
    assert res.status_code == 404
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Snapshot)) == 0
    assert not (tmp / "snapshots").exists()


def test_snapshot_rbac_filters_and_not_found(ctx):
    c, admin, operator, _, _, _ = ctx
    cam = make_camera(c, admin)
    assert snapshot(c, {}, cam["id"]).status_code == 401
    assert c.get("/api/v1/snapshots").status_code == 401
    assert c.get("/api/v1/snapshots", headers=operator).status_code == 200
    assert c.get(f"/api/v1/snapshots/{uuid.uuid4()}", headers=operator).status_code == 404
    assert c.get(f"/api/v1/snapshots/{uuid.uuid4()}/image", headers=operator).status_code == 404
    assert c.get("/api/v1/snapshots?job_status=bogus", headers=operator).status_code == 422
    assert c.get("/api/v1/snapshots?limit=101", headers=operator).status_code == 422
    assert c.get("/api/v1/snapshots?from=2026-10-27T12:00:00", headers=operator).status_code == 422


def test_camera_config_frozen_when_spot_changes_after_completion(ctx):
    c, admin, operator, factory, _, _ = ctx
    cam = make_camera(c, admin)
    orig_id = cam["spot"]["id"]
    set_ai(ctx, lambda req: httpx.Response(200, json=mock_ai_payload(orig_id, cam["id"])))
    response = snapshot(c, admin, cam["id"])
    snap_id = response.json()["id"]
    change = c.patch(f"/api/v1/spots/{orig_id}", headers=admin,
                     json={"spot_code": "P02", "expected_camera_config_version": cam["config_version"]})
    assert change.status_code == 200
    body = c.get(f"/api/v1/snapshots/{snap_id}", headers=operator).json()
    assert body["predictions"][0]["spot_code"] == "P01"
    assert body["camera_config_version"] == cam["config_version"]
    with factory() as db:
        row = db.get(Snapshot, uuid.UUID(snap_id))
        assert row.spots_at_capture[0]["spot_code"] == "P01"
