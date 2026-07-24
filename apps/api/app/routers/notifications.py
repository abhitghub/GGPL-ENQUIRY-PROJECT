"""Server-Sent Events stream of real-time work notifications.

The browser opens one long-lived `GET /api/v1/notifications/stream` per tab
(via the Next.js same-origin proxy, so the session cookie flows normally) and
receives an SSE `notification` event whenever the hub publishes something for
the caller's role or user id. Keepalive comments every 20s stop idle proxies
from closing the connection; `retry: 5000` tells EventSource to reconnect
automatically after any drop.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.deps import CurrentUser, get_current_user
from app.services.notification_hub import hub

router = APIRouter(prefix="/api/v1", tags=["notifications"])

KEEPALIVE_SECONDS = 20


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