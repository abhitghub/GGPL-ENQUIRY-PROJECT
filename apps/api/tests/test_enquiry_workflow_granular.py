"""Side-by-side tests for the granular 11-stage enquiry workflow.

Verifies that:
- With ENABLE_GRANULAR_WORKFLOW off, the original 6-step handoff is unchanged.
- With the flag on, the full 11-stage machine drives the happy path, the
  spec-check customer-query loop, and the gasket-type conditional branch to
  technical review — with API-layer RBAC blocking out-of-role actions.
- Role ownership agrees between the two machines at equivalent checkpoints.

Auth is via X-Org-Id / X-User-Id headers (LOGIN_ENABLED=false, set in conftest).
Seeded users: shashnam (admin), sales, estimation, technical, verifier (approver).
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
from app.services.enquiry_workflow import active_step_ids, active_transitions, can_act_on_step  # noqa: E402


@pytest.fixture
def granular(monkeypatch):
    """Turn the feature flag on for the duration of a test. The flag is read
    through the lru-cached settings, so the cache must be cleared on both sides."""
    monkeypatch.setenv("ENABLE_GRANULAR_WORKFLOW", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("ENABLE_GRANULAR_WORKFLOW", raising=False)
    get_settings.cache_clear()


def _headers(org: str, user_id: str) -> dict:
    return {"X-Org-Id": org, "X-User-Id": user_id}


def _create_enquiry(client: TestClient, org: str, owner: str = "sales") -> str:
    """Create an enquiry owned by `owner` (self-assigned) so Sales keeps
    read visibility after the record is handed off to other teams."""
    created = client.post(
        "/api/v1/quotes",
        headers=_headers(org, owner),
        json={
            "customer": "ACME",
            "project_ref": "P-GW",
            "items": [],
            "stage_meta": {"owner_id": owner},
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _act(client, org, user_id, quote_id, action, *, expect=200, **body):
    resp = client.post(
        f"/api/v1/quotes/{quote_id}/workflow",
        headers=_headers(org, user_id),
        json={"action": action, **body},
    )
    assert resp.status_code == expect, f"{action} as {user_id}: {resp.status_code} {resp.text}"
    return resp


def _act_blocked(client, org, user_id, quote_id, action, **body):
    """Assert a role is denied a transition. A non-owning role that also lacks
    step-visibility gets 404 (cannot see the record); a visible-but-unauthorised
    role gets 403. Both are valid API-layer enforcement of "no out-of-stage acts"."""
    resp = client.post(
        f"/api/v1/quotes/{quote_id}/workflow",
        headers=_headers(org, user_id),
        json={"action": action, **body},
    )
    assert resp.status_code in (403, 404), f"{action} as {user_id} should be blocked: {resp.status_code} {resp.text}"
    return resp


def _stage(resp) -> str:
    return resp.json()["stage_meta"]["workflow_stage"]


def test_legacy_path_unchanged():
    """Flag off: the original 6-step flow behaves exactly as before, and
    wrong-role transitions are rejected at the API layer."""
    get_settings.cache_clear()  # ensure no leaked flag from another test
    client = TestClient(app)
    org = f"org-gw-legacy-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    assert _stage(_act(client, org, "sales", qid, "send_to_estimation")) == "estimation_review"
    # Sales cannot act on an estimation-owned stage.
    _act(client, org, "sales", qid, "transfer_to_technical", expect=403)
    assert _stage(_act(client, org, "estimation", qid, "transfer_to_technical")) == "technical_specs"
    assert _stage(_act(client, org, "technical", qid, "return_to_estimation")) == "estimation_review"
    assert _stage(_act(client, org, "estimation", qid, "send_for_pricing")) == "pricing"
    # Pricing routing is a management/admin action; admin drives it here.
    assert _stage(_act(client, org, "shashnam", qid, "send_for_final_review")) == "estimation_final_review"
    assert _stage(_act(client, org, "estimation", qid, "send_final_to_sales")) == "sales_final"
    # A granular action must not exist when the flag is off.
    _act(client, org, "sales", qid, "forward_to_estimation", expect=400)


def test_granular_happy_path(granular):
    """Full 11-stage path with a non-specific gasket (skips technical review),
    domestic pricing, and a growing audit history_log."""
    client = TestClient(app)
    org = f"org-gw-happy-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    assert _stage(_act(client, org, "sales", qid, "forward_to_estimation")) == "forwarded_to_estimation"
    assert _stage(_act(client, org, "estimation", qid, "begin_spec_check")) == "spec_check"
    assert _stage(_act(client, org, "estimation", qid, "mark_spec_complete")) == "converted_to_ggpl_format"
    assert _stage(_act(client, org, "estimation", qid, "proceed_to_gasket_check")) == "gasket_type_check"
    # Non-specific gasket -> skip technical review, straight to combined review.
    skip = _act(client, org, "estimation", qid, "run_gasket_type_check", gasket_type="soft_cut")
    assert _stage(skip) == "combined_spec_review"
    assert _stage(_act(client, org, "estimation", qid, "submit_for_pricing")) == "sent_for_pricing"
    # Admin sets the pricing formula and hands it back to estimation to price.
    assert _stage(_act(client, org, "shashnam", qid, "open_pricing")) == "pricing_decision"
    # Estimation now prices per the formula; admin must not (out-of-role for pricing).
    priced = _act(client, org, "estimation", qid, "price_domestic")
    assert _stage(priced) == "quotation_generated"
    assert priced.json()["stage_meta"]["pricing_route"] == "domestic"
    # Estimation finalises and hands to sales; only sales sends to customer.
    assert _stage(_act(client, org, "estimation", qid, "send_quotation")) == "ready_for_customer"
    _act_blocked(client, org, "estimation", qid, "send_to_customer")
    final = _act(client, org, "sales", qid, "send_to_customer")
    assert _stage(final) == "quotation_sent_to_customer"

    granular_meta = final.json()["stage_meta"]["granular_workflow"]
    assert granular_meta["current_stage"] == "quotation_sent_to_customer"
    assert len(granular_meta["history_log"]) == 10
    assert granular_meta["history_log"][0]["action"] == "forward_to_estimation"
    assert granular_meta["history_log"][-1]["by"]  # actor recorded for audit


def test_granular_query_loop(granular):
    """Estimation raises a customer query; only Sales may answer it (the sole
    post-handoff Sales action), returning the enquiry to spec check."""
    client = TestClient(app)
    org = f"org-gw-query-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "sales", qid, "forward_to_estimation")
    _act(client, org, "estimation", qid, "begin_spec_check")
    assert _stage(_act(client, org, "estimation", qid, "raise_customer_query")) == "query_raised_to_customer"
    # Estimation may not answer a customer query; Sales must.
    _act_blocked(client, org, "estimation", qid, "answer_customer_query")
    assert _stage(_act(client, org, "sales", qid, "answer_customer_query")) == "spec_check"
    # Loop closed: spec can now be marked complete.
    assert _stage(_act(client, org, "estimation", qid, "mark_spec_complete")) == "converted_to_ggpl_format"


def test_granular_gasket_specific_branch(granular):
    """A specific gasket type routes to technical review; only Technical may
    return the spec, after which Estimation combines it."""
    client = TestClient(app)
    org = f"org-gw-gasket-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "sales", qid, "forward_to_estimation")
    _act(client, org, "estimation", qid, "begin_spec_check")
    _act(client, org, "estimation", qid, "mark_spec_complete")
    _act(client, org, "estimation", qid, "proceed_to_gasket_check")
    branched = _act(client, org, "estimation", qid, "run_gasket_type_check", gasket_type="ring_joint")
    assert _stage(branched) == "technical_review_pending"
    # Estimation cannot return a TR spec; only Technical can.
    _act_blocked(client, org, "estimation", qid, "return_tr_spec")
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "tr_spec_returned"
    assert _stage(_act(client, org, "estimation", qid, "combine_after_tr")) == "combined_spec_review"


def test_granular_is_superset_of_legacy(granular):
    """With the flag on, legacy actions/stages/ownership remain valid alongside
    the granular ones, so the existing (unmodified) screens and any in-flight
    legacy records keep working — enabling the flag only ADDS behaviour."""
    tx = active_transitions()
    assert "send_for_pricing" in tx and "submit_for_pricing" in tx  # legacy + granular
    assert "send_to_estimation" in tx and "forward_to_estimation" in tx
    ids = active_step_ids()
    assert "estimation_review" in ids and "spec_check" in ids
    # Legacy-stage ownership is still enforced under the flag.
    assert can_act_on_step("estimation", "estimation_review") is True
    assert can_act_on_step("sales", "estimation_review") is False


# (legacy_step, granular_step, owning_role) equivalence checkpoints.
_PARITY = [
    ("enquiry", "enquiry_received", "sales"),
    ("estimation_review", "spec_check", "estimation"),
    ("technical_specs", "technical_review_pending", "technical"),
    ("pricing", "pricing_decision", "admin"),
]


@pytest.mark.parametrize("legacy_step, granular_step, role", _PARITY)
def test_role_ownership_parity(monkeypatch, legacy_step, granular_step, role):
    """The owning role for each stage agrees across both machines, and a
    non-owning role is rejected on both sides."""
    other = "technical" if role != "technical" else "sales"

    # Flag off -> legacy ownership.
    monkeypatch.delenv("ENABLE_GRANULAR_WORKFLOW", raising=False)
    get_settings.cache_clear()
    assert can_act_on_step(role, legacy_step) is True
    assert can_act_on_step(other, legacy_step) is False

    # Flag on -> granular ownership, same owning role.
    monkeypatch.setenv("ENABLE_GRANULAR_WORKFLOW", "true")
    get_settings.cache_clear()
    assert can_act_on_step(role, granular_step) is True
    assert can_act_on_step(other, granular_step) is False
    # Admin owns every stage in both machines.
    assert can_act_on_step("admin", granular_step) is True

    monkeypatch.delenv("ENABLE_GRANULAR_WORKFLOW", raising=False)
    get_settings.cache_clear()
