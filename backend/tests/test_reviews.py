
"""W5 – Prediction Review API tests."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    User, ParkingLot, Camera, ParkingSpot,
    Snapshot, SpotPrediction, SpotReview, AuditLog,
)

PASSWORD = "Test-Password-123456!"
POLYGON = [
    {"x": 0.1, "y": 0.1},
    {"x": 0.3, "y": 0.1},
    {"x": 0.3, "y": 0.35},
    {"x": 0.1, "y": 0.35},
]


@pytest.fixture()
def context(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "w5-review-test-secret-not-for-production"
    )
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db:
        admin = User(
            username="w5_admin",
            password_hash=hash_password(PASSWORD),
            role="admin",
        )
        operator = User(
            username="w5_operator",
            password_hash=hash_password(PASSWORD),
            role="operator",
        )
        db.add_all([admin, operator])

        lot = ParkingLot(name="W5 Test Lot")
        db.add(lot)
        db.flush()

        camera = Camera(
            parking_lot_id=lot.id,
            name="W5 Test Camera",
        )
        db.add(camera)
        db.flush()

        spot = ParkingSpot(
            camera_id=camera.id,
            spot_code="P01",
            polygon=POLYGON,
        )
        db.add(spot)
        db.flush()

        snapshot = Snapshot(
            camera_id=camera.id,
            image_path="test.jpg",
            captured_at=datetime.now(timezone.utc),
            camera_config_version=1,
            job_status="completed",
        )
        db.add(snapshot)
        db.flush()

        prediction = SpotPrediction(
            snapshot_id=snapshot.id,
            parking_spot_id=spot.id,
            spot_code_at_capture="P01",
            polygon_at_capture=POLYGON,
            predicted_label="empty",
            confidence=0.95,
            model_version="test-model",
        )
        db.add(prediction)
        db.commit()
        prediction_id = prediction.id

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(app) as client:
            def auth(username):
                response = client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": username,
                        "password": PASSWORD,
                    },
                )
                assert response.status_code == 200
                return {
                    "Authorization":
                    "Bearer " + response.json()["access_token"]
                }

            yield (
                client,
                auth("w5_admin"),
                auth("w5_operator"),
                prediction_id,
                factory,
            )
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        get_settings.cache_clear()


def test_accept_and_correct(context):
    client, admin, _, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"

    accepted = client.post(
        url,
        headers=admin,
        json={
            "action": "accept",
            "expected_revision": 0,
        },
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["verified_label"] == "empty"
    assert accepted.json()["revision"] == 1

    corrected = client.post(
        url,
        headers=admin,
        json={
            "action": "correct",
            "expected_revision": 1,
            "verified_label": "occupied",
            "reason": "Test correction",
        },
    )
    assert corrected.status_code == 201, corrected.text
    assert corrected.json()["revision"] == 2
    assert corrected.json()["verified_label"] == "occupied"

    with factory() as db:
        rows = db.scalars(
            select(SpotReview)
            .where(SpotReview.spot_prediction_id == prediction_id)
            .order_by(SpotReview.revision)
        ).all()

        assert len(rows) == 2
        assert [r.revision for r in rows] == [1, 2]
        assert db.get(
            SpotPrediction, prediction_id
        ).predicted_label == "empty"
        assert db.scalar(
            select(func.count()).select_from(AuditLog)
        ) == 2


def test_revision_conflict(context):
    client, admin, _, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"

    first = client.post(
        url,
        headers=admin,
        json={"action": "accept", "expected_revision": 0},
    )
    assert first.status_code == 201

    conflict = client.post(
        url,
        headers=admin,
        json={"action": "accept", "expected_revision": 0},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == (
        "REVIEW_VERSION_CONFLICT"
    )

    with factory() as db:
        count = db.scalar(
            select(func.count())
            .select_from(SpotReview)
        )
        assert count == 1


def test_validation_and_auth(context):
    client, admin, operator, prediction_id, _ = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"

    assert client.post(
        url,
        json={"action": "accept", "expected_revision": 0},
    ).status_code == 401

    invalid_accept = client.post(
        url,
        headers=admin,
        json={
            "action": "accept",
            "expected_revision": 0,
            "verified_label": "empty",
        },
    )
    assert invalid_accept.status_code == 422

    invalid_correct = client.post(
        url,
        headers=admin,
        json={
            "action": "correct",
            "expected_revision": 0,
            "verified_label": "occupied",
        },
    )
    assert invalid_correct.status_code == 422

    missing = client.post(
        f"/api/v1/predictions/{uuid4()}/reviews",
        headers=admin,
        json={"action": "accept", "expected_revision": 0},
    )
    assert missing.status_code == 404

    allowed = client.post(
        url,
        headers=operator,
        json={"action": "accept", "expected_revision": 0},
    )
    assert allowed.status_code == 201

# W5 6.1.3: Review history and derived effective labels.
def test_w5_review_history_and_effective_label(context):
    client, admin, operator, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"

    empty = client.get(url, headers=operator)
    assert empty.status_code == 200, empty.text
    assert empty.json() == []

    accepted = client.post(
        url, headers=admin,
        json={"action": "accept", "expected_revision": 0},
    )
    assert accepted.status_code == 201, accepted.text

    corrected = client.post(
        url, headers=operator,
        json={
            "action": "correct", "expected_revision": 1,
            "verified_label": "occupied", "reason": "W5 correction test",
        },
    )
    assert corrected.status_code == 201, corrected.text

    history = client.get(url, headers=operator)
    assert history.status_code == 200, history.text
    items = history.json()
    assert len(items) == 2
    assert [r["revision"] for r in items] == [1, 2]
    assert [r["action"] for r in items] == ["accept", "correct"]
    assert [r["verified_label"] for r in items] == ["empty", "occupied"]
    assert all(r["reviewer_id"] and r["changed_at"] for r in items)

    with factory() as db:
        snapshot_id = db.get(SpotPrediction, prediction_id).snapshot_id

    response = client.get(f"/api/v1/snapshots/{snapshot_id}", headers=operator)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job_status"] == "completed"
    assert len(body["predictions"]) == 1
    assert body["predictions"][0]["predicted_label"] == "empty"
    assert body["predictions"][0]["effective_label"] == "occupied"
    assert body["summary"]["occupied"] == 1
    assert body["summary"]["empty"] == 0
    assert body["summary"]["occupancy_rate"] == 100.0
    assert body["summary"]["status"] == "FULL"


def test_w5_history_auth_not_found_and_accept_restores_ai_label(context):
    client, admin, operator, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"
    assert client.get(url).status_code == 401
    missing = client.get(f"/api/v1/predictions/{__import__('uuid').uuid4()}/reviews", headers=operator)
    assert missing.status_code == 404

    first = client.post(
        url, headers=admin,
        json={
            "action": "correct", "expected_revision": 0,
            "verified_label": "occupied", "reason": "Test initial correction",
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        url, headers=admin,
        json={"action": "accept", "expected_revision": 1},
    )
    assert second.status_code == 201, second.text
    assert second.json()["verified_label"] == "empty"
    assert second.json()["revision"] == 2

    with factory() as db:
        snapshot_id = db.get(SpotPrediction, prediction_id).snapshot_id
    body = client.get(f"/api/v1/snapshots/{snapshot_id}", headers=operator).json()
    assert body["predictions"][0]["predicted_label"] == "empty"
    assert body["predictions"][0]["effective_label"] == "empty"
    assert body["summary"]["status"] == "AVAILABLE"
    assert [x["action"] for x in client.get(url, headers=admin).json()] == ["correct", "accept"]

# W5 6.1.4: RBAC, invalid labels and optimistic concurrency tests.

def test_w5_614_operator_admin_access_and_audit(context):
    client, admin, operator, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"
    assert client.get(url).status_code == 401
    assert client.post(url, json={"action": "accept", "expected_revision": 0}).status_code == 401

    first = client.post(url, headers=operator, json={"action": "accept", "expected_revision": 0})
    assert first.status_code == 201, first.text
    second = client.post(url, headers=admin, json={
        "action": "correct", "expected_revision": 1,
        "verified_label": "occupied", "reason": "Checked by administrator",
    })
    assert second.status_code == 201, second.text

    with factory() as db:
        operator_id = db.scalar(select(User.id).where(User.username == "w5_operator"))
        admin_id = db.scalar(select(User.id).where(User.username == "w5_admin"))
        rows = db.scalars(select(SpotReview).where(
            SpotReview.spot_prediction_id == prediction_id
        ).order_by(SpotReview.revision)).all()
        assert [r.reviewer_id for r in rows] == [operator_id, admin_id]
        actions = db.scalars(select(AuditLog.action).order_by(AuditLog.created_at)).all()
        assert "prediction.review.accept" in actions
        assert "prediction.review.correct" in actions


def test_w5_614_deactivated_operator_cannot_review(context):
    client, admin, operator, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"
    with factory() as db:
        user = db.scalar(select(User).where(User.username == "w5_operator"))
        user.is_active = False
        db.commit()
    assert client.get(url, headers=operator).status_code == 401
    assert client.post(url, headers=operator, json={
        "action": "accept", "expected_revision": 0,
    }).status_code == 401
    assert client.get(url, headers=admin).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(SpotReview)) == 0


@pytest.mark.parametrize("payload", [
    {"action": "accept", "expected_revision": 0, "verified_label": "empty"},
    {"action": "correct", "expected_revision": 0, "verified_label": "occupied"},
    {"action": "correct", "expected_revision": 0, "verified_label": "occupied", "reason": "   "},
    {"action": "correct", "expected_revision": 0, "verified_label": "car", "reason": "invalid label"},
    {"action": "reject", "expected_revision": 0},
    {"action": "accept", "expected_revision": -1},
    {"action": "accept"},
    {"action": "accept", "expected_revision": 0, "unexpected": "extra"},
])
def test_w5_614_invalid_requests_do_not_write(context, payload):
    client, admin, _, prediction_id, factory = context
    result = client.post(f"/api/v1/predictions/{prediction_id}/reviews", headers=admin, json=payload)
    assert result.status_code == 422, result.text
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(SpotReview)) == 0
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_w5_614_correct_same_as_original_ai_label_rejected(context):
    client, admin, _, prediction_id, factory = context
    result = client.post(f"/api/v1/predictions/{prediction_id}/reviews", headers=admin, json={
        "action": "correct", "expected_revision": 0,
        "verified_label": "empty", "reason": "Should use accept",
    })
    assert result.status_code == 422, result.text
    assert result.json()["error"]["code"] == "UNCHANGED_LABEL"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(SpotReview)) == 0


def test_w5_614_two_reviewers_stale_revision_and_retry(context):
    # Simulates two reviewers who opened the same prediction at revision 0.
    # This is a stale-write regression test, not a simultaneous PostgreSQL race.
    client, admin, operator, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"
    first = client.post(url, headers=admin, json={"action": "accept", "expected_revision": 0})
    assert first.status_code == 201, first.text
    stale = client.post(url, headers=operator, json={
        "action": "correct", "expected_revision": 0,
        "verified_label": "occupied", "reason": "Stale reviewer",
    })
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "REVIEW_VERSION_CONFLICT"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(SpotReview)) == 1
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1

    retried = client.post(url, headers=operator, json={
        "action": "correct", "expected_revision": 1,
        "verified_label": "occupied", "reason": "After refreshing revision",
    })
    assert retried.status_code == 201, retried.text
    assert retried.json()["revision"] == 2
    with factory() as db:
        assert db.get(SpotPrediction, prediction_id).predicted_label == "empty"
        revisions = db.scalars(select(SpotReview.revision).where(
            SpotReview.spot_prediction_id == prediction_id
        ).order_by(SpotReview.revision)).all()
        assert revisions == [1, 2]


def test_w5_614_processing_snapshot_cannot_be_reviewed(context):
    client, admin, _, prediction_id, factory = context
    with factory() as db:
        pred = db.get(SpotPrediction, prediction_id)
        snap = db.get(Snapshot, pred.snapshot_id)
        snap.job_status = "processing"
        db.commit()
    result = client.post(f"/api/v1/predictions/{prediction_id}/reviews", headers=admin, json={
        "action": "accept", "expected_revision": 0,
    })
    assert result.status_code == 409, result.text
    assert result.json()["error"]["code"] == "SNAPSHOT_NOT_COMPLETED"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(SpotReview)) == 0


def test_w5_614_unknown_correction_effective_label(context):
    client, admin, _, prediction_id, factory = context
    url = f"/api/v1/predictions/{prediction_id}/reviews"
    corrected = client.post(url, headers=admin, json={
        "action": "correct", "expected_revision": 0,
        "verified_label": "unknown", "reason": "Unable to verify occupancy",
    })
    assert corrected.status_code == 201, corrected.text
    with factory() as db:
        snapshot_id = db.get(SpotPrediction, prediction_id).snapshot_id
    snapshot_response = client.get(f"/api/v1/snapshots/{snapshot_id}", headers=admin)
    assert snapshot_response.status_code == 200, snapshot_response.text
    body = snapshot_response.json()
    assert body["predictions"][0]["predicted_label"] == "empty"
    assert body["predictions"][0]["effective_label"] == "unknown"
    assert body["summary"]["unknown"] == 1
    assert body["summary"]["status"] == "UNDETERMINED"
    assert body["summary"]["full"] is False

