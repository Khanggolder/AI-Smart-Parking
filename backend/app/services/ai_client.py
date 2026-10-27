"""Strict adapter to Khang's v0.1.0-rc2 POST /v1/infer contract.

Only validated predictions are returned; malformed/unavailable AI never creates
synthetic UNKNOWN states. This module does not load Torch or model weights.
"""
import json
from math import isclose
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.core.config import get_settings


class AIJobError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class AIPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spot_id: str
    raw_label: Literal["empty", "occupied"]
    label: Literal["empty", "occupied", "unknown"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    scores: dict[str, float]

    @model_validator(mode="after")
    def consistent_scores(self):
        if set(self.scores) != {"empty", "occupied"}:
            raise ValueError("Scores must include both classes")
        from math import isfinite
        if any(not isfinite(v) or not 0 <= v <= 1 for v in self.scores.values()):
            raise ValueError("Invalid score")
        if not isclose(sum(self.scores.values()), 1.0, abs_tol=0.002):
            raise ValueError("Scores must sum to 1")
        if not isclose(self.confidence, max(self.scores.values()), abs_tol=0.002):
            raise ValueError("Confidence differs from softmax max")
        if self.scores[self.raw_label] + 0.002 < self.scores["occupied" if self.raw_label == "empty" else "empty"]:
            raise ValueError("Raw label does not match scores")
        return self


class AIResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    camera_id: str
    model_version: str = Field(min_length=1, max_length=100)
    threshold: float = Field(ge=0, le=1, allow_inf_nan=False)
    predictions: list[AIPrediction]
    processing_time_ms: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def consistent_labels(self):
        for p in self.predictions:
            expected = p.raw_label if p.confidence >= self.threshold else "unknown"
            if p.label != expected:
                raise ValueError("Final label is inconsistent with threshold")
        return self


def create_http_client(timeout: float) -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(timeout, connect=min(timeout, 5.0)))


def infer(camera_id: str, spots: list[dict], image: bytes, mime: str) -> AIResponse:
    settings = get_settings()
    if settings.ai_timeout_seconds <= 0 or settings.ai_timeout_seconds > 300:
        raise AIJobError("AI_TIMEOUT_CONFIG_INVALID")
    payload = [{"spot_id": str(spot["id"]),
                "polygon": [[p["x"], p["y"]] for p in spot["polygon"]]}
               for spot in spots]
    if not 1 <= len(payload) <= 100:
        raise AIJobError("INVALID_SNAPSHOT_SPOTS")
    spots_json = json.dumps(payload, separators=(",", ":"))
    if len(spots_json.encode("utf-8")) > 262144:
        raise AIJobError("INVALID_SNAPSHOT_SPOTS")
    try:
        with create_http_client(settings.ai_timeout_seconds) as client:
            response = client.post(
                settings.ai_service_url.rstrip("/") + "/v1/infer",
                data={"camera_id": camera_id, "spots_json": spots_json},
                files={"image": ("snapshot.jpg" if mime == "image/jpeg" else "snapshot.png", image, mime)},
            )
    except httpx.TimeoutException as exc:
        raise AIJobError("AI_TIMEOUT") from exc
    except httpx.RequestError as exc:
        raise AIJobError("AI_UNAVAILABLE") from exc
    if response.status_code != 200:
        if response.status_code == 503:
            raise AIJobError("AI_UNAVAILABLE")
        if response.status_code in (413, 415, 422):
            raise AIJobError("AI_REJECTED_INPUT")
        raise AIJobError("AI_HTTP_ERROR")
    try:
        output = AIResponse.model_validate(response.json())
    except (ValueError, ValidationError) as exc:
        raise AIJobError("AI_INVALID_RESPONSE") from exc
    expected_ids = [item["spot_id"] for item in payload]
    if output.camera_id != camera_id or [p.spot_id for p in output.predictions] != expected_ids:
        raise AIJobError("AI_RESPONSE_MISMATCH")
    return output
