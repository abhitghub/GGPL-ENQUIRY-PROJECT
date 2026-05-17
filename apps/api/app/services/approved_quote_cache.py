from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


def cache_final_approved_quote(quote: Any) -> None:
    """Optionally cache only final approved quotations in Redis.

    Redis is disabled by default for the first migration window. When enabled,
    this function is only called after a quote reaches the final approved state,
    represented by the Phase-1 pipeline's `po` stage.
    """
    settings = get_settings()
    if not (settings.redis_enabled and settings.approved_quote_redis_enabled):
        return

    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        payload = quote.model_dump(mode="json") if hasattr(quote, "model_dump") else quote
        client.set(f"approved_quote:{payload['id']}", json.dumps(payload))
    except Exception as exc:
        logger.warning("Approved quotation Redis cache skipped: %s", exc)
