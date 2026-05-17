from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.db import repo
from app.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/metrics")
def dashboard_metrics(user: CurrentUser = Depends(get_current_user)) -> dict:
    quotes = repo.list_quotes(user.org_id)
    sent = sum(1 for q in quotes if q.stage in ("sent", "po"))
    won = sum(1 for q in quotes if q.stage == "po")
    pending_review = sum(1 for q in quotes if q.stage in ("initial", "review"))
    total_items = sum(q.n_items for q in quotes)
    total_quote_value = 0.0
    sent_durations: list[float] = []
    type_dist: dict[str, int] = {}
    stage_counts = {stage: 0 for stage in ("initial", "review", "quote_prep", "repricing", "sent", "po")}
    for quote in quotes:
        stage_counts[quote.stage] = stage_counts.get(quote.stage, 0) + 1
        for item in quote.items:
            gtype = str(item.get("gasket_type") or "UNKNOWN")
            type_dist[gtype] = type_dist.get(gtype, 0) + 1
        unit_prices = quote.quote_data.get("unit_prices") or []
        for idx, item in enumerate(quote.items):
            if item.get("status") == "regret":
                continue
            try:
                qty = float(item.get("quantity") or 0)
                price = float(unit_prices[idx] if idx < len(unit_prices) else 0)
            except (TypeError, ValueError):
                continue
            total_quote_value += qty * price
        sent_at = None
        for entry in quote.stage_history:
            if entry.stage == "sent":
                sent_at = entry.at
                break
        if sent_at:
            created = quote.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
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
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
