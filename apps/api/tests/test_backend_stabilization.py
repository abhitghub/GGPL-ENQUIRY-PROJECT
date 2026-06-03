from __future__ import annotations

import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.db import repo
from app.main import app
from app.schemas.quotes import QuotePatch


client = TestClient(app)


def headers(org_id: str, user_id: str) -> dict[str, str]:
    return {"X-Org-Id": org_id, "X-User-Id": user_id}


def create_user(org_id: str, admin_headers: dict[str, str], *, name: str, role: str) -> str:
    email = f"{name.lower()}-{uuid.uuid4().hex}@example.com"
    response = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"name": name, "email": email, "role": role, "active": True},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_assignment_visibility_inheritance_and_legacy_owner_matching():
    org_id = f"org-assignment-{uuid.uuid4().hex}"
    admin_headers = headers(org_id, "shashnam@flosil.com")
    estimator_id = create_user(org_id, admin_headers, name="Estimator", role="estimation")
    other_id = create_user(org_id, admin_headers, name="Other Estimator", role="estimation")

    created = client.post(
        "/api/v1/quotes",
        headers=headers(org_id, estimator_id),
        json={"customer": "Owned customer", "items": [], "stage_meta": {}},
    )
    assert created.status_code == 201
    assert created.json()["stage_meta"]["owner_id"] == estimator_id
    quote_id = created.json()["id"]
    assert client.get(f"/api/v1/quotes/{quote_id}", headers=headers(org_id, other_id)).status_code == 404

    assigned = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=admin_headers,
        json={
            "stage_meta": {
                **created.json()["stage_meta"],
                "owner_id": other_id,
                "owner_name": "Other Estimator",
                "owner_email": other_id,
            },
        },
    )
    assert assigned.status_code == 200
    assert assigned.json()["stage_meta"]["owner_id"] == other_id
    assert assigned.json()["stage_meta"]["activity_log"][0]["title"] == "Assignment updated"

    linked = client.post(
        "/api/v1/quotes",
        headers=admin_headers,
        json={
            "customer": "Linked quotation",
            "stage": "quote_prep",
            "items": [],
            "stage_meta": {"source_enquiry_id": quote_id},
        },
    )
    assert linked.status_code == 201
    assert linked.json()["stage_meta"]["owner_id"] == other_id
    assert linked.json()["stage_meta"]["opportunity_id"] == quote_id

    repo.update_quote(
        org_id,
        quote_id,
        QuotePatch(stage_meta={**assigned.json()["stage_meta"], "owner_id": "", "owner_name": "Other Estimator", "owner_email": other_id}),
    )
    legacy_visible = client.get(f"/api/v1/quotes/{quote_id}", headers=headers(org_id, other_id))
    assert legacy_visible.status_code == 200


def test_summary_patch_authorization_staleness_conflicts_and_search():
    org_id = f"org-stabilization-{uuid.uuid4().hex}"
    admin_headers = headers(org_id, "shashnam@flosil.com")
    sales_id = create_user(org_id, admin_headers, name="Sales", role="sales")
    estimator_id = create_user(org_id, admin_headers, name="Estimator", role="estimation")
    sales_headers = headers(org_id, sales_id)
    estimator_headers = headers(org_id, estimator_id)
    item = {
        "line_no": 1,
        "quantity": 2,
        "status": "missing",
        "clarification_note": "Confirm size",
        "raw_description": "Custom ASME DIN gasket",
        "gasket_type": "",
    }
    created = client.post(
        "/api/v1/quotes",
        headers=estimator_headers,
        json={
            "customer": "Searchable ACME",
            "project_ref": "PROJECT-X",
            "items": [item],
            "quote_data": {"unit_prices": [250]},
            "stage_meta": {
                "material_breakdown": [{"type": "sheet"}],
                "material_plan": {"rows": []},
                "material_plan_status": "draft",
                "clarification_status": "requested",
            },
        },
    )
    assert created.status_code == 201
    quote_id = created.json()["id"]

    assigned_to_sales = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=admin_headers,
        json={"stage_meta": {**created.json()["stage_meta"], "owner_id": sales_id}},
    )
    assert assigned_to_sales.status_code == 200
    denied_items = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=sales_headers,
        json={"items": [{**item, "quantity": 4}]},
    )
    assert denied_items.status_code == 403
    allowed_sales = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=sales_headers,
        json={"customer": "Searchable customer"},
    )
    assert allowed_sales.status_code == 200
    stale_version = allowed_sales.json()["version"]
    conflict = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=sales_headers,
        json={"customer": "Old write", "expected_version": stale_version - 1},
    )
    assert conflict.status_code == 409

    reassigned = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=admin_headers,
        json={"stage_meta": {**allowed_sales.json()["stage_meta"], "owner_id": estimator_id}},
    )
    assert reassigned.status_code == 200
    changed_items = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=estimator_headers,
        json={"items": [{**item, "quantity": 4}]},
    )
    assert changed_items.status_code == 200
    assert changed_items.json()["stage_meta"]["material_plan_stale"] is True
    assert changed_items.json()["stage_meta"]["extraction_summary"]["source_quote_version"] == changed_items.json()["version"]

    summary = client.get("/api/v1/quotes?summary=true", headers=estimator_headers)
    assert summary.status_code == 200
    row = next(row for row in summary.json() if row["id"] == quote_id)
    assert row["items"] == []
    assert row["estimated_quote_value"] == 1000
    assert row["high_risk_count"] > 0
    assert row["has_clarification"] is True
    assert row["next_action"] == "Follow up customer"

    visible_search = client.get("/api/v1/quotes/search?q=searchable&limit=1", headers=estimator_headers)
    assert visible_search.status_code == 200
    assert [row["id"] for row in visible_search.json()] == [quote_id]
    assert client.get("/api/v1/quotes/search?q=searchable&limit=51", headers=estimator_headers).status_code == 422
    assert client.get("/api/v1/quotes/search?q=searchable", headers=sales_headers).json() == []


