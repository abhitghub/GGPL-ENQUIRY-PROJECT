"""Service layer for the portal's description memory.

Storage (`repo`) and the pure index (`core.description_memory`) meet here. Two
directions of traffic:

* **Learn** — `capture_item_edits` compares the rows a user just saved against
  what was stored and writes a memory entry for every GGPL description they
  corrected. `teach` is the explicit version: estimation/management/admin
  saving a description into permanent memory on purpose.
* **Recall** — `apply_memory` runs over freshly extracted or recomputed rows and
  replaces the engine's answer with what the team already decided, for any row
  whose customer wording the portal has seen corrected before.

The index is cached per org and invalidated on every write, because extraction
resolves it once per row and the store is small enough to hold whole.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Iterable

from core.description_memory import (
    ACTIVE_STATUSES,
    SOURCE_EDIT,
    SOURCE_MANUAL,
    STATUS_APPROVED,
    STATUS_PENDING,
    DescriptionMemory,
    LearnedEntry,
    apply_match,
    changed_fields,
    descriptions_differ,
    entry_from_item,
    fingerprint,
    learnable_fields_of,
    source_text_of,
)

from app.db import repo
from app.deps import CurrentUser, can_role
from app.schemas.description_memory import (
    LearnedDescriptionCreate,
    LearnedDescriptionRead,
    LearningSettings,
)

logger = logging.getLogger(__name__)

#: Capability that lets a user write straight into permanent (approved) memory
#: and curate what is already there.
MANAGE_CAPABILITY = "manage_description_memory"

#: (org_id, apply_pending) -> (version, index). Two variants per org because the
#: approved-only view is a different index, not a filter on lookup.
_cache: dict[tuple[str, bool], tuple[int, DescriptionMemory]] = {}
_cache_versions: dict[str, int] = {}
_cache_lock = threading.RLock()


def _entry_of(row: LearnedDescriptionRead) -> LearnedEntry:
    return LearnedEntry(
        id=row.id,
        fingerprint=row.fingerprint,
        source_text=row.source_text,
        ggpl_description=row.ggpl_description,
        fields=dict(row.fields or {}),
        customer=row.customer,
        status=row.status,
        source=row.source,
        created_by=row.created_by,
        approved_by=row.approved_by,
        note=row.note,
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def invalidate(org_id: str) -> None:
    """Force the next read to rebuild this org's index."""
    with _cache_lock:
        _cache_versions[org_id] = _cache_versions.get(org_id, 0) + 1
        for key in [key for key in _cache if key[0] == org_id]:
            _cache.pop(key, None)


def memory_for(org_id: str, *, settings: LearningSettings | None = None) -> DescriptionMemory:
    """This org's memory index, rebuilt only after a write.

    A store that cannot be read must not break extraction, so a failure here
    degrades to an empty memory — the engine's own answer — not an error.
    """
    resolved = settings if settings is not None else get_settings(org_id)
    apply_pending = bool(resolved.apply_pending)
    key = (org_id, apply_pending)
    with _cache_lock:
        version = _cache_versions.get(org_id, 0)
        cached = _cache.get(key)
        if cached and cached[0] == version:
            return cached[1]

    try:
        rows = repo.list_learned_descriptions(org_id)
    except Exception:
        logger.warning("Description memory unavailable for org %s", org_id, exc_info=True)
        return DescriptionMemory.empty()

    wanted = ACTIVE_STATUSES if apply_pending else {STATUS_APPROVED}
    index = DescriptionMemory.build(_entry_of(row) for row in rows if row.status in wanted)
    with _cache_lock:
        _cache[key] = (version, index)
    return index


def get_settings(org_id: str) -> LearningSettings:
    try:
        return repo.get_learning_settings(org_id)
    except Exception:
        logger.warning("Learning settings unavailable for org %s", org_id, exc_info=True)
        return LearningSettings()


def apply_memory(
    org_id: str,
    items: list[dict],
    *,
    customer: str = "",
    settings: LearningSettings | None = None,
) -> list[dict]:
    """Answer every row the team has already corrected from memory.

    Rows are mutated in place and returned. Applications are counted so the
    curation screen can show which learned rules actually earn their keep.
    """
    if not items:
        return items
    resolved = settings if settings is not None else get_settings(org_id)
    index = memory_for(org_id, settings=resolved)
    if not index:
        return items

    hits: list[str] = []
    for item in items:
        match = index.resolve(source_text_of(item), customer)
        if not match:
            continue
        if not match.should_apply and not resolved.suggest_similar:
            continue
        apply_match(item, match)
        if match.should_apply:
            hits.append(match.entry.id)
    if hits:
        try:
            repo.record_learned_hits(org_id, hits)
        except Exception:
            # Usage statistics are not worth failing an extraction over.
            logger.warning("Could not record description-memory hits", exc_info=True)
    return items


def _descriptions_by_wording(rows: list[dict]) -> dict[str, dict | None]:
    """Map each wording in `rows` to the single row that answered it.

    A wording answered two different ways maps to None — there is no one previous
    answer, so nothing about it can be called a correction.
    """
    seen: dict[str, dict | None] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = fingerprint(source_text_of(row))
        if not key:
            continue
        if key not in seen:
            seen[key] = row
            continue
        held = seen[key]
        if held is None:
            continue
        if descriptions_differ(held.get("ggpl_description"), row.get("ggpl_description")):
            seen[key] = None
    return seen


