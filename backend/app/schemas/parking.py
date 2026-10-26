"""W2 (3.2): request and response contracts for parking lots and cameras."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class ParkingLotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: str | None = Field(default=None, max_length=1000)


class ParkingLotPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def ensure_valid_patch(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class ParkingLotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    created_at: datetime


class ParkingLotPage(BaseModel):
    items: list[ParkingLotOut]
    total: int
    limit: int
    offset: int


class CameraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parking_lot_id: UUID
    name: Name


class CameraPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    expected_camera_config_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def ensure_valid_patch(self):
        if "name" not in self.model_fields_set or self.name is None:
            raise ValueError("Provide a non-null name to update a camera")
        return self


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    parking_lot_id: UUID
    name: str
    reference_image_path: str | None
    reference_width: int | None
    reference_height: int | None
    config_version: int


class CameraPage(BaseModel):
    items: list[CameraOut]
    total: int
    limit: int
    offset: int
