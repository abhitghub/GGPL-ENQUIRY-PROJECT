from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import repo
from app.deps import CurrentUser, can_manage_users, get_current_user
from app.schemas.common import APIMessage
from app.schemas.users import AppUserCreate, AppUserPatch, AppUserRead

router = APIRouter(prefix="/api/v1", tags=["users"])


def _require_admin(user: CurrentUser) -> None:
    if not can_manage_users(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can manage app users")


def _active_admin_count(org_id: str, exclude_id: str | None = None) -> int:
    return sum(
        1
        for row in repo.list_app_users(org_id)
        if row.active and row.role == "admin" and row.id != exclude_id
    )


@router.get("/users", response_model=list[AppUserRead])
def list_users(user: CurrentUser = Depends(get_current_user)) -> list[AppUserRead]:
    return repo.list_app_users(user.org_id)


@router.post("/users", response_model=AppUserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: AppUserCreate, user: CurrentUser = Depends(get_current_user)) -> AppUserRead:
    _require_admin(user)
    return repo.create_app_user(user.org_id, payload)


@router.patch("/users/{user_id}", response_model=AppUserRead)
def update_user(user_id: str, payload: AppUserPatch, user: CurrentUser = Depends(get_current_user)) -> AppUserRead:
    _require_admin(user)
    current = next((row for row in repo.list_app_users(user.org_id) if row.id == user_id), None)
    if not current:
        raise HTTPException(status_code=404, detail="User not found")
    next_role = payload.role if payload.role is not None else current.role
    next_active = payload.active if payload.active is not None else current.active
    if current.role == "admin" and (next_role != "admin" or not next_active) and _active_admin_count(user.org_id, exclude_id=user_id) == 0:
        raise HTTPException(status_code=400, detail="Keep at least one active admin user")
    updated = repo.update_app_user(user.org_id, user_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@router.delete("/users/{user_id}", response_model=APIMessage)
def delete_user(user_id: str, user: CurrentUser = Depends(get_current_user)) -> APIMessage:
    _require_admin(user)
    current = next((row for row in repo.list_app_users(user.org_id) if row.id == user_id), None)
    if not current:
        raise HTTPException(status_code=404, detail="User not found")
    if current.role == "admin" and _active_admin_count(user.org_id, exclude_id=user_id) == 0:
        raise HTTPException(status_code=400, detail="Keep at least one active admin user")
    if not repo.delete_app_user(user.org_id, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return APIMessage(message="deleted")
