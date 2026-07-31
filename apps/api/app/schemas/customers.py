from pydantic import BaseModel, Field


class CustomerLocation(BaseModel):
    """One site of a customer company.

    A company in the CRM export often spans several plants or offices, and every
    contact person sits at exactly one of them. Keeping the sites as their own
    list (instead of a single address on the company) is what lets the enquiry
    setup fill the buyer address from the chosen contact, and lets the user pick
    between sites when the contact does not pin one down.
    """

    id: str
    label: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    pin_code: str = ""
    country: str = ""
    region: str = ""
    gst_no: str = ""

    def display_label(self) -> str:
        """Human name for the site — the saved label, else its city/state/country."""
        if self.label.strip():
            return self.label.strip()
        parts = [self.city, self.state, self.country]
        return ", ".join(part.strip() for part in parts if part and part.strip())


class ContactPerson(BaseModel):
    id: str
    name: str
    designation: str = ""
    department: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    # Which of the customer's locations this person sits at. Empty means unknown,
    # in which case the enquiry setup falls back to the company's own address.
    location_id: str = ""


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
    locations: list[CustomerLocation] = Field(default_factory=list)


class CustomerSettings(BaseModel):
    customers: list[CustomerRecord] = Field(default_factory=list)
    epc_names: list[str] = Field(default_factory=list)


class EpcNameCreate(BaseModel):
    name: str


class ContactCreate(BaseModel):
    name: str
    designation: str = ""
    department: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    location_id: str = ""


class ContactUpdate(BaseModel):
    """Edit an existing contact. Only the keys sent are changed."""

    name: str | None = None
    designation: str | None = None
    department: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    location_id: str | None = None


class LocationCreate(BaseModel):
    label: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    pin_code: str = ""
    country: str = ""
    region: str = ""
    gst_no: str = ""


class LocationUpdate(BaseModel):
    """Edit an existing location. Only the keys sent are changed."""

    label: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    pin_code: str | None = None
    country: str | None = None
    region: str | None = None
    gst_no: str | None = None


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


class CustomerUpdate(BaseModel):
    """Edit the company header of an existing customer. Only the keys sent are changed."""

    name: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    pin_code: str | None = None
    country: str | None = None
    gst_no: str | None = None
    default_currency: str | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
