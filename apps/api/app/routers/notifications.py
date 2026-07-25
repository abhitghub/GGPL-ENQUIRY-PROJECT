"""Work notifications: real-time stream plus the persisted Updates feed.

The browser opens one long-lived `GET /api/v1/notifications/stream` per tab
(via the Next.js same-origin proxy, so the session cookie flows normally) and
receives an SSE `notification` event whenever the hub publishes something for
the caller's role or user id. Keepalive comments every 20s stop idle proxies
from closing the connection; `retry: 5000` tells EventSource to reconnect
automatically after any drop.

`GET /api/v1/notifications` returns the persisted history of those events for
the Updates page, and `GET /api/v1/notifications/assigned` lists the open
enquiries currently waiting on a person (owned by them, or parked at a
workflow step their role handles). Both accept `?user=<id>` so admin and
management can review any department member's queue.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.db import repo
from app.deps import CurrentUser, get_current_user
from app.services.enquiry_workflow import active_steps, current_workflow_step, stage_owner_roles
from app.services.notification_hub import hub
from app.services.quote_rules import quote_owner_matches

router = APIRouter(prefix="/api/v1", tags=["notifications"])

KEEPALIVE_SECONDS = 20

# Roles allowed to open another person's Updates/assigned-work view.
TEAM_VIEWER_ROLES = {"admin", "management"}

# Primary quote stages that still count as work in progress (mirrors the
# dashboard's OPEN_STAGES): sent/po enquiries are done from a queue viewpoint.
OPEN_STAGES = {"initial", "review", "quote_prep", "repricing"}


@dataclass(frozen=True)
class FeedTarget:
    user_id: str
    name: str
    role: str
    email: str

    def public(self) -> dict:
        return {"user_id": self.user_id, "name": self.name, "role": self.role}


def _resolve_target(current: CurrentUser, user_param: str) -> FeedTarget:
    """Whose feed/queue is being viewed: yourself by default; anyone in the
    org for admin/management."""
    requested = (user_param or "").strip().lower()
    if not requested or requested == current.user_id.lower():
        return FeedTarget(current.user_id, current.name or current.user_id, current.role, current.email)
    if current.role not in TEAM_VIEWER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or management can view another person's updates")
    person = next(
        (row for row in repo.list_app_users(current.org_id) if row.id.lower() == requested or row.email.lower() == requested),
        None,
    )
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return FeedTarget(person.id, person.name or person.id, person.role, person.email)


@router.get("/notifications")
def list_notifications(
    user: str = "",
    limit: int = Query(default=100, ge=1, le=200),
    current: CurrentUser = Depends(get_current_user),
) -> dict:
    target = _resolve_target(current, user)
    items = repo.list_notifications(current.org_id, user_id=target.user_id, role=target.role, limit=limit)
    return {"target": target.public(), "items": items}


@router.get("/notifications/assigned")
def list_assigned_work(user: str = "", current: CurrentUser = Depends(get_current_user)) -> dict:
    """Open enquiries waiting on the target person: ones they own, plus ones
    parked at a workflow step their role is responsible for."""
    target = _resolve_target(current, user)
    step_info = {step["id"]: step for step in active_steps()}
    items: list[dict] = []
    for quote in repo.list_quotes(current.org_id):
        if quote.stage not in OPEN_STAGES:
            continue
        meta = quote.stage_meta or {}
        # A source enquiry superseded by its quotation record would double up
        # in the list — the linked record carries the live workflow state.
        if str(meta.get("linked_quote_id") or "").strip():
            continue
        step = current_workflow_step(meta)
        owned = quote_owner_matches(quote, user_id=target.user_id, user_name=target.name, user_email=target.email)
        on_team_queue = target.role in stage_owner_roles(step)
        if not owned and not on_team_queue:
            continue
        info = step_info.get(step, {})
        items.append(
            {
                "quote_id": quote.id,
                "quote_no": quote.quote_no,
                "customer": quote.customer,
                "project_ref": quote.project_ref,
                "stage": quote.stage,
                "workflow_stage": step,
                "workflow_label": info.get("label") or step.replace("_", " "),
                "team": info.get("team", ""),
                "owner_name": str(meta.get("owner_name") or meta.get("owner_id") or ""),
                "n_items": quote.n_items,
                "updated_at": quote.updated_at.isoformat(),
                "assigned_via": "owner" if owned else "team",
            }
        )
    items.sort(key=lambda row: row["updated_at"], reverse=True)
    return {"target": target.public(), "items": items}


@router.get("/notifications/stream")
async def stream_notifications(request: Request, user: CurrentUser = Depends(get_current_user)) -> StreamingResponse:
    sub = hub.subscribe(user.org_id, user.user_id, user.role)

    async def events():
        try:
            yield "retry: 5000\nevent: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(sub.queue.get(), timeout=KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"event: notification\ndata: {json.dumps(event)}\n\n"
        finally:
            hub.unsubscribe(sub)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # Tell any buffering proxy (nginx et al.) to pass events through
            # immediately; the Next.js rewrite streams as-is.
            "X-Accel-Buffering": "no",
        },
    )