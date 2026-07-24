"""The enquiry register: an Excel sheet of every enquiry whose quotation has
been generated, downloadable by any colleague from the portal."""

import io
import sys
import uuid
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.main import app


def _shared_strings(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return archive.read("xl/sharedStrings.xml").decode("utf-8")


def test_enquiry_register_lists_only_quoted_enquiries():
    client = TestClient(app)
    org_id = f"org-register-{uuid.uuid4().hex}"
    headers = {"X-Org-Id": org_id, "X-User-Id": "shashnam@flosil.com"}

    quoted = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "customer": "Register Quoted Co",
            "project_ref": "Register Refinery Expansion",
            "items": [{"line_no": 1, "quantity": 3, "raw_description": "gasket", "status": "ready"}],
            "quote_data": {"attention": "Priya Menon", "email": "priya@example.com", "unit_prices": [50]},
            "stage_meta": {
                "market_type": "export",
                "bid_type": "firm",
                "epc_name": "Register EPC Ltd",
                "country": "India",
                "city": "Chennai",
                "owner_name": "Register Sales Rep",
            },
        },
    )
    assert quoted.status_code == 201
    enquiry_id = quoted.json()["id"]

    draft = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={"customer": "Register DraftOnly Co", "project_ref": "P-draft", "items": []},
    )
    assert draft.status_code == 201

    # Legacy flow: creating a quotation record from the enquiry links the two
    # and marks the enquiry as quoted.
    quotation = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "customer": "Register Quoted Co",
            "project_ref": "Register Refinery Expansion",
            "stage": "quote_prep",
            "items": [{"line_no": 1, "quantity": 3, "raw_description": "gasket", "status": "ready"}],
            "quote_data": {"quote_no": "QT-REG-1", "currency": "USD", "unit_prices": [50]},
            "stage_meta": {"source_enquiry_id": enquiry_id},
        },
    )
    assert quotation.status_code == 201

    exported = client.post("/api/v1/quotes/exports/enquiry-register", headers=headers)
    assert exported.status_code == 200
    body = exported.json()
    assert body["filename"] == "Enquiry Register.xlsx"

    downloaded = client.get(body["signed_url"])
    assert downloaded.status_code == 200
    strings = _shared_strings(downloaded.content)
    assert "Register Quoted Co" in strings
    assert "Register Refinery Expansion" in strings
    assert "Register EPC Ltd" in strings
    assert "Register Sales Rep" in strings
    assert "Export" in strings  # market type, title-cased
    assert "QT-REG-1" in strings  # quotation ref from the linked record
    assert "Register DraftOnly Co" not in strings  # no quotation generated yet


def test_enquiry_detail_workbook_and_drive_package(tmp_path, monkeypatch):
    client = TestClient(app)
    org_id = f"org-register-{uuid.uuid4().hex}"
    headers = {"X-Org-Id": org_id, "X-User-Id": "shashnam@flosil.com"}

    created = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "customer": "Detail Test Co",
            "project_ref": "Detail Pipeline Project",
            "items": [
                {
                    "line_no": 1,
                    "quantity": 4,
                    "uom": "NOS",
                    "raw_description": '2" 300# SW gasket',
                    "ggpl_description": "SPIRAL WOUND GASKET 2IN 300LB",
                    "gasket_type": "SPIRAL_WOUND",
                    "size": '2"',
                    "rating": "300#",
                    "moc": "SS316",
                    "status": "ready",
                }
            ],
            "quote_data": {"attention": "Detail Contact", "unit_prices": [125.5], "currency": "INR"},
            "stage_meta": {"market_type": "domestic", "epc_name": "Detail EPC", "owner_name": "Detail Rep"},
        },
    )
    assert created.status_code == 201
    enquiry_id = created.json()["id"]

    # The detail workbook carries the context fields and every line item.
    from app.schemas.quotes import QuoteRead
    from app.services.enquiry_register import build_enquiry_detail_xlsx

    quote = QuoteRead(**client.get(f"/api/v1/quotes/{enquiry_id}", headers=headers).json())
    detail = build_enquiry_detail_xlsx(quote)
    strings = _shared_strings(detail)
    for expected in ["Detail Test Co", "Detail Pipeline Project", "Detail EPC", "Detail Rep", "SPIRAL WOUND GASKET 2IN 300LB"]:
        assert expected in strings
    with zipfile.ZipFile(io.BytesIO(detail)) as archive:
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
    for sheet in ["Enquiry", "Line Items", "Workflow History"]:
        assert sheet in workbook_xml

    # Drive folder mode: the package writes one folder per enquiry with the
    # details workbook inside (no quotation Excel yet — nothing generated).
    monkeypatch.setenv("GDRIVE_EXPORT_ENABLED", "true")
    monkeypatch.setenv("GDRIVE_LOCAL_DIR", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        from app.services.gdrive_export import export_enquiry_package

        folder = export_enquiry_package(quote)
        assert folder == f"{quote.quote_no} - Detail Test Co"
        assert (tmp_path / folder / "Enquiry Details.xlsx").exists()
        assert not list((tmp_path / folder).glob("Quotation*.xlsx"))
    finally:
        get_settings.cache_clear()


def test_enquiry_register_requires_a_read_capability():
    client = TestClient(app)
    org_id = f"org-register-{uuid.uuid4().hex}"
    admin = {"X-Org-Id": org_id, "X-User-Id": "shashnam@flosil.com"}
    viewer = client.post(
        "/api/v1/users",
        headers=admin,
        json={"user_id": "reg-viewer", "name": "Register Viewer", "email": "reg-viewer@example.com", "role": "viewer"},
    )
    assert viewer.status_code in {200, 201}

    response = client.post(
        "/api/v1/quotes/exports/enquiry-register",
        headers={"X-Org-Id": org_id, "X-User-Id": "reg-viewer"},
    )
    # Viewers hold view_enquiry, so even the most restricted role can download.
    assert response.status_code == 200
