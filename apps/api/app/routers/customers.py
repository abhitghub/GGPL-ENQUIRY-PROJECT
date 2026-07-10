import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import repo
from app.deps import CurrentUser, can_manage_users, get_current_user, require_capability
from app.schemas.customers import ContactPerson, CustomerCreate, CustomerRecord, CustomerSettings

router = APIRouter(prefix="/api/v1", tags=["customers"])


@router.get("/customers", response_model=CustomerSettings)
def get_customers(user: CurrentUser = Depends(get_current_user)) -> CustomerSettings:
    return repo.get_customer_settings(user.org_id)


@router.put("/customers", response_model=CustomerSettings)
def update_customers(payload: CustomerSettings, user: CurrentUser = Depends(get_current_user)) -> CustomerSettings:
    if not can_manage_users(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can manage customers")
    return repo.update_customer_settings(user.org_id, payload)


@router.post("/customers/records", response_model=CustomerRecord)
def add_customer(payload: CustomerCreate, user: CurrentUser = Depends(get_current_user)) -> CustomerRecord:
    """Append a single new customer to the master, allowed to anyone who can
    create enquiries (so sales can add a customer not yet in the data)."""
    require_capability(user, "create_enquiry")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Customer name is required")
    settings = repo.get_customer_settings(user.org_id)
    if any((customer.name or "").strip().lower() == name.lower() for customer in settings.customers):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Customer already exists: {name}")
    new_id = f"cust-{uuid.uuid4().hex[:10]}"
    contacts: list[ContactPerson] = []
    if payload.contact_name or payload.email:
        contacts.append(
            ContactPerson(
                id=f"{new_id}-c1",
                name=payload.contact_name,
                designation=payload.designation,
                email=payload.email,
                phone=payload.phone,
                mobile=payload.mobile,
            )
        )
    record = CustomerRecord(
        id=new_id,
        name=name,
        address_line1=payload.address_line1,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        gst_no=payload.gst_no,
        contact_name=payload.contact_name,
        designation=payload.designation,
        email=payload.email,
        phone=payload.phone or payload.mobile,
        contacts=contacts,
    )
    settings.customers.append(record)
    repo.update_customer_settings(user.org_id, settings)
    return record
