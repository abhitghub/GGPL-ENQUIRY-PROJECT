from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header


@dataclass(frozen=True)
class CurrentUser:
    org_id: str
    user_id: str


def get_current_user(
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> CurrentUser:
    return CurrentUser(
        org_id=(x_org_id or "local-org").strip() or "local-org",
        user_id=(x_user_id or "local-user").strip() or "local-user",
    )
