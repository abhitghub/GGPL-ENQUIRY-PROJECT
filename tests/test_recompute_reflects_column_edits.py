"""A recompute must reflect the columns as they are NOW.

When estimation (or management, or admin) corrects a spec column in the portal,
the row is re-run through `apply_rules` and re-described. That only works if the
engine's *derived* outputs are rebuilt from the current field values rather than
carried over from the stored row.

`flags` always worked that way. `escalation`, `deviation_notes` and
`applied_defaults` did not, and `escalation` was the damaging one: the phrase IS
the GGPL description (see `describe_item`), so once a row escalated the operator
could fill in every missing column and the GGPL Description cell would never
change — and the status stayed `missing` forever.
"""
from core.formatter import describe_item
from core.rules import apply_rules

_UNDESCRIBABLE = "SPIRAL WOUND GASKET ASME B16.20"  # no size, rating or material


def _process(item: dict) -> dict:
    out = apply_rules(dict(item))
    out["ggpl_description"] = describe_item(out)
    return out


def _row(description: str, **extra) -> dict:
    return _process({
        "line_no": 1,
        "quantity": 2,
        "uom": "NOS",
        "is_gasket": True,
        "raw_description": description,
        **extra,
    })


def test_escalated_row_describes_normally_once_the_columns_are_filled_in():
    escalated = _row(_UNDESCRIBABLE)
    assert escalated["escalation"]
    assert escalated["ggpl_description"] == escalated["escalation"]
    assert escalated["status"] == "missing"

    # The operator supplies what the customer left out — as the portal does:
    # edited fields are recorded in manual_fields and the row is recomputed.
    fixed = _process({
        **escalated,
        "size": '2"',
        "rating": "300#",
        "moc": "SS316",
        "sw_winding_material": "SS316",
        "sw_filler": "GRAPHITE",
        "sw_outer_ring": "CS",
        "manual_fields": ["size", "rating", "moc", "sw_winding_material", "sw_filler", "sw_outer_ring"],
    })

    assert not fixed.get("escalation")
    assert fixed["ggpl_description"] != escalated["ggpl_description"]
    assert 'SIZE : 2" X 300#' in fixed["ggpl_description"]
    assert "SS316 SPIRAL WOUND GASKET" in fixed["ggpl_description"]
    assert fixed["status"] != "missing"


def test_recomputing_an_unedited_row_keeps_its_escalation():
    """Dropping the stored escalation must not make escalations un-raisable:
    a row nobody corrected escalates again on every run, with the same phrase."""
    once = _row(_UNDESCRIBABLE)
    twice = _process(once)
    assert twice["escalation"] == once["escalation"]
    assert twice["ggpl_description"] == once["ggpl_description"]
    assert twice["status"] == once["status"]


def test_stale_deviation_notes_do_not_survive_the_fix_that_removed_them():
    """A deviation is a consequence of the row's current values. Once the
    operator supplies what was defaulted, the old register line must go — an
    operator-worded Deviation cell still wins (manual_fields)."""
    defaulted = _row('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER')
    assert defaulted.get("deviation_notes")

    stated = _process({
        **defaulted,
        "standard": "ASME B16.20",
        "sw_inner_ring": "SS316",
        "sw_outer_ring": "CS",
        "manual_fields": ["standard", "sw_inner_ring", "sw_outer_ring"],
    })
    assert stated.get("deviation_notes", []) != defaulted["deviation_notes"]
    for note in stated.get("deviation_notes", []):
        assert note in (stated["deviation"] or "")


def test_applied_defaults_are_rewritten_every_run():
    """A row that stops needing a default must stop advertising it."""
    defaulted = _row('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER')
    assert defaulted["applied_defaults"]

    stated = _process({
        **defaulted,
        "standard": "ASME B16.20",
        "sw_inner_ring": "SS316",
        "sw_outer_ring": "CS",
        "manual_fields": ["standard", "sw_inner_ring", "sw_outer_ring"],
    })
    assert "standard defaulted to ASME B16.20" not in stated["applied_defaults"]
