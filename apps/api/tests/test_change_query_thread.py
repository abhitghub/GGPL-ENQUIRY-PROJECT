"""Change queries are a two-way thread, not a one-way instruction.

When management raises a query on an enquiry ("please check column 11 and 12,
wrong spec"), the team it was sent to must be able to answer on that same query.
A reply is conversation only: it appends to the query's history and never
changes the query's status or moves the enquiry.

Auth is via X-Org-Id / X-User-Id headers (LOGIN_ENABLED=false, set in conftest).
Seeded users used here: shashnam (admin), jagadeeshan (management),
estimation (estimation).
"""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def granular(monkeypatch):
    monkeypatch.setenv("ENABLE_GRANULAR_WORKFLOW", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("ENABLE_GRANULAR_WORKFLOW", raising=False)
    get_settings.cache_clear()


def _headers(org: str, user_id: str) -> dict:
    return {"X-Org-Id": org, "X-User-Id": user_id}


def _enquiry_at_spec_check(client: TestClient, org: str) -> str:
    # A complete enquiry header: an enquiry with a blank in it cannot leave the
    # first step (see REQUIRED_ENQUIRY_DETAILS in app/services/enquiry_workflow.py).
    created = client.post(
        "/api/v1/quotes",
        headers=_headers(org, "estimation"),
        json={
            "customer": "ACME",
            "project_ref": "P-Q1",
            "custom_label": "RFQ - P-Q1",
            "items": [{"raw_description": "SPW 6IN 150# CS/GRAPHITE", "quantity": 4}],
            "quote_data": {"attention": "R Kumar", "email": "rkumar@acme.test", "contact_no": "+91 90000 00000"},
            "stage_meta": {
                "owner_id": "sales",
                "market_type": "domestic",
                "bid_type": "firm",
                "country": "India",
                "city": "Chennai",
                "epc_name": "ACME Projects Ltd",
                "due_date": "2026-08-31",
            },
        },
    )
    assert created.status_code == 201, created.text
    quote_id = created.json()["id"]
    started = client.post(
        f"/api/v1/quotes/{quote_id}/workflow",
        headers=_headers(org, "estimation"),
        json={"action": "begin_spec_check"},
    )
    assert started.status_code == 200, started.text
    assert started.json()["stage_meta"]["workflow_stage"] == "spec_check"
    return quote_id


def _raise_query(client: TestClient, org: str, user_id: str, quote_id: str, note: str, target: str = "spec_check") -> dict:
    resp = client.post(
        f"/api/v1/quotes/{quote_id}/queries",
        headers=_headers(org, user_id),
        json={"target_stage": target, "note": note},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["stage_meta"]["change_queries"][-1]


def _reply(client: TestClient, org: str, user_id: str, quote_id: str, query_id: str, note: str, expect: int = 200):
    resp = client.post(
        f"/api/v1/quotes/{quote_id}/queries/{query_id}/action",
        headers=_headers(org, user_id),
        json={"action": "reply", "note": note},
    )
    assert resp.status_code == expect, resp.text
    return resp


def test_receiving_team_replies_on_the_same_query(granular):
    """Management raises a spec query; estimation answers on that query. The
    reply lands in the same thread and nothing else about the enquiry moves."""
    client = TestClient(app)
    org = f"org-qthread-{uuid.uuid4().hex}"
    quote_id = _enquiry_at_spec_check(client, org)

    query = _raise_query(client, org, "jagadeeshan", quote_id, "please check column 11 and 12 , wrong spec")
    assert query["status"] == "pending_approval"
    assert query["raised_by_role"] == "management"
    assert query["raised_by_id"] == "jagadeeshan"

    replied = _reply(client, org, "estimation", quote_id, query["id"], "Column 11 and 12 corrected — 4.5 mm thk").json()
    thread = replied["stage_meta"]["change_queries"][-1]

    # Conversation only: same query, same status, same stage.
    assert thread["id"] == query["id"]
    assert thread["status"] == "pending_approval"
    assert replied["stage_meta"]["workflow_stage"] == "spec_check"
    # The answer is on the query's own history, attributed to the replier.
    assert [event["action"] for event in thread["history"]] == ["raised", "reply"]
    last = thread["history"][-1]
    assert last["role"] == "estimation"
    assert last["by_id"] == "estimation"
    assert last["note"] == "Column 11 and 12 corrected — 4.5 mm thk"
    assert thread["last_reply_note"] == "Column 11 and 12 corrected — 4.5 mm thk"
    assert thread["last_reply_at"]


def test_reply_needs_a_note_and_both_sides_can_keep_talking(granular):
    """An empty reply is rejected, and the raiser can answer back on the thread
    (a query is a conversation, not a single hand-off message)."""
    client = TestClient(app)
    org = f"org-qthread-{uuid.uuid4().hex}"
    quote_id = _enquiry_at_spec_check(client, org)
    query = _raise_query(client, org, "jagadeeshan", quote_id, "wrong spec on column 12")

    _reply(client, org, "estimation", quote_id, query["id"], "   ", expect=422)
    _reply(client, org, "estimation", quote_id, query["id"], "Which sheet — the GGPL format one?")
    final = _reply(client, org, "jagadeeshan", quote_id, query["id"], "Yes, the GGPL format sheet").json()

    thread = final["stage_meta"]["change_queries"][-1]
    assert [event["action"] for event in thread["history"]] == ["raised", "reply", "reply"]
    assert [event["role"] for event in thread["history"]] == ["management", "estimation", "management"]


def test_reply_still_works_after_the_query_is_decided(granular):
    """Approval moves the enquiry to the requested stage; the thread stays open
    so the team doing the change can report back without resolving it yet."""
    client = TestClient(app)
    org = f"org-qthread-{uuid.uuid4().hex}"
    quote_id = _enquiry_at_spec_check(client, org)
    # Raised from a later stage so approval visibly jumps the enquiry back.
    sent = client.post(
        f"/api/v1/quotes/{quote_id}/workflow",
        headers=_headers(org, "estimation"),
        json={"action": "send_to_technical_review", "gasket_type": "soft_cut"},
    )
    assert sent.status_code == 200, sent.text
    query = _raise_query(client, org, "jagadeeshan", quote_id, "spec wrong in column 11")

    approved = client.post(
        f"/api/v1/quotes/{quote_id}/queries/{query['id']}/action",
        headers=_headers(org, "shashnam"),
        json={"action": "approve", "note": "valid, send it back"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["stage_meta"]["workflow_stage"] == "spec_check"

    after = _reply(client, org, "estimation", quote_id, query["id"], "Redoing column 11 now").json()
    thread = after["stage_meta"]["change_queries"][-1]
    assert thread["status"] == "approved"
    assert after["stage_meta"]["workflow_stage"] == "spec_check"
    assert [event["action"] for event in thread["history"]] == ["raised", "approve", "reply"]
