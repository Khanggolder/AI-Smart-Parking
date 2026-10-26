"""W3 JSON API schemas for parking spot polygons."""
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

SpotCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class Point(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)


class SpotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spot_code: SpotCode
    polygon: list[Point] = Field(min_length=3, max_length=50)
    expected_camera_config_version: int = Field(ge=1)

    @field_validator("spot_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()

    @field_validator("polygon")
    @classmethod
    def valid_geometry(cls, value: list[Point]) -> list[Point]:
        from app.services.polygon_geometry import validate_polygon
        validate_polygon(value)
        return value


class SpotPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_camera_config_version: int = Field(ge=1)
    spot_code: SpotCode | None = None
    polygon: list[Point] | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("spot_code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("polygon")
    @classmethod
    def valid_geometry(cls, value: list[Point] | None) -> list[Point] | None:
        if value is not None:
            from app.services.polygon_geometry import validate_polygon
            validate_polygon(value)
        return value

    @model_validator(mode="after")
    def require_change(self):
        if self.spot_code is None and self.polygon is None:
            raise ValueError("Supply spot_code and/or polygon")
        return self


class SpotOut(BaseModel):
    id: UUID
    camera_id: UUID
    spot_code: str
    polygon: list[Point]
    is_active: bool
    camera_config_version: int


class SpotList(BaseModel):
    items: list[SpotOut]
    total: int
    camera_config_version: int
