"""Regression fixtures for the three rules shipped together:

  RULE X-2 — multi-level (spanned) headers & unit-banner inheritance
  RULE Y    — Kammprofile conversion (thickness engine, core stock, geometry)
  RULE Z    — Spiral wound conversion (register, thickness guards, standards)

Each rule document ships a "REGRESSION FIXTURE" section; these are those
fixtures, plus the drift cases each rule says must not be reproduced.
"""
import io

import pandas as pd

from core.document_reader import (
    _banner_unit,
    _canonical_header,
    _excel_to_text,
    _is_group_banner,
    is_raw_mm_column,
)
from core.formatter import format_description, _fmt_size
from core.parser import _enrich_from_description, _infer_gasket_type
from core.rules import apply_rules


def _process(item: dict) -> dict:
    out = apply_rules(dict(item))
    out["ggpl_description"] = format_description(out)
    return out


def _enriched(description: str, **extra) -> dict:
    """Run the regex extractor first, as the real pipeline does, so these are
    end-to-end fixtures rather than hand-fed field sets."""
    base = _enrich_from_description({
        "description": description,
        "raw_description": description,
        "quantity": 1,
        "uom": "NOS",
    })
    base.update(extra)
    return _process(base)


def _spw(description: str, **extra) -> dict:
    extra.setdefault("gasket_type", "SPIRAL_WOUND")
    return _enriched(description, **extra)


def _kamm(description: str, **extra) -> dict:
    return _enriched(description, **extra)


# ===========================================================================
# RULE X-2 — spanned headers
# ===========================================================================

_NEOPRENE_BOQ = [
    (100, 3, 223, 60), (100, 3, 318, 24), (100, 5, 393, 8), (130, 5, 707, 4),
    (260, 5, 867, 14), (400, 10, 1716, 54), (540, 10, 4666, 13), (630, 10, 4666, 19),
    (540, 10, 5002, 29), (630, 10, 5002, 13), (680, 10, 5002, 4), (540, 10, 5640, 2),
    (630, 10, 5640, 3), (680, 10, 5640, 4), (540, 10, 5969, 26), (630, 10, 5969, 20),
    (680, 10, 5969, 3), (710, 10, 5969, 5),
]


def _neoprene_boq_bytes() -> bytes:
    rows = [
        ["SR.NO", "MATERIAL DESCRIPTION", "DIMENSION IN MM", "", "", "QTY"],
        ["", "", "WIDTH", "TRHICKNESS", "LENGTH", ""],
    ]
    for i, (w, t, l, q) in enumerate(_NEOPRENE_BOQ, 1):
        rows.append([str(i), "NEOPRENE RUBBER", str(w), str(t), str(l), str(q)])
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False, header=False)
    return buf.getvalue()


def test_x2_neoprene_boq_all_18_lines_survive_with_dimensions():
    """The reported failure: dimensions dropped because the sub-header columns
    were unnamed in row 1. All 18 lines must come through with all three dims.
    """
    text, truncated, count = _excel_to_text(_neoprene_boq_bytes())

    assert count == 18
    assert not truncated
    # Every dimension column bound by its own sub-header name.
    assert "WIDTH (MM)" in text
    assert "TRHICKNESS (MM)" in text
    assert "LENGTH (MM)" in text
    # Unit inherited from the banner, so no value is left unitless.
    for width, thk, length, qty in _NEOPRENE_BOQ:
        assert f"| {width}MM | {thk}MM | {length}MM | {qty} |" in text


def test_x2_qty_column_spanning_both_header_rows_is_not_given_a_unit():
    text, _, _ = _excel_to_text(_neoprene_boq_bytes())
    assert "| QTY |" in text
    # The QTY column is the last cell on every data row and must stay unitless.
    for line in text.splitlines():
        if line.startswith("| Sheet1 |"):
            last_cell = line.rstrip("| ").rsplit("|", 1)[-1].strip()
            assert last_cell.isdigit(), last_cell
    # RULE_X2 Part 4 asserts "total qty 315", but the 18 quantities it lists sum
    # to 305 (60+24+8+4+14+54+13+19+29+13+4+2+3+4+26+20+3+5). The line listing
    # is the authority here; the summary figure in the doc is off by 10.
    total = sum(row[3] for row in _NEOPRENE_BOQ)
    assert total == 305


