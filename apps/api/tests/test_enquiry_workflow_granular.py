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
from app.services.enquiry_workflow import (  # noqa: E402
    REVIEW_LOOP_ACTIONS,
    active_step_ids,
    active_transitions,
    can_act_on_step,
)


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
    # Re-submitting a returned spec is a reply, so it must say what changed —
    # a note-less re-submission is rejected (a first submission needs no note).
    _act(client, org, "estimation", qid, "send_to_technical_review", expect=422)
    resubmitted = _act(client, org, "estimation", qid, "send_to_technical_review", comment="Added the rating on lines 3-5")
    # Estimation cannot skip the re-check by pushing straight past the reviewer
    # once it has re-submitted.
    assert _stage(resubmitted) == "technical_review_pending"
    _act_blocked(client, org, "estimation", qid, "return_tr_spec")
    # Both sides of the exchange survive in the history log, so the reviewer can
    # read what he flagged next to estimation's reply when he re-checks.
    thread = [
        (row["action"], row["comment"])
        for row in resubmitted.json()["stage_meta"]["granular_workflow"]["history_log"]
        if row["action"] in REVIEW_LOOP_ACTIONS
    ]
    assert thread == [
        ("send_to_technical_review", ""),
        ("return_spec_errors", "Flange rating missing on lines 3-5"),
        ("send_to_technical_review", "Added the rating on lines 3-5"),
    ]
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


def test_admin_releases_an_empty_enquiry_without_a_formula(granular):
    """There is no single formula for an enquiry — the rate rule is written per
    spec. With nothing to price, the release needs no formula and no note, and
    a free-text note stays an ordinary workflow_comment."""
    client = TestClient(app)
    org = f"org-gw-formula-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    _act(client, org, "estimation", qid, "begin_spec_check")
    _act(client, org, "estimation", qid, "send_to_pricing_direct")
    # No specs to price -> the handoff goes through with nothing recorded.
    priced = _act(client, org, "shashnam", qid, "open_pricing")
    meta = priced.json()["stage_meta"]
    assert _stage(priced) == "pricing_decision"
    assert "pricing_formula" not in meta
    assert "pricing_formulas" not in meta
    submitted = _act(client, org, "estimation", qid, "submit_priced_quotation", comment="Priced per spec")
    submitted_meta = submitted.json()["stage_meta"]
    assert submitted_meta["workflow_comment"] == "Priced per spec"
    assert "pricing_formula" not in submitted_meta


def test_technical_reviewer_is_review_only(granular):
    """Technical review reviews and routes — it does not fix. The reviewer can
    read the enquiry and perform both review handoffs, but cannot edit the line
    items, the quotation or the enquiry metadata: estimation makes the changes."""
    client = TestClient(app)
    org = f"org-gw-review-only-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)
    _act(client, org, "estimation", qid, "begin_spec_check")
    _act(client, org, "estimation", qid, "send_to_technical_review")

    # He can read the enquiry he is reviewing.
    assert client.get(f"/api/v1/quotes/{qid}", headers=_headers(org, "technical")).status_code == 200
    # But he cannot rewrite the specs — that is estimation's job after a return.
    for payload in (
        {"items": [{"raw_description": "reviewer edited this"}]},
        {"quote_data": {"payment_terms": "reviewer edited this"}},
        {"stage_meta": {"due_date": "2026-01-01"}},
    ):
        resp = client.patch(f"/api/v1/quotes/{qid}", headers=_headers(org, "technical"), json=payload)
        assert resp.status_code == 403, f"technical should not edit {list(payload)[0]}: {resp.status_code} {resp.text}"
    # Both review handoffs still work — they gate on stage ownership, not on an
    # edit capability, so stripping the edit rights does not disarm the reviewer.
    returned = _act(client, org, "technical", qid, "return_spec_errors", comment="Rating missing on line 2")
    assert _stage(returned) == "spec_check"
    _act(client, org, "estimation", qid, "send_to_technical_review", comment="Rating added")
    assert _stage(_act(client, org, "technical", qid, "return_tr_spec")) == "sent_for_pricing"


