"""Argon2id password hashes and HS256 short-lived bearer tokens."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.errors import APIError

PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
# Avoid a large difference in computation time for unknown usernames.
DUMMY_HASH = PASSWORD_HASHER.hash("invalid-account-placeholder-only")


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(encoded_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def get_signing_secret() -> str:
    secret = get_settings().jwt_secret_key
    if not secret or len(secret.encode("utf-8")) < 32:
        raise APIError(503, "AUTH_NOT_CONFIGURED", "JWT secret is not configured")
    return secret


def create_access_token(user_id: UUID) -> tuple[str, int]:
    settings = get_settings()
    if not 1 <= settings.jwt_expire_minutes <= 1440:
        raise APIError(503, "AUTH_NOT_CONFIGURED", "Invalid JWT token lifetime")
    now = datetime.now(timezone.utc)
    ttl_seconds = settings.jwt_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
        "typ": "access",
    }
    return jwt.encode(payload, get_signing_secret(), algorithm="HS256"), ttl_seconds


def verify_access_token(token: str) -> UUID:
    try:
        data = jwt.decode(
            token,
            get_signing_secret(),
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp", "typ"]},
        )
        if data.get("typ") != "access":
            raise ValueError("Wrong token type")
        return UUID(data["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise APIError(
            401,
            "INVALID_TOKEN",
            "Missing, invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
