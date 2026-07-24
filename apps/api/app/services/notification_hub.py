"""In-process real-time work-notification hub (SSE backplane).

Quote/workflow endpoints publish small JSON events here after a successful
write; each logged-in browser holds an open `GET /api/v1/notifications/stream`
(Server-Sent Events) connection and receives matching events instantly, so
users learn about new work without refreshing the portal.

Single-process by design: production runs one uvicorn worker with no Redis, so
a thread-safe in-memory subscriber set is sufficient. Endpoints are sync (they
run on threadpool threads) while the SSE generator is async, so publish()
forwards events onto each subscriber's event loop with call_soon_threadsafe.
If the deployment ever scales to multiple workers/nodes, replace the fan-out
with Redis pub/sub (REDIS_URL is already in config).

Missed-while-offline is intentionally not persisted: the role dashboard is
itself the durable queue — anything still waiting on a role shows up there on
the next login. These events only make the arrival real-time.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.services.enquiry_workflow import active_steps, stage_owner_roles

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type hints only
    from app.deps import CurrentUser
    from app.schemas.quotes import QuoteRead

logger = logging.getLogger(__name__)

# Roles allowed to decide a pending change query (mirrors deps.can_approve).
QUERY_APPROVER_ROLES: set[str] = {"admin", "approver", "management"}


@dataclass(eq=False)
class Subscriber:
    org_id: str
    user_id: str
    role: str
    loop: asyncio.AbstractEventLoop
    # Bounded so one stalled connection can never grow memory unboundedly; a
    # full queue just drops that subscriber's oldest pending toast.
    queue: "asyncio.Queue[dict]" = field(default_factory=lambda: asyncio.Queue(maxsize=100))


class NotificationHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[Subscriber] = []

    def subscribe(self, org_id: str, user_id: str, role: str) -> Subscriber:
        """Register a listener. Must be called from a running event loop (the
        SSE endpoint), whose loop is captured for thread-safe delivery."""
        sub = Subscriber(org_id=org_id, user_id=user_id, role=role, loop=asyncio.get_running_loop())
        with self._lock:
            self._subscribers.append(sub)
        return sub

    def unsubscribe(self, sub: Subscriber) -> None:
        with self._lock:
            try:
                self._subscribers.remove(sub)
            except ValueError:
                pass

    def publish(
        self,
        org_id: str,
        event: dict,
        *,
        roles: set[str] | None = None,
        user_ids: set[str] | None = None,
        exclude_user_ids: set[str] | None = None,
    ) -> int:
        """Fan an event out to matching subscribers. Thread-safe; callable from
        sync endpoint code. A subscriber matches when it is in the same org,
        not excluded (the actor never gets notified of their own action), and
        either their user_id or their role is targeted. Returns the number of
        deliveries attempted (handy for tests)."""
        roles = roles or set()
        user_ids = {u for u in (user_ids or set()) if u}
        exclude = exclude_user_ids or set()
        with self._lock:
            targets = [
                sub
                for sub in self._subscribers
                if sub.org_id == org_id
                and sub.user_id not in exclude
                and (sub.user_id in user_ids or sub.role in roles)
            ]
        for sub in targets:
            try:
                sub.loop.call_soon_threadsafe(_offer, sub.queue, event)
            except RuntimeError:
                # The subscriber's loop is gone (connection torn down mid-publish).
                self.unsubscribe(sub)
        return len(targets)


def _offer(queue: "asyncio.Queue[dict]", event: dict) -> None:
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        pass


hub = NotificationHub()


def _step_label(step_id: str) -> str:
    for step in active_steps():
        if step["id"] == step_id:
            return step["label"]
    return step_id.replace("_", " ")


def _quote_ref(quote: "QuoteRead") -> str:
    return str(quote.project_ref or quote.quote_no or "").strip()


def _base_event(kind: str, quote: "QuoteRead", actor: "CurrentUser", stage: str) -> dict:
    return {
        "id": f"ntf-{uuid.uuid4().hex[:12]}",
        "kind": kind,
        "quote_id": quote.id,
        "customer": (quote.customer or "").strip(),
        "project_ref": _quote_ref(quote),
        "stage": stage,
        "stage_label": _step_label(stage),
        "by": actor.name or actor.user_id,
        "at": datetime.now(timezone.utc).isoformat(),
    }


def _describe(quote: "QuoteRead") -> str:
    customer = (quote.customer or "").strip() or "An enquiry"
    ref = _quote_ref(quote)
    return f"{customer} ({ref})" if ref else customer


def notify_stage_change(actor: "CurrentUser", quote: "QuoteRead", dest_step: str, *, kind: str = "workflow") -> None:
    """A quote landed on a new workflow step: tell everyone whose role owns
    that step (except the person who moved it) that work is waiting on them.
    Never raises — notifications must not fail the underlying request."""
    try:
        event = _base_event(kind, quote, actor, dest_step)
        event["title"] = "New work in your queue"
        event["message"] = f"{_describe(quote)} is now at '{event['stage_label']}' — waiting on your team."
        hub.publish(
            actor.org_id,
            event,
            roles=stage_owner_roles(dest_step),
            exclude_user_ids={actor.user_id},
        )
    except Exception:  # pragma: no cover - defensive: never break the request
        logger.exception("Failed to publish stage-change notification")


def notify_assignment(actor: "CurrentUser", quote: "QuoteRead", owner_id: str) -> None:
    """A specific user was made owner of an enquiry: tell exactly that user."""
    try:
        owner_id = (owner_id or "").strip()
        if not owner_id or owner_id == actor.user_id:
            return
        stage = str((quote.stage_meta or {}).get("workflow_stage") or "").strip()
        event = _base_event("assignment", quote, actor, stage)
        event["title"] = "Enquiry assigned to you"
        event["message"] = f"{event['by']} assigned {_describe(quote)} to you."
        hub.publish(actor.org_id, event, user_ids={owner_id}, exclude_user_ids={actor.user_id})
    except Exception:  # pragma: no cover - defensive: never break the request
        logger.exception("Failed to publish assignment notification")


def notify_change_query(actor: "CurrentUser", quote: "QuoteRead", target_label: str) -> None:
    """A change query is pending approval: tell the approvers."""
    try:
        stage = str((quote.stage_meta or {}).get("workflow_stage") or "").strip()
        event = _base_event("query", quote, actor, stage)
        event["title"] = "Change query awaiting approval"
        event["message"] = f"{event['by']} raised a change query on {_describe(quote)} (to {target_label})."
        hub.publish(actor.org_id, event, roles=QUERY_APPROVER_ROLES, exclude_user_ids={actor.user_id})
    except Exception:  # pragma: no cover - defensive: never break the request
        logger.exception("Failed to publish change-query notification")