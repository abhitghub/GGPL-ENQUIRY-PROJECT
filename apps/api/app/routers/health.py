from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import repo
from app.deps import CurrentUser, get_current_user
from app.routers.quotes import _repo_visibility_kwargs

from ..config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/healthz/db")
def db_healthz(user: CurrentUser = Depends(get_current_user)) -> dict[str, str | int]:
    quotes = repo.list_quotes(user.org_id, **_repo_visibility_kwargs(user))
    return {
        "status": "ok",
        "repository": type(repo).__name__,
        "org_id": user.org_id,
        "quote_count": len(quotes),
    }
