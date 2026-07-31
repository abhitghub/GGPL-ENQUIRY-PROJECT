"""Enquiry -> priced-specs handoff pipeline.

Models the team-ownership flow: Sales files the enquiry, Estimation checks it and
either builds the specs itself or hands off to Technical review (which returns to
Estimation), Estimation sends the GGPL-format specs to pricing (Ashwin sir), and
the priced specs come back to Sales to send to the customer.

This is a lightweight status layer stored in stage_meta.workflow_stage; it does not
replace the primary quote.stage machine.
"""

from __future__ import annotations

from typing import Any

WORKFLOW_STEPS: list[dict[str, str]] = [
    {"id": "enquiry", "label": "Enquiry", "team": "Sales"},
    {"id": "estimation_review", "label": "Estimation review", "team": "Estimation"},
    {"id": "technical_specs", "label": "Technical specs", "team": "Technical review"},
    {"id": "pricing", "label": "Pricing", "team": "Ashwin sir"},
    {"id": "estimation_final_review", "label": "Final review", "team": "Estimation"},
    {"id": "sales_final", "label": "Ready for customer", "team": "Sales"},
]

WORKFLOW_STEP_IDS = {step["id"] for step in WORKFLOW_STEPS}
DEFAULT_WORKFLOW_STEP = "enquiry"

# action -> transition rule. `roles` is additive to admin (admin may do anything).
WORKFLOW_TRANSITIONS: dict[str, dict] = {
    "send_to_estimation": {
        "from": {"enquiry", "sales_final"},
        "roles": {"sales", "management"},
        "to": "estimation_review",
        "with_whom": "Estimation",
        "label": "Send to estimation",
    },
    "transfer_to_technical": {
        "from": {"estimation_review"},
        "roles": {"estimation"},
        "to": "technical_specs",
        "with_whom": "Technical review",
        "label": "Transfer to technical review",
    },
    "return_to_estimation": {
        "from": {"technical_specs"},
        "roles": {"technical"},
        "to": "estimation_review",
        "with_whom": "Estimation",
        "label": "Return specs to estimation",
    },
    "send_for_pricing": {
        "from": {"estimation_review"},
        "roles": {"estimation"},
        "to": "pricing",
        "with_whom": "Ashwin sir",
        "label": "Send for pricing",
    },
    # After pricing, Ashwin sir (admin) routes it — to Estimation for final review,
    # back to Technical for a spec correction, or straight to Sales — with a comment.
    "send_for_final_review": {
        "from": {"pricing"},
        "roles": {"management"},
        "to": "estimation_final_review",
        "with_whom": "Estimation",
        "label": "Send to estimation for final review",
    },
    "pricing_to_technical": {
        "from": {"pricing"},
        "roles": {"management"},
        "to": "technical_specs",
        "with_whom": "Technical review",
        "label": "Send to technical review",
    },
    "pricing_to_sales": {
        "from": {"pricing"},
        "roles": {"management"},
        "to": "sales_final",
        "with_whom": "Sales",
        "label": "Send to sales",
    },
    # Estimation signs off the priced specs and hands the final quotation to Sales.
    "send_final_to_sales": {
        "from": {"estimation_final_review"},
        "roles": {"estimation"},
        "to": "sales_final",
        "with_whom": "Sales",
        "label": "Send final quotation to sales",
    },
}


# Which workflow steps a back-office role may see regardless of record ownership,
# so handed-off enquiries appear in the receiving team's queue. Sales/viewer stay
# owner-scoped; admin sees everything already.
ROLE_VISIBLE_STEPS: dict[str, set[str]] = {
    "estimation": {"estimation_review", "estimation_final_review"},
    "technical": {"technical_specs"},
    "management": set(WORKFLOW_STEP_IDS),
}


# ---------------------------------------------------------------------------
# Granular 6-step machine (additive; active only when ENABLE_GRANULAR_WORKFLOW).
#
# The business flow is presented to users as 6 numbered steps; three exception
# states (customer query open, awaiting the admin release to pricing, quotation
# generated but not yet sent) live INSIDE a numbered step and are shown as a
# sub-status badge on that step — "mainline" names the step they anchor to.
# When the feature flag is off, every accessor below returns the legacy
# structures and behaviour is byte-identical to the original engine.
# ---------------------------------------------------------------------------