def test_x2_count_mismatch_alone_triggers_a_multilevel_reread():
    """Part 1.3 — row 1 names N columns, data rows carry M > N. This is the
    reliable test, and it must fire without a recognised banner keyword.
    """
    rows = [
        ["SR", "DESC", "BLAH", "", ""],
        ["", "", "WIDTH", "THICKNESS", "LENGTH"],
        ["1", "NEOPRENE", "100", "3", "223"],
        ["2", "NEOPRENE", "130", "5", "707"],
    ]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False, header=False)
    text, _, count = _excel_to_text(buf.getvalue())
    assert count == 2
    assert "WIDTH" in text and "THICKNESS" in text and "LENGTH" in text


def test_x2_fuzzy_header_matching_binds_observed_misspellings():
    """Part 2.4 — an exact lookup fails on TRHICKNESS and loses a column."""
    assert _canonical_header("TRHICKNESS") == "THICKNESS"
    assert _canonical_header("THCKNESS") == "THICKNESS"
    assert _canonical_header("THIKNESS") == "THICKNESS"
    assert _canonical_header("LENGHT") == "LENGTH"
    assert _canonical_header("WITDH") == "WIDTH"
    assert _canonical_header("WIDHT") == "WIDTH"
    assert _canonical_header("QNTY") == "QTY"
    assert _canonical_header("DIAMETER") == "OD"
    assert _canonical_header("MATL") == "MATERIAL"
    # A unit suffix must not stop the binding.
    assert _canonical_header("WIDTH (MM)") == "WIDTH"


def test_x2_unit_banner_detection_and_inheritance():
    assert _is_group_banner("DIMENSION IN MM")
    assert _is_group_banner("DIMENSIONS")
    assert _is_group_banner("PRICE (USD)")
    assert not _is_group_banner("NEOPRENE RUBBER")
    assert _banner_unit("DIMENSION IN MM") == "MM"
    assert _banner_unit("DIMENSION IN INCH") == "INCH"
    assert _banner_unit("WEIGHT (KG)") == "KG"
    assert _banner_unit("PRICE (USD)") == "USD"


def test_x2_raw_mm_guard_off_series_test_settles_the_column():
    """Part 2.2 test 5 — one off-series value proves the whole column is raw MM.
    Without this, widths 100/400/630 read as NB 100/400/630 and cut strips get
    quoted as flange gaskets.
    """
    siblings = ["WIDTH", "THICKNESS", "LENGTH", "QTY"]
    on_series_only = ["100", "400", "630"]
    off_series = ["130", "223", "5969"]
    assert is_raw_mm_column("WIDTH", on_series_only, siblings)
    assert is_raw_mm_column("WIDTH", off_series, siblings)
    # A measurement banner is enough on its own (test 1).
    assert is_raw_mm_column("DIMENSION IN MM", on_series_only, [])


def test_x2_bore_reading_requires_positive_evidence():
    """A bare metric number is a measurement unless an NB/DN/NPS token or a
    class/PN rating says otherwise. The two size worlds never blend.
    """
    assert not is_raw_mm_column("NB", ["100", "150"], ["CLASS", "MATERIAL"])
    assert not is_raw_mm_column("DN", ["100", "150"], ["PN", "MATERIAL"])
    assert not is_raw_mm_column("SIZE", ["100", "150"], ["RATING", "MATERIAL"])


# ===========================================================================
# RULE Y — Kammprofile
# ===========================================================================

def test_y_detection_covers_the_short_and_brand_forms():
    """Part 1 — GROOVED METAL / PROFILE GASKET / CAMP / MET GRVD never route to
    spiral wound. Two historical rows converted a Camprofile enquiry into a
    SPIRAL WOUND quote (Part 11.1).
    """
    for text in (
        "GASKET, MET GRVD, 316L, GPH, 558x582x3mm",
        "GASKET GRVD SS316L 3MM",
        "GSKT CAMP CL600 RF 1-1/2IN GRAPHITE 316L",
        "PROFILE GASKET WITH FKM FACING",
        "GASKET, METAL GROOVED, SS316",
        "GKT 100NB KMP 4.5MM SS317L GPH B16.20",
        "GROOVED METAL GASKET SS316 WITH COVERING LAYERS",
        "METAKAMM GASKET SS316L",
        "FLEXPRO GASKET SS316",
    ):
        assert _infer_gasket_type(text) == "KAMM", text


