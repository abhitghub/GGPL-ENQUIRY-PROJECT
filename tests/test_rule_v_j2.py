"""RULE J-2 (spaced abbreviations + element-vs-overall OD/ID) and RULE V
(standards selection engine: OD x ID law, construction-only citations,
unknown-standard catch-all, legacy typo normalization) regression fixtures."""
from core.formatter import format_description
from core.parser import (
    _collapse_spaced_abbrevs,
    _enrich_from_description,
    _infer_gasket_type,
    _standard_from_text,
)
from core.rules import FLAG_SW_ELEMENT_VS_OVERALL, apply_rules


def _process(item: dict) -> dict:
    out = apply_rules(dict(item))
    out["ggpl_description"] = format_description(out)
    return out


# ---------------------------------------------------------------------------
# RULE J-2 Part 1 — space-tolerant abbreviation matching
# ---------------------------------------------------------------------------

def test_spaced_spwd_collapses_and_classifies():
    text = "SS304 S P W D WITH SS INNER AND OUTER RING"
    assert _collapse_spaced_abbrevs(text) == "SS304 SPWD WITH SS INNER AND OUTER RING"
    assert _infer_gasket_type(text) == "SPIRAL_WOUND"


def test_spaced_abbrev_period_variants():
    assert _collapse_spaced_abbrevs("GASKET R.T.J SOFT IRON") == "GASKET RTJ SOFT IRON"
    assert _collapse_spaced_abbrevs("C N A F GASKET FULL FACE") == "CNAF GASKET FULL FACE"
    assert _infer_gasket_type('GASKET S.W.G 2" 300#') == "SPIRAL_WOUND"


def test_collapse_guard_never_touches_words_or_dimensions():
    for text in (
        "SS INNER RING",          # real words stay separate tokens
        "4 MM THK",               # dimensions untouched
        "TYPE A OR B",            # natural single letters untouched
        "GRADE X Y Z",            # unknown run left alone
        "BS 7531 GR X",           # material grade untouched
    ):
        assert _collapse_spaced_abbrevs(text) == text


def test_enrich_spaced_spwd_line_end_to_end():
    item = _enrich_from_description({
        "raw_description": "GASKET SS304 S P W D WITH SS INNER AND OUTER RING 4.5 THK OD 2126 X ID 2100",
    })
    assert item["gasket_type"] == "SPIRAL_WOUND"


# ---------------------------------------------------------------------------
# RULE J-2 Part 2 — element-vs-overall OD/ID confirmation (ringed SPW, W3)
# ---------------------------------------------------------------------------

_HX_SPW = {
    "gasket_type": "SPIRAL_WOUND",
    "size_type": "OD_ID",
    "od_mm": 2126,
    "id_mm": 2100,
    "thickness_mm": 4.5,
    "sw_winding_material": "SS304",
    "sw_filler": "GRAPHITE",
    "sw_inner_ring": "SS304",
    "sw_outer_ring": "SS304",
    "raw_description": "SS304 SPWD WITH SS INNER AND OUTER RING 2126 OD X 2100 ID X 4.5 THK",
}


def test_ringed_spw_bare_od_id_gets_confirmation_flag():
    item = _process(_HX_SPW)
    assert FLAG_SW_ELEMENT_VS_OVERALL in item["flags"]
    # Coherent HX geometry (13MM width, 4.5MM THK) passes silently
    assert not any("coherence" in f.lower() for f in item["flags"])


def test_dims_only_spw_gets_no_defaulted_standard():
    # RULE V OD x ID law: no size+class -> no dimensional standard defaulted
    item = _process(_HX_SPW)
    assert not item.get("standard")
    assert "ASME" not in item["ggpl_description"]


def test_drawing_reference_suppresses_confirmation_flag():
    item = _process({
        **_HX_SPW,
        "raw_description": _HX_SPW["raw_description"] + " AS PER DRAWING DWG-4711",
    })
    assert FLAG_SW_ELEMENT_VS_OVERALL not in item["flags"]


