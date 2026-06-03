from __future__ import annotations

from core.formatter import format_description
from core.rules import STATUS_CHECK, STATUS_MISSING, STATUS_READY, apply_rules


def _processed(row: dict) -> dict:
    item = apply_rules(dict(row))
    item["ggpl_description"] = format_description(item)
    return item


def test_reference_spiral_wound_simple_domestic_pattern():
    item = _processed({
        "gasket_type": "SPIRAL_WOUND",
        "raw_description": '1/2",150#,GASKET SPIRAL WOUND SS316+ GRAPHITE FILLED ASME B 16.20 / ANSI B 16.5',
        "size": '1/2"',
        "rating": "150#",
        "quantity": 1,
        "uom": "NOS",
        "sw_winding_material": "SS316",
        "sw_filler": "GRAPHITE",
        "sw_inner_ring": "SS316",
        "sw_outer_ring": "CS",
    })

    assert item["status"] in {STATUS_READY, STATUS_CHECK}
    assert "SS316 SPIRAL WOUND GASKET WITH GRAPHITE FILLER" in item["ggpl_description"]
    assert "SS316 INNER RING" in item["ggpl_description"]
    assert "CS OUTER RING" in item["ggpl_description"]
    assert "ASME B16.20" in item["ggpl_description"]


def test_reference_rtj_ring_number_hardness_pattern():
    item = _processed({
        "gasket_type": "RTJ",
        "raw_description": "RTJ Ring number - 23 , Moc :- Inconel 825 ,Hardness required - 160 HBN",
        "ring_no": "R-23",
        "rtj_groove_type": "OCT",
        "moc": "INCONEL 825",
        "rtj_hardness_bhn": 160,
        "quantity": 4,
        "uom": "NOS",
    })

    assert item["status"] in {STATUS_READY, STATUS_CHECK}
    assert item["ggpl_description"] == "SIZE : R-23 ,RTJ ,OCTAGONAL ,INCONEL 825 ,160 BHN HARDNESS ,ASME B16.20"


def test_reference_soft_cut_non_metallic_asbestos_free_pattern():
    item = _processed({
        "gasket_type": "SOFT_CUT",
        "raw_description": '1 1/2 ",150#,Non-metallic, asbestos-free, Flat Ring',
        "size": '1 1/2"',
        "rating": "150#",
        "moc": "ASBESTOS FREE",
        "quantity": 2,
        "uom": "NOS",
    })

    assert item["gasket_type"] == "SOFT_CUT"
    assert "ASBESTOS FREE" in item["ggpl_description"]
    assert "ASME B16.21" in item["ggpl_description"]


def test_reference_kamm_od_id_core_and_covering_pattern():
    item = _processed({
        "gasket_type": "KAMM",
        "raw_description": "(3.2 CORE + 0.5 FACING) THK x 1506 ID x 1532 OD GROOVED METAL GRAPHITE KAMMPROFILE SS347",
        "size_type": "OD_ID",
        "od_mm": 1532,
        "id_mm": 1506,
        "thickness_mm": 4.2,
        "kamm_core_thk": 3.2,
        "kamm_core_material": "SS347",
        "kamm_surface_material": "GRAPHITE",
        "quantity": 1,
        "uom": "NOS",
    })

    assert item["status"] in {STATUS_READY, STATUS_CHECK}
    assert "OD 1532MM X ID 1506MM X 4.2MM THK" in item["ggpl_description"]
    assert "3.2MM CORE THK" in item["ggpl_description"]
    assert "KAMMPROFILE SS347 GRAPHITE LAYER ON BOTH SIDES" in item["ggpl_description"]


def test_reference_dji_compact_copper_jacket_pattern():
    item = _processed({
        "gasket_type": "DJI",
        "raw_description": "copper jacket gasket 13X18X1,5",
        "od_mm": 18,
        "id_mm": 13,
        "thickness_mm": 1.5,
        "moc": "COPPER",
        "dji_filler": "GRAPHITE",
        "quantity": 10,
        "uom": "NOS",
    })

    assert item["status"] in {STATUS_READY, STATUS_CHECK}
    assert item["ggpl_description"] == "SIZE : 18MM OD X 13MM ID X 1.5MM THK, DOUBLE JACKET GASKET WITH COPPER + GRAPHITE FILLED"


def test_reference_vague_isk_requires_clear_spec_instead_of_overquoting():
    item = _processed({
        "gasket_type": "ISK",
        "raw_description": "INSULATING GASKET ,IG001,CL 150,ASME B16.5",
        "size": '2"',
        "rating": "150#",
        "quantity": 1,
        "uom": "NOS",
    })

    assert item["status"] == STATUS_MISSING
    assert any("ISK component specification" in flag for flag in item["flags"])
    assert "PTFE SPRING ENERGIZED SEAL" not in item["ggpl_description"]