GRANULAR_WORKFLOW_STEPS: list[dict[str, str]] = [
    {"id": "enquiry_received", "label": "Enquiry received", "team": "Estimation"},
    {"id": "spec_check", "label": "Spec check & GGPL format", "team": "Estimation"},
    {"id": "query_raised_to_customer", "label": "Query raised to customer", "team": "Sales", "mainline": "spec_check"},
    # Technical review is the MANAGER's step: there is no separate technical-review
    # team. The step keeps its business name; the team holding it is management.
    {"id": "technical_review_pending", "label": "Technical review", "team": "Manager"},
    {"id": "sent_for_pricing", "label": "Sent for pricing", "team": "Admin", "mainline": "pricing_decision"},
    {"id": "pricing_decision", "label": "Pricing", "team": "Estimation"},
    {"id": "pricing_submitted", "label": "Quotation generation", "team": "Sales / Admin"},
    {"id": "quotation_generated", "label": "Quotation generated", "team": "Sales", "mainline": "pricing_submitted"},
    {"id": "quotation_sent_to_customer", "label": "Quotation sent to customer", "team": "Sales"},
]

GRANULAR_WORKFLOW_STEP_IDS = {step["id"] for step in GRANULAR_WORKFLOW_STEPS}
DEFAULT_GRANULAR_STEP = "enquiry_received"

# The earlier 13-step machine had four extra same-team states. In-flight records
# parked on one of them are read as the surviving state that now covers that
# work, so nothing strands when the consolidated machine ships.
RETIRED_GRANULAR_STEPS: dict[str, str] = {
    "forwarded_to_estimation": "spec_check",
    "converted_to_ggpl_format": "spec_check",
    "gasket_type_check": "spec_check",
    # Post-TR estimation review is gone; its only exit was submitting for
    # pricing, so records there land in the admin pricing queue.
    "combined_spec_review": "sent_for_pricing",
}

# Gasket types that require a technical-review pass before pricing (stage 5
# branch). Compared case-insensitively against stage_meta["gasket_type"].
# Centralised here so the business rule is trivially adjustable.
TR_REQUIRED_GASKET_TYPES: set[str] = {
    "ring_joint",
    "rtj",
    "spring_energized",
    "metal_jacketed",
    "kammprofile",
}

# action -> transition rule for the granular machine. Fresh action names (no
# collision with the legacy 8). `roles` is additive to admin (admin may do
# anything). Optional keys: "branch" (runtime destination), "set" (extra
# stage_meta markers to persist).
GRANULAR_WORKFLOW_TRANSITIONS: dict[str, dict] = {
    # Estimation creates enquiries (and assigns the sales owner), so it also
    # picks each one up to start the spec work.
    "begin_spec_check": {
        "from": {"enquiry_received"},
        "roles": {"estimation", "management"},
        "to": "spec_check",
        "with_whom": "Estimation",
        "label": "Begin spec check",
    },
    # branch A: specs incomplete -> customer query loop (sub-status of the
    # spec-check step; ownership flips to Sales until the answer comes back).
    "raise_customer_query": {
        "from": {"spec_check"},
        "roles": {"estimation"},
        "to": "query_raised_to_customer",
        "with_whom": "Sales",
        "label": "Raise query to customer",
    },
    # The only post-handoff action Sales may take: answer the query and return
    # the enquiry to Estimation's spec check.
    "answer_customer_query": {
        "from": {"query_raised_to_customer"},
        "roles": {"sales", "management"},
        "to": "spec_check",
        "with_whom": "Estimation",
        "label": "Answer customer query",
    },
    # branch B: specs complete — GGPL conversion and the gasket-type check are
    # part of Estimation's spec work, so one action closes the step and hands
    # the enquiry to the reviewer (technical review team).
    "send_to_technical_review": {
        "from": {"spec_check"},
        "roles": {"estimation"},
        "to": "technical_review_pending",
        "with_whom": "Manager",
        "label": "Spec complete — send for technical review",
        # First trip: no note needed. Re-submitting a spec the reviewer sent back
        # is a reply, so it must say what changed — otherwise the reviewer has to
        # re-check the whole spec blind.
        "require_comment_after": {
            "return_spec_errors": "Say what you changed so the reviewer knows what to re-check",
        },
    },
    # Technical review is optional: when the specs need no review pass,
    # estimation may send the enquiry straight to the admin pricing queue.
    "send_to_pricing_direct": {
        "from": {"spec_check"},
        "roles": {"estimation"},
        "to": "sent_for_pricing",
        "with_whom": "Admin",
        "label": "Spec complete — send for pricing (skip technical review)",
    },
    # The manager found errors — send the enquiry back to estimation with a
    # note describing what to fix. After the fix, estimation re-submits for
    # review, so the loop repeats until the manager clears it.
    "return_spec_errors": {
        "from": {"technical_review_pending"},
        "roles": {"management"},
        "to": "spec_check",
        "with_whom": "Estimation",
        "label": "Errors found — return to estimation",
        "require_comment": "Describe the errors found so estimation knows what to fix",
    },
    # Only the manager can forward an enquiry that is up for technical review —
    # done means the specs are cleared for pricing, so it goes straight to the
    # admin pricing queue.
    "return_tr_spec": {
        "from": {"technical_review_pending"},
        "roles": {"management"},
        "to": "sent_for_pricing",
        "with_whom": "Admin",
        "label": "Technical review done — submit for pricing",
    },
    # Admin (the pricing desk) releases the enquiry to estimation. One formula
    # cannot cover an enquiry carrying many different specs, so the formula is
    # entered PER SPEC against the quotation summary and every spec row must
    # carry one before the release goes through. A handoff note stays optional.
    "open_pricing": {
        "from": {"sent_for_pricing"},
        "roles": {"admin", "management"},
        "to": "pricing_decision",
        "with_whom": "Estimation",
        "label": "Send to estimation for pricing",
        "require_pricing_formulas": True,
    },
    # Estimation fills the pricing per the formula (and can preview the quotation),
    # then submits it for generation. Estimation does NOT generate the quotation.
    "submit_priced_quotation": {
        "from": {"pricing_decision"},
        "roles": {"estimation", "management"},
        "to": "pricing_submitted",
        "with_whom": "Sales / Admin",
        "label": "Submit priced quotation",
    },
    # Sales OR admin generates the priced quotation. The domestic/international
    # route is NOT asked again here — it is derived from the quote type chosen in
    # the enquiry setup (stage_meta.market_type: export -> international).
    "generate_quotation": {
        "from": {"pricing_submitted"},
        "roles": {"sales", "admin", "management"},
        "to": "quotation_generated",
        "with_whom": "Sales",
        "label": "Generate quotation",
        "route_from_market_type": True,
    },
    # Sales downloads the generated quotation and releases it to the customer.
    "send_to_customer": {
        "from": {"quotation_generated"},
        "roles": {"sales", "management"},
        "to": "quotation_sent_to_customer",
        "with_whom": "Customer",
        "label": "Send quotation to customer",
    },
}


# Which granular steps a back-office role may see regardless of record ownership.
# Sales/viewer stay owner-scoped; admin sees everything already; management stays
# omniscient (mirrors the legacy map).
GRANULAR_ROLE_VISIBLE_STEPS: dict[str, set[str]] = {
    # Estimation owns spec correctness for the whole life of an enquiry, not just
    # while it is parked on an estimation step: a wrong MOC or thickness spotted
    # during technical review, at the pricing desk, or after the quotation was
    # generated is still estimation's to fix. So estimation SEES every step
    # (like management and admin) and can open any enquiry to correct its
    # columns. This widens visibility only — which enquiries land in whose queue
    # is GRANULAR_STAGE_OWNER_ROLES below, and the workflow HANDOFFS stay
    # stage-gated, so estimation still cannot advance an enquiry out of turn.
    "estimation": set(GRANULAR_WORKFLOW_STEP_IDS),
    # No `technical` entry: the technical-review step belongs to the manager, so
    # the legacy `technical` role sees no granular step at all. It stays a valid
    # role (accounts holding it keep working, and it still owns the legacy
    # `technical_specs` stage via ROLE_VISIBLE_STEPS) but has no job in this flow.
    "admin": {"sent_for_pricing", "pricing_submitted"},
    "management": set(GRANULAR_WORKFLOW_STEP_IDS),
}

