"""Curation API for the portal's learned descriptions.

Who may do what:

* Anyone who can edit line items contributes — their saves are captured
  automatically, and `POST /learned-descriptions` accepts an explicit teach that
  lands in the pending queue.
* `manage_description_memory` (admin, management, approver, estimation by
  default) approves an entry into permanent memory, edits it, retires it, and
  changes the org's learning switches.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.description_memory import STATUS_APPROVED, STATUS_REJECTED

from app.db import repo
from app.deps import CurrentUser, can_role, get_current_user, require_capability
from app.schemas.common import APIMessage
from app.schemas.description_memory import (
    LearnedDescriptionCreate,
    LearnedDescriptionLookup,
    LearnedDescriptionMatch,
    LearnedDescriptionPatch,
    LearnedDescriptionRead,
    LearningSettings,
    LearningSettingsPatch,
)
from app.services import description_memory as memory

router = APIRouter(prefix="/api/v1", tags=["description-memory"])


def _require_curator(user: CurrentUser) -> None:
    if not can_role(user, memory.MANAGE_CAPABILITY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to curate learned descriptions",
        )


@router.get("/learned-descriptions", response_model=list[LearnedDescriptionRead])
def list_learned_descriptions(
    q: str = Query(default="", description="Substring filter over wording, description and customer"),
    entry_status: str = Query(default="", alias="status"),
    limit: int = Query(default=200, ge=1, le=2000),
    user: CurrentUser = Depends(get_current_user),
) -> list[LearnedDescriptionRead]:
    require_capability(user, "edit_line_items")
    rows = repo.list_learned_descriptions(user.org_id)
    if entry_status:
        rows = [row for row in rows if row.status == entry_status]
    return memory.entries_matching(rows, q)[:limit]


@router.post("/learned-descriptions", response_model=LearnedDescriptionRead, status_code=201)
def create_learned_description(
    payload: LearnedDescriptionCreate,
    user: CurrentUser = Depends(get_current_user),
) -> LearnedDescriptionRead:
    """Teach the portal a description.

    Either pass `source_text` (+ `ggpl_description` and/or `fields`) directly, or
    point at the row being corrected with `quote_id` + `item_index` so the
    server reads the wording and classified construction off the row itself.
    """
    require_capability(user, "edit_line_items")
    item: dict | None = None
    if payload.quote_id is not None:
        quote = repo.get_quote(user.org_id, payload.quote_id)
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")
        index = payload.item_index
        if index is None or not (0 <= index < len(quote.items)):
            raise HTTPException(status_code=400, detail="item_index is not a line on this quote")
        item = dict(quote.items[index])
    # `customer` is taken verbatim: blank means the entry answers this wording for
    # every customer, which is the default the team asked for. Scoping to one
    # customer is deliberate and must be requested.
    try:
        return memory.teach(user, payload, item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/learned-descriptions/{entry_id}", response_model=LearnedDescriptionRead)
def patch_learned_description(
    entry_id: str,
    payload: LearnedDescriptionPatch,
    user: CurrentUser = Depends(get_current_user),
) -> LearnedDescriptionRead:
    _require_curator(user)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Nothing to update")
    if changes.get("status") == STATUS_APPROVED:
        changes["approved_by"] = user.user_id
    updated = repo.patch_learned_description(user.org_id, entry_id, changes)
    if not updated:
        raise HTTPException(status_code=404, detail="Learned description not found")
    memory.invalidate(user.org_id)
    return updated


@router.post("/learned-descriptions/{entry_id}/approve", response_model=LearnedDescriptionRead)
def approve_learned_description(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> LearnedDescriptionRead:
    """Promote a captured correction into permanent memory."""
    _require_curator(user)
    updated = repo.patch_learned_description(
        user.org_id, entry_id, {"status": STATUS_APPROVED, "approved_by": user.user_id}
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Learned description not found")
    memory.invalidate(user.org_id)
    return updated


@router.post("/learned-descriptions/{entry_id}/reject", response_model=LearnedDescriptionRead)
def reject_learned_description(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> LearnedDescriptionRead:
    """Retire an entry: kept as a record of the decision, never applied again."""
    _require_curator(user)
    updated = repo.patch_learned_description(
        user.org_id, entry_id, {"status": STATUS_REJECTED, "approved_by": user.user_id}
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Learned description not found")
    memory.invalidate(user.org_id)
    return updated


@router.delete("/learned-descriptions/{entry_id}", response_model=APIMessage)
def delete_learned_description(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> APIMessage:
    _require_curator(user)
    if not repo.delete_learned_description(user.org_id, entry_id):
        raise HTTPException(status_code=404, detail="Learned description not found")
    memory.invalidate(user.org_id)
    return APIMessage(message="deleted")


@router.post("/learned-descriptions/lookup", response_model=LearnedDescriptionMatch)
def lookup_learned_description(
    payload: LearnedDescriptionLookup,
    user: CurrentUser = Depends(get_current_user),
) -> LearnedDescriptionMatch:
    """What memory already holds for a wording — used by the portal to show the
    operator that a description came from (or conflicts with) a learned rule."""
    require_capability(user, "edit_line_items")
    kind, entry = memory.lookup(user.org_id, payload.source_text, payload.customer)
    return LearnedDescriptionMatch(matched=bool(entry), kind=kind, entry=entry)


@router.get("/learning-settings", response_model=LearningSettings)
def get_learning_settings(user: CurrentUser = Depends(get_current_user)) -> LearningSettings:
    return memory.get_settings(user.org_id)


@router.put("/learning-settings", response_model=LearningSettings)
def update_learning_settings(
    payload: LearningSettingsPatch,
    user: CurrentUser = Depends(get_current_user),
) -> LearningSettings:
    _require_curator(user)
    current = memory.get_settings(user.org_id)
    updated = repo.update_learning_settings(user.org_id, payload.as_settings(current))
    memory.invalidate(user.org_id)
    return updated
