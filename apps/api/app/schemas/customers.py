from pydantic import BaseModel, Field


class ContactPerson(BaseModel):
    id: str
    name: str
    designation: str = ""
    department: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""


class CustomerRecord(BaseModel):
    id: str
    name: str
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    pin_code: str = ""
    country: str = ""
    contact_name: str = ""
    designation: str = ""
    email: str = ""
    phone: str = ""
    gst_no: str = ""
    default_currency: str = "INR"
    payment_terms: str = ""
    delivery_terms: str = ""
    active: bool = True
    contacts: list[ContactPerson] = Field(default_factory=list)


class CustomerSettings(BaseModel):
    customers: list[CustomerRecord] = Field(default_factory=list)
    epc_names: list[str] = Field(default_factory=list)


class ContactCreate(BaseModel):
    name: str
    designation: str = ""
    department: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""


class CustomerCreate(BaseModel):
    name: str
    address_line1: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    gst_no: str = ""
    contact_name: str = ""
    designation: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