# Single RBAC source of truth: which roles may ACT on / edit an enquiry parked at
# each granular step. Enforced at the API layer via can_act_on_step(); blocks
# out-of-stage edits even when a transition's role set is broad. `management`
# retained everywhere for back-compat; `admin` bypasses in code regardless.
GRANULAR_STAGE_OWNER_ROLES: dict[str, set[str]] = {
    "enquiry_received": {"estimation", "management"},
    "spec_check": {"estimation", "management"},
    "query_raised_to_customer": {"sales", "management"},
    # The manager (Jagadeeshan) owns technical review — he clears it for pricing or
    # returns it to estimation. This also picks the notification target.
    "technical_review_pending": {"management"},
    "sent_for_pricing": {"admin", "management"},
    "pricing_decision": {"estimation", "management"},
    "pricing_submitted": {"sales", "admin", "management"},
    "quotation_generated": {"sales", "management"},
    "quotation_sent_to_customer": {"sales", "management"},
}

# Legacy stage -> roles allowed to act, derived from the legacy transitions'
# from-sets so the same guard yields identical semantics when the flag is off.
_LEGACY_STAGE_OWNER_ROLES: dict[str, set[str]] = {
    "enquiry": {"sales", "management"},
    "estimation_review": {"estimation", "management"},
    "technical_specs": {"technical", "management"},
    "pricing": {"management"},
    "estimation_final_review": {"estimation", "management"},
    "sales_final": {"sales", "management"},
}


def _merge_role_steps(*maps: dict[str, set[str]]) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = {}
    for mapping in maps:
        for role, steps in mapping.items():
            merged.setdefault(role, set()).update(steps)
    return merged


# When the flag is on, the granular machine is a SUPERSET of the legacy one:
# legacy actions/stages/ownership stay valid so the existing (unmodified) screens
# and any in-flight legacy records keep working, while the finer granular stages
# are added. Step ids and action names never collide between the two machines, so
# a plain dict merge is safe; role keys do collide, so those are unioned per role.
_ALL_TRANSITIONS = {**WORKFLOW_TRANSITIONS, **GRANULAR_WORKFLOW_TRANSITIONS}
_ALL_STEP_IDS = WORKFLOW_STEP_IDS | GRANULAR_WORKFLOW_STEP_IDS
_ALL_STEPS = [*WORKFLOW_STEPS, *GRANULAR_WORKFLOW_STEPS]
_ALL_STAGE_OWNER_ROLES = {**_LEGACY_STAGE_OWNER_ROLES, **GRANULAR_STAGE_OWNER_ROLES}
_ALL_VISIBLE_STEPS = _merge_role_steps(ROLE_VISIBLE_STEPS, GRANULAR_ROLE_VISIBLE_STEPS)


def granular_enabled() -> bool:
    # Lazy import avoids a config<->service import cycle and keeps the flag
    # re-readable after get_settings.cache_clear() in tests.
    from app.config import get_settings

    return get_settings().enable_granular_workflow


def active_steps() -> list[dict[str, str]]:
    return _ALL_STEPS if granular_enabled() else WORKFLOW_STEPS


def active_step_ids() -> set[str]:
    return _ALL_STEP_IDS if granular_enabled() else WORKFLOW_STEP_IDS


def active_transitions() -> dict[str, dict]:
    return _ALL_TRANSITIONS if granular_enabled() else WORKFLOW_TRANSITIONS


def active_default_step() -> str:
    # New enquiries created while the flag is on start in the granular machine.
    return DEFAULT_GRANULAR_STEP if granular_enabled() else DEFAULT_WORKFLOW_STEP


def _active_visible_steps() -> dict[str, set[str]]:
    return _ALL_VISIBLE_STEPS if granular_enabled() else ROLE_VISIBLE_STEPS


def stage_owner_roles(step_id: str) -> set[str]:
    table = _ALL_STAGE_OWNER_ROLES if granular_enabled() else _LEGACY_STAGE_OWNER_ROLES
    return table.get(step_id, set())


