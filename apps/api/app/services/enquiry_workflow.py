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


def visible_steps_for_role(role: str) -> set[str]:
    return ROLE_VISIBLE_STEPS.get(role, set())


def current_workflow_step(stage_meta: dict | None) -> str:
    step = str((stage_meta or {}).get("workflow_stage") or "").strip()
    return step if step in WORKFLOW_STEP_IDS else DEFAULT_WORKFLOW_STEP


def can_perform(action: str, role: str) -> bool:
    rule = WORKFLOW_TRANSITIONS.get(action)
    if not rule:
        return False
    return role == "admin" or role in rule["roles"]
