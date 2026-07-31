"""Side-by-side tests for the consolidated 6-step enquiry workflow.

Verifies that:
- With ENABLE_GRANULAR_WORKFLOW off, the original legacy handoff is unchanged.
- With the flag on, the 6-step machine drives the happy path, the spec-check
  customer-query loop, and the mandatory technical-review gate — with
  API-layer RBAC blocking out-of-role actions.
- Records parked on retired 13-step ids read as the surviving state, so
  in-flight enquiries keep moving after the consolidation.
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
    """Flag off: the original legacy flow behaves exactly as before, and
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
    _act(client, org, "sales", qid, "begin_spec_check", expect=400)


def test_granular_happy_path(granular):
    """Full 6-step path: estimation does the spec work in one step, technical
    review is a mandatory gate, admin releases it to estimation, estimation
    prices, sales generates and sends — with a growing audit history_log."""
    client = TestClient(app)
    org = f"org-gw-happy-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    # Estimation picks up the enquiry; sales may not act here.
    _act_blocked(client, org, "sales", qid, "begin_spec_check")
    assert _stage(_act(client, org, "estimation", qid, "begin_spec_check")) == "spec_check"
    # One action closes the spec work (GGPL conversion + gasket check included)
    # and hands the enquiry to the technical review team.
    tr = _act(client, org, "estimation", qid, "send_to_technical_review", gasket_type="soft_cut")
    assert _stage(tr) == "technical_review_pending"
    # Technical review done -> straight into the admin pricing queue.
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "sent_for_pricing"
    # Admin releases the enquiry back to estimation to price, no formula needed.
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
    assert len(granular_meta["history_log"]) == 7
    assert granular_meta["history_log"][0]["action"] == "begin_spec_check"
    assert granular_meta["history_log"][-1]["by"]  # actor recorded for audit