def can_act_on_step(role: str, step_id: str) -> bool:
    """Whether a role may act on an enquiry parked at the given step. Admin
    always may; otherwise the role must own the current stage."""
    return role == "admin" or role in stage_owner_roles(step_id)


def visible_steps_for_role(role: str) -> set[str]:
    return _active_visible_steps().get(role, set())


def canonical_workflow_step(step: str) -> str:
    """Map a stored step id onto the current machines: retired 13-step ids read
    as the surviving state that now covers that work."""
    return RETIRED_GRANULAR_STEPS.get(step, step)


def current_workflow_step(stage_meta: dict | None) -> str:
    step = canonical_workflow_step(str((stage_meta or {}).get("workflow_stage") or "").strip())
    # Accept ids from either machine so legacy records stay readable if the flag
    # is flipped on; unknown/empty falls back to the active machine's default.
    if step in WORKFLOW_STEP_IDS or step in GRANULAR_WORKFLOW_STEP_IDS:
        return step
    return active_default_step()


def can_perform(action: str, role: str) -> bool:
    rule = active_transitions().get(action)
    if not rule:
        return False
    return role == "admin" or role in rule["roles"]


# The technical-review conversation: the reviewer returns a spec with an error
# list, estimation replies saying what it changed, and the enquiry comes back for
# a re-check. Every note in this loop is worth reading side by side, so the UI
# rebuilds the thread from the history_log by filtering on these actions.
REVIEW_LOOP_ACTIONS: tuple[str, ...] = (
    "send_to_technical_review",
    "return_spec_errors",
    "return_tr_spec",
)


def last_workflow_action(stage_meta: dict | None) -> str:
    """The action name of the most recent handoff, or "" for a fresh enquiry."""
    granular = (stage_meta or {}).get("granular_workflow") or {}
    history = granular.get("history_log") or []
    if not isinstance(history, list) or not history:
        return ""
    last = history[-1]
    if not isinstance(last, dict):
        return ""
    return str(last.get("action") or "")


def required_comment_reason(transition: dict, stage_meta: dict | None) -> str:
    """Why this handoff needs a note, or "" when the note is optional.

    Some handoffs always need one (the reviewer's error list). Others only need
    one on a repeat trip — estimation re-submitting a spec the reviewer returned
    must say what it changed.
    """
    always = transition.get("require_comment")
    if always:
        return str(always)
    conditional = transition.get("require_comment_after") or {}
    return str(conditional.get(last_workflow_action(stage_meta)) or "")


# ---------------------------------------------------------------------------
# Pricing formulas
#
# The pricing desk works off the quotation summary: the line items collapse into
# one row per spec and a rate formula is written against each row (stored on
# stage_meta.pricing_formulas by the portal). Estimation then prices every line
# against its spec's formula and raises the process for those materials — so an
# enquiry must not reach estimation with specs left unpriced.
# ---------------------------------------------------------------------------

PRICING_FORMULA_KEY = "pricing_formulas"


def pricing_formula_gap(stage_meta: dict | None, items: list[dict] | None) -> str:
    """Why this enquiry is not ready to leave the pricing desk, or "".

    Nothing to price (no items, or every line regretted) is not a gap: the
    release goes through and the formula table stays empty.
    """
    priceable = [item for item in (items or []) if (item or {}).get("status") != "regret"]
    if not priceable:
        return ""
    record = (stage_meta or {}).get(PRICING_FORMULA_KEY)
    rows = record.get("rows") if isinstance(record, dict) else None
    if not isinstance(rows, list) or not rows:
        return (
            "Enter a pricing formula against every spec on the quotation summary "
            "before sending this enquiry to estimation"
        )
    missing = [
        str((row or {}).get("item") or "")
        for row in rows
        if not str((row or {}).get("formula") or "").strip()
    ]
    if missing:
        return f"{len(missing)} spec(s) still have no pricing formula: {'; '.join(filter(None, missing))[:400]}"
    if isinstance(record, dict) and record.get("stale") is True:
        return (
            "The line items changed after these formulas were entered — "
            "review the quotation summary and re-save the formulas"
        )
    return ""


