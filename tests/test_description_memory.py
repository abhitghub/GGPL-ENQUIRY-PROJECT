"""Rule L — the portal learns from what the team corrects.

These cover the pure layer: what counts as "the same wording", what a learned
entry is allowed to change on a row, and what it must leave alone.
"""

from core.description_memory import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    DescriptionMemory,
    LearnedEntry,
    apply_match,
    changed_fields,
    descriptions_differ,
    entry_from_item,
    fingerprint,
    normalize_source_text,
    source_text_of,
)

SPW_ROW = '2" 150# SPIRAL WOUND GASKET, SS316 GRAPHITE, CS OUTER RING'


def _entry(**overrides) -> LearnedEntry:
    base = dict(
        id="e1",
        fingerprint=fingerprint(SPW_ROW),
        source_text=SPW_ROW,
        ggpl_description='SIZE : 2" X 150# X 4.5MM THK ,SS316 + GRAPHITE WITH CS OUTER RING ,ASME B16.20',
        fields={"gasket_type": "SPIRAL_WOUND", "sw_outer_ring": "CS"},
        status=STATUS_APPROVED,
        updated_at="2026-07-01T00:00:00+00:00",
    )
    base.update(overrides)
    return LearnedEntry(**base)


# --- what counts as the same wording ---------------------------------------

def test_case_spacing_and_punctuation_noise_key_the_same():
    assert fingerprint('2" 150# SPW,  SS316') == fingerprint('2"  150#  spw ,ss316')


def test_trailing_zero_decimals_key_the_same():
    """Excel writes 4.50 where a human writes 4.5 — the same gasket either way."""
    assert fingerprint("4.50MM THK") == fingerprint("4.5MM THK")
    assert fingerprint("150.0 NB") == fingerprint("150 NB")
    assert fingerprint("OD 1200.00 X ID 1150.") == fingerprint("OD 1200 X ID 1150")


def test_standard_citations_survive_decimal_normalization():
    """B16.20 must not collapse into B16.2 — the trailing zero is part of the name."""
    assert normalize_source_text("ASME B16.20") == "ASME B16.20"
    assert normalize_source_text("ASME B16.47 SERIES A") == "ASME B16.47 SERIES A"
    assert fingerprint("ASME B16.20 SPW") != fingerprint("ASME B16.2 SPW")


def test_significant_tokens_are_kept():
    """Grades, ratings and fractions are what distinguish two requests."""
    assert fingerprint("SS316 GASKET") != fingerprint("SS316L GASKET")
    assert fingerprint('1-1/2" 150#') != fingerprint('1-1/4" 150#')
    assert fingerprint("150#") != fingerprint("300#")


def test_normalization_keeps_size_separators_readable():
    assert normalize_source_text('2" × 150#, SS316') == '2 X 150# SS316'


def test_blank_wording_has_no_key():
    assert fingerprint("") == ""
    assert fingerprint("   ") == ""
    assert fingerprint(None) == ""


def test_source_text_prefers_the_customer_wording():
    item = {"raw_description": "customer text", "description": "llm echo"}
    assert source_text_of(item) == "customer text"
    assert source_text_of({"description": "llm echo"}) == "llm echo"
    assert source_text_of({}) == ""


# --- resolution -------------------------------------------------------------

def test_exact_wording_match_is_applied():
    memory = DescriptionMemory.build([_entry()])
    match = memory.resolve(SPW_ROW)
    assert match is not None
    assert match.kind == "exact"
    assert match.should_apply


def test_reordered_wording_is_a_suggestion_not_a_law():
    memory = DescriptionMemory.build([_entry()])
    match = memory.resolve('SS316 GRAPHITE, CS OUTER RING, SPIRAL WOUND GASKET 150# 2"')
    assert match is not None
    assert match.kind == "similar"
    assert not match.should_apply


def test_unrelated_wording_does_not_match():
    memory = DescriptionMemory.build([_entry()])
    assert memory.resolve('6" 300# CNAF 3MM GASKET') is None


def test_rejected_entries_are_never_applied_again():
    memory = DescriptionMemory.build([_entry(status=STATUS_REJECTED)])
    assert memory.resolve(SPW_ROW) is None
    assert not memory


def test_customer_scoped_knowledge_outranks_the_org_wide_rule():
    org_wide = _entry(id="global", ggpl_description="GLOBAL ANSWER")
    toyo = _entry(id="toyo", customer="Toyo Engineering", ggpl_description="TOYO ANSWER")
    memory = DescriptionMemory.build([org_wide, toyo])
    assert memory.resolve(SPW_ROW, "TOYO  ENGINEERING").entry.id == "toyo"
    assert memory.resolve(SPW_ROW, "HSEPL").entry.id == "global"
    assert memory.resolve(SPW_ROW).entry.id == "global"


