"""JSON request/response schemas for /api/v1/auth endpoints."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    role: Literal["admin", "operator"]
    is_active: bool
