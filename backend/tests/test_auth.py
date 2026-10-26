"""FR-01: Authentication and RBAC; test DB is disposable SQLite."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import router as auth_router
from app.api.deps import require_roles
from app.core.config import get_settings
from app.core.errors import APIError, api_error_handler
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.db.session import get_db
from app.models import User

SECRET = "unit-test-signing-secret-should-never-be-used-outside-tests"
PASSWORD = "A-realistic-test-password-123"


@pytest.fixture()
def context(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            User(username="admin01", password_hash=hash_password(PASSWORD), role="admin"),
            User(username="operator01", password_hash=hash_password(PASSWORD), role="operator"),
            User(username="disabled01", password_hash=hash_password(PASSWORD), role="operator", is_active=False),
        ])
        db.commit()

    app = FastAPI()
    app.add_exception_handler(APIError, api_error_handler)
    app.include_router(auth_router, prefix="/api/v1")

    @app.get("/api/v1/admin-only")
    def admin_route(_user: User = Depends(require_roles("admin"))):
        return {"ok": True}

    @app.get("/api/v1/all-users")
    def all_users_route(_user: User = Depends(require_roles("admin", "operator"))):
        return {"ok": True}

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, factory
    engine.dispose()
    get_settings.cache_clear()


def login(client, username="admin01", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_password_hash_is_argon2id_and_verifies():
    encoded = hash_password(PASSWORD)
    assert encoded.startswith("$argon2id$")
    assert PASSWORD not in encoded
    assert verify_password(PASSWORD, encoded)
    assert not verify_password("wrong", encoded)


def test_login_token_and_me(context):
    client, _ = context
    response = login(client)
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 3600
    user_response = client.get("/api/v1/auth/me", headers=auth(payload["access_token"]))
    assert user_response.status_code == 200
    assert user_response.json()["role"] == "admin"
    assert user_response.json()["username"] == "admin01"
    assert "password_hash" not in user_response.json()


@pytest.mark.parametrize("username,password", [
    ("missing01", PASSWORD),
    ("admin01", "not-the-password"),
    ("disabled01", PASSWORD),
])
def test_invalid_credentials(context, username, password):
    client, _ = context
    resp = login(client, username, password)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "password" not in str(resp.json()).lower() or resp.json()["error"]["message"] == "Invalid username or password"


def test_missing_and_bad_token(context):
    client, _ = context
    for headers in ({}, auth("not.a.jwt"), {"Authorization": "Basic token"}):
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Bearer"


def test_expired_token_is_denied(context):
    client, factory = context
    with factory() as db:
        user_id = str(db.scalar(select(User.id).where(User.username == "admin01")))
    expired = jwt.encode({
        "sub": user_id,
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "typ": "access",
    }, SECRET, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers=auth(expired)).status_code == 401


def test_admin_and_operator_permissions(context):
    client, _ = context
    admin_token = login(client).json()["access_token"]
    operator_token = login(client, username="operator01").json()["access_token"]
    assert client.get("/api/v1/admin-only", headers=auth(admin_token)).status_code == 200
    forbidden = client.get("/api/v1/admin-only", headers=auth(operator_token))
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"
    assert client.get("/api/v1/all-users", headers=auth(operator_token)).status_code == 200
    assert client.get("/api/v1/all-users", headers=auth(admin_token)).status_code == 200


def test_disabled_after_issue_denied(context):
    client, factory = context
    token = login(client, username="operator01").json()["access_token"]
    with factory() as db:
        user = db.scalar(select(User).where(User.username == "operator01"))
        user.is_active = False
        db.commit()
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_role_checked_from_db_not_jwt(context):
    client, factory = context
    token = login(client, username="operator01").json()["access_token"]
    with factory() as db:
        user = db.scalar(select(User).where(User.username == "operator01"))
        user.role = "admin"
        db.commit()
    assert client.get("/api/v1/admin-only", headers=auth(token)).status_code == 200
