"""Rule L end to end: a correction the team makes once is applied from then on.

Covers the two ways the portal learns — automatic capture from a line edit, and
an explicit save into permanent memory — plus who is allowed to curate what.
"""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.main import app
from app.services import description_memory as memory

CUSTOMER_WORDING = 'GASKET 2" 150# SPIRAL WOUND SS316 GRAPHITE CS OUTER RING'
TEAM_ANSWER = 'SIZE : 2" X 150# X 4.5MM THK ,SS316 + GRAPHITE WITH CS OUTER RING ,ASME B16.20'

ADMIN = "shashnam@flosil.com"
ESTIMATION = "estimation@flosil.com"


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def org():
    """A fresh org per test so learned entries never leak between cases."""
    return f"org-learn-{uuid.uuid4().hex}"


def _headers(org: str, user: str = ADMIN) -> dict:
    return {"X-Org-Id": org, "X-User-Id": user}


def _new_quote(client, org, *, user: str = ADMIN, customer: str = "Toyo Engineering", items=None) -> dict:
    response = client.post(
        "/api/v1/quotes",
        headers=_headers(org, user),
        json={"customer": customer, "project_ref": "P-learn", "items": items or []},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _recompute(client, org, rows, *, user: str = ADMIN, customer: str = "Toyo Engineering") -> list[dict]:
    quote = _new_quote(client, org, user=user, customer=customer)
    response = client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk-recompute",
        headers=_headers(org, user),
        json={"rows": rows},
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- learning from a team edit ---------------------------------------------

def test_a_corrected_description_is_reused_on_the_next_enquiry(client, org):
    """The whole point: fix it once, and the portal answers the same next time."""
    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    engine_answer = quote["items"][0].get("ggpl_description", "")

    saved = client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"ggpl_description": TEAM_ANSWER}}],
            "expected_version": quote["version"],
        },
    )
    assert saved.status_code == 200, saved.text

    # A brand new enquiry carrying the same customer wording.
    recomputed = _recompute(client, org, [{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    assert recomputed[0]["ggpl_description"] == TEAM_ANSWER
    assert recomputed[0]["ggpl_description"] != engine_answer
    assert recomputed[0]["learned_from"]["match"] == "exact"


def test_the_capture_lands_in_the_pending_queue_for_review(client, org):
    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"ggpl_description": TEAM_ANSWER}}],
            "expected_version": quote["version"],
        },
    )
    listed = client.get("/api/v1/learned-descriptions", headers=_headers(org))
    assert listed.status_code == 200, listed.text
    entries = listed.json()
    assert len(entries) == 1
    assert entries[0]["status"] == "pending"
    assert entries[0]["source"] == "edit"
    assert entries[0]["ggpl_description"] == TEAM_ANSWER


def test_a_quantity_edit_teaches_the_portal_nothing(client, org):
    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING, "quantity": 2}])
    client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"quantity": 40}}],
            "expected_version": quote["version"],
        },
    )
    assert client.get("/api/v1/learned-descriptions", headers=_headers(org)).json() == []


def test_learning_survives_a_recompute(client, org):
    """A recompute re-derives everything from the raw text; without memory it
    would silently undo the team's correction."""
    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"ggpl_description": TEAM_ANSWER}}],
            "expected_version": quote["version"],
        },
    )
    current = client.get(f"/api/v1/quotes/{quote['id']}", headers=_headers(org)).json()
    recomputed = client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk-recompute",
        headers=_headers(org),
        json={"indices": [0], "expected_version": current["version"]},
    )
    assert recomputed.status_code == 200, recomputed.text
    assert recomputed.json()[0]["ggpl_description"] == TEAM_ANSWER


# --- teaching a brand new description on purpose ---------------------------

def test_estimation_can_save_a_new_gasket_description_permanently(client, org):
    """A gasket the engine has no format for: estimation types the wording once
    and saves it, and the portal answers it from then on."""
    wording = "ODM 1200 X IDM 1150 X 3MM THK, PTFE ENVELOPE WITH CNAF INSERT, RAISED FACE"
    house_answer = "SIZE : 1200MM OD X 1150MM ID X 3MM THK ,PTFE ENVELOPE WITH CNAF INSERT ,RF"

    created = client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org, ESTIMATION),
        json={"source_text": wording, "ggpl_description": house_answer, "approve": True},
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "approved"
    assert created.json()["source"] == "manual"

    recomputed = _recompute(client, org, [{"line_no": 1, "raw_description": wording}], user=ESTIMATION)
    assert recomputed[0]["ggpl_description"] == house_answer