def capture_item_edits(
    user: CurrentUser,
    *,
    before: list[dict],
    after: list[dict],
) -> list[LearnedDescriptionRead]:
    """Learn from the GGPL descriptions this save changed.

    Only rows whose description text actually moved are captured — a quantity or
    price edit teaches nothing about wording. Captures land as `pending`, so a
    single operator's fix is applied but stays visibly unverified until someone
    with curation rights approves it. `auto_capture` off disables this entirely.

    Rows are paired by customer wording, not by position: the same save may have
    deleted lines, and a positional pairing would then read one row's correction
    off a different row's description.

    A capture is stored ORG-WIDE, deliberately unscoped to the quote's customer:
    the same wording deserves the same answer whoever sends it, which is what the
    team asked for, and scoping every capture would mean re-learning one fix once
    per customer. Narrowing a rule to a single customer is a deliberate act, done
    through the curation screen.
    """
    settings = get_settings(user.org_id)
    if not settings.auto_capture:
        return []

    previous = _descriptions_by_wording(before)
    stored: list[LearnedDescriptionRead] = []
    for new_row in after:
        if not isinstance(new_row, dict):
            continue
        key = fingerprint(source_text_of(new_row))
        # An unseen wording is a new line, not a correction of a previous answer.
        # Its own next edit is what should be learned.
        if not key or key not in previous:
            continue
        was = previous[key]
        # Two lines shared this wording and disagreed about the answer before the
        # save — there is no single previous answer to have corrected.
        if was is None:
            continue
        if not descriptions_differ(was.get("ggpl_description"), new_row.get("ggpl_description")):
            continue
        if not str(new_row.get("ggpl_description") or "").strip():
            continue
        old_row = was

        # Prefer the fields the operator actually changed; fall back to the row's
        # full classification when the description was typed on its own (a
        # hand-written description carries the whole construction implicitly).
        fields = changed_fields(old_row, new_row) or learnable_fields_of(new_row)
        entry = entry_from_item(
            new_row,
            entry_id="",
            customer="",
            status=STATUS_PENDING,
            source=SOURCE_EDIT,
            # `note` is the curator's field and is deliberately left untouched: a
            # capture must not overwrite someone's "confirmed with Ashwin sir".
            # Provenance is already on the entry as source=edit + created_by.
            created_by=user.user_id,
            fields=fields,
        )
        if entry is None:
            continue
        try:
            stored.append(_persist(user.org_id, entry))
        except Exception:
            # Learning is a side effect of saving a quote; never fail the save.
            logger.warning("Could not capture learned description", exc_info=True)
    if stored:
        invalidate(user.org_id)
    return stored


def teach(user: CurrentUser, payload: LearnedDescriptionCreate, item: dict | None = None) -> LearnedDescriptionRead:
    """Save a description into memory on purpose.

    `approve=True` needs the curation capability and writes straight into
    permanent memory; anyone who may edit line items can still contribute, but
    their entry lands pending for review.
    """
    source_item: dict[str, Any] = dict(item or {})
    if payload.source_text.strip():
        source_item["raw_description"] = payload.source_text
    if payload.ggpl_description.strip():
        source_item["ggpl_description"] = payload.ggpl_description

    fields = dict(payload.fields) if payload.fields else learnable_fields_of(source_item)
    approve = bool(payload.approve) and can_role(user, MANAGE_CAPABILITY)
    entry = entry_from_item(
        source_item,
        entry_id="",
        customer=payload.customer,
        status=STATUS_APPROVED if approve else STATUS_PENDING,
        source=SOURCE_MANUAL,
        created_by=user.user_id,
        approved_by=user.user_id if approve else "",
        note=payload.note,
        fields=fields,
    )
    if entry is None:
        raise ValueError(
            "A learned description needs the customer wording to match on and "
            "either a GGPL description or at least one classified field."
        )
    stored = _persist(user.org_id, entry)
    invalidate(user.org_id)
    return stored


def _persist(org_id: str, entry: LearnedEntry) -> LearnedDescriptionRead:
    return repo.upsert_learned_description(
        org_id,
        {
            "fingerprint": entry.fingerprint,
            "source_text": entry.source_text,
            "ggpl_description": entry.ggpl_description,
            "fields": dict(entry.fields or {}),
            "customer": entry.customer,
            "status": entry.status,
            "source": entry.source,
            "note": entry.note,
            "created_by": entry.created_by,
            "approved_by": entry.approved_by,
        },
    )


def lookup(org_id: str, source_text: str, customer: str = "") -> tuple[str, LearnedDescriptionRead | None]:
    """What memory holds for a wording: ('exact'|'similar'|'', entry|None)."""
    index = memory_for(org_id)
    match = index.resolve(source_text, customer)
    if not match:
        return "", None
    row = repo.get_learned_description(org_id, match.entry.id)
    return match.kind, row


def entries_matching(rows: Iterable[LearnedDescriptionRead], query: str) -> list[LearnedDescriptionRead]:
    """Substring filter over wording and description, for the curation screen."""
    needle = " ".join(str(query or "").strip().upper().split())
    if not needle:
        return list(rows)
    return [
        row
        for row in rows
        if needle in row.source_text.upper()
        or needle in row.ggpl_description.upper()
        or needle in row.customer.upper()
    ]