def _set_formulas(client, org, user_id, quote_id, rows, *, expect=200, **extra):
    resp = client.patch(
        f"/api/v1/quotes/{quote_id}",
        headers=_headers(org, user_id),
        json={"stage_meta": {"pricing_formulas": {"rows": rows, "set_by": user_id, **extra}}},
    )
    assert resp.status_code == expect, f"set formulas as {user_id}: {resp.status_code} {resp.text}"
    return resp


def _at_pricing_desk(client, org, items) -> str:
    """An enquiry with line items, parked in the pricing desk's queue."""
    qid = _create_enquiry(client, org)
    client.patch(f"/api/v1/quotes/{qid}", headers=_headers(org, "estimation"), json={"items": items})
    _act(client, org, "estimation", qid, "begin_spec_check")
    _act(client, org, "estimation", qid, "send_to_pricing_direct")
    return qid


SPEC_A = {"raw_description": "SPIRAL WOUND SS316 GRAPHITE 150#", "quantity": 4, "gasket_type": "SPIRAL_WOUND"}
SPEC_B = {"raw_description": "CNAF SHEET 3MM 150# RF", "quantity": 10, "gasket_type": "SOFT_CUT"}


def test_every_spec_needs_a_formula_before_the_release_to_estimation(granular):
    """Estimation prices each line against its spec's rate rule, so an enquiry
    with line items cannot leave the pricing desk until every spec row on the
    quotation summary carries a formula."""
    client = TestClient(app)
    org = f"org-gw-per-spec-{uuid.uuid4().hex}"
    qid = _at_pricing_desk(client, org, [SPEC_A, SPEC_B])

    # Nothing entered yet -> blocked.
    blocked = _act(client, org, "shashnam", qid, "open_pricing", expect=422)
    assert "pricing formula" in blocked.json()["detail"].lower()
    # One spec priced, one blank -> still blocked, and the gap is named.
    _set_formulas(
        client, org, "shashnam", qid,
        [{"item": "SPW SS316/GRA", "count": 1, "formula": "weight x rate + 20%"}, {"item": "CNAF 3MM", "count": 1, "formula": ""}],
    )
    partial = _act(client, org, "shashnam", qid, "open_pricing", expect=422)
    assert "CNAF 3MM" in partial.json()["detail"]
    # Every spec priced -> the release goes through and the formulas travel with
    # the enquiry to estimation.
    _set_formulas(
        client, org, "shashnam", qid,
        [
            {"item": "SPW SS316/GRA", "count": 1, "formula": "weight x rate + 20%"},
            {"item": "CNAF 3MM", "count": 1, "formula": "area x sheet rate"},
        ],
    )
    released = _act(client, org, "shashnam", qid, "open_pricing")
    assert _stage(released) == "pricing_decision"
    rows = released.json()["stage_meta"]["pricing_formulas"]["rows"]
    assert [row["formula"] for row in rows] == ["weight x rate + 20%", "area x sheet rate"]


def test_only_the_pricing_desk_writes_the_formulas(granular):
    """Estimation reads the formulas and prices against them; it cannot rewrite
    the rate rule itself."""
    client = TestClient(app)
    org = f"org-gw-formula-rbac-{uuid.uuid4().hex}"
    qid = _at_pricing_desk(client, org, [SPEC_A])
    rows = [{"item": "SPW SS316/GRA", "count": 1, "formula": "weight x rate + 20%"}]
    _set_formulas(client, org, "shashnam", qid, rows)
    _act(client, org, "shashnam", qid, "open_pricing")

    overwritten = [{"item": "SPW SS316/GRA", "count": 1, "formula": "whatever estimation likes"}]
    resp = client.patch(
        f"/api/v1/quotes/{qid}",
        headers=_headers(org, "estimation"),
        json={"stage_meta": {"pricing_formulas": {"rows": overwritten}}},
    )
    assert resp.status_code == 403, resp.text
    current = client.get(f"/api/v1/quotes/{qid}", headers=_headers(org, "estimation"))
    assert current.json()["stage_meta"]["pricing_formulas"]["rows"][0]["formula"] == "weight x rate + 20%"