def test_teaching_from_a_quote_row_carries_the_classified_construction(client, org):
    """Saving off the row the operator just fixed also stores the fields, so the
    learned row prices and plans correctly — not just displays correctly."""
    quote = _new_quote(
        client,
        org,
        items=[{
            "line_no": 1,
            "raw_description": CUSTOMER_WORDING,
            "ggpl_description": TEAM_ANSWER,
            "gasket_type": "SPIRAL_WOUND",
            "sw_winding_material": "SS316",
            "sw_outer_ring": "CS",
            "quantity": 40,
        }],
    )
    created = client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={"quote_id": quote["id"], "item_index": 0, "approve": True},
    )
    assert created.status_code == 201, created.text
    entry = created.json()
    assert entry["fields"]["gasket_type"] == "SPIRAL_WOUND"
    assert entry["fields"]["sw_outer_ring"] == "CS"
    # Commercial columns are per-enquiry facts, never knowledge.
    assert "quantity" not in entry["fields"]

    recomputed = _recompute(client, org, [{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    assert recomputed[0]["gasket_type"] == "SPIRAL_WOUND"
    assert recomputed[0]["sw_outer_ring"] == "CS"


def test_teaching_needs_something_to_remember(client, org):
    response = client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={"source_text": CUSTOMER_WORDING},
    )
    assert response.status_code == 400


def test_an_entry_scoped_to_one_customer_does_not_answer_for_another(client, org):
    client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={
            "source_text": CUSTOMER_WORDING,
            "ggpl_description": TEAM_ANSWER,
            "customer": "Toyo Engineering",
            "approve": True,
        },
    )
    rows = [{"line_no": 1, "raw_description": CUSTOMER_WORDING}]
    assert _recompute(client, org, rows, customer="Toyo Engineering")[0]["ggpl_description"] == TEAM_ANSWER
    assert _recompute(client, org, rows, customer="HSEPL")[0]["ggpl_description"] != TEAM_ANSWER


# --- curation ---------------------------------------------------------------

def test_approving_a_capture_promotes_it_to_permanent_memory(client, org):
    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"ggpl_description": TEAM_ANSWER}}],
            "expected_version": quote["version"],
        },
    )
    entry_id = client.get("/api/v1/learned-descriptions", headers=_headers(org)).json()[0]["id"]
    approved = client.post(f"/api/v1/learned-descriptions/{entry_id}/approve", headers=_headers(org))
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_by"]

    recomputed = _recompute(client, org, [{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    flags = " | ".join(str(flag) for flag in recomputed[0].get("flags") or [])
    assert "NOT YET APPROVED" not in flags
    assert recomputed[0]["learned_from"]["status"] == "approved"


def test_a_rejected_entry_stops_being_applied(client, org):
    created = client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={"source_text": CUSTOMER_WORDING, "ggpl_description": TEAM_ANSWER, "approve": True},
    ).json()
    rejected = client.post(f"/api/v1/learned-descriptions/{created['id']}/reject", headers=_headers(org))
    assert rejected.status_code == 200, rejected.text

    recomputed = _recompute(client, org, [{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    assert recomputed[0]["ggpl_description"] != TEAM_ANSWER


def test_sales_cannot_curate_but_can_still_contribute(client, org):
    """Sales edits line items, so its corrections are worth capturing — but
    promoting one into permanent portal-wide law is not its call."""
    contributed = client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org, "sales@flosil.com"),
        json={"source_text": CUSTOMER_WORDING, "ggpl_description": TEAM_ANSWER, "approve": True},
    )
    assert contributed.status_code == 201, contributed.text
    # `approve` was requested but silently downgraded: the capability is missing.
    assert contributed.json()["status"] == "pending"

    entry_id = contributed.json()["id"]
    denied = client.post(
        f"/api/v1/learned-descriptions/{entry_id}/approve",
        headers=_headers(org, "sales@flosil.com"),
    )
    assert denied.status_code == 403

    assert client.delete(
        f"/api/v1/learned-descriptions/{entry_id}",
        headers=_headers(org, "sales@flosil.com"),
    ).status_code == 403


def test_re_teaching_a_wording_replaces_the_entry_instead_of_duplicating_it(client, org):
    for answer in (TEAM_ANSWER, "SIZE : 2\" X 150# X 3MM THK ,SS316 + GRAPHITE ,ASME B16.20"):
        client.post(
            "/api/v1/learned-descriptions",
            headers=_headers(org),
            json={"source_text": CUSTOMER_WORDING, "ggpl_description": answer, "approve": True},
        )
    entries = client.get("/api/v1/learned-descriptions", headers=_headers(org)).json()
    assert len(entries) == 1
    assert entries[0]["ggpl_description"].endswith("3MM THK ,SS316 + GRAPHITE ,ASME B16.20")


def test_a_later_edit_cannot_demote_an_approved_rule(client, org):
    """An operator's incidental re-save must not knock a curated rule back into
    the pending queue."""
    client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={"source_text": CUSTOMER_WORDING, "ggpl_description": TEAM_ANSWER, "approve": True},
    )
    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"ggpl_description": "OPERATOR TWEAK"}}],
            "expected_version": quote["version"],
        },
    )
    entries = client.get("/api/v1/learned-descriptions", headers=_headers(org)).json()
    assert len(entries) == 1
    assert entries[0]["status"] == "approved"


