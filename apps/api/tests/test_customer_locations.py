"""Customer sites: a company can have several, and the portal can correct them.

One company in the CRM export routinely spans several plants (L&T alone has a
dozen), and every contact person sits at one of them. These tests pin the two
behaviours the enquiry setup depends on: a contact carries its own location so
picking the person settles the address, and the saved details can be edited from
the portal instead of only by re-importing the workbook.
"""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.main import app

# The seeded local admin — creating and correcting customers is open to anyone
# with create_enquiry, which admin always has.
ADMIN = "shashnam@flosil.com"


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def org():
    return f"org-loc-{uuid.uuid4().hex}"


def _headers(org: str, user: str = ADMIN) -> dict:
    return {"X-Org-Id": org, "X-User-Id": user}


def _new_customer(client, org, **kwargs) -> dict:
    payload = {"name": kwargs.pop("name", "Toyo Engineering India Pvt Ltd"), **kwargs}
    response = client.post("/api/v1/customers/records", headers=_headers(org), json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_new_customer_address_becomes_its_first_location(client, org):
    record = _new_customer(client, org, city="Mumbai", state="Maharashtra", country="India", contact_name="A Rao")
    assert len(record["locations"]) == 1
    location = record["locations"][0]
    assert (location["city"], location["state"], location["country"]) == ("Mumbai", "Maharashtra", "India")
    # The sole contact is pinned there, so the enquiry setup fills the address
    # from the person without a second selection.
    assert record["contacts"][0]["location_id"] == location["id"]


def test_customer_without_an_address_gets_no_phantom_location(client, org):
    record = _new_customer(client, org, name="Unknown Address Ltd", contact_name="B Rao")
    assert record["locations"] == []
    assert record["contacts"][0]["location_id"] == ""


def test_multi_site_company_keeps_each_site_and_pins_contacts(client, org):
    record = _new_customer(client, org, city="Mumbai", state="Maharashtra", country="India")
    customer_id = record["id"]

    response = client.post(
        f"/api/v1/customers/records/{customer_id}/locations",
        headers=_headers(org),
        json={"city": "Ernakulam", "state": "Kerala", "country": "India", "address_line1": "Refinery Road"},
    )
    assert response.status_code == 200, response.text
    record = response.json()
    assert len(record["locations"]) == 2
    ernakulam = record["locations"][1]

    # A second site means the choice is real, so a new contact is not silently
    # pinned to either one unless the caller says which.
    response = client.post(
        f"/api/v1/customers/records/{customer_id}/contacts",
        headers=_headers(org),
        json={"name": "C Nair", "email": "c.nair@example.com"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["contacts"][-1]["location_id"] == ""

    response = client.post(
        f"/api/v1/customers/records/{customer_id}/contacts",
        headers=_headers(org),
        json={"name": "D Menon", "location_id": ernakulam["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["contacts"][-1]["location_id"] == ernakulam["id"]


def test_single_site_company_pins_a_new_contact_automatically(client, org):
    record = _new_customer(client, org, city="Chennai", state="Tamil Nadu", country="India")
    response = client.post(
        f"/api/v1/customers/records/{record['id']}/contacts",
        headers=_headers(org),
        json={"name": "E Kumar"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["contacts"][-1]["location_id"] == record["locations"][0]["id"]


def test_contact_cannot_be_pinned_to_a_site_of_another_company(client, org):
    record = _new_customer(client, org, city="Chennai", country="India")
    response = client.post(
        f"/api/v1/customers/records/{record['id']}/contacts",
        headers=_headers(org),
        json={"name": "F Singh", "location_id": "cust-other-l1"},
    )
    assert response.status_code == 404, response.text


def test_location_needs_a_label_or_a_place(client, org):
    record = _new_customer(client, org, city="Chennai", country="India")
    response = client.post(
        f"/api/v1/customers/records/{record['id']}/locations",
        headers=_headers(org),
        json={"pin_code": "600032"},
    )
    assert response.status_code == 422, response.text


def test_editing_a_location_from_the_portal_persists(client, org):
    record = _new_customer(client, org, city="Hazira", state="Gujrat", country="India")
    location_id = record["locations"][0]["id"]
    response = client.patch(
        f"/api/v1/customers/records/{record['id']}/locations/{location_id}",
        headers=_headers(org),
        json={"state": "Gujarat", "pin_code": "394510", "label": "Hazira Works"},
    )
    assert response.status_code == 200, response.text
    location = next(row for row in response.json()["locations"] if row["id"] == location_id)
    assert (location["state"], location["pin_code"], location["label"]) == ("Gujarat", "394510", "Hazira Works")

    reread = client.get("/api/v1/customers", headers=_headers(org)).json()
    stored = next(row for row in reread["customers"] if row["id"] == record["id"])
    # A PATCH sends only the corrected keys — the rest of the site must survive.
    assert next(row for row in stored["locations"] if row["id"] == location_id)["city"] == "Hazira"
    assert next(row for row in stored["locations"] if row["id"] == location_id)["state"] == "Gujarat"


def test_editing_a_contact_can_move_them_to_another_site(client, org):
    record = _new_customer(client, org, city="Mumbai", country="India", contact_name="G Iyer")
    customer_id = record["id"]
    contact_id = record["contacts"][0]["id"]
    added = client.post(
        f"/api/v1/customers/records/{customer_id}/locations",
        headers=_headers(org),
        json={"city": "Vadodara", "state": "Gujarat", "country": "India"},
    ).json()
    vadodara = added["locations"][1]["id"]

    response = client.patch(
        f"/api/v1/customers/records/{customer_id}/contacts/{contact_id}",
        headers=_headers(org),
        json={"email": "g.iyer@example.com", "location_id": vadodara},
    )
    assert response.status_code == 200, response.text
    contact = next(row for row in response.json()["contacts"] if row["id"] == contact_id)
    assert contact["location_id"] == vadodara
    assert contact["email"] == "g.iyer@example.com"
    assert contact["name"] == "G Iyer"


def test_editing_the_company_header_rejects_a_duplicate_name(client, org):
    first = _new_customer(client, org, name="Alpha Engineering")
    _new_customer(client, org, name="Beta Engineering")
    response = client.patch(
        f"/api/v1/customers/records/{first['id']}",
        headers=_headers(org),
        json={"name": "beta engineering"},
    )
    assert response.status_code == 409, response.text


def test_editing_the_company_header_persists_the_corrections(client, org):
    record = _new_customer(client, org, name="Gamma Engineering", city="Pune", country="India")
    response = client.patch(
        f"/api/v1/customers/records/{record['id']}",
        headers=_headers(org),
        json={"gst_no": "27AAACG1234A1Z5", "payment_terms": "30 days"},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["gst_no"] == "27AAACG1234A1Z5"
    assert updated["payment_terms"] == "30 days"
    # Untouched keys are left alone, and the location list is not disturbed.
    assert updated["name"] == "Gamma Engineering"
    assert len(updated["locations"]) == 1


def test_deleting_a_site_releases_the_contacts_pinned_to_it(client, org):
    record = _new_customer(client, org, city="Kolkata", country="India", contact_name="H Das")
    customer_id = record["id"]
    location_id = record["locations"][0]["id"]
    assert record["contacts"][0]["location_id"] == location_id

    response = client.delete(
        f"/api/v1/customers/records/{customer_id}/locations/{location_id}", headers=_headers(org)
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["locations"] == []
    assert updated["contacts"][0]["location_id"] == ""


def test_unknown_customer_and_location_ids_are_reported(client, org):
    record = _new_customer(client, org, city="Delhi", country="India")
    assert client.patch("/api/v1/customers/records/cust-nope", headers=_headers(org), json={"gst_no": "x"}).status_code == 404
    missing = client.patch(
        f"/api/v1/customers/records/{record['id']}/locations/loc-nope",
        headers=_headers(org),
        json={"city": "Delhi"},
    )
    assert missing.status_code == 404, missing.text
