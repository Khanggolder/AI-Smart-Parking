"""Reusable authentication and role-checking dependencies for CRUD APIs."""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import verify_access_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(
            401, "UNAUTHORIZED", "Bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = verify_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.role not in {"admin", "operator"}:
        raise APIError(
            401, "UNAUTHORIZED", "Account is unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str) -> Callable:
    """Use Depends(require_roles('admin')) for config writes."""
    if not allowed_roles or not set(allowed_roles) <= {"admin", "operator"}:
        raise ValueError("Unknown or empty role list")

    def role_guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise APIError(403, "FORBIDDEN", "Insufficient permissions")
        return current_user

    return role_guard