def test_a_customer_scoped_entry_does_not_leak_to_other_customers():
    memory = DescriptionMemory.build([_entry(customer="Toyo Engineering")])
    assert memory.resolve(SPW_ROW, "HSEPL") is None
    assert memory.resolve(SPW_ROW) is None


def test_approved_entry_wins_over_a_pending_one_for_the_same_wording():
    pending = _entry(id="pending", status=STATUS_PENDING, updated_at="2026-07-30T00:00:00+00:00")
    approved = _entry(id="approved", status=STATUS_APPROVED, updated_at="2026-07-02T00:00:00+00:00")
    memory = DescriptionMemory.build([pending, approved])
    assert memory.resolve(SPW_ROW).entry.id == "approved"


# --- application ------------------------------------------------------------

def test_applying_a_match_writes_the_description_and_the_fields():
    item = {"raw_description": SPW_ROW, "ggpl_description": "WRONG ANSWER", "gasket_type": "SOFT_CUT"}
    memory = DescriptionMemory.build([_entry()])
    apply_match(item, memory.resolve(SPW_ROW))
    assert item["ggpl_description"].startswith('SIZE : 2"')
    assert item["gasket_type"] == "SPIRAL_WOUND"
    assert item["sw_outer_ring"] == "CS"
    assert item["learned_from"]["entry_id"] == "e1"
    assert any("PORTAL MEMORY" in flag for flag in item["flags"])


def test_a_learned_entry_never_overwrites_this_row_s_manual_edit():
    """The operator working this row outranks a rule learned from another one."""
    item = {
        "raw_description": SPW_ROW,
        "gasket_type": "KAMM",
        "ggpl_description": "OPERATOR WROTE THIS",
        "manual_fields": ["gasket_type", "ggpl_description"],
    }
    memory = DescriptionMemory.build([_entry()])
    apply_match(item, memory.resolve(SPW_ROW))
    assert item["gasket_type"] == "KAMM"
    assert item["ggpl_description"] == "OPERATOR WROTE THIS"
    # Fields the operator did not claim are still learned.
    assert item["sw_outer_ring"] == "CS"


def test_an_unapproved_entry_says_so_on_the_row():
    item = {"raw_description": SPW_ROW}
    memory = DescriptionMemory.build([_entry(status=STATUS_PENDING)])
    apply_match(item, memory.resolve(SPW_ROW))
    assert any("NOT YET APPROVED" in flag for flag in item["flags"])


def test_a_near_match_only_suggests():
    item = {"raw_description": 'SS316 GRAPHITE, CS OUTER RING, SPIRAL WOUND GASKET 150# 2"',
            "ggpl_description": "ENGINE ANSWER"}
    memory = DescriptionMemory.build([_entry()])
    apply_match(item, memory.resolve(item["raw_description"]))
    assert item["ggpl_description"] == "ENGINE ANSWER"
    assert item["learned_suggestion"]["entry_id"] == "e1"
    assert "learned_from" not in item


# --- capture ---------------------------------------------------------------

def test_changed_fields_reports_only_real_moves():
    before = {"gasket_type": "SOFT_CUT", "moc": "CNAF", "thickness_mm": 3.0}
    after = {"gasket_type": "SPIRAL_WOUND", "moc": "cnaf", "thickness_mm": 3, "sw_filler": "GRAPHITE"}
    assert changed_fields(before, after) == {"gasket_type": "SPIRAL_WOUND", "sw_filler": "GRAPHITE"}


def test_changed_fields_ignores_non_learnable_columns():
    """Quantity and line numbers are per-enquiry facts, not knowledge."""
    before = {"quantity": 2, "line_no": 1, "unit_price": 100}
    after = {"quantity": 40, "line_no": 7, "unit_price": 250}
    assert changed_fields(before, after) == {}


def test_descriptions_differ_ignores_case_and_spacing():
    assert not descriptions_differ("SIZE : 2 X 150#", "size :  2 x 150#")
    assert descriptions_differ("SIZE : 2 X 150#", "SIZE : 2 X 300#")


def test_entry_from_item_needs_wording_to_key_on():
    assert entry_from_item({"ggpl_description": "ANYTHING"}, entry_id="x") is None


def test_entry_from_item_needs_something_to_remember():
    assert entry_from_item({"raw_description": SPW_ROW}, entry_id="x") is None


def test_entry_from_item_captures_a_hand_written_description():
    entry = entry_from_item(
        {"raw_description": SPW_ROW, "ggpl_description": "HOUSE WORDING", "quantity": 40},
        entry_id="x",
        created_by="yuvashree",
    )
    assert entry is not None
    assert entry.ggpl_description == "HOUSE WORDING"
    assert entry.fingerprint == fingerprint(SPW_ROW)
    assert entry.created_by == "yuvashree"
    # Commercial columns are not knowledge and must not be stored.
    assert "quantity" not in entry.fields
