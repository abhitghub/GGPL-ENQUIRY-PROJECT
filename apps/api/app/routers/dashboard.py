from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user, require_capability
from app.routers.quotes import _visible_quotes
from app.services.quote_rules import quote_estimated_value, quote_has_clarification, quote_opportunity_id

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

BUSINESS_TIMEZONE = ZoneInfo("Asia/Kolkata")
OPEN_STAGES = {"initial", "review", "quote_prep", "repricing"}
STAGE_RANK = {"initial": 0, "review": 1, "quote_prep": 2, "repricing": 3, "sent": 4, "po": 5}


def _as_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BUSINESS_TIMEZONE)


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BUSINESS_TIMEZONE)
    return parsed.astimezone(BUSINESS_TIMEZONE)


def _source_record(rows: list[Any]) -> Any:
    return next((row for row in rows if not (row.stage_meta or {}).get("source_enquiry_id")), min(rows, key=lambda row: row.created_at))


def _current_record(rows: list[Any]) -> Any:
    return max(rows, key=lambda row: (STAGE_RANK.get(row.stage, -1), row.updated_at))


def _value_record(rows: list[Any]) -> Any:
    quotations = [row for row in rows if (row.stage_meta or {}).get("source_enquiry_id")]
    return max(quotations or rows, key=lambda row: row.updated_at)


@router.get("/dashboard/metrics")
def dashboard_metrics(user: CurrentUser = Depends(get_current_user)) -> dict:
    require_capability(user, "view_dashboard")
    quotes = _visible_quotes(user)
    groups: dict[str, list[Any]] = {}
    for quote in quotes:
        groups.setdefault(quote_opportunity_id(quote), []).append(quote)

    now = datetime.now(BUSINESS_TIMEZONE)
    today = now.date()
    sent = 0
    won = 0
    pending_review = 0
    total_items = 0
    total_quote_value = 0.0
    open_quote_value = 0.0
    sent_durations: list[float] = []
    type_dist: dict[str, int] = {}
    stage_counts = {stage: 0 for stage in ("initial", "review", "quote_prep", "repricing", "sent", "po")}
    new_enquiries_today = 0
    clarification_required = 0
    delayed_enquiries = 0
    pending_approval = 0
    high_value_enquiries = 0
    due_today = 0
    owner_workload: dict[str, dict[str, Any]] = {}

    for rows in groups.values():
        source = _source_record(rows)
        current = _current_record(rows)
        value = quote_estimated_value(_value_record(rows))
        stage_meta = current.stage_meta or {}
        source_meta = source.stage_meta or {}
        is_open = current.stage in OPEN_STAGES

        stage_counts[current.stage] = stage_counts.get(current.stage, 0) + 1
        total_items += source.n_items
        total_quote_value += value
        if current.stage in {"sent", "po"}:
            sent += 1
        if current.stage == "po":
            won += 1
        if current.stage in {"initial", "review"}:
            pending_review += 1
        if _as_local(source.created_at).date() == today:
            new_enquiries_today += 1
        for item in source.items:
            gasket_type = str(item.get("gasket_type") or "UNKNOWN")
            type_dist[gasket_type] = type_dist.get(gasket_type, 0) + 1

        if is_open:
            open_quote_value += value
            if value >= 500000:
                high_value_enquiries += 1
        if any(quote_has_clarification(row) for row in rows):
            clarification_required += 1
        if any(
            isinstance((row.stage_meta or {}).get("approval"), dict)
            and (row.stage_meta or {})["approval"].get("status") == "pending"
            for row in rows
        ):
            pending_approval += 1

        due_at = _parse_date(source_meta.get("due_date") or stage_meta.get("due_date"))
        if is_open and due_at:
            if due_at.date() == today:
                due_today += 1
            elif due_at.date() < today:
                delayed_enquiries += 1

        owner_id = str(source_meta.get("owner_id") or stage_meta.get("owner_id") or "unassigned")
        owner_name = str(source_meta.get("owner_name") or stage_meta.get("owner_name") or "Unassigned")
        if is_open:
            workload = owner_workload.setdefault(
                owner_id,
                {"owner_id": owner_id, "owner_name": owner_name, "open_count": 0, "delayed_count": 0, "value": 0.0},
            )
            workload["open_count"] += 1
            workload["value"] += value
            if due_at and due_at.date() < today:
                workload["delayed_count"] += 1

        sent_at = min(
            (
                entry.at
                for row in rows
                for entry in row.stage_history
                if entry.stage == "sent"
            ),
            default=None,
        )
        if sent_at:
            sent_durations.append(max((_as_local(sent_at) - _as_local(source.created_at)).total_seconds() / 86400, 0))

    return {
        "total_quotes": len(groups),
        "items_processed": total_items,
        "pending_review": pending_review,
        "quotes_sent": sent,
        "converted_to_po": won,
        "conversion_rate": sent / len(groups) if groups else 0,
        "win_rate": won / sent if sent else 0,
        "avg_time_to_sent_days": sum(sent_durations) / len(sent_durations) if sent_durations else 0,
        "total_quote_value": total_quote_value,
        "stage_counts": stage_counts,
        "gasket_type_distribution": type_dist,
        "new_enquiries_today": new_enquiries_today,
        "clarification_required": clarification_required,
        "delayed_enquiries": delayed_enquiries,
        "pending_approval": pending_approval,
        "high_value_enquiries": high_value_enquiries,
        "owner_workload": sorted(owner_workload.values(), key=lambda row: (row["delayed_count"], row["open_count"]), reverse=True),
        "due_today": due_today,
        "open_quote_value": open_quote_value,
        "generated_at": now.isoformat(),
    }
