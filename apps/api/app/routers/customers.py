from fastapi import APIRouter, Depends, HTTPException, status

from app.db import repo
from app.deps import CurrentUser, can_manage_users, get_current_user
from app.schemas.customers import CustomerSettings

router = APIRouter(prefix="/api/v1", tags=["customers"])


@router.get("/customers", response_model=CustomerSettings)
def get_customers(user: CurrentUser = Depends(get_current_user)) -> CustomerSettings:
    return repo.get_customer_settings(user.org_id)


@router.put("/customers", response_model=CustomerSettings)
def update_customers(payload: CustomerSettings, user: CurrentUser = Depends(get_current_user)) -> CustomerSettings:
    if not can_manage_users(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can manage customers")
    return repo.update_customer_settings(user.org_id, payload)
