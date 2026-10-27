"""W3 reference-image API regressions. SQLite and temporary filesystem only."""

from io import BytesIO
import uuid

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
from app.models import AuditLog, Camera, User

PASSWORD = "Strong-test-password-12345"


def image_data(kind="PNG"):
    buf = BytesIO()
    Image.new("RGB", (48, 24), color=(34, 67, 21)).save(buf, format=kind)
    return buf.getvalue()


@pytest.fixture()
def context(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "reference-image-tests-use-only-disposable-secret")
    monkeypatch.setenv("REFERENCE_IMAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def fkeys(raw, _record):
        raw.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            User(username="refadmin", password_hash=hash_password(PASSWORD), role="admin"),
            User(username="refoperator", password_hash=hash_password(PASSWORD), role="operator"),
        ])
        db.commit()

    def db_override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app) as client:
            def auth(name):
                login = client.post("/api/v1/auth/login", json={"username": name, "password": PASSWORD})
                assert login.status_code == 200, login.text
                return {"Authorization": "Bearer " + login.json()["access_token"]}
            yield client, auth("refadmin"), auth("refoperator"), factory, tmp_path / "storage"
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        get_settings.cache_clear()


def create_camera(client, headers):
    lot = client.post("/api/v1/parking-lots", headers=headers, json={"name": "Camera lot"})
    assert lot.status_code == 201, lot.text
    camera = client.post("/api/v1/cameras", headers=headers, json={
        "parking_lot_id": lot.json()["id"], "name": "REF-01"})
    assert camera.status_code == 201, camera.text
    return camera.json()


def upload(client, headers, camera, data=None, media_type="image/png", version=1):
    return client.put(
        f"/api/v1/cameras/{camera['id']}/reference-image",
        headers=headers,
        data={"expected_camera_config_version": str(version)},
        files={"image": ("../../evil.png", image_data() if data is None else data, media_type)},
    )


def test_upload_png_and_secure_get(context):
    client, admin, operator, factory, root = context
    cam = create_camera(client, admin)
    path = f"/api/v1/cameras/{cam['id']}/reference-image"
    assert client.get(path, headers=operator).status_code == 404
    data = image_data()
    response = upload(client, admin, cam, data=data)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reference_width"] == 48 and body["reference_height"] == 24
    assert body["config_version"] == 2
    assert ".." not in body["reference_image_path"]
    assert "evil" not in body["reference_image_path"]
    assert (root / body["reference_image_path"]).read_bytes() == data
    got = client.get(path, headers=operator)
    assert got.status_code == 200 and got.content == data
    assert got.headers["content-type"] == "image/png"
    assert got.headers["cache-control"] == "private, no-store"
    with factory() as db:
        assert db.get(Camera, uuid.UUID(cam["id"])).config_version == 2
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 3


def test_upload_jpeg_and_form_validation(context):
    client, admin, _, _, _ = context
    cam = create_camera(client, admin)
    pic = image_data("JPEG")
    response = upload(client, admin, cam, pic, "image/jpeg")
    assert response.status_code == 200
    assert response.json()["reference_image_path"].endswith(".jpg")
    invalid = client.put(f"/api/v1/cameras/{cam['id']}/reference-image", headers=admin,
        files={"image": ("test.jpg", pic, "image/jpeg")})
    assert invalid.status_code == 422


def test_rbac_and_not_found(context):
    client, admin, operator, _, root = context
    cam = create_camera(client, admin)
    url = f"/api/v1/cameras/{cam['id']}/reference-image"
    assert upload(client, operator, cam).status_code == 403
    assert upload(client, {}, cam).status_code == 401
    assert client.get(url).status_code == 401
    assert client.get(url, headers=operator).status_code == 404
    unknown = {"id": str(uuid.uuid4())}
    assert upload(client, admin, unknown).status_code == 404
    assert client.get(f"/api/v1/cameras/{unknown['id']}/reference-image", headers=operator).status_code == 404
    assert not root.exists()


@pytest.mark.parametrize("content,media_type,status", [
    (b"not an image", "image/png", 422),
    (b"not an image", "application/octet-stream", 415),
    (b"", "image/png", 422),
    (image_data("JPEG"), "image/png", 415),
])
def test_corrupt_or_mismatched_type(context, content, media_type, status):
    client, admin, _, factory, root = context
    cam = create_camera(client, admin)
    response = upload(client, admin, cam, content, media_type)
    assert response.status_code == status, response.text
    with factory() as db:
        row = db.get(Camera, uuid.UUID(cam["id"]))
        assert row.config_version == 1 and row.reference_image_path is None
    assert not root.exists()


def test_large_image_fails_without_file(context, monkeypatch):
    client, admin, _, _, root = context
    cam = create_camera(client, admin)
    monkeypatch.setenv("UPLOAD_MAX_MB", "1")
    get_settings.cache_clear()
    response = upload(client, admin, cam, b"x" * (1024 * 1024 + 3), "image/png")
    assert response.status_code == 413
    assert not root.exists()


def test_stale_version_and_immutable_replacement(context):
    client, admin, _, _, root = context
    cam = create_camera(client, admin)
    first = upload(client, admin, cam)
    assert first.status_code == 200
    assert upload(client, admin, cam, version=1).status_code == 409
    second = upload(client, admin, cam, version=2)
    assert second.status_code == 200
    assert second.json()["config_version"] == 3
    assert second.json()["reference_image_path"] != first.json()["reference_image_path"]
    # Immutable old files are retained until an explicit retention policy exists.
    assert len(list(root.rglob("*.png"))) == 2


def test_active_polygons_block_reference_replacement(context):
    client, admin, _, _, root = context
    cam = create_camera(client, admin)
    spot = client.post(f"/api/v1/cameras/{cam['id']}/spots", headers=admin, json={
        "spot_code": "P01", "polygon": [{"x": .1, "y": .1}, {"x": .7, "y": .1}, {"x": .7, "y": .6}],
        "expected_camera_config_version": 1,
    })
    assert spot.status_code == 201, spot.text
    refused = upload(client, admin, cam, version=2)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "ACTIVE_SPOTS_EXIST"
    assert not root.exists()
    deleted = client.delete(f"/api/v1/spots/{spot.json()['id']}?expected_camera_config_version=2", headers=admin)
    assert deleted.status_code == 204
    allowed = upload(client, admin, cam, version=3)
    assert allowed.status_code == 200 and allowed.json()["config_version"] == 4


def test_reject_invalid_stored_path(context):
    client, admin, operator, factory, _ = context
    cam = create_camera(client, admin)
    with factory() as db:
        row = db.get(Camera, uuid.UUID(cam["id"]))
        row.reference_image_path = "../.env"
        db.commit()
    res = client.get(f"/api/v1/cameras/{cam['id']}/reference-image", headers=operator)
    assert res.status_code == 404