def test_disambiguated_text_suppresses_confirmation_flag():
    item = _process({
        **_HX_SPW,
        "raw_description": "SS304 SPWD WITH SS INNER AND OUTER RING WINDING OD 2126 X ID 2100",
    })
    assert FLAG_SW_ELEMENT_VS_OVERALL not in item["flags"]


def test_od_id_coherence_advisory_fires_on_suspect_geometry():
    # 5MM radial width on a 600MM gasket with 6MM THK -> verify note
    item = _process({
        **_HX_SPW,
        "od_mm": 600,
        "id_mm": 590,
        "thickness_mm": 6,
    })
    assert any("coherence" in f.lower() for f in item["flags"])


# ---------------------------------------------------------------------------
# RULE V — standards selection engine
# ---------------------------------------------------------------------------

_SOFT_CUT_NPS = {
    "gasket_type": "SOFT_CUT",
    "size": '2"',
    "rating": "150#",
    "moc": "CNAF",
    "thickness_mm": 3,
}


def test_unknown_standard_kept_verbatim_and_flagged():
    item = _process({**_SOFT_CUT_NPS, "standard": "JIS B 2404"})
    assert item["standard"] == "JIS B 2404"
    assert any("NOT IN GGPL LIBRARY" in f for f in item["flags"])
    assert item["status"] != "ready"


def test_known_library_standards_do_not_fire_catchall():
    for std in (
        "ASME B16.20",
        "ASME B16.21",
        "ASME B16.47 (SERIES-A)",
        "EN 1514-1",
        "API 6A",
        "NACE MR-01-75 / ISO 15156, API 6B",
        "TO SUIT ASME B16.5",
    ):
        item = _process({**_SOFT_CUT_NPS, "standard": std})
        assert not any("NOT IN GGPL LIBRARY" in f for f in item["flags"]), std


def test_dims_only_spw_with_cited_b1620_becomes_construction_reference():
    item = _process({
        "gasket_type": "SPIRAL_WOUND",
        "size_type": "OD_ID",
        "od_mm": 669,
        "id_mm": 643,
        "thickness_mm": 4.5,
        "sw_winding_material": "SS304L",
        "standard": "ASME B16.20",
        "raw_description": "OD 669/643 X 4.5T SS304L SPWD ASME B16.20",
    })
    assert item["standard"] == "NON STANDARD"
    assert any("CONSTRUCTION PER ASME B16.20" in n for n in item.get("deviation_notes", []))
    assert "ASME B16.20" not in item["ggpl_description"]


def test_soft_cut_od_id_keeps_ground_truth_b1621_convention():
    # Pinned behavior: the OD x ID conversion is scoped to SPW/DJI/KAMM —
    # soft cut keeps its ground-truth B16.21 default (test_non_standard.py)
    item = _process({
        "gasket_type": "SOFT_CUT",
        "size_type": "OD_ID",
        "od_mm": 35,
        "id_mm": 30,
        "thickness_mm": 3,
        "moc": "SOFT IRON",
        "raw_description": "GSKT,PLUG,35ODX30IDX2MM,SOFT IRON",
    })
    assert item["ggpl_description"].endswith("ASME B16.21")


def test_legacy_standard_typos_normalize():
    assert _standard_from_text("ASME B16..20") == "ASME B16.20"
    assert _standard_from_text("B-16.21") == "ASME B16.21"
    assert _standard_from_text("ASME 16.20") == "ASME B16.20"
    assert _standard_from_text("ASME B16.47 SERIES A") == "ASME B16.47 (SERIES-A)"


def test_obsolete_standard_in_field_replaced_with_successor():
    item = _process({
        "gasket_type": "SPIRAL_WOUND",
        "size": '8"',
        "rating": "300#",
        "sw_winding_material": "SS316",
        "standard": "API 601",
        "raw_description": 'SPIRAL WOUND GASKET 8" 300# CONFIRMING TO API 601',
    })
    assert item["standard"] == "ASME B16.20"
    assert any("SUPERSEDED" in n for n in item.get("deviation_notes", []))
    assert not any("NOT IN GGPL LIBRARY" in f for f in item["flags"])