def test_generate_route_derived_from_market_type(granular):
    """An export enquiry generates an international quotation without being asked
    for the route again — it derives from the quote type set in the enquiry setup."""
    client = TestClient(app)
    org = f"org-gw-route-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org, market_type="export")
    for role, action in [
        ("estimation", "begin_spec_check"),
        ("estimation", "send_to_technical_review"),
        ("technical", "return_tr_spec"),
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

    _act(client, org, "estimation", qid, "begin_spec_check")
    assert _stage(_act(client, org, "estimation", qid, "raise_customer_query")) == "query_raised_to_customer"
    # Estimation may not answer a customer query; Sales must.
    _act_blocked(client, org, "estimation", qid, "answer_customer_query")
    assert _stage(_act(client, org, "sales", qid, "answer_customer_query")) == "spec_check"
    # Loop closed: the spec work can now be finished and handed to technical.
    assert _stage(_act(client, org, "estimation", qid, "send_to_technical_review")) == "technical_review_pending"


def test_reviewer_returns_errors_then_rechecks(granular):
    """The reviewer finds errors and returns the enquiry to estimation with a
    note; estimation fixes it and re-submits, and the reviewer checks it again
    before it can go to pricing. The loop can repeat any number of times."""
    client = TestClient(app)
    org = f"org-gw-errors-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "estimation", qid, "begin_spec_check")
    _act(client, org, "estimation", qid, "send_to_technical_review")
    # A return with no note is rejected — estimation must be told what to fix.
    _act(client, org, "technical", qid, "return_spec_errors", expect=422)
    returned = _act(client, org, "technical", qid, "return_spec_errors", comment="Flange rating missing on lines 3-5")
    assert _stage(returned) == "spec_check"
    assert returned.json()["stage_meta"]["workflow_comment"] == "Flange rating missing on lines 3-5"
    # Estimation cannot skip the re-check by pushing straight past the reviewer
    # once it has re-submitted.
    assert _stage(_act(client, org, "estimation", qid, "send_to_technical_review")) == "technical_review_pending"
    _act_blocked(client, org, "estimation", qid, "return_tr_spec")
    # Second round: the reviewer clears it, so it moves to the pricing queue.
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "sent_for_pricing"


def test_technical_review_is_optional(granular):
    """Technical review is optional: estimation may send a spec-complete enquiry
    straight to the admin pricing queue, skipping the review step."""
    client = TestClient(app)
    org = f"org-gw-optional-tr-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "estimation", qid, "begin_spec_check")
    assert _stage(_act(client, org, "estimation", qid, "send_to_pricing_direct")) == "sent_for_pricing"
    # Only estimation may skip the review — sales cannot.
    other = _create_enquiry(client, org)
    _act(client, org, "estimation", other, "begin_spec_check")
    _act_blocked(client, org, "sales", other, "send_to_pricing_direct")


def test_admin_releases_to_pricing_without_a_formula(granular):
    """An enquiry carries many different specs, so admin gives no single pricing
    formula — the release to estimation needs no note, and none is recorded."""
    client = TestClient(app)
    org = f"org-gw-formula-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "estimation", qid, "begin_spec_check")
    _act(client, org, "estimation", qid, "send_to_pricing_direct")
    # No note needed -> the handoff goes through.
    priced = _act(client, org, "shashnam", qid, "open_pricing")
    meta = priced.json()["stage_meta"]
    assert _stage(priced) == "pricing_decision"
    assert "pricing_formula" not in meta
    # A free-text note on this handoff stays an ordinary workflow_comment and is
    # not promoted to a durable formula.
    submitted = _act(client, org, "estimation", qid, "submit_priced_quotation", comment="Priced per spec")
    submitted_meta = submitted.json()["stage_meta"]
    assert submitted_meta["workflow_comment"] == "Priced per spec"
    assert "pricing_formula" not in submitted_meta


def test_granular_technical_review_gate(granular):
    """When estimation does send an enquiry for technical review, the review is
    a real gate: only technical may move it on. Done means the specs are cleared
    for pricing, so it lands in the admin pricing queue."""
    client = TestClient(app)
    org = f"org-gw-tr-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "estimation", qid, "begin_spec_check")
    assert _stage(_act(client, org, "estimation", qid, "send_to_technical_review", gasket_type="ring_joint")) == "technical_review_pending"
    # Estimation cannot act while the enquiry is with technical review.
    _act_blocked(client, org, "estimation", qid, "return_tr_spec")
    # Admin's pricing action is a wrong-stage action here.
    wrong_stage = client.post(
        f"/api/v1/quotes/{qid}/workflow",
        headers=_headers(org, "shashnam"),
        json={"action": "open_pricing"},
    )
    assert wrong_stage.status_code in (403, 404, 409)
    # Only technical forwards the enquiry ahead — into the pricing queue.
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "sent_for_pricing"


def test_retired_step_ids_keep_flowing(granular):
    """An in-flight record parked on a retired 13-step id reads as the surviving
    6-step state, stays in the owning team's queue, and moves on normally."""
    client = TestClient(app)
    org = f"org-gw-retired-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    # Simulate a record the old machine left at the gasket-type check.
    patched = client.patch(
        f"/api/v1/quotes/{qid}",
        headers=_headers(org, "estimation"),
        json={"stage_meta": {"owner_id": "sales", "market_type": "domestic", "workflow_stage": "gasket_type_check"}},
    )
    assert patched.status_code == 200, patched.text
    # Estimation (who owns spec_check, the surviving state) can finish the spec
    # work directly — no dead-end, no unknown-stage error.
    assert _stage(_act(client, org, "estimation", qid, "send_to_technical_review")) == "technical_review_pending"


def test_granular_is_superset_of_legacy(granular):
    """With the flag on, legacy actions/stages/ownership remain valid alongside
    the granular ones, so the existing (unmodified) screens and any in-flight
    legacy records keep working — enabling the flag only ADDS behaviour."""
    tx = active_transitions()
    assert "send_for_pricing" in tx and "begin_spec_check" in tx  # legacy + granular
    assert "send_to_estimation" in tx and "send_to_technical_review" in tx
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
    ("pricing", "admin", "pricing_decision", "estimation"),
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
