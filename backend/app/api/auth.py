"""Public JSON login and protected current-user lookup (FR-01)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import APIError
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None:
        verify_password(payload.password, DUMMY_HASH)
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise APIError(
            401, "INVALID_CREDENTIALS", "Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role not in {"admin", "operator"}:
        raise APIError(401, "INVALID_CREDENTIALS", "Invalid username or password")
    token, ttl = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=ttl)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