def test_a_curators_note_survives_a_later_capture_of_the_same_wording(client, org):
    """The note explains why a rule exists — it is the curator's field. An
    operator's later correction updates the description but must not erase it."""
    created = client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={
            "source_text": CUSTOMER_WORDING,
            "ggpl_description": TEAM_ANSWER,
            "note": "Confirmed with Ashwin sir",
            "approve": True,
        },
    ).json()
    assert created["note"] == "Confirmed with Ashwin sir"

    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"ggpl_description": "OPERATOR TWEAK"}}],
            "expected_version": quote["version"],
        },
    )
    entries = client.get("/api/v1/learned-descriptions", headers=_headers(org)).json()
    assert len(entries) == 1
    assert entries[0]["note"] == "Confirmed with Ashwin sir"
    assert entries[0]["ggpl_description"] == "OPERATOR TWEAK"


def test_turning_auto_capture_off_stops_the_portal_learning_silently(client, org):
    updated = client.put(
        "/api/v1/learning-settings",
        headers=_headers(org),
        json={"auto_capture": False},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["auto_capture"] is False

    quote = _new_quote(client, org, items=[{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    client.post(
        f"/api/v1/quotes/{quote['id']}/items/bulk",
        headers=_headers(org),
        json={
            "patches": [{"index": 0, "values": {"ggpl_description": TEAM_ANSWER}}],
            "expected_version": quote["version"],
        },
    )
    assert client.get("/api/v1/learned-descriptions", headers=_headers(org)).json() == []


def test_lookup_reports_what_memory_holds_for_a_wording(client, org):
    client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={"source_text": CUSTOMER_WORDING, "ggpl_description": TEAM_ANSWER, "approve": True},
    )
    hit = client.post(
        "/api/v1/learned-descriptions/lookup",
        headers=_headers(org),
        json={"source_text": CUSTOMER_WORDING.lower()},
    ).json()
    assert hit["matched"] and hit["kind"] == "exact"
    assert hit["entry"]["ggpl_description"] == TEAM_ANSWER

    miss = client.post(
        "/api/v1/learned-descriptions/lookup",
        headers=_headers(org),
        json={"source_text": '6" 300# CNAF 3MM GASKET'},
    ).json()
    assert not miss["matched"]


def test_learned_entries_do_not_leak_between_orgs(client, org):
    other_org = f"org-learn-{uuid.uuid4().hex}"
    client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={"source_text": CUSTOMER_WORDING, "ggpl_description": TEAM_ANSWER, "approve": True},
    )
    assert client.get("/api/v1/learned-descriptions", headers=_headers(other_org)).json() == []
    recomputed = _recompute(client, other_org, [{"line_no": 1, "raw_description": CUSTOMER_WORDING}])
    assert recomputed[0]["ggpl_description"] != TEAM_ANSWER


def test_the_index_cache_is_invalidated_when_an_entry_changes(client, org):
    """Guards the cache: an approve/reject must take effect on the next lookup,
    not after a restart."""
    created = client.post(
        "/api/v1/learned-descriptions",
        headers=_headers(org),
        json={"source_text": CUSTOMER_WORDING, "ggpl_description": TEAM_ANSWER, "approve": True},
    ).json()
    assert memory.memory_for(org).resolve(CUSTOMER_WORDING) is not None
    client.delete(f"/api/v1/learned-descriptions/{created['id']}", headers=_headers(org))
    assert memory.memory_for(org).resolve(CUSTOMER_WORDING) is None
