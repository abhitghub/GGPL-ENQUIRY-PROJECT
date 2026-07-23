"""Enquiry -> priced-specs handoff pipeline.

Models the team-ownership flow: Sales files the enquiry, Estimation checks it and
either builds the specs itself or hands off to Technical review (which returns to
Estimation), Estimation sends the GGPL-format specs to pricing (Ashwin sir), and
the priced specs come back to Sales to send to the customer.

This is a lightweight status layer stored in stage_meta.workflow_stage; it does not
replace the primary quote.stage machine.
"""

from __future__ import annotations

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
# Granular 11-stage machine (additive; active only when ENABLE_GRANULAR_WORKFLOW).
#
# This refines the 6-step flow above into the full business process without
# renaming or removing any legacy step, transition, field, or role. When the
# feature flag is off, every accessor below returns the legacy structures and
# behaviour is byte-identical to the original engine.
# ---------------------------------------------------------------------------

GRANULAR_WORKFLOW_STEPS: list[dict[str, str]] = [
    {"id": "enquiry_received", "label": "Enquiry received", "team": "Estimation"},
    {"id": "forwarded_to_estimation", "label": "Forwarded to estimation", "team": "Estimation"},
    {"id": "spec_check", "label": "Spec check", "team": "Estimation"},
    {"id": "query_raised_to_customer", "label": "Query raised to customer", "team": "Sales"},
    {"id": "converted_to_ggpl_format", "label": "Converted to GGPL format", "team": "Estimation"},
    {"id": "gasket_type_check", "label": "Gasket type check", "team": "Estimation"},
    {"id": "technical_review_pending", "label": "Technical review pending", "team": "Technical review"},
    {"id": "combined_spec_review", "label": "Combined spec review", "team": "Estimation"},
    {"id": "sent_for_pricing", "label": "Sent for pricing", "team": "Admin"},
    {"id": "pricing_decision", "label": "Pricing (estimation)", "team": "Estimation"},
    {"id": "pricing_submitted", "label": "Ready to generate", "team": "Sales / Admin"},
    {"id": "quotation_generated", "label": "Quotation generated", "team": "Sales"},
    {"id": "quotation_sent_to_customer", "label": "Quotation sent to customer", "team": "Sales"},
]

GRANULAR_WORKFLOW_STEP_IDS = {step["id"] for step in GRANULAR_WORKFLOW_STEPS}
DEFAULT_GRANULAR_STEP = "enquiry_received"

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
    # owns the first handoff.
    "forward_to_estimation": {
        "from": {"enquiry_received"},
        "roles": {"estimation", "management"},
        "to": "forwarded_to_estimation",
        "with_whom": "Estimation",
        "label": "Forward to estimation",
    },
    "begin_spec_check": {
        "from": {"forwarded_to_estimation"},
        "roles": {"estimation"},
        "to": "spec_check",
        "with_whom": "Estimation",
        "label": "Begin spec check",
    },
    # branch A: specs incomplete -> customer query loop
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
    # branch B: specs complete
    "mark_spec_complete": {
        "from": {"spec_check"},
        "roles": {"estimation"},
        "to": "converted_to_ggpl_format",
        "with_whom": "Estimation",
        "label": "Mark spec complete",
    },
    "proceed_to_gasket_check": {
        "from": {"converted_to_ggpl_format"},
        "roles": {"estimation"},
        "to": "gasket_type_check",
        "with_whom": "Estimation",
        "label": "Proceed to gasket type check",
    },
    # Estimation runs the gasket type check and the enquiry goes to the
    # technical review team — TR is not bypassed.
    "run_gasket_type_check": {
        "from": {"gasket_type_check"},
        "roles": {"estimation"},
        "to": "technical_review_pending",
        "with_whom": "Technical review",
        "label": "Run gasket type check",
    },
    # Estimation may also route to technical review from the combined review
    # (either send for pricing or send for technical review).
    "send_to_technical_review": {
        "from": {"combined_spec_review"},
        "roles": {"estimation"},
        "to": "technical_review_pending",
        "with_whom": "Technical review",
        "label": "Send for technical review",
    },
    # Only technical can view/forward an enquiry that is up for technical
    # review — it moves it ahead to the combined spec review.
    "return_tr_spec": {
        "from": {"technical_review_pending"},
        "roles": {"technical"},
        "to": "combined_spec_review",
        "with_whom": "Estimation",
        "label": "Technical review done — forward",
    },
    "submit_for_pricing": {
        "from": {"combined_spec_review"},
        "roles": {"estimation"},
        "to": "sent_for_pricing",
        "with_whom": "Admin",
        "label": "Submit for pricing",
    },
    # Admin sets the pricing formula (in the enquiry notes) and hands the enquiry
    # back to estimation to price against it — admin does not price directly.
    "open_pricing": {
        "from": {"sent_for_pricing"},
        "roles": {"admin", "management"},
        "to": "pricing_decision",
        "with_whom": "Estimation",
        "label": "Set pricing formula & send to estimation",
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
    "estimation": {
        "enquiry_received",
        "forwarded_to_estimation",
        "spec_check",
        "converted_to_ggpl_format",
        "gasket_type_check",
        "combined_spec_review",
        # estimation prices the enquiry (admin sets the formula); it does not
        # generate the quotation — sales/admin do.
        "pricing_decision",
    },
    "technical": {"technical_review_pending"},
    "admin": {"sent_for_pricing", "pricing_submitted"},
    "management": set(GRANULAR_WORKFLOW_STEP_IDS),
}

# Single RBAC source of truth: which roles may ACT on / edit an enquiry parked at
# each granular step. Enforced at the API layer via can_act_on_step(); blocks
# out-of-stage edits even when a transition's role set is broad. `management`
# retained everywhere for back-compat; `admin` bypasses in code regardless.
GRANULAR_STAGE_OWNER_ROLES: dict[str, set[str]] = {
    "enquiry_received": {"estimation", "management"},
    "forwarded_to_estimation": {"estimation", "management"},
    "spec_check": {"estimation", "management"},
    "query_raised_to_customer": {"sales", "management"},
    "converted_to_ggpl_format": {"estimation", "management"},
    "gasket_type_check": {"estimation", "management"},
    "technical_review_pending": {"technical", "management"},
    "combined_spec_review": {"estimation", "management"},
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


def current_workflow_step(stage_meta: dict | None) -> str:
    step = str((stage_meta or {}).get("workflow_stage") or "").strip()
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
