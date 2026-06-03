from core.rules import apply_rules


def test_spw_preserves_customer_uns_material_codes():
    item = apply_rules(
        {
            "gasket_type": "SPIRAL_WOUND",
            "raw_description": 'SPIRAL WOUND GASKET 3" 150 RF UNS N06625 WINDING GRAPHITE FILLER UNS N06625 INNER RING SS 316 OUTER RING',
            "size": '3"',
            "rating": "150#",
            "quantity": 1,
            "sw_winding_material": "UNS N06625",
            "sw_filler": "GRAPHITE",
            "sw_inner_ring": "UNS N06625",
            "sw_outer_ring": "SS316",
        }
    )

    assert item["sw_winding_material"] == "UNS N06625"
    assert item["sw_inner_ring"] == "UNS N06625"
    assert "INCONEL" not in item["moc"]


def test_spw_generic_ss_components_use_same_row_specific_grade():
    item = apply_rules(
        {
            "gasket_type": "SPIRAL_WOUND",
            "raw_description": 'SPW gasket 4" 150 RF SS winding graphite filler SS inner and outer ring, outer ring material SS316',
            "size": '4"',
            "rating": "150#",
            "quantity": 1,
            "sw_winding_material": "SS",
            "sw_filler": "GRAPHITE",
            "sw_inner_ring": "SS",
            "sw_outer_ring": "SS316",
        }
    )

    assert item["sw_winding_material"] == "SS316"
    assert item["sw_inner_ring"] == "SS316"
    assert item["sw_outer_ring"] == "SS316"


def test_isk_fire_safety_defaults_to_non_fire_safe():
    item = apply_rules(
        {
            "gasket_type": "ISK",
            "raw_description": 'ISK Type-F 6" 150 RF GRE G10 gasket with SS316 core',
            "size": '6"',
            "rating": "150#",
            "quantity": 1,
            "isk_gasket_material": "GRE G10",
            "isk_core_material": "SS316",
        }
    )

    assert item["isk_fire_safety"] == "NON FIRE SAFE"
