from __future__ import annotations

import logging

import structlog

from .config import Settings


def configure_observability(settings: Settings) -> None:
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.05,
        )

    if settings.posthog_api_key:
        from posthog import Posthog

        Posthog(
            project_api_key=settings.posthog_api_key,
            host=settings.posthog_host,
            enable_exception_autocapture=True,
        )
