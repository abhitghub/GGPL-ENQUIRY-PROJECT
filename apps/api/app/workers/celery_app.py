from __future__ import annotations

from celery import Celery

from app.config import get_settings


settings = get_settings()

broker_url = settings.redis_url if settings.redis_enabled else "memory://"
backend_url = settings.redis_url if settings.redis_enabled else "cache+memory://"

celery_app = Celery(
    "gasket_quote",
    broker=broker_url,
    backend=backend_url,
    include=["app.workers.extraction_task"],
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_always_eager=not settings.redis_enabled,
)