# ---------------------------------------------------------------------------
# Mandatory enquiry details
#
# Estimation files the enquiry and owns its header. Every team after it — the
# reviewer, the pricing desk, sales — plus the enquiry register and the
# quotation itself read those fields, and none of them can recover one that was
# left blank. So an incomplete enquiry does not move on: not into spec check,
# and not into any later step. The rule lives in one table so tightening or
# relaxing it is a one-line edit.
# ---------------------------------------------------------------------------

# (label, sources) per mandatory detail. A detail counts as filled when ANY of
# its sources carries text: "quote" reads a top-level record field, "quote_data"
# the quotation payload, "stage_meta" the enquiry metadata. Several details are
# captured in more than one place (choosing a customer master fills the name,
# choosing a contact fills the person), so any one source is enough.
#
# Deliberately NOT required: the internal notes and the Outlook thread (the form
# marks both optional), the customer's own RFQ number (not every customer sends
# one), and priority/enquiry stage (the system applies a default).
REQUIRED_ENQUIRY_DETAILS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Customer", (("quote", "customer"), ("stage_meta", "customer_master_id"))),
    ("Contact person", (("quote_data", "attention"), ("stage_meta", "customer_contact_id"))),
    ("Contact person email", (("quote_data", "email"),)),
    ("Contact number", (("quote_data", "contact_no"), ("quote_data", "mobile_no"), ("quote_data", "telephone_no"))),
    ("Email subject", (("quote", "custom_label"),)),
    ("Enquiry reference", (("quote", "quote_no"),)),
    ("Quote type (export or domestic)", (("stage_meta", "market_type"),)),
    ("Bidding or firm", (("stage_meta", "bid_type"),)),
    ("Project name", (("quote", "project_ref"),)),
    ("Country", (("stage_meta", "country"),)),
    ("City", (("stage_meta", "city"),)),
    ("EPC / project company", (("stage_meta", "epc_name"),)),
    ("Sales rep", (("stage_meta", "owner_id"),)),
    ("Due date", (("stage_meta", "due_date"),)),
)

LINE_ITEMS_DETAIL_LABEL = "Line items (at least one)"

# The handoffs that stay open while details are missing: the ones whose whole
# point is to GET the enquiry corrected — a query to the customer, its answer, a
# spec the reviewer sent back. Anything absent from this set is gated, so a
# transition added later is mandatory-by-default.
DETAIL_GATE_EXEMPT_ACTIONS: frozenset[str] = frozenset(
    {
        "raise_customer_query",
        "answer_customer_query",
        "return_spec_errors",
        # Legacy-machine equivalents: both return the enquiry to the team that
        # has to fix the specs.
        "return_to_estimation",
        "pricing_to_technical",
    }
)


def _detail_value(quote: Any, source: str, key: str) -> str:
    if source == "quote":
        return str(getattr(quote, key, "") or "").strip()
    container = getattr(quote, source, None)
    if not isinstance(container, dict):
        return ""
    return str(container.get(key) or "").strip()


def enquiry_detail_gaps(quote: Any) -> list[str]:
    """The mandatory enquiry details still blank on this record, by label.

    `quote` is anything with the QuoteRead surface (the top-level fields plus
    quote_data / stage_meta dicts) — duck-typed so this module keeps its
    schema-free imports. Records fetched as list summaries carry no line items,
    so the item count is read from n_items when items are absent.
    """
    gaps = [
        label
        for label, sources in REQUIRED_ENQUIRY_DETAILS
        if not any(_detail_value(quote, source, key) for source, key in sources)
    ]
    items = getattr(quote, "items", None) or []
    try:
        n_items = int(getattr(quote, "n_items", 0) or 0)
    except (TypeError, ValueError):
        n_items = 0
    if not items and not n_items:
        gaps.append(LINE_ITEMS_DETAIL_LABEL)
    return gaps


def enquiry_detail_blockers(action: str, quote: Any) -> list[str]:
    """The mandatory details holding this handoff back — empty when it may go.

    Exempt handoffs return no blockers however incomplete the enquiry is: they
    are the route to getting it completed.
    """
    if action in DETAIL_GATE_EXEMPT_ACTIONS:
        return []
    return enquiry_detail_gaps(quote)


DETAIL_GATE_MESSAGE = (
    "Fill in every enquiry detail before this enquiry can move forward — "
    "open Enquiry setup to complete the missing ones"
)