def test_y_thickness_engine_core_plus_two_facings():
    """Part 4 — TOTAL = CORE + 2 x LAYER, both printed."""
    item = _kamm(
        "(3.2 CORE + 0.5 FACING) THK x 1506 ID x 1532 OD GROOVED METAL GRAPHITE SS316")
    assert item["thickness_mm"] == 4.2
    assert item["kamm_core_thk"] == 3.2
    assert "(3.2MM CORE THK)" in item["ggpl_description"]


def test_y_non_stock_core_is_substituted_with_the_register_line():
    """Part 4.1 — a 3.5MM core is supplied as GGPL's 3.2MM stock core, giving a
    4.2MM total. House practice, not an error, but never undocumented.
    """
    item = _kamm(
        "(3.5 CORE + 0.5 FACING) THK x 1282 ID x 1342 OD GROOVED METAL GRAPHITE SS316")
    assert item["kamm_core_thk"] == 3.2
    assert item["thickness_mm"] == 4.2
    assert "AS PER MANUFACTURING PRACTICE" in item["deviation"]
    assert "4.2MM" in item["deviation"] and "3.2MM" in item["deviation"]


def test_y_total_only_back_derives_the_core():
    """Part 4 — total only => core = total - 1.0MM (0.5MM per side)."""
    item = _kamm("GROOVED METAL GASKET SS316 GRAPHITE, 4MM THK x 1950 ID x 1980 OD")
    assert item["thickness_mm"] == 4
    assert item["kamm_core_thk"] == 3
    assert "(3MM CORE THK)" in item["ggpl_description"]


def test_y_the_4_5mm_ambiguity_applies_3_5_core_and_says_so():
    """Part 4.2 — three cores appear against a 4.5MM total in house data."""
    item = _kamm("GROOVED METAL GASKET SS316 GRAPHITE, 4.5MM THK x 1950 ID x 1980 OD")
    assert item["kamm_core_thk"] == 3.5
    assert "CONFIRM IF 0.6 OR 0.75MM" in item["deviation"]


def test_y_thin_core_raises_the_groove_depth_confirmation():
    """Part 4.2 — a core below 3MM is manufacturable but weak."""
    item = _kamm("GROOVED METAL GASKET SS316L GRAPHITE, 3MM THK x 558 ID x 582 OD")
    assert item["kamm_core_thk"] == 2
    assert "CONFIRM GROOVE DEPTH" in item["deviation"]


def test_y_every_kamm_line_carries_a_core_thickness():
    """Validation 13.2 — the output must always carry ({core}MM CORE THK)."""
    for text in (
        "GROOVED METAL GASKET SS316 GRAPHITE, 4MM THK x 1950 ID x 1980 OD",
        "(3.2 CORE + 0.5 FACING) THK x 1506 ID x 1532 OD GROOVED METAL GRAPHITE SS316",
        "KAMMPROFILE SS316L GRAPHITE 5MM THK x 340 ID x 410 OD",
    ):
        item = _kamm(text)
        assert item["kamm_core_thk"] is not None, text
        assert "CORE THK" in item["ggpl_description"], text


def test_y_three_bare_numbers_are_od_id_and_seal_width():
    """Part 2 — "1216 1184 16": (OD-ID)/2 = 16 confirms the third number."""
    item = _kamm("1216 1184 16 SS 347 KAMM PROFILE")
    assert item["od_mm"] == 1216
    assert item["id_mm"] == 1184
    assert item["kamm_seal_width_mm"] == 16


def test_y_three_bare_numbers_rejected_when_width_does_not_reconcile():
    """The width check is what stops an unrelated third number being adopted."""
    item = _kamm("1216 1184 97 SS 347 KAMM PROFILE")
    assert item.get("kamm_seal_width_mm") is None


