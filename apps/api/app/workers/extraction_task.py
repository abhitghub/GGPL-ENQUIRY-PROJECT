from __future__ import annotations

from openai import OpenAI

from services.extraction import process_document

from .celery_app import celery_app


@celery_app.task(name="extraction.process_document")
def process_document_task(source, source_type: str, api_key: str) -> dict:
    client = OpenAI(api_key=api_key, timeout=180.0)
    items, skipped_count, error = process_document(source, source_type, client)
    return {
        "items": items,
        "skipped_count": skipped_count,
        "error": error,
    }
