"""W3 parking polygon API tests with in-memory SQLite; no production data touched."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AuditLog, Camera, ParkingSpot, User

PASSWORD = "Local-password-12345"
TRIANGLE = [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.5}]
RECTANGLE = [{"x": 0.1, "y": 0.1}, {"x": 0.5, "y": 0.1},
             {"x": 0.5, "y": 0.6}, {"x": 0.1, "y": 0.6}]


@pytest.fixture()
def context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "testing-secret-token-should-not-be-used-in-production")
    get_settings.cache_clear()
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(raw, _):
        raw.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            User(username="admin_spots", password_hash=hash_password(PASSWORD), role="admin"),
            User(username="operator_spots", password_hash=hash_password(PASSWORD), role="operator"),
        ])
        db.commit()

    def db_override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app) as client:
            def auth(username):
                response = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
                assert response.status_code == 200, response.text
                return {"Authorization": "Bearer " + response.json()["access_token"]}
            yield client, auth("admin_spots"), auth("operator_spots"), factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        get_settings.cache_clear()


def setup_camera(c, admin):
    lot = c.post("/api/v1/parking-lots", headers=admin, json={"name": "Demo lot"})
    assert lot.status_code == 201, lot.text
    camera = c.post("/api/v1/cameras", headers=admin, json={"parking_lot_id": lot.json()["id"], "name": "CAM-01"})
    assert camera.status_code == 201, camera.text
    return camera.json()


def create_spot(c, admin, camera, code="P01", polygon=TRIANGLE, version=1):
    return c.post(f"/api/v1/cameras/{camera['id']}/spots", headers=admin, json={
        "spot_code": code, "polygon": polygon, "expected_camera_config_version": version,
    })


def test_create_list_and_read_by_operator(context):
    c, admin, operator, factory = context
    camera = setup_camera(c, admin)
    assert c.get(f"/api/v1/cameras/{camera['id']}/spots", headers=operator).json() == {
        "items": [], "total": 0, "camera_config_version": 1,
    }
    result = create_spot(c, admin, camera)
    assert result.status_code == 201, result.text
    spot = result.json()
    assert spot["spot_code"] == "P01" and spot["is_active"] is True
    assert spot["polygon"] == TRIANGLE and spot["camera_config_version"] == 2
    listed = c.get(f"/api/v1/cameras/{camera['id']}/spots", headers=operator)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == spot["id"]
    assert listed.json()["camera_config_version"] == 2
    with factory() as db:
        assert db.get(Camera, uuid.UUID(camera["id"])).config_version == 2
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 3


def test_patch_version_and_noop(context):
    c, admin, _, _ = context
    camera = setup_camera(c, admin)
    spot = create_spot(c, admin, camera).json()
    uri = f"/api/v1/spots/{spot['id']}"
    response = c.patch(uri, headers=admin, json={"spot_code": "  p02  ", "polygon": RECTANGLE, "expected_camera_config_version": 2})
    assert response.status_code == 200, response.text
    assert response.json()["spot_code"] == "P02"
    assert response.json()["polygon"] == RECTANGLE
    assert response.json()["camera_config_version"] == 3
    noop = c.patch(uri, headers=admin, json={"spot_code": "P02", "expected_camera_config_version": 3})
    assert noop.status_code == 200 and noop.json()["camera_config_version"] == 3
    stale = c.patch(uri, headers=admin, json={"spot_code": "P03", "expected_camera_config_version": 2})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "CAMERA_VERSION_CONFLICT"


def test_duplicate_code_same_camera_and_different_cameras(context):
    c, admin, _, factory = context
    a = setup_camera(c, admin)
    b = setup_camera(c, admin)
    created = create_spot(c, admin, a, "p01")
    assert created.status_code == 201
    duplicate = create_spot(c, admin, a, " P01 ", version=2)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "SPOT_CODE_CONFLICT"
    assert create_spot(c, admin, b, "P01").status_code == 201
    with factory() as db:
        assert db.get(Camera, uuid.UUID(a["id"])).config_version == 2


def test_soft_delete_and_history_preserved(context):
    c, admin, operator, factory = context
    camera = setup_camera(c, admin)
    spot = create_spot(c, admin, camera).json()
    url = f"/api/v1/spots/{spot['id']}?expected_camera_config_version=2"
    res = c.delete(url, headers=admin)
    assert res.status_code == 204 and res.content == b""
    assert c.get(f"/api/v1/cameras/{camera['id']}/spots", headers=operator).json()["total"] == 0
    all_spots = c.get(f"/api/v1/cameras/{camera['id']}/spots?include_inactive=true", headers=operator).json()
    assert all_spots["items"][0]["is_active"] is False
    assert all_spots["camera_config_version"] == 3
    assert c.delete(url, headers=admin).status_code == 409
    assert c.patch(f"/api/v1/spots/{spot['id']}", headers=admin, json={"spot_code": "P99", "expected_camera_config_version": 3}).status_code == 409
    with factory() as db:
        assert db.get(ParkingSpot, uuid.UUID(spot["id"])) is not None
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 4


def test_rbac_for_all_spot_routes(context):
    c, admin, op, _ = context
    camera = setup_camera(c, admin)
    uri = f"/api/v1/cameras/{camera['id']}/spots"
    assert c.get(uri).status_code == 401
    assert c.post(uri, json={"spot_code": "P01", "polygon": TRIANGLE, "expected_camera_config_version": 1}).status_code == 401
    assert c.post(uri, headers=op, json={"spot_code": "P01", "polygon": TRIANGLE, "expected_camera_config_version": 1}).status_code == 403
    spot = create_spot(c, admin, camera).json()
    assert c.patch(f"/api/v1/spots/{spot['id']}", headers=op, json={"spot_code": "P02", "expected_camera_config_version": 2}).status_code == 403
    assert c.delete(f"/api/v1/spots/{spot['id']}?expected_camera_config_version=2", headers=op).status_code == 403


@pytest.mark.parametrize("polygon", [
    [{"x": 0.1, "y": 0.2}, {"x": 0.4, "y": 0.6}],
    [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.4}, {"x": 0.4, "y": 0.4}],
    [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.4}, {"x": 0.7, "y": 0.7}],
    [{"x": -0.1, "y": 0.1}, {"x": 0.4, "y": 0.4}, {"x": 0.7, "y": 0.1}],
    [{"x": 0.1, "y": 0.1}, {"x": 0.7, "y": 0.7}, {"x": 0.1, "y": 0.7}, {"x": 0.7, "y": 0.1}],
    [{"x": 0.1, "y": 0.1}, {"x": 0.8, "y": 0.1}, {"x": 0.8, "y": 0.8}, {"x": 0.5, "y": 0.1}, {"x": 0.1, "y": 0.8}],
    [{"x": 0.1, "y": 0.1, "z": 1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.4}],
    [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": "Infinity"}],
    [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.1}, {"x": 0.4, "y": 0.4}] + [{"x": 0.2, "y": 0.2}] * 48,
])
def test_polygon_invalid_422_and_version_unchanged(context, polygon):
    c, admin, _, factory = context
    cam = setup_camera(c, admin)
    result = create_spot(c, admin, cam, polygon=polygon)
    assert result.status_code == 422, result.text
    with factory() as db:
        assert db.get(Camera, uuid.UUID(cam["id"])).config_version == 1
        assert db.scalar(select(func.count()).select_from(ParkingSpot)) == 0


def test_missing_and_wrong_versions(context):
    c, admin, _, factory = context
    camera = setup_camera(c, admin)
    assert create_spot(c, admin, camera, version=2).status_code == 409
    assert c.post(f"/api/v1/cameras/{camera['id']}/spots", headers=admin,
                  json={"spot_code": "P01", "polygon": TRIANGLE}).status_code == 422
    missing = c.post(f"/api/v1/cameras/{uuid.uuid4()}/spots", headers=admin,
                     json={"spot_code": "P01", "polygon": TRIANGLE, "expected_camera_config_version": 1})
    assert missing.status_code == 404
    spot = create_spot(c, admin, camera).json()
    assert c.patch(f"/api/v1/spots/{uuid.uuid4()}", headers=admin,
                   json={"spot_code": "P02", "expected_camera_config_version": 2}).status_code == 404
    assert c.delete(f"/api/v1/spots/{spot['id']}", headers=admin).status_code == 422
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ParkingSpot)) == 1


def test_spot_code_rename_conflict(context):
    c, admin, _, factory = context
    cam = setup_camera(c, admin)
    p1 = create_spot(c, admin, cam, "P01", version=1).json()
    create_spot(c, admin, cam, "P02", version=2)
    result = c.patch(f"/api/v1/spots/{p1['id']}", headers=admin, json={
        "spot_code": "P02", "expected_camera_config_version": 3,
    })
    assert result.status_code == 409
    with factory() as db:
        assert db.get(Camera, uuid.UUID(cam["id"])).config_version == 3


def test_valid_concave_and_reversed_polygon(context):
    c, admin, _, _ = context
    cam = setup_camera(c, admin)
    concave = [{"x": 0.1, "y": 0.1}, {"x": 0.8, "y": 0.1}, {"x": 0.8, "y": 0.8},
               {"x": 0.5, "y": 0.5}, {"x": 0.1, "y": 0.8}]
    assert create_spot(c, admin, cam, "P01", concave, 1).status_code == 201
    assert create_spot(c, admin, cam, "P02", concave[::-1], 2).status_code == 201


def test_max_active_spots(context):
    c, admin, _, factory = context
    cam = setup_camera(c, admin)
    # Insert 100 valid spots directly for speed; API should not add a 101st.
    with factory() as db:
        db.add_all([ParkingSpot(camera_id=uuid.UUID(cam["id"]), spot_code=f"P{i:03d}", polygon=TRIANGLE)
                    for i in range(100)])
        db.commit()
    result = create_spot(c, admin, cam, "P200")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "CAMERA_SPOT_LIMIT"


def test_delete_cors_preflight(context):
    c, _, _, _ = context
    res = c.options("/api/v1/spots/" + str(uuid.uuid4()), headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "DELETE",
        "Access-Control-Request-Headers": "authorization",
    })
    assert res.status_code == 200
