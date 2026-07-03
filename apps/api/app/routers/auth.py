from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.auth_session import create_session_token, session_cookie_params
from app.config import get_settings
from app.db import repo
from app.deps import CurrentUser, get_current_user
from app.schemas.users import AppUserLogin, AppUserRead

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/login", response_model=AppUserRead)
def login(
    payload: AppUserLogin,
    response: Response,
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> AppUserRead:
    org_id = (x_org_id or "local-org").strip() or "local-org"
    user = repo.authenticate_app_user(org_id, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    response.set_cookie(
        value=create_session_token(user.org_id, user.id),
        **session_cookie_params(),
    )
    return user


@router.get("/auth/me", response_model=AppUserRead)
def me(user: CurrentUser = Depends(get_current_user)) -> AppUserRead:
    current = next(
        (
            row
            for row in repo.list_app_users(user.org_id)
            if row.active and (row.id.lower() == user.user_id.lower() or row.email.lower() == user.user_id.lower())
        ),
        None,
    )
    if current:
        return current
    # Login has been disabled: no stored user is required. Return the resolved
    # default identity so the app can render without a real account.
    now = datetime.now(timezone.utc)
    return AppUserRead(
        id=user.user_id,
        org_id=user.org_id,
        name=user.name or user.user_id,
        email=user.email,
        role=user.role,  # type: ignore[arg-type]
        active=True,
        created_at=now,
        updated_at=now,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(get_settings().auth_cookie_name, path="/")
    return response