def test_linked_delete_transition_job_visibility_and_dashboard_grouping():
    org_id = f"org-linked-{uuid.uuid4().hex}"
    admin_headers = headers(org_id, "shashnam@flosil.com")
    estimator_id = create_user(org_id, admin_headers, name="Estimator", role="estimation")
    other_id = create_user(org_id, admin_headers, name="Other", role="estimation")
    estimator_headers = headers(org_id, estimator_id)
    item = {"line_no": 1, "quantity": 1, "status": "ready", "gasket_type": "SOFT_CUT", "size": '4"', "moc": "CNAF"}
    source = client.post(
        "/api/v1/quotes",
        headers=estimator_headers,
        json={"customer": "Opportunity", "items": [item], "stage_meta": {}},
    ).json()
    invalid_transition = client.post(
        f"/api/v1/quotes/{source['id']}/stage",
        headers=admin_headers,
        json={"stage": "quote_prep"},
    )
    assert invalid_transition.status_code == 409

    linked = client.post(
        "/api/v1/quotes",
        headers=estimator_headers,
        json={
            "customer": "Opportunity quotation",
            "stage": "quote_prep",
            "items": [item],
            "quote_data": {"unit_prices": [100]},
            "stage_meta": {"source_enquiry_id": source["id"]},
        },
    ).json()
    automatically_linked_source = client.get(f"/api/v1/quotes/{source['id']}", headers=estimator_headers)
    assert automatically_linked_source.status_code == 200
    assert automatically_linked_source.json()["stage_meta"]["linked_quote_id"] == linked["id"]
    linked_source = client.patch(
        f"/api/v1/quotes/{source['id']}",
        headers=admin_headers,
        json={"stage_meta": {**source["stage_meta"], "linked_quote_id": linked["id"]}},
    )
    assert linked_source.status_code == 200
    assert client.delete(f"/api/v1/quotes/{source['id']}", headers=admin_headers).status_code == 409
    duplicate_number = client.patch(
        f"/api/v1/quotes/{linked['id']}",
        headers=estimator_headers,
        json={"quote_no": source["quote_no"]},
    )
    assert duplicate_number.status_code == 409

    job = repo.create_job(org_id, "email", quote_id=source["id"], created_by=estimator_id)
    assert client.get(f"/api/v1/jobs/{job.id}/status", headers=estimator_headers).status_code == 200
    assert client.get(f"/api/v1/jobs/{job.id}/status", headers=headers(org_id, other_id)).status_code == 404

    metrics = client.get("/api/v1/dashboard/metrics", headers=estimator_headers)
    assert metrics.status_code == 200
    assert metrics.json()["total_quotes"] == 1
    assert metrics.json()["items_processed"] == 1


def test_business_master_data_is_admin_managed_and_readable():
    org_id = f"org-master-{uuid.uuid4().hex}"
    admin_headers = headers(org_id, "shashnam@flosil.com")
    estimator_id = create_user(org_id, admin_headers, name="Estimator", role="estimation")
    estimator_headers = headers(org_id, estimator_id)
    payload = {
        "customers": [
            {
                "id": "acme",
                "name": "ACME",
                "city": "Mumbai",
                "country": "India",
                "contact_name": "Buyer",
                "email": "buyer@example.com",
                "default_currency": "INR",
                "payment_terms": "30 days",
            },
        ],
        "epc_names": ["Example EPC"],
    }
    assert client.put("/api/v1/customers", headers=estimator_headers, json=payload).status_code == 403
    saved = client.put("/api/v1/customers", headers=admin_headers, json=payload)
    assert saved.status_code == 200
    restored = client.get("/api/v1/customers", headers=estimator_headers)
    assert restored.status_code == 200
    assert restored.json()["customers"][0]["name"] == "ACME"
    assert restored.json()["epc_names"] == ["Example EPC"]
