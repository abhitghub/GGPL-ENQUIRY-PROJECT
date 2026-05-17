from core.material_planning import build_material_plan


def test_material_plan_soft_cut_uses_default_sheet_and_weight():
    plan = build_material_plan([
        {
            "line_no": 1,
            "gasket_type": "SOFT_CUT",
            "moc": "CNAF",
            "quantity": 4,
            "uom": "NOS",
            "thickness_mm": 3,
            "od_mm": 200,
            "id_mm": 100,
            "ggpl_description": "SIZE : OD 200MM X ID 100MM X 3MM THK ,CNAF",
        }
    ])

    assert plan["config"]["sheet_width_mm"] == 1250
    assert plan["config"]["sheet_length_mm"] == 1500
    assert len(plan["rows"]) == 1
    row = plan["rows"][0]
    assert row["component"] == "Soft-cut sheet blank"
    assert row["material"] == "CNAF"
    assert row["sheets_required"] > 0
    assert row["total_weight_kg"] > 0


def test_material_plan_spiral_wound_splits_winding_filler_and_rings():
    plan = build_material_plan([
        {
            "line_no": 2,
            "gasket_type": "SPIRAL_WOUND",
            "quantity": 2,
            "uom": "NOS",
            "thickness_mm": 4.5,
            "od_mm": 180,
            "id_mm": 110,
            "sw_winding_material": "SS316",
            "sw_filler": "GRAPHITE",
            "sw_inner_ring": "SS316",
            "sw_outer_ring": "CS",
        }
    ])

    components = {row["component"] for row in plan["rows"]}
    assert "SPW winding strip" in components
    assert "SPW filler tape" in components
    assert "SPW inner ring" in components
    assert "SPW outer ring" in components
    assert plan["totals"]["total_weight_kg"] > 0


def test_material_plan_rtj_creates_ring_blank_weight():
    plan = build_material_plan([
        {
            "line_no": 3,
            "gasket_type": "RTJ",
            "quantity": 1,
            "uom": "NOS",
            "size": '6"',
            "size_norm": '6"',
            "rating": "1500#",
            "ring_no": "R-46",
            "moc": "INCONEL 625",
        }
    ])

    assert len(plan["rows"]) == 1
    row = plan["rows"][0]
    assert row["component"] == "RTJ ring blank"
    assert row["stock_form"] == "Forged/rolled ring"
    assert row["stock_uom"] == "RING"
    assert row["total_weight_kg"] > 0