def test_changed_line_items_send_the_formulas_back_for_a_re_check(granular):
    """Rates written against a different set of line items must not be released
    unreviewed: changing the items marks the formulas stale until they are
    re-saved."""
    client = TestClient(app)
    org = f"org-gw-formula-stale-{uuid.uuid4().hex}"
    qid = _at_pricing_desk(client, org, [SPEC_A])
    rows = [{"item": "SPW SS316/GRA", "count": 1, "formula": "weight x rate + 20%"}]
    _set_formulas(client, org, "shashnam", qid, rows)

    changed = client.patch(
        f"/api/v1/quotes/{qid}",
        headers=_headers(org, "shashnam"),
        json={"items": [SPEC_A, SPEC_B]},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["stage_meta"]["pricing_formulas"]["stale"] is True

    stale = _act(client, org, "shashnam", qid, "open_pricing", expect=422)
    assert "changed" in stale.json()["detail"].lower()
    # Re-saving the formulas against the new items clears it.
    _set_formulas(client, org, "shashnam", qid, rows + [{"item": "CNAF 3MM", "count": 1, "formula": "area x sheet rate"}])
    assert _stage(_act(client, org, "shashnam", qid, "open_pricing")) == "pricing_decision"


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


# Estimation, Jagadeeshan (management) and admin are the three parties that
# correct enquiry specs. Seeded ids: estimation / jagadeeshan / shashnam.
_SPEC_EDITORS = ["estimation", "jagadeeshan", "shashnam"]


@pytest.mark.parametrize("editor", _SPEC_EDITORS)
def test_spec_editors_can_fix_columns_at_any_stage(granular, editor):
    """A wrong column is estimation's (or management's, or admin's) to fix
    whenever it is spotted — including while the enquiry sits on another team's
    stage. Editing the line items must not require owning the current step, and
    the corrected columns must show up in the recomputed GGPL description."""
    client = TestClient(app)
    org = f"org-gw-edit-{editor}-{uuid.uuid4().hex}"
    qid = _create_enquiry(client, org)

    # A row the engine cannot describe yet: it escalates to "provide datasheet".
    seeded = client.patch(
        f"/api/v1/quotes/{qid}",
        headers=_headers(org, "estimation"),
        json={"items": [{"line_no": 1, "quantity": 2, "uom": "NOS", "is_gasket": True,
                         "raw_description": "SPIRAL WOUND GASKET ASME B16.20"}]},
    )
    assert seeded.status_code == 200, seeded.text
    first = client.post(
        f"/api/v1/quotes/{qid}/items/bulk-recompute",
        headers=_headers(org, "estimation"),
        json={"rows": seeded.json()["items"]},
    )
    assert first.status_code == 200, first.text
    assert first.json()[0]["escalation"]  # nothing to describe yet

    # Park it on technical review — a stage none of the three editors owns.
    _act(client, org, "estimation", qid, "begin_spec_check")
    assert _stage(_act(client, org, "estimation", qid, "send_to_technical_review")) == "technical_review_pending"

    # The editor can still open the record and correct its columns.
    row = {**first.json()[0], "size": '2"', "rating": "300#", "moc": "SS316",
           "sw_winding_material": "SS316", "sw_filler": "GRAPHITE", "sw_outer_ring": "CS",
           "manual_fields": ["size", "rating", "moc", "sw_winding_material", "sw_filler", "sw_outer_ring"]}
    patched = client.patch(f"/api/v1/quotes/{qid}", headers=_headers(org, editor), json={"items": [row]})
    assert patched.status_code == 200, f"{editor} could not edit the columns: {patched.text}"

    # ...and the correction reaches the GGPL description instead of being masked
    # by the escalation phrase the row was carrying.
    recomputed = client.post(
        f"/api/v1/quotes/{qid}/items/bulk-recompute",
        headers=_headers(org, editor),
        json={"rows": patched.json()["items"]},
    )
    assert recomputed.status_code == 200, recomputed.text
    described = recomputed.json()[0]
    assert not described.get("escalation")
    assert "SS316" in described["ggpl_description"] and "300#" in described["ggpl_description"]

    # Editing specs is not a workflow handoff: the enquiry has not moved, and
    # the editor still cannot advance it out of technical review's turn.
    assert _stage(patched) == "technical_review_pending"
    if editor == "estimation":
        _act_blocked(client, org, editor, qid, "return_tr_spec")


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
