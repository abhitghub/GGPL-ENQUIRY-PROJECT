from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import QuoteStage, StageHistoryEntry


class QuoteBase(BaseModel):
    quote_no: str = ""
    customer: str = ""
    project_ref: str = ""
    custom_label: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
    quote_data: dict[str, Any] = Field(default_factory=dict)
    stage: QuoteStage = "initial"
    stage_meta: dict[str, Any] = Field(default_factory=dict)


class QuoteCreate(QuoteBase):
    pass


class QuotePatch(BaseModel):
    expected_version: int | None = None
    quote_no: str | None = None
    customer: str | None = None
    project_ref: str | None = None
    custom_label: str | None = None
    items: list[dict[str, Any]] | None = None
    quote_data: dict[str, Any] | None = None
    stage: QuoteStage | None = None
    stage_meta: dict[str, Any] | None = None


class QuoteRead(QuoteBase):
    id: str
    org_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    version: int
    n_items: int = 0
    n_ready: int = 0
    n_check: int = 0
    n_missing: int = 0
    n_regret: int = 0
    stage_history: list[StageHistoryEntry] = Field(default_factory=list)
    estimated_quote_value: float = 0.0
    high_risk_count: int = 0
    has_clarification: bool = False
    next_action: str = ""
    opportunity_id: str = ""


class BulkItemPatch(BaseModel):
    index: int
    values: dict[str, Any]


class BulkItemsRequest(BaseModel):
    expected_version: int | None = None
    patches: list[BulkItemPatch] = Field(default_factory=list)
    delete_indices: list[int] = Field(default_factory=list)


class BulkRecomputeRequest(BaseModel):
    expected_version: int | None = None
    indices: list[int] | None = None
    rows: list[dict[str, Any]] | None = None


class ReprocessTextRequest(BaseModel):
    descriptions: list[str]
    source_type: str = "email"
    api_key: str | None = None


class RfiDraftResponse(BaseModel):
    text: str
    groups: dict[str, list[int]]


class StageAdvanceRequest(BaseModel):
    stage: QuoteStage
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    expected_version: int | None = None


class WorkflowActionRequest(BaseModel):
    action: str
    comment: str = ""
    expected_version: int | None = None
    # Optional gasket-type flag that drives the granular stage-5 branch (specific
    # types route to technical review). When omitted, any value already on
    # stage_meta is reused. Ignored unless ENABLE_GRANULAR_WORKFLOW is on.
    gasket_type: str | None = None


class ChangeQueryCreateRequest(BaseModel):
    # Workflow step id the enquiry should be sent to once the query is approved
    # (e.g. "spec_check" to send it back to estimation for a quantity change).
    target_stage: str
    note: str


class ChangeQueryActionRequest(BaseModel):
    # "approve" | "reject" (admin decision) or "resolve" (change made, send the
    # enquiry back to where it was when the query was approved).
    action: str
    note: str = ""
