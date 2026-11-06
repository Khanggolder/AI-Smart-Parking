"""W5 6.1.4: genuinely simultaneous review calls on isolated PostgreSQL TEST DB.

Set W5_TEST_POSTGRES_URL to a PostgreSQL URL whose database name includes
"test". A uniquely named schema is created and dropped; no production tables
are modified. Without this variable, the test is explicitly SKIPPED.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    User, ParkingLot, Camera, ParkingSpot,
    Snapshot, SpotPrediction, SpotReview, AuditLog,
)


@pytest.mark.skipif(
    not os.getenv("W5_TEST_POSTGRES_URL"),
    reason="Real PostgreSQL concurrency not run: set W5_TEST_POSTGRES_URL to a dedicated test database",
)
def test_w5_614_true_postgres_two_simultaneous_reviews(monkeypatch):
    url = os.environ["W5_TEST_POSTGRES_URL"]
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or "test" not in (parsed.database or "").lower():
        pytest.fail("W5_TEST_POSTGRES_URL must target a dedicated PostgreSQL TEST database")

    schema = "w5_review_test_" + uuid4().hex[:16]
    master = create_engine(url, pool_pre_ping=True)
    scoped = None
    created = False
    monkeypatch.setenv("JWT_SECRET_KEY", "w5-postgres-concurrent-test-secret-not-for-production")
    get_settings.cache_clear()
    try:
        with master.begin() as conn:
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        created = True
        scoped = create_engine(
            url,
            connect_args={"options": f"-csearch_path={schema},public"},
            pool_size=5, max_overflow=5, pool_pre_ping=True,
        )
        Base.metadata.create_all(scoped)
        factory = sessionmaker(bind=scoped, expire_on_commit=False)
        with factory() as db:
            admin = User(username="w5_concurrent_admin", password_hash=hash_password("Concurrent-Test-123!"), role="admin")
            operator = User(username="w5_concurrent_operator", password_hash=hash_password("Concurrent-Test-123!"), role="operator")
            lot = ParkingLot(name="Isolated W5 concurrency test")
            db.add_all([admin, operator, lot]); db.flush()
            cam = Camera(name="Concurrency Camera", parking_lot_id=lot.id)
            db.add(cam); db.flush()
            polygon = [{"x": .1, "y": .1}, {"x": .3, "y": .1}, {"x": .3, "y": .3}]
            spot = ParkingSpot(camera_id=cam.id, spot_code="P01", polygon=polygon)
            snap = Snapshot(camera_id=cam.id, image_path="test-only.jpg",
                            captured_at=datetime.now(timezone.utc), camera_config_version=1, job_status="completed")
            db.add_all([spot, snap]); db.flush()
            pred = SpotPrediction(snapshot_id=snap.id, parking_spot_id=spot.id,
                                  spot_code_at_capture="P01", polygon_at_capture=polygon,
                                  predicted_label="empty", confidence=.98, model_version="test-model")
            db.add(pred); db.commit()
            prediction_id = pred.id

        def override_db():
            with factory() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        try:
            with TestClient(app) as client:
                def login(username):
                    response = client.post("/api/v1/auth/login", json={
                        "username": username, "password": "Concurrent-Test-123!",
                    })
                    assert response.status_code == 200, response.text
                    return {"Authorization": "Bearer " + response.json()["access_token"]}

                first_headers = login("w5_concurrent_admin")
                second_headers = login("w5_concurrent_operator")
                path = f"/api/v1/predictions/{prediction_id}/reviews"
                barrier = Barrier(2, timeout=15)
                def send(headers, payload):
                    barrier.wait()
                    response = client.post(path, headers=headers, json=payload)
                    return response.status_code, response.json()
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [
                        pool.submit(send, first_headers, {"action": "accept", "expected_revision": 0}),
                        pool.submit(send, second_headers, {
                            "action": "correct", "expected_revision": 0,
                            "verified_label": "occupied", "reason": "Concurrent correction",
                        }),
                    ]
                    results = [f.result(timeout=40) for f in futures]
                assert sorted(status for status, _ in results) == [201, 409], results
                rejected = [body for status, body in results if status == 409]
                assert rejected[0]["error"]["code"] == "REVIEW_VERSION_CONFLICT"
                with factory() as db:
                    rows = db.scalars(select(SpotReview).where(
                        SpotReview.spot_prediction_id == prediction_id
                    )).all()
                    assert len(rows) == 1 and rows[0].revision == 1
                    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1
                    assert db.get(SpotPrediction, prediction_id).predicted_label == "empty"
        finally:
            app.dependency_overrides.pop(get_db, None)
    finally:
        if scoped is not None:
            scoped.dispose()
        if created:
            with master.begin() as conn:
                conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        master.dispose()
        get_settings.cache_clear()