def test_y_w1_flange_silence_on_rings_means_integral_outer_ring():
    """Part 6 — GGPL default for flange KAMM, evidenced in the register."""
    item = _kamm('24" 600# CAMPROFILE GASKET SS316 GRAPHITE ASME B16.20')
    assert item["kamm_integral_outer_ring"] == "INTEGRAL"


def test_y_series_b_is_the_kamm_house_default_above_26_inch():
    """Part 8 — KAMM defaults to SERIES B where SPW defaults to SERIES A."""
    item = _kamm('30" 900# GROOVED METAL GASKET SS316 GRAPHITE')
    assert item["series"] == "B"
    assert item["standard"] == "ASME B16.47 (SERIES-B)"
    assert 'SERIES-B' in item["deviation"]


def test_y_convex_profile_uses_major_od_wording():
    """Part 3 Y6 — crowned profiles are quoted on MAJOR OD / MAJOR ID."""
    item = _kamm(
        "GROOVED METAL GASKET, TYPE: CONVEX, SS316 GRAPHITE, "
        "4.5MM THK X 450 ID X 510 OD AS PER DRAWING SK-8293")
    assert "MAJOR OD" in item["ggpl_description"]
    assert "MAJOR ID" in item["ggpl_description"]
    assert "CONFIRM CROWN GEOMETRY" in item["deviation"]


def test_y_crossbars_without_an_attached_drawing_escalate():
    """Part 10 — crossbar layout is drawing-governed; never invented."""
    item = _kamm(
        "GASKET, KAMMPROFILE, STYLE PN, MATL 316SS 4MM THK PLUS 0.5MM GRAPHITE "
        "LAYER ON BOTH SIDES, TOTAL THICKNESS 5MM, 1801MM OD X 1745MM ID, "
        "WITH 6 CROSSBAR 10MM THK")
    assert item["kamm_crossbar"] is not None
    assert item["ggpl_description"] == "KINDLY PROVIDE DRAWING"


def test_y_no_misspellings_in_output():
    """Validation 13.11 — canonical spellings only."""
    item = _kamm("GROOVED METAL GASKET SS316 GRAPHITE, 4MM THK x 1950 ID x 1980 OD")
    out = item["ggpl_description"].upper()
    for bad in ("GROOOVED", "LOSSE", "KAMPROFILE"):
        assert bad not in out


# ===========================================================================
# RULE Z — Spiral wound
# ===========================================================================

def test_z_standard_thickness_default_emits_the_register_line():
    """Part 4 / Part 7 — 4.5MM in 20,828 of 21,814 rows, and the customer is
    told whenever GGPL chose it.
    """
    item = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER ASME B16.20')
    assert item["thickness_mm"] == 4.5
    assert 'WE ARE PROCEEDING STANDARD THICKNESS AS "4.5MM"' in item["deviation"]


def test_z_material_register_line_is_the_house_wording():
    """Part 7 — the single most common line in the source set (467 rows)."""
    item = _spw('1/2", 150#, GASKET SPIRAL WOUND SS316 + GRAPHITE FILLED ASME B16.20')
    assert item["sw_inner_ring"] == "SS316"
    assert item["sw_outer_ring"] == "CS"
    assert 'Winding & Inner ring material as "SS316"' in item["deviation"]
    assert 'Outer ring material as "CS"' in item["deviation"]


def test_z_series_a_is_the_spw_house_default_above_26_inch():
    """Part 5 — SPW defaults to SERIES A (KAMM defaults to SERIES B)."""
    item = _spw('NPS 30, SPW SS316 / flexible graphite, SS316 IR & OR, Cl.150')
    assert item["series"] == "A"
    assert item["standard"] == "ASME B16.47 (SERIES-A)"
    assert 'SERIES-A' in item["deviation"]


def test_z_b1621_is_never_the_standard_on_a_spiral_wound_line():
    """Part 9.3 — 67 such rows exist in the source set."""
    item = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER',
                standard="ASME B16.21")
    assert item["standard"] == "ASME B16.20"
    assert "ASME B16.21" not in item["ggpl_description"]


def test_z_series_moved_off_b1620_onto_b1647():
    """Part 9.4 — 81 rows carry `ASME B16.20 (SERIES B)`; Series belongs to
    B16.47.
    """
    item = _spw('30" 150# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER',
                standard="ASME B16.20 (SERIES-B)")
    assert item["standard"] == "ASME B16.47 (SERIES-B)"


