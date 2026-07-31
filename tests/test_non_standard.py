"""Operator-selected NON STANDARD on the `standard` field: the rules engine
must not default a standard back in, and the formatter must drop the
ASME/API/EN/DIN tag from the GGPL description."""
from core.formatter import format_description, is_non_standard
from core.rules import apply_rules


def _process(item: dict) -> dict:
    out = apply_rules(dict(item))
    out["ggpl_description"] = format_description(out)
    return out


def test_is_non_standard_accepts_common_spellings():
    for value in ("NON STANDARD", "non standard", "Non-Standard", "NONSTANDARD", "non std"):
        assert is_non_standard(value)
    for value in (None, "", "ASME B16.21", "STANDARD"):
        assert not is_non_standard(value)


def test_soft_cut_od_id_non_standard_drops_asme_tag():
    base = {
        "gasket_type": "SOFT_CUT",
        "size_type": "OD_ID",
        "od_mm": 35,
        "id_mm": 30,
        "thickness_mm": 3,
        "moc": "SOFT IRON",
        "raw_description": "GSKT,PLUG,35ODX30IDX2MM,SOFT IRON",
    }
    # Dims-only: RULE V Part 5.0 already suppresses the tag without an operator
    # having to mark the row (see test_rule_v_j2).
    assert "ASME" not in _process(base)["ggpl_description"]
    item = _process({**base, "standard": "Non standard"})
    assert item["standard"] == "NON STANDARD"
    assert item["ggpl_description"] == "SIZE : OD 35MM X ID 30MM X 3MM THK, SOFT IRON"


def test_soft_cut_nps_non_standard_skips_default():
    item = _process({
        "gasket_type": "SOFT_CUT", "size": '2"', "rating": "150#",
        "moc": "CNAF", "thickness_mm": 3, "standard": "NON STANDARD",
    })
    assert item["standard"] == "NON STANDARD"
    assert "ASME" not in item["ggpl_description"]


def test_spiral_wound_large_bore_non_standard_beats_b1647_convention():
    base = {
        "gasket_type": "SPIRAL_WOUND", "size": '26"', "rating": "150#",
        "moc": "SS316", "sw_winding_material": "SS316", "sw_filler": "GRAPHITE",
    }
    assert "B16.47" in _process(base)["standard"]
    item = _process({**base, "standard": "NON STANDARD"})
    assert item["standard"] == "NON STANDARD"
    assert "B16.47" not in item["ggpl_description"]


def test_rtj_non_standard_drops_b1620_tag():
    item = _process({
        "gasket_type": "RTJ", "ring_no": "R-24", "moc": "SOFT IRON",
        "standard": "NON STANDARD",
    })
    assert item["standard"] == "NON STANDARD"
    assert "ASME" not in item["ggpl_description"]
    assert "API" not in item["ggpl_description"]


def test_envelope_non_standard_drops_default_tag():
    item = _process({
        "gasket_type": "ENVELOPE", "size": '2"', "rating": "150#",
        "moc": "CNAF", "standard": "NON STANDARD",
    })
    assert "ASME" not in item["ggpl_description"]
