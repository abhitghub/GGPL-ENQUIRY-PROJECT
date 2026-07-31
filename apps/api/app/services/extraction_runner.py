from __future__ import annotations

import logging
import os
from typing import Any

from openai import OpenAI

from services.extraction import process_document

from app.db import repo
from app.schemas.quotes import QuotePatch
from app.services import description_memory

logger = logging.getLogger(__name__)


def run_extraction_job(
    *,
    org_id: str,
    job_id: str,
    source: Any,
    source_type: str,
    api_key: str | None,
    quote_id: str | None = None,
    customer: str = "",
) -> None:
    """Run Smart Parse and store the result on the job (and quote, if given).

    `customer` scopes the description-memory lookup. It is passed separately from
    `quote_id` because the first extraction of an enquiry happens before the
    quote record exists, and a customer's own wording conventions are exactly
    what memory is most often scoped to.
    """
    key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        repo.update_job(
            org_id,
            job_id,
            status="failed",
            progress=1.0,
            error="OPENAI_API_KEY is required for Smart Parse extraction.",
            message="missing OpenAI API key",
        )
        return

    def progress_cb(done: int, total: int) -> None:
        progress = done / total if total else 0.0
        repo.update_job(org_id, job_id, status="running", progress=progress, message=f"{done}/{total}")

    def on_chunk_items(_chunk_items: list[dict]) -> None:
        # Keep in-flight job records small. Large enquiries can produce thousands
        # of rows, and rewriting that growing JSON payload on every chunk makes
        # both polling and database writes expensive.
        return None

    repo.update_job(org_id, job_id, status="running", progress=0.0, message="Smart Parse started")
    client = OpenAI(api_key=key, timeout=180.0)
    items, skipped_count, error = process_document(
        source,
        source_type,
        client,
        progress_cb=progress_cb,
        on_chunk_items=on_chunk_items,
    )
    if error:
        repo.update_job(
            org_id,
            job_id,
            status="failed",
            progress=1.0,
            skipped_count=skipped_count,
            error=error,
            message="Smart Parse failed",
        )
        return

    # Descriptions the team has already corrected are answered from memory rather
    # than re-derived, so a construction the engine gets wrong is only ever
    # fixed once. Runs after the rules engine so the learned values are what the
    # operator actually sees on the row.
    target_quote = repo.get_quote(org_id, quote_id) if quote_id else None
    try:
        description_memory.apply_memory(
            org_id,
            items,
            customer=customer or str(getattr(target_quote, "customer", "") or ""),
        )
    except Exception:
        # An extraction that reaches the operator un-learned is recoverable; one
        # that fails outright is not.
        logger.warning("Could not apply description memory to extraction %s", job_id, exc_info=True)

    if quote_id:
        try:
            quote = target_quote or repo.get_quote(org_id, quote_id)
            if quote:
                repo.update_quote(
                    org_id,
                    quote_id,
                    QuotePatch(items=[*quote.items, *items], expected_version=quote.version),
                )
        except Exception as exc:
            repo.update_job(
                org_id,
                job_id,
                status="failed",
                progress=1.0,
                skipped_count=skipped_count,
                error=str(exc),
                message="Could not save extracted items",
            )
            return
    repo.update_job(
        org_id,
        job_id,
        status="succeeded",
        progress=1.0,
        items=items,
        skipped_count=skipped_count,
        message="Smart Parse completed",
    )