def test_z_api_6a_is_cleared_on_a_spiral_wound_line():
    """Part 5 — never API 6A/6B on an SPW row."""
    item = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER',
                standard="API 6A")
    assert "API" not in (item["standard"] or "")


def test_z_spiral_wound_gasket_phrase_is_mandatory():
    """Part 9.2 — the product phrase was dropped from some rows."""
    item = _spw("GASKET SPIRALDN1/2;CL150RF;TYPE SPV2F316L/GRAPH.ASME B16.20")
    assert "SPIRAL WOUND GASKET" in item["ggpl_description"]


def test_z_dn_with_a_fraction_is_inches_not_dn():
    """Part 9.1 — DN has no fractional sizes. `DN1/2` is the ERP's DN prefix on
    a 1/2" size, and was historically quoted as `1/2 DN`.
    """
    assert _fmt_size("DN1/2", "SPIRAL_WOUND") == '1/2"'
    assert _fmt_size("DN 3/4", "SPIRAL_WOUND") == '3/4"'
    # Whole metric values from the DN series are still true DN.
    assert _fmt_size("DN100", "SPIRAL_WOUND") == "100 DN"


def test_z_ring_thickness_never_becomes_the_gasket_thickness():
    """Part 4 — a 3.2MM figure next to a ring is the ring, not the gasket."""
    item = _spw(
        'GASKET SPIRAL WOUND 2" 300# SS316L THERMICULITE FILLER, '
        'CENTERING RING THICKNESS : 3.2 MM')
    assert item["thickness_mm"] == 4.5
    assert any("RING THICKNESS" in f.upper() for f in item["flags"])


def test_z_compressed_service_dimension_is_not_the_quoted_thickness():
    """Part 4 — "3.2 compressed" is a service dimension."""
    item = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER, 3.2 COMPRESSED')
    assert item["thickness_mm"] == 4.5


def test_z_lost_decimal_635_reads_as_6_35mm():
    """Part 9.5 — `635` is 6.35MM; no SPW is 635MM thick."""
    item = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER',
                thickness_mm=635)
    assert item["thickness_mm"] == 6.35


def test_z_four_diameter_form_quotes_the_sealing_element():
    """Part 6 — GGPL quotes the winding; ring dims go to the notes."""
    item = _spw(
        'GASKET, SPIRAL WOUND; (FOR 14" ASME APP.2 RF FLANGE); '
        "OROD: 576 x GOD: 404 x GID: 330 x IRID: 310 x 4.50 THK; "
        "INNER RING SS-321; WINDING SS-321; CS CENTERING RING")
    assert item["od_mm"] == 404
    assert item["id_mm"] == 330
    notes = " ".join(item["flags"]).upper()
    assert "576" in notes and "310" in notes
    # Labelled element dims leave nothing to confirm.
    assert not any("SEALING ELEMENT DIMS OR OVERALL" in f for f in item["flags"])


def test_z_missing_quantity_still_quotes_and_asks_for_the_number():
    """Part 8 — 136 rows; the line is quoted, the customer is asked."""
    item = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER ASME B16.20',
                quantity=None)
    assert "KINDLY PROVIDE QUANTITY" in item["deviation"]
    assert item["ggpl_description"].startswith("SIZE")


def test_z_low_stress_and_mo_content_qualify_the_standard_slot():
    """Part 5 — both are standard-slot variants, not free-text specials."""
    low = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER, LOW STRESS')
    assert "(LOW STRESS)" in low["ggpl_description"]

    mo = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER, '
              '2 %MO TO 2.5% MOLLY CONTENT')
    assert "MOLLY CONTENT" in mo["ggpl_description"]


def test_z_operator_edited_deviation_survives_recompute():
    """The Deviation cell is customer-facing copy; an operator who worded it
    owns it.
    """
    item = _spw('2" 300# SPIRAL WOUND GASKET SS316 GRAPHITE FILLER ASME B16.20',
                deviation="OUR OWN WORDING",
                manual_fields=["deviation"])
    assert item["deviation"] == "OUR OWN WORDING"