"""W4 snapshot job and prediction responses."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

Status = Literal["queued", "processing", "completed", "failed"]


class SnapshotAccepted(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    camera_id: UUID
    captured_at: datetime
    camera_config_version: int
    job_status: Status


class PredictionOut(BaseModel):
    id: UUID
    parking_spot_id: UUID
    spot_code: str
    polygon: list[dict[str, float]]
    predicted_label: str
    effective_label: str
    raw_label: str | None
    confidence: float
    scores: dict[str, float] | None
    model_version: str
    threshold: float | None


class SummaryOut(BaseModel):
    total: int
    empty: int
    occupied: int
    unknown: int
    occupancy_rate: float | None
    full: bool
    status: Literal["NO_SPOTS", "AVAILABLE", "UNDETERMINED", "FULL"]


class SnapshotOut(SnapshotAccepted):
    created_at: datetime
    error_code: str | None
    ai_model_version: str | None
    ai_threshold: float | None
    ai_processing_time_ms: float | None
    summary: SummaryOut | None
    predictions: list[PredictionOut]
    is_stale: bool | None


class SnapshotPage(BaseModel):
    items: list[SnapshotAccepted]
    total: int
    limit: int
    offset: int
