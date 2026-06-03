from pydantic import BaseModel, Field


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


class CustomerSettings(BaseModel):
    customers: list[CustomerRecord] = Field(default_factory=list)
    epc_names: list[str] = Field(default_factory=list)
