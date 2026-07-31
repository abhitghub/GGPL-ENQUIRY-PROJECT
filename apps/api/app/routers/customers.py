import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import repo
from app.deps import CurrentUser, can_manage_users, get_current_user, require_capability
from app.schemas.customers import (
    ContactCreate,
    ContactPerson,
    ContactUpdate,
    CustomerCreate,
    CustomerLocation,
    CustomerRecord,
    CustomerSettings,
    CustomerUpdate,
    EpcNameCreate,
    LocationCreate,
    LocationUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["customers"])


def _find_customer(settings: CustomerSettings, record_id: str) -> CustomerRecord:
    record = next((customer for customer in settings.customers if customer.id == record_id), None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer not found: {record_id}")
    return record


def _apply_patch(target: object, payload: object) -> None:
    """Copy the keys the caller actually sent onto the stored model.

    Editing is a PATCH so a form that only knows about a few fields can never
    blank out the rest of the record; ``exclude_unset`` is what draws that line.
    """
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        setattr(target, key, value.strip() if isinstance(value, str) else value)


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
    # A brand new customer gets its typed address as its first location, so the
    # location dropdown behaves the same for hand-added and imported companies.
    locations: list[CustomerLocation] = []
    if any((payload.address_line1, payload.city, payload.state, payload.country)):
        locations.append(
            CustomerLocation(
                id=f"{new_id}-l1",
                address_line1=payload.address_line1,
                city=payload.city,
                state=payload.state,
                country=payload.country,
                gst_no=payload.gst_no,
            )
        )
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
                location_id=locations[0].id if locations else "",
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
        locations=locations,
    )
    settings.customers.append(record)
    repo.update_customer_settings(user.org_id, settings)
    return record


@router.patch("/customers/records/{record_id}", response_model=CustomerRecord)
def update_customer_record(
    record_id: str, payload: CustomerUpdate, user: CurrentUser = Depends(get_current_user)
) -> CustomerRecord:
    """Correct the company header of an existing customer from the portal.

    Open to anyone who can create enquiries: the CRM export it came from has
    gaps and typos, and the person filling the enquiry is the one who spots them.
    """
    require_capability(user, "create_enquiry")
    settings = repo.get_customer_settings(user.org_id)
    record = _find_customer(settings, record_id)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Customer name is required")
        clash = any(
            customer.id != record_id and (customer.name or "").strip().lower() == name.lower()
            for customer in settings.customers
        )
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Customer already exists: {name}")
    _apply_patch(record, payload)
    repo.update_customer_settings(user.org_id, settings)
    return record


@router.post("/customers/epc-names", response_model=CustomerSettings)
def add_epc_name(payload: EpcNameCreate, user: CurrentUser = Depends(get_current_user)) -> CustomerSettings:
    """Append an EPC / project company to the master list, allowed to anyone who
    can create enquiries (so sales can add one while filling the enquiry setup
    instead of waiting for an admin). Adding an existing name is a no-op."""
    require_capability(user, "create_enquiry")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="EPC / company name is required")
    settings = repo.get_customer_settings(user.org_id)
    if not any(existing.strip().lower() == name.lower() for existing in settings.epc_names):
        settings.epc_names.append(name)
        repo.update_customer_settings(user.org_id, settings)
    return settings


@router.post("/customers/records/{record_id}/locations", response_model=CustomerRecord)
def add_customer_location(
    record_id: str, payload: LocationCreate, user: CurrentUser = Depends(get_current_user)
) -> CustomerRecord:
    """Append a site / plant address to an existing customer."""
    require_capability(user, "create_enquiry")
    settings = repo.get_customer_settings(user.org_id)
    record = _find_customer(settings, record_id)
    location = CustomerLocation(id=f"{record_id}-l-{uuid.uuid4().hex[:8]}", **payload.model_dump())
    if not location.display_label():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Give the location a label, or a city / state / country",
        )
    record.locations.append(location)
    # First address on a company that had none also becomes its default, so the
    # older single-address consumers (quotation PDF, exports) keep working.
    if len(record.locations) == 1 and not (record.address_line1 or record.city):
        record.address_line1 = location.address_line1
        record.address_line2 = location.address_line2
        record.city = location.city
        record.state = location.state
        record.pin_code = location.pin_code
        record.country = location.country
    repo.update_customer_settings(user.org_id, settings)
    return record


