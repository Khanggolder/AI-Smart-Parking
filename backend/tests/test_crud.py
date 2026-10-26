"""W2 3.2 CRUD regression suite; DB state isolated per test (SQLite)."""

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
from app.models import AuditLog, User

PASSWORD = "Safe-local-test-pass-123"


@pytest.fixture()
def context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "only-tests-fixed-secret-with-more-than-32-bytes")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            User(username="admincrud", password_hash=hash_password(PASSWORD), role="admin"),
            User(username="operatorcrud", password_hash=hash_password(PASSWORD), role="operator"),
        ])
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        def bearer(username):
            res = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
            assert res.status_code == 200, res.text
            return {"Authorization": "Bearer " + res.json()["access_token"]}
        yield client, bearer("admincrud"), bearer("operatorcrud"), factory
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()
    get_settings.cache_clear()


def lot(client, admin, name="Lot A"):
    res = client.post("/api/v1/parking-lots", json={"name": name, "description": "Demo"}, headers=admin)
    assert res.status_code == 201, res.text
    return res.json()


def camera(client, admin, parking_lot_id, name="CAM-01"):
    res = client.post("/api/v1/cameras", json={"name": name, "parking_lot_id": parking_lot_id}, headers=admin)
    assert res.status_code == 201, res.text
    return res.json()


def test_parking_lots_crud_and_page(context):
    c, adm, op, factory = context
    assert c.get("/api/v1/parking-lots").status_code == 401
    empty = c.get("/api/v1/parking-lots", headers=op).json()
    assert empty == {"items": [], "total": 0, "limit": 20, "offset": 0}
    first = lot(c, adm, "  First  ")
    assert first["name"] == "First"
    assert first["description"] == "Demo"
    assert "created_at" in first
    second = lot(c, adm, "Second")
    paged = c.get("/api/v1/parking-lots?limit=1&offset=1", headers=op)
    assert paged.status_code == 200
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1
    assert c.get(f"/api/v1/parking-lots/{first['id']}", headers=op).status_code == 200
    updated = c.patch(f"/api/v1/parking-lots/{first['id']}", json={"description": None}, headers=adm)
    assert updated.status_code == 200
    assert updated.json()["description"] is None
    assert c.get(f"/api/v1/parking-lots/{second['id']}", headers=adm).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 3


def test_cameras_crud_filter_version_and_audit(context):
    c, adm, op, factory = context
    l1 = lot(c, adm)
    l2 = lot(c, adm, "Lot B")
    a = camera(c, adm, l1["id"])
    camera(c, adm, l2["id"], "CAM-B")
    assert a["config_version"] == 1
    filtered = c.get(f"/api/v1/cameras?parking_lot_id={l1['id']}", headers=op)
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == a["id"]
    assert c.get(f"/api/v1/cameras/{a['id']}", headers=op).status_code == 200
    updated = c.patch(f"/api/v1/cameras/{a['id']}", headers=adm, json={"name": "CAM-02", "expected_camera_config_version": 1})
    assert updated.status_code == 200, updated.text
    assert updated.json()["config_version"] == 2
    old = c.patch(f"/api/v1/cameras/{a['id']}", headers=adm, json={"name": "CAM-03", "expected_camera_config_version": 1})
    assert old.status_code == 409
    assert old.json()["error"]["code"] == "CAMERA_VERSION_CONFLICT"
    noop = c.patch(f"/api/v1/cameras/{a['id']}", headers=adm, json={"name": "CAM-02"})
    assert noop.status_code == 200 and noop.json()["config_version"] == 2
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 5


@pytest.mark.parametrize("resource,post_payload,patch_payload", [
    ("parking-lots", {"name": "New Lot"}, {"name": "Bad"}),
    ("cameras", {"name": "CAM", "parking_lot_id": str(uuid.uuid4())}, {"name": "Bad"}),
])
def test_operator_cannot_write(context, resource, post_payload, patch_payload):
    c, adm, op, _ = context
    bogus = uuid.uuid4()
    assert c.post(f"/api/v1/{resource}", json=post_payload, headers=op).status_code == 403
    assert c.patch(f"/api/v1/{resource}/{bogus}", json=patch_payload, headers=op).status_code == 403
    assert c.post(f"/api/v1/{resource}", json=post_payload).status_code == 401


def test_missing_resources_and_camera_parent(context):
    c, adm, op, _ = context
    unknown = str(uuid.uuid4())
    assert c.get(f"/api/v1/parking-lots/{unknown}", headers=adm).status_code == 404
    assert c.patch(f"/api/v1/parking-lots/{unknown}", headers=adm, json={"name": "Test"}).status_code == 404
    assert c.get(f"/api/v1/cameras/{unknown}", headers=op).status_code == 404
    res = c.post("/api/v1/cameras", json={"name": "CAM-01", "parking_lot_id": unknown}, headers=adm)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PARKING_LOT_NOT_FOUND"


def test_bad_validation_and_no_mass_assignment(context):
    c, adm, _, _ = context
    for bad in ({"name": "  "}, {"name": "ok", "unknown": "admin"}, {"name": "x" * 161}):
        assert c.post("/api/v1/parking-lots", json=bad, headers=adm).status_code == 422
    l = lot(c, adm)
    assert c.patch(f"/api/v1/parking-lots/{l['id']}", json={}, headers=adm).status_code == 422
    assert c.patch(f"/api/v1/parking-lots/{l['id']}", json={"name": None}, headers=adm).status_code == 422
    assert c.get("/api/v1/parking-lots?limit=101", headers=adm).status_code == 422
    assert c.get("/api/v1/parking-lots?offset=-1", headers=adm).status_code == 422
    assert c.get("/api/v1/cameras?parking_lot_id=bad", headers=adm).status_code == 422
    assert c.post("/api/v1/cameras", json={"name": "A", "parking_lot_id": l["id"], "config_version": 99}, headers=adm).status_code == 422
    cam = camera(c, adm, l["id"])
    assert c.patch(f"/api/v1/cameras/{cam['id']}", json={"parking_lot_id": str(uuid.uuid4())}, headers=adm).status_code == 422
    assert c.patch(f"/api/v1/cameras/{cam['id']}", json={"name": "  "}, headers=adm).status_code == 422


def test_cors_local_react_preflight(context):
    c, _, _, _ = context
    res = c.options("/api/v1/parking-lots", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert res.status_code == 200, res.text
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"
