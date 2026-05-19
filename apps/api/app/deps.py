from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header


@dataclass(frozen=True)
class CurrentUser:
    org_id: str
    user_id: str
    role: str = "sales"
    name: str = ""


def get_current_user(
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_user_name: str | None = Header(default=None, alias="X-User-Name"),
) -> CurrentUser:
    org_id = (x_org_id or "local-org").strip() or "local-org"
    user_id = (x_user_id or "local-user").strip() or "local-user"
    role = "sales"
    try:
        from app.db import repo

        user_key = user_id.lower()
        app_user = next(
            (
                row
                for row in repo.list_app_users(org_id)
                if row.active and (row.id.lower() == user_key or row.email.lower() == user_key)
            ),
            None,
        )
        if app_user:
            role = app_user.role
    except Exception:
        # Keep request handling available even if the user store is temporarily unavailable.
        role = "sales"
    return CurrentUser(
        org_id=org_id,
        user_id=user_id,
        role=role,
        name=(x_user_name or "").strip(),
    )


def can_approve(user: CurrentUser) -> bool:
    return user.role in {"admin", "approver"}


def can_manage_users(user: CurrentUser) -> bool:
    return user.role == "admin"
