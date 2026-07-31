from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

LearnedStatus = Literal["pending", "approved", "rejected"]
LearnedSource = Literal["edit", "manual", "import"]


class LearnedDescriptionRead(BaseModel):
    """One learned description as returned to the portal."""

    id: str
    org_id: str
    fingerprint: str
    source_text: str
    ggpl_description: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    #: Empty string means the entry applies to every customer.
    customer: str = ""
    status: LearnedStatus = "pending"
    source: LearnedSource = "edit"
    note: str = ""
    created_by: str = ""
    approved_by: str = ""
    hit_count: int = 0
    last_applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LearnedDescriptionCreate(BaseModel):
    """Teach the portal a description.

    `source_text` is the customer wording to match on; when omitted the caller
    must supply `quote_id` + `item_index` so the server can read the wording and
    the classified fields straight off the row being corrected.
    """

    source_text: str = ""
    ggpl_description: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    customer: str = ""
    note: str = ""
    quote_id: str | None = None
    item_index: int | None = None
    #: Save straight into permanent memory instead of the pending queue.
    approve: bool = True


class LearnedDescriptionPatch(BaseModel):
    ggpl_description: str | None = None
    fields: dict[str, Any] | None = None
    customer: str | None = None
    note: str | None = None
    status: LearnedStatus | None = None


class LearnedDescriptionLookup(BaseModel):
    source_text: str
    customer: str = ""


class LearnedDescriptionMatch(BaseModel):
    """Result of a lookup: what memory holds for a wording, if anything."""

    matched: bool = False
    #: "exact" matches are applied automatically; "similar" are suggestions.
    kind: str = ""
    entry: LearnedDescriptionRead | None = None


class LearningSettings(BaseModel):
    """Org-level switches for the learning layer."""

    #: Capture a pending entry whenever the team edits a GGPL description.
    auto_capture: bool = True
    #: Apply pending (not yet approved) entries, not just approved ones.
    apply_pending: bool = True
    #: Offer near-wording matches as review suggestions.
    suggest_similar: bool = True


class LearningSettingsPatch(BaseModel):
    auto_capture: bool | None = None
    apply_pending: bool | None = None
    suggest_similar: bool | None = None

    def as_settings(self, current: LearningSettings) -> LearningSettings:
        data: dict[str, Any] = current.model_dump()
        for name in ("auto_capture", "apply_pending", "suggest_similar"):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        return LearningSettings(**data)