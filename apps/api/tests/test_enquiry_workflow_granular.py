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


def _create_enquiry(client: TestClient, org: str, owner: str = "sales", market_type: str = "domestic") -> str:
    """Create an enquiry as ESTIMATION (who owns enquiry creation) and assign it
    to `owner` — estimation decides which sales person owns the record, and the
    owner keeps read visibility after handoffs. The quote type (market_type) is
    set up front, as in the enquiry setup form."""
    created = client.post(
        "/api/v1/quotes",
        headers=_headers(org, "estimation"),
        json={
            "customer": "ACME",
            "project_ref": "P-GW",
            "items": [],
            "stage_meta": {"owner_id": owner, "market_type": market_type},
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

    # Estimation creates and forwards the enquiry; sales may not act here.
    _act_blocked(client, org, "sales", qid, "forward_to_estimation")
    assert _stage(_act(client, org, "estimation", qid, "forward_to_estimation")) == "forwarded_to_estimation"
    assert _stage(_act(client, org, "estimation", qid, "begin_spec_check")) == "spec_check"
    assert _stage(_act(client, org, "estimation", qid, "mark_spec_complete")) == "converted_to_ggpl_format"
    assert _stage(_act(client, org, "estimation", qid, "proceed_to_gasket_check")) == "gasket_type_check"
    # Gasket type check routes to the technical review team (no bypass); only
    # technical forwards it ahead to the combined review.
    tr = _act(client, org, "estimation", qid, "run_gasket_type_check", gasket_type="soft_cut")
    assert _stage(tr) == "technical_review_pending"
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "combined_spec_review"
    assert _stage(_act(client, org, "estimation", qid, "submit_for_pricing")) == "sent_for_pricing"
    # Admin sets the pricing formula and hands it back to estimation to price.
    assert _stage(_act(client, org, "shashnam", qid, "open_pricing")) == "pricing_decision"
    # Estimation prices and submits the quotation for generation.
    assert _stage(_act(client, org, "estimation", qid, "submit_priced_quotation")) == "pricing_submitted"
    # Estimation cannot generate the quotation — only sales or admin.
    _act_blocked(client, org, "estimation", qid, "generate_quotation")
    # Sales (or admin) generates; the route derives from the enquiry's quote type
    # (market_type=domestic set at creation) — it is not asked again.
    priced = _act(client, org, "sales", qid, "generate_quotation")
    assert _stage(priced) == "quotation_generated"
    assert priced.json()["stage_meta"]["pricing_route"] == "domestic"
    # Sales downloads and sends to the customer.
    final = _act(client, org, "sales", qid, "send_to_customer")
    assert _stage(final) == "quotation_sent_to_customer"

    granular_meta = final.json()["stage_meta"]["granular_workflow"]
    assert granular_meta["current_stage"] == "quotation_sent_to_customer"
    assert len(granular_meta["history_log"]) == 11
    assert granular_meta["history_log"][0]["action"] == "forward_to_estimation"
    assert granular_meta["history_log"][-1]["by"]  # actor recorded for audit


def test_generate_route_derived_from_market_type(granular):
    """An export enquiry generates an international quotation without being asked
    for the route again — it derives from the quote type set in the enquiry setup."""
    client = TestClient(app)
    org = f"org-gw-route-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org, market_type="export")
    for role, action in [
        ("estimation", "forward_to_estimation"),
        ("estimation", "begin_spec_check"),
        ("estimation", "mark_spec_complete"),
        ("estimation", "proceed_to_gasket_check"),
        ("estimation", "run_gasket_type_check"),
        ("technical", "return_tr_spec"),
        ("estimation", "submit_for_pricing"),
        ("shashnam", "open_pricing"),
        ("estimation", "submit_priced_quotation"),
    ]:
        _act(client, org, role, qid, action)
    generated = _act(client, org, "sales", qid, "generate_quotation")
    assert _stage(generated) == "quotation_generated"
    assert generated.json()["stage_meta"]["pricing_route"] == "international"


def test_granular_query_loop(granular):
    """Estimation raises a customer query; only Sales may answer it (the sole
    post-handoff Sales action), returning the enquiry to spec check."""
    client = TestClient(app)
    org = f"org-gw-query-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "estimation", qid, "forward_to_estimation")
    _act(client, org, "estimation", qid, "begin_spec_check")
    assert _stage(_act(client, org, "estimation", qid, "raise_customer_query")) == "query_raised_to_customer"
    # Estimation may not answer a customer query; Sales must.
    _act_blocked(client, org, "estimation", qid, "answer_customer_query")
    assert _stage(_act(client, org, "sales", qid, "answer_customer_query")) == "spec_check"
    # Loop closed: spec can now be marked complete.
    assert _stage(_act(client, org, "estimation", qid, "mark_spec_complete")) == "converted_to_ggpl_format"


def test_granular_technical_review_routing(granular):
    """The gasket type check routes the enquiry to the technical review team (no
    bypass). Only technical may view/forward it ahead. From the combined review,
    estimation may either send for pricing or send for technical review again."""
    client = TestClient(app)
    org = f"org-gw-tr-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "estimation", qid, "forward_to_estimation")
    _act(client, org, "estimation", qid, "begin_spec_check")
    _act(client, org, "estimation", qid, "mark_spec_complete")
    _act(client, org, "estimation", qid, "proceed_to_gasket_check")
    # Gasket type check -> technical review team (mandatory, no bypass).
    assert _stage(_act(client, org, "estimation", qid, "run_gasket_type_check", gasket_type="ring_joint")) == "technical_review_pending"
    # Estimation cannot skip past TR from here — pricing is a wrong-stage action.
    _act_blocked_or_conflict = client.post(
        f"/api/v1/quotes/{qid}/workflow",
        headers=_headers(org, "estimation"),
        json={"action": "submit_for_pricing"},
    )
    assert _act_blocked_or_conflict.status_code in (403, 404, 409)
    # Only technical forwards the enquiry ahead.
    _act_blocked(client, org, "estimation", qid, "return_tr_spec")
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "combined_spec_review"
    # From the combined review estimation chooses: technical review again...
    assert _stage(_act(client, org, "estimation", qid, "send_to_technical_review")) == "technical_review_pending"
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "combined_spec_review"
    # ...or send for pricing.
    assert _stage(_act(client, org, "estimation", qid, "submit_for_pricing")) == "sent_for_pricing"


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


# (legacy_step, legacy_role, granular_step, granular_role) ownership checkpoints.
# The enquiry-received stage intentionally DIVERGES: legacy keeps sales for
# in-flight records, while the granular machine hands creation to estimation.
_PARITY = [
    ("enquiry", "sales", "enquiry_received", "estimation"),
    ("estimation_review", "estimation", "spec_check", "estimation"),
    ("technical_specs", "technical", "technical_review_pending", "technical"),
    ("pricing", "admin", "pricing_decision", "admin"),
]


@pytest.mark.parametrize("legacy_step, legacy_role, granular_step, granular_role", _PARITY)
def test_role_ownership_parity(monkeypatch, legacy_step, legacy_role, granular_step, granular_role):
    """Each stage has the expected owning role in each machine, and a
    non-owning role is rejected on both sides."""
    legacy_other = "technical" if legacy_role != "technical" else "sales"
    granular_other = "sales" if granular_role != "sales" else "technical"

    # Flag off -> legacy ownership.
    monkeypatch.delenv("ENABLE_GRANULAR_WORKFLOW", raising=False)
    get_settings.cache_clear()
    assert can_act_on_step(legacy_role, legacy_step) is True
    assert can_act_on_step(legacy_other, legacy_step) is False

    # Flag on -> granular ownership.
    monkeypatch.setenv("ENABLE_GRANULAR_WORKFLOW", "true")
    get_settings.cache_clear()
    assert can_act_on_step(granular_role, granular_step) is True
    assert can_act_on_step(granular_other, granular_step) is False
    # Admin owns every stage in both machines.
    assert can_act_on_step("admin", granular_step) is True

    monkeypatch.delenv("ENABLE_GRANULAR_WORKFLOW", raising=False)
    get_settings.cache_clear()
