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
    {"id": "enquiry_received", "label": "Enquiry received", "team": "Sales"},
    {"id": "forwarded_to_estimation", "label": "Forwarded to estimation", "team": "Estimation"},
    {"id": "spec_check", "label": "Spec check", "team": "Estimation"},
    {"id": "query_raised_to_customer", "label": "Query raised to customer", "team": "Sales"},
    {"id": "converted_to_ggpl_format", "label": "Converted to GGPL format", "team": "Estimation"},
    {"id": "gasket_type_check", "label": "Gasket type check", "team": "Estimation"},
    {"id": "technical_review_pending", "label": "Technical review pending", "team": "Technical review"},
    {"id": "tr_spec_returned", "label": "TR spec returned", "team": "Estimation"},
    {"id": "combined_spec_review", "label": "Combined spec review", "team": "Estimation"},
    {"id": "sent_for_pricing", "label": "Sent for pricing", "team": "Admin"},
    {"id": "pricing_decision", "label": "Pricing decision", "team": "Admin"},
    {"id": "quotation_generated", "label": "Quotation generated", "team": "Admin"},
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
    "forward_to_estimation": {
        "from": {"enquiry_received"},
        "roles": {"sales", "management"},
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
    # stage 5 conditional auto-branch: specific gasket types route to technical
    # review, everything else skips straight to combined spec review. The "to"
    # key holds the safe default for any branch-unaware reader.
    "run_gasket_type_check": {
        "from": {"gasket_type_check"},
        "roles": {"estimation"},
        "branch": {
            "field": "gasket_type",
            "specific": "technical_review_pending",
            "default": "combined_spec_review",
        },
        "to": "combined_spec_review",
        "with_whom": "Estimation",
        "label": "Run gasket type check",
    },
    "return_tr_spec": {
        "from": {"technical_review_pending"},
        "roles": {"technical"},
        "to": "tr_spec_returned",
        "with_whom": "Estimation",
        "label": "Return TR spec to estimation",
    },
    "combine_after_tr": {
        "from": {"tr_spec_returned"},
        "roles": {"estimation"},
        "to": "combined_spec_review",
        "with_whom": "Estimation",
        "label": "Combine specs",
    },
    "submit_for_pricing": {
        "from": {"combined_spec_review"},
        "roles": {"estimation"},
        "to": "sent_for_pricing",
        "with_whom": "Admin",
        "label": "Submit for pricing",
    },
    "open_pricing": {
        "from": {"sent_for_pricing"},
        "roles": {"admin", "management"},
        "to": "pricing_decision",
        "with_whom": "Admin",
        "label": "Open pricing",
    },
    # stage 9 domestic/international split -> two sibling actions converging on
    # quotation_generated, each recording the chosen route.
    "price_domestic": {
        "from": {"pricing_decision"},
        "roles": {"admin", "management"},
        "to": "quotation_generated",
        "with_whom": "Admin",
        "label": "Price (domestic)",
        "set": {"pricing_route": "domestic"},
    },
    "price_international": {
        "from": {"pricing_decision"},
        "roles": {"admin", "management"},
        "to": "quotation_generated",
        "with_whom": "Admin",
        "label": "Price (international)",
        "set": {"pricing_route": "international"},
    },
    # Admin owns the generated quotation and releases it to the customer; the
    # resulting stage is terminal (nobody acts further).
    "send_quotation": {
        "from": {"quotation_generated"},
        "roles": {"admin", "management"},
        "to": "quotation_sent_to_customer",
        "with_whom": "Sales",
        "label": "Send quotation to customer",
    },
}


# Which granular steps a back-office role may see regardless of record ownership.
# Sales/viewer stay owner-scoped; admin sees everything already; management stays
# omniscient (mirrors the legacy map).
GRANULAR_ROLE_VISIBLE_STEPS: dict[str, set[str]] = {
    "estimation": {
        "forwarded_to_estimation",
        "spec_check",
        "converted_to_ggpl_format",
        "gasket_type_check",
        "tr_spec_returned",
        "combined_spec_review",
    },
    "technical": {"technical_review_pending"},
    "admin": {"sent_for_pricing", "pricing_decision", "quotation_generated"},
    "management": set(GRANULAR_WORKFLOW_STEP_IDS),
}

# Single RBAC source of truth: which roles may ACT on / edit an enquiry parked at
# each granular step. Enforced at the API layer via can_act_on_step(); blocks
# out-of-stage edits even when a transition's role set is broad. `management`
# retained everywhere for back-compat; `admin` bypasses in code regardless.
GRANULAR_STAGE_OWNER_ROLES: dict[str, set[str]] = {
    "enquiry_received": {"sales", "management"},
    "forwarded_to_estimation": {"estimation", "management"},
    "spec_check": {"estimation", "management"},
    "query_raised_to_customer": {"sales", "management"},
    "converted_to_ggpl_format": {"estimation", "management"},
    "gasket_type_check": {"estimation", "management"},
    "technical_review_pending": {"technical", "management"},
    "tr_spec_returned": {"estimation", "management"},
    "combined_spec_review": {"estimation", "management"},
    "sent_for_pricing": {"admin", "management"},
    "pricing_decision": {"admin", "management"},
    "quotation_generated": {"admin", "management"},
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


def granular_enabled() -> bool:
    # Lazy import avoids a config<->service import cycle and keeps the flag
    # re-readable after get_settings.cache_clear() in tests.
    from app.config import get_settings

    return get_settings().enable_granular_workflow


def active_steps() -> list[dict[str, str]]:
    return GRANULAR_WORKFLOW_STEPS if granular_enabled() else WORKFLOW_STEPS


def active_step_ids() -> set[str]:
    return GRANULAR_WORKFLOW_STEP_IDS if granular_enabled() else WORKFLOW_STEP_IDS


def active_transitions() -> dict[str, dict]:
    return GRANULAR_WORKFLOW_TRANSITIONS if granular_enabled() else WORKFLOW_TRANSITIONS


def active_default_step() -> str:
    return DEFAULT_GRANULAR_STEP if granular_enabled() else DEFAULT_WORKFLOW_STEP


def _active_visible_steps() -> dict[str, set[str]]:
    return GRANULAR_ROLE_VISIBLE_STEPS if granular_enabled() else ROLE_VISIBLE_STEPS


def stage_owner_roles(step_id: str) -> set[str]:
    table = GRANULAR_STAGE_OWNER_ROLES if granular_enabled() else _LEGACY_STAGE_OWNER_ROLES
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