@router.patch("/customers/records/{record_id}/locations/{location_id}", response_model=CustomerRecord)
def update_customer_location(
    record_id: str,
    location_id: str,
    payload: LocationUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> CustomerRecord:
    """Correct one of a customer's site addresses from the portal."""
    require_capability(user, "create_enquiry")
    settings = repo.get_customer_settings(user.org_id)
    record = _find_customer(settings, record_id)
    location = next((row for row in record.locations if row.id == location_id), None)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location not found: {location_id}")
    _apply_patch(location, payload)
    repo.update_customer_settings(user.org_id, settings)
    return record


@router.delete("/customers/records/{record_id}/locations/{location_id}", response_model=CustomerRecord)
def delete_customer_location(
    record_id: str, location_id: str, user: CurrentUser = Depends(get_current_user)
) -> CustomerRecord:
    """Drop a site address. Contacts pinned to it fall back to the company address."""
    require_capability(user, "create_enquiry")
    settings = repo.get_customer_settings(user.org_id)
    record = _find_customer(settings, record_id)
    if not any(row.id == location_id for row in record.locations):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location not found: {location_id}")
    record.locations = [row for row in record.locations if row.id != location_id]
    for contact in record.contacts:
        if contact.location_id == location_id:
            contact.location_id = ""
    repo.update_customer_settings(user.org_id, settings)
    return record


@router.post("/customers/records/{record_id}/contacts", response_model=CustomerRecord)
def add_customer_contact(record_id: str, payload: ContactCreate, user: CurrentUser = Depends(get_current_user)) -> CustomerRecord:
    """Append a contact person to an existing customer, allowed to anyone who can
    create enquiries (so sales can add a buyer contact while filling an enquiry)."""
    require_capability(user, "create_enquiry")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Contact name is required")
    settings = repo.get_customer_settings(user.org_id)
    record = _find_customer(settings, record_id)
    if any((contact.name or "").strip().lower() == name.lower() for contact in record.contacts):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Contact already exists: {name}")
    location_id = payload.location_id.strip()
    if location_id and not any(row.id == location_id for row in record.locations):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location not found: {location_id}")
    # A company with exactly one site leaves no choice to make — pin the new
    # person there so their address fills in without a second selection.
    if not location_id and len(record.locations) == 1:
        location_id = record.locations[0].id
    record.contacts.append(
        ContactPerson(
            id=f"{record_id}-c-{uuid.uuid4().hex[:8]}",
            name=name,
            designation=payload.designation,
            department=payload.department,
            email=payload.email,
            phone=payload.phone,
            mobile=payload.mobile,
            location_id=location_id,
        )
    )
    repo.update_customer_settings(user.org_id, settings)
    return record


@router.patch("/customers/records/{record_id}/contacts/{contact_id}", response_model=CustomerRecord)
def update_customer_contact(
    record_id: str,
    contact_id: str,
    payload: ContactUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> CustomerRecord:
    """Correct an existing contact person, including which location they sit at."""
    require_capability(user, "create_enquiry")
    settings = repo.get_customer_settings(user.org_id)
    record = _find_customer(settings, record_id)
    contact = next((row for row in record.contacts if row.id == contact_id), None)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contact not found: {contact_id}")
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Contact name is required")
        clash = any(
            row.id != contact_id and (row.name or "").strip().lower() == name.lower() for row in record.contacts
        )
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Contact already exists: {name}")
    if payload.location_id:
        if not any(row.id == payload.location_id for row in record.locations):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Location not found: {payload.location_id}"
            )
    # An explicit empty location_id clears the link, which _apply_patch already
    # does — it skips only None (the "key not sent" case).
    _apply_patch(contact, payload)
    repo.update_customer_settings(user.org_id, settings)
    return record
