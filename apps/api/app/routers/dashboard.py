from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from app.db import repo
from app.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/metrics")
def dashboard_metrics(user: CurrentUser = Depends(get_current_user)) -> dict:
    quotes = repo.list_quotes(user.org_id)
    now = datetime.now(timezone.utc)
    today = now.date()
    sent = sum(1 for q in quotes if q.stage in ("sent", "po"))
    won = sum(1 for q in quotes if q.stage == "po")
    pending_review = sum(1 for q in quotes if q.stage in ("initial", "review"))
    total_items = sum(q.n_items for q in quotes)
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

    def as_float(value: Any, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def parse_date(value: Any) -> datetime | None:
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
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def quote_value(quote: Any) -> float:
        meta_value = as_float((quote.stage_meta or {}).get("estimated_quote_value"), -1)
        if meta_value >= 0:
            return meta_value
        unit_prices = quote.quote_data.get("unit_prices") or []
        total = 0.0
        for idx, item in enumerate(quote.items):
            if item.get("status") == "regret":
                continue
            qty = as_float(item.get("quantity"))
            price = as_float(unit_prices[idx] if idx < len(unit_prices) else 0)
            total += qty * price
        return total

    for quote in quotes:
        stage_meta = quote.stage_meta or {}
        created = quote.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created.date() == today:
            new_enquiries_today += 1
        stage_counts[quote.stage] = stage_counts.get(quote.stage, 0) + 1
        for item in quote.items:
            gtype = str(item.get("gasket_type") or "UNKNOWN")
            type_dist[gtype] = type_dist.get(gtype, 0) + 1
        value = quote_value(quote)
        total_quote_value += value
        if quote.stage not in ("sent", "po"):
            open_quote_value += value
        if value >= 500000:
            high_value_enquiries += 1
        if stage_meta.get("clarification_status") == "required":
            clarification_required += 1
        approval = stage_meta.get("approval") if isinstance(stage_meta.get("approval"), dict) else {}
        if approval.get("status") == "pending":
            pending_approval += 1
        due_at = parse_date(stage_meta.get("due_date"))
        if due_at:
            due_date = due_at.date()
            if due_date == today:
                due_today += 1
            if due_date < today and quote.stage not in ("sent", "po"):
                delayed_enquiries += 1
        owner_id = str(stage_meta.get("owner_id") or "unassigned")
        owner_name = str(stage_meta.get("owner_name") or "Unassigned")
        if quote.stage not in ("sent", "po"):
            workload = owner_workload.setdefault(
                owner_id,
                {"owner_id": owner_id, "owner_name": owner_name, "open_count": 0, "delayed_count": 0, "value": 0.0},
            )
            workload["open_count"] += 1
            workload["value"] += value
            if due_at and due_at.date() < today:
                workload["delayed_count"] += 1
        sent_at = None
        for entry in quote.stage_history:
            if entry.stage == "sent":
                sent_at = entry.at
                break
        if sent_at:
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            sent_durations.append(max((sent_at - created).total_seconds() / 86400, 0))
    return {
        "total_quotes": len(quotes),
        "items_processed": total_items,
        "pending_review": pending_review,
        "quotes_sent": sent,
        "converted_to_po": won,
        "conversion_rate": sent / len(quotes) if quotes else 0,
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
