from core.formatter import format_description
from core.rules import apply_rules


def _processed_oring(description: str) -> dict:
    item = apply_rules(
        {
            "description": description,
            "quantity": 1,
            "uom": "NOS",
        }
    )
    item["ggpl_description"] = format_description(item)
    return item


def test_oring_rules_recover_id_cross_section_material_and_pressure():
    # Master Spec v3.1 template: SIZE: {ID}MM ID X {CS}MM THK, {MAT} O-RING —
    # pressure bar ratings stay in the side-fields, never in the GGPL string.
    cases = [
        (
            "O-RING,MATERIAL:VITON,SIZE:ID 14 X THK 3 MM,PRESSURE RATING:250 BAR,",
            14,
            3,
            "SIZE: 14MM ID X 3MM THK, VITON O-RING",
        ),
        (
            "O-RING,MATERIAL:VITON,SIZE:ID 12 X THK 2 MM,PRESSURE RATING:250 BAR,",
            12,
            2,
            "SIZE: 12MM ID X 2MM THK, VITON O-RING",
        ),
    ]

    for description, expected_id, expected_cs, expected_description in cases:
        item = _processed_oring(description)

        assert item["status"] == "ready"
        assert item["gasket_type"] == "O_RING"
        assert item["size_type"] == "ID_CS"
        assert item["id_mm"] == expected_id
        assert item["thickness_mm"] == expected_cs
        assert item["moc"] == "VITON"
        assert item["pressure_rating"] == "250 BAR"
        assert item["size"] is None
        assert item["rating"] is None
        assert item["standard"] is None
        assert item["ggpl_description"] == expected_description


def test_oring_rules_normalize_common_material_and_size_variants():
    cases = [
        (
            "O RING MOC: FKM SIZE: ID 14MM X CS 3MM WORKING PRESSURE: 250 BAR",
            14,
            3,
            "VITON",
            "250 BAR",
            "SIZE: 14MM ID X 3MM THK, VITON O-RING",
        ),
        (
            "SIZE: 12MM ID X 2MM THK, VITON O-RING",
            12,
            2,
            "VITON",
            None,
            "SIZE: 12MM ID X 2MM THK, VITON O-RING",
        ),
        (
            "O RING MATERIAL: NBR SIZE: ID 18MM X C/S 4MM PRESSURE: 10 BAR",
            18,
            4,
            "NITRILE BUTADIENE RUBBER",
            "10 BAR",
            "SIZE: 18MM ID X 4MM THK, NITRILE BUTADIENE RUBBER O-RING",
        ),
        (
            "SIZE: 25MM ID X 5MM, EPDM O-RING",
            25,
            5,
            "EPDM",
            None,
            "SIZE: 25MM ID X 5MM THK, EPDM O-RING",
        ),
    ]

    for description, expected_id, expected_cs, expected_moc, expected_pressure, expected_description in cases:
        item = _processed_oring(description)

        assert item["status"] == "ready"
        assert item["gasket_type"] == "O_RING"
        assert item["id_mm"] == expected_id
        assert item["thickness_mm"] == expected_cs
        assert item["moc"] == expected_moc
        assert item.get("pressure_rating") == expected_pressure
        assert item["ggpl_description"] == expected_description


def test_oring_detection_does_not_override_spiral_wound_outer_ring_text():
    item = apply_rules(
        {
            "description": '2", 150#, SPIRAL WOUND GASKET, SS304/GRAPHITE, O-RING: SS304',
            "quantity": 1,
            "uom": "NOS",
        }
    )

    assert item["gasket_type"] == "SPIRAL_WOUND"
