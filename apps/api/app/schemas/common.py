from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


QuoteStage = Literal["initial", "review", "quote_prep", "repricing", "sent", "po"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class APIMessage(BaseModel):
    message: str


class SignedUrlResponse(BaseModel):
    signed_url: str
    filename: str
    content_type: str


class GasketItemPayload(BaseModel):
    model_config = {"extra": "allow"}


class StageHistoryEntry(BaseModel):
    stage: QuoteStage
    at: datetime = Field(default_factory=utc_now)
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    user_id: str = ""
