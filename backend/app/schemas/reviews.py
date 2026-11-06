
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Label = Literal["empty", "occupied", "unknown"]


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["accept", "correct"]
    expected_revision: int = Field(ge=0)
    verified_label: Label | None = None
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_action(self):
        if self.reason is not None:
            self.reason = self.reason.strip() or None

        if self.action == "accept":
            if self.verified_label is not None:
                raise ValueError(
                    "Accept must not provide verified_label"
                )
        else:
            if self.verified_label is None:
                raise ValueError(
                    "Correct requires verified_label"
                )
            if not self.reason:
                raise ValueError(
                    "Correct requires a reason"
                )
        return self


class ReviewOut(BaseModel):
    id: UUID
    prediction_id: UUID
    reviewer_id: UUID
    action: Literal["accept", "correct"]
    verified_label: Label
    revision: int
    reason: str | None
    changed_at: datetime
