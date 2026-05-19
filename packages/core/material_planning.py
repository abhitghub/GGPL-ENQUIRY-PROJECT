from __future__ import annotations

"""
Material planning estimates for gasket quote enquiries.

The planner deliberately separates deterministic calculations from Streamlit UI.
It uses the normalized item contract produced by apply_rules(), then falls back to
visible assumptions when exact manufacturing dimensions are not available.
"""

import math
import re
from collections import defaultdict
from typing import Any

from data.reference_data import lookup_dimensions, normalize_rating, normalize_size


DEFAULT_SHEET_WIDTH_MM = 1250.0
DEFAULT_SHEET_LENGTH_MM = 1500.0
DEFAULT_NESTING_EFFICIENCY = 0.82

_METAL_RING_THICKNESS_MM = 3.0
_SPW_WINDING_METAL_FRACTION = 0.35
_SPW_FILLER_FRACTION = 0.30
_SPW_RING_RADIAL_WIDTH_MM = 8.0
_KAMM_COVERING_EQUIV_THK_MM = 0.5

_DENSITIES_G_PER_CM3: dict[str, float] = {
    "CS": 7.85,
    "CARBON STEEL": 7.85,
    "LOW CARBON STEEL": 7.85,
    "LTCS": 7.85,
    "SOFTIRON": 7.85,
    "SOFT IRON": 7.85,
    "SS": 7.9,
    "SS304": 7.9,
    "SS304L": 7.9,
    "SS316": 8.0,
    "SS316L": 8.0,
    "SS321": 8.0,
    "SS347": 8.0,
    "SS410": 7.75,
    "DUPLEX": 7.8,
    "SUPER DUPLEX": 7.8,
    "UNS S31803": 7.8,
    "UNS S32205": 7.8,
    "UNS S32750": 7.8,
    "UNS S32760": 7.8,
    "INCONEL 600": 8.47,
    "INCONEL 625": 8.44,
    "INCONEL 718": 8.19,
    "MONEL 400": 8.83,
    "HASTELLOY C276": 8.89,
    "HASTELLOY C22": 8.69,
    "INCOLOY 800": 7.94,
    "INCOLOY 825": 8.14,
    "ALLOY 20": 8.08,
    "TITANIUM": 4.51,
    "TITANIUM GR.2": 4.51,
    "TITANIUM GR.12": 4.54,
    "ALUMINIUM": 2.7,
    "ALUMINUM": 2.7,
    "BRASS": 8.5,
    "BRONZE": 8.8,
    "CU-NI 70/30": 8.94,
    "GRAPHITE": 1.2,
    "FLEXIBLE GRAPHITE": 1.1,
    "PTFE": 2.2,
    "TEFLON": 2.2,
    "CNAF": 1.85,
    "NON ASBESTOS": 1.85,
    "AF139": 1.85,
    "AF157": 1.85,
    "EPDM": 1.15,
    "NEOPRENE": 1.35,
    "NBR": 1.1,
    "VITON": 1.85,
    "MICA": 2.8,
    "GRE": 1.85,
    "G10": 1.85,
    "G11": 1.85,
}


def build_material_plan(
    items: list[dict[str, Any]],
    *,
    sheet_width_mm: float = DEFAULT_SHEET_WIDTH_MM,
    sheet_length_mm: float = DEFAULT_SHEET_LENGTH_MM,
    nesting_efficiency: float = DEFAULT_NESTING_EFFICIENCY,
) -> dict[str, Any]:
    """Build a reviewable material plan for the current quote enquiry."""
    sheet_width_mm = _positive_float(sheet_width_mm, DEFAULT_SHEET_WIDTH_MM)
    sheet_length_mm = _positive_float(sheet_length_mm, DEFAULT_SHEET_LENGTH_MM)
    nesting_efficiency = max(0.1, min(_positive_float(nesting_efficiency, DEFAULT_NESTING_EFFICIENCY), 1.0))

    config = {
        "sheet_width_mm": sheet_width_mm,
        "sheet_length_mm": sheet_length_mm,
        "sheet_area_m2": sheet_width_mm * sheet_length_mm / 1_000_000,
        "nesting_efficiency": nesting_efficiency,
    }
    rows: list[dict[str, Any]] = []
    assumptions: set[str] = {
        f"Default sheet size: {_fmt_num(sheet_width_mm)} x {_fmt_num(sheet_length_mm)} mm.",
        f"Sheet nesting efficiency defaulted to {nesting_efficiency:.0%}.",
        "Weights are planning estimates; final purchase quantities should be checked against approved drawings and shop nesting.",
    }
    warnings: list[str] = []

    for item in items:
        if item.get("regret") or item.get("status") == "regret":
            continue
        item_rows, item_assumptions, item_warnings = _plan_item(item, config)
        rows.extend(item_rows)
        assumptions.update(item_assumptions)
        warnings.extend(item_warnings)

    summary = _summarize_materials(rows)
    totals = {
        "line_count": len({row["line_no"] for row in rows}),
        "component_count": len(rows),
        "sheet_count": sum(float(row.get("sheets_required") or 0) for row in rows),
        "total_weight_kg": sum(float(row.get("total_weight_kg") or 0) for row in rows),
    }
    return {
        "config": config,
        "rows": rows,
        "summary": summary,
        "assumptions": sorted(assumptions),
        "warnings": warnings,
        "totals": totals,
    }


def _plan_item(item: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    gtype = str(item.get("gasket_type") or "SOFT_CUT").upper()
    if gtype == "SPIRAL_WOUND":
        return _plan_spiral_wound(item, config)
    if gtype == "RTJ":
        return _plan_rtj(item)
    if gtype == "KAMM":
        return _plan_kamm(item, config)
    if gtype == "DJI":
        return _plan_dji(item, config)
    if gtype in ("ISK", "ISK_RTJ"):
        return _plan_isk(item, config)
    return _plan_soft_cut(item, config)


def _plan_soft_cut(item: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    dims, assumptions, warnings = _item_dimensions(item, preferred_face=item.get("face_type") or "RF")
    qty = _quantity(item)
    material = _material(item.get("moc") or "UNSPECIFIED")
    thk = _positive_float(item.get("thickness_mm"), 3.0)
    if not dims:
        warnings.append(_line_warning(item, "OD/ID unavailable; soft-cut sheet weight could not be calculated."))
        return [_base_row(item, "Soft-cut sheet blank", material, "Sheet", qty, "OD/ID required")], assumptions, warnings

    od, id_ = dims
    finished_weight = _annulus_weight_kg(od, id_, thk, material)
    blank_area = _blank_area_mm2(od)
    sheets = _sheets_required(blank_area * qty, config)
    row = _base_row(item, "Soft-cut sheet blank", material, "Sheet", qty, "Annular gasket from sheet")
    row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": thk,
        "unit_weight_kg": finished_weight,
        "total_weight_kg": finished_weight * qty,
        "blank_area_m2": blank_area / 1_000_000,
        "sheets_required": sheets,
        "calculation_notes": "Sheet consumption uses square OD blank; finished weight uses annular area.",
    })
    return [row], assumptions, warnings


def _plan_spiral_wound(item: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    dims, assumptions, warnings = _item_dimensions(item, preferred_face="RF")
    assumptions.add("SPW winding estimate uses available RF OD/ID envelope when B16.20 winding dimensions are not available in the app data.")
    qty = _quantity(item)
    thk = _positive_float(item.get("thickness_mm"), 4.5)
    rows: list[dict[str, Any]] = []
    if not dims:
        warnings.append(_line_warning(item, "OD/ID unavailable; SPW winding weight could not be calculated."))
        dims = (0.0, 0.0)
    od, id_ = dims
    annulus_area = _annulus_area_mm2(od, id_) if od and id_ else 0.0
    winding_material = _material(item.get("sw_winding_material") or "UNSPECIFIED")
    filler_material = _material(item.get("sw_filler") or "GRAPHITE")

    metal_row = _base_row(item, "SPW winding strip", winding_material, "Strip coil", qty, "Winding metal")
    filler_row = _base_row(item, "SPW filler tape", filler_material, "Filler tape", qty, "Compressed filler")
    metal_row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": thk,
        "unit_weight_kg": annulus_area * thk * _SPW_WINDING_METAL_FRACTION * _density_kg_per_mm3(winding_material),
        "calculation_notes": f"{_SPW_WINDING_METAL_FRACTION:.0%} compacted metal fraction of winding annulus.",
    })
    filler_row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": thk,
        "unit_weight_kg": annulus_area * thk * _SPW_FILLER_FRACTION * _density_kg_per_mm3(filler_material),
        "calculation_notes": f"{_SPW_FILLER_FRACTION:.0%} compacted filler fraction of winding annulus.",
    })
    for row in (metal_row, filler_row):
        row["total_weight_kg"] = row["unit_weight_kg"] * qty
        rows.append(row)

    if item.get("sw_inner_ring"):
        rows.append(_spw_ring_row(item, "SPW inner ring", item.get("sw_inner_ring"), id_, "ID support ring", qty))
    if item.get("sw_outer_ring"):
        rows.append(_spw_ring_row(item, "SPW outer ring", item.get("sw_outer_ring"), od, "Centering ring", qty))
    return rows, assumptions, warnings


def _plan_rtj(item: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    qty = _quantity(item)
    material = _material(item.get("moc") or "UNSPECIFIED")
    assumptions = {
        "RTJ estimate treats the input stock as one forged/rolled ring blank per gasket, then CNC machining.",
        "RTJ weight uses estimated mean diameter and cross-section when an exact ring chart is not available.",
    }
    warnings: list[str] = []
    mean_dia = _rtj_mean_diameter_mm(item)
    cross_section = _rtj_cross_section_area_mm2(item)
    unit_weight = math.pi * mean_dia * cross_section * _density_kg_per_mm3(material)
    row = _base_row(item, "RTJ ring blank", material, "Forged/rolled ring", qty, "CNC ring blank")
    row.update({
        "od_mm": None,
        "id_mm": None,
        "thickness_mm": None,
        "unit_weight_kg": unit_weight,
        "total_weight_kg": unit_weight * qty,
        "stock_qty": qty,
        "stock_uom": "RING",
        "calculation_notes": f"Mean dia {_fmt_num(mean_dia)} mm x section {_fmt_num(cross_section)} mm2.",
    })
    if not item.get("ring_no"):
        warnings.append(_line_warning(item, "RTJ ring number missing; ring blank estimate should be checked manually."))
    return [row], assumptions, warnings


def _plan_kamm(item: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    dims, assumptions, warnings = _item_dimensions(item, preferred_face="RF")
    assumptions.add("Kammprofile core estimate uses OD/ID envelope and core thickness when available.")
    qty = _quantity(item)
    core_material = _material(item.get("kamm_core_material") or item.get("moc") or "UNSPECIFIED")
    covering_material = _material(item.get("kamm_surface_material") or item.get("kamm_covering_layer") or "GRAPHITE")
    thk = _positive_float(item.get("kamm_core_thk") or item.get("thickness_mm"), 3.0)
    rows: list[dict[str, Any]] = []
    if not dims:
        warnings.append(_line_warning(item, "OD/ID unavailable; Kammprofile core weight could not be calculated."))
        return [_base_row(item, "Kammprofile core", core_material, "Plate/ring blank", qty, "OD/ID required")], assumptions, warnings
    od, id_ = dims
    blank_area = _blank_area_mm2(od)
    core_row = _base_row(item, "Kammprofile core", core_material, "Plate/ring blank", qty, "Machined grooved core")
    core_row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": thk,
        "unit_weight_kg": _annulus_weight_kg(od, id_, thk, core_material),
        "blank_area_m2": blank_area / 1_000_000,
        "sheets_required": _sheets_required(blank_area * qty, config),
        "calculation_notes": "Core consumption uses square OD blank; finished weight uses annular area.",
    })
    core_row["total_weight_kg"] = core_row["unit_weight_kg"] * qty
    cover_row = _base_row(item, "Kammprofile covering", covering_material, "Facing sheet/tape", qty, "Both-side covering")
    cover_row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": _KAMM_COVERING_EQUIV_THK_MM,
        "unit_weight_kg": _annulus_weight_kg(od, id_, _KAMM_COVERING_EQUIV_THK_MM * 2, covering_material),
        "calculation_notes": "Uses 0.5 mm equivalent covering per side.",
    })
    cover_row["total_weight_kg"] = cover_row["unit_weight_kg"] * qty
    rows.extend([core_row, cover_row])
    return rows, assumptions, warnings


def _plan_dji(item: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    dims, assumptions, warnings = _item_dimensions(item, preferred_face="RF")
    qty = _quantity(item)
    jacket = _material(item.get("moc") or "UNSPECIFIED")
    filler = _material(item.get("dji_filler") or "GRAPHITE")
    thk = _positive_float(item.get("thickness_mm"), 3.0)
    rows: list[dict[str, Any]] = []
    if not dims:
        warnings.append(_line_warning(item, "OD/ID unavailable; double-jacket weight could not be calculated."))
        return [_base_row(item, "Double-jacket shell", jacket, "Sheet", qty, "OD/ID required")], assumptions, warnings
    od, id_ = dims
    jacket_row = _base_row(item, "Double-jacket shell", jacket, "Sheet", qty, "Metal jacket")
    filler_row = _base_row(item, "Double-jacket filler", filler, "Filler sheet", qty, "Inner filler")
    jacket_row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": thk,
        "unit_weight_kg": _annulus_weight_kg(od, id_, thk * 0.35, jacket),
        "blank_area_m2": _blank_area_mm2(od) / 1_000_000,
        "sheets_required": _sheets_required(_blank_area_mm2(od) * qty, config),
        "calculation_notes": "Metal jacket estimated as 35% of nominal gasket thickness.",
    })
    filler_row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": thk * 0.65,
        "unit_weight_kg": _annulus_weight_kg(od, id_, thk * 0.65, filler),
        "calculation_notes": "Filler estimated as 65% of nominal gasket thickness.",
    })
    for row in (jacket_row, filler_row):
        row["total_weight_kg"] = row["unit_weight_kg"] * qty
        rows.append(row)
    return rows, assumptions, warnings


def _plan_isk(item: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    dims, assumptions, warnings = _item_dimensions(item, preferred_face=item.get("face_type") or "RF")
    assumptions.add("ISK sleeves and washers are listed as component counts; detailed bolt count is not yet available in the normalized item.")
    qty = _quantity(item)
    gasket_mat = _material(item.get("isk_gasket_material") or item.get("moc") or "PTFE")
    thk = 3.0
    if not dims:
        warnings.append(_line_warning(item, "OD/ID unavailable; ISK gasket sheet weight could not be calculated."))
        row = _base_row(item, "ISK gasket", gasket_mat, "Sheet/component kit", qty, "OD/ID required")
        return [row], assumptions, warnings
    od, id_ = dims
    row = _base_row(item, "ISK gasket", gasket_mat, "Sheet/component kit", qty, "Insulating gasket kit")
    row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": thk,
        "unit_weight_kg": _annulus_weight_kg(od, id_, thk, gasket_mat),
        "blank_area_m2": _blank_area_mm2(od) / 1_000_000,
        "sheets_required": _sheets_required(_blank_area_mm2(od) * qty, config),
        "calculation_notes": "Kit hardware counts require flange bolt data; gasket ring only is weighted.",
    })
    row["total_weight_kg"] = row["unit_weight_kg"] * qty
    rows = [row]
    for label, field in (
        ("ISK sleeves", "isk_sleeve_material"),
        ("ISK insulating washers", "isk_insulating_washer"),
        ("ISK metallic washers", "isk_washer_material"),
    ):
        if item.get(field):
            comp = _base_row(item, label, _material(item.get(field)), "Kit component", qty, "Count after bolt schedule")
            comp["calculation_notes"] = "Bolt count not in quote enquiry; review manually."
            rows.append(comp)
    return rows, assumptions, warnings


def _spw_ring_row(
    item: dict[str, Any],
    component: str,
    material_raw: Any,
    boundary_dia_mm: float,
    basis: str,
    qty: float,
) -> dict[str, Any]:
    material = _material(material_raw or "UNSPECIFIED")
    radial = _SPW_RING_RADIAL_WIDTH_MM
    if component.endswith("inner ring"):
        id_ = max(boundary_dia_mm - radial, 0)
        od = boundary_dia_mm + radial
    else:
        id_ = max(boundary_dia_mm - radial, 0)
        od = boundary_dia_mm + radial
    row = _base_row(item, component, material, "Ring strip/blank", qty, basis)
    row.update({
        "od_mm": od,
        "id_mm": id_,
        "thickness_mm": _METAL_RING_THICKNESS_MM,
        "unit_weight_kg": _annulus_weight_kg(od, id_, _METAL_RING_THICKNESS_MM, material),
        "calculation_notes": f"Default {_fmt_num(radial)} mm radial ring allowance.",
    })
    row["total_weight_kg"] = row["unit_weight_kg"] * qty
    return row


def _base_row(
    item: dict[str, Any],
    component: str,
    material: str,
    stock_form: str,
    qty: float,
    basis: str,
) -> dict[str, Any]:
    return {
        "line_no": item.get("line_no") or "",
        "gasket_type": item.get("gasket_type") or "",
        "component": component,
        "material": material,
        "stock_form": stock_form,
        "basis": basis,
        "quote_qty": qty,
        "quote_uom": item.get("uom") or "NOS",
        "stock_qty": None,
        "stock_uom": "",
        "od_mm": None,
        "id_mm": None,
        "thickness_mm": None,
        "blank_area_m2": 0.0,
        "sheets_required": 0.0,
        "unit_weight_kg": 0.0,
        "total_weight_kg": 0.0,
        "density_g_cm3": _density_g_cm3(material),
        "description": item.get("ggpl_description") or item.get("raw_description") or "",
        "calculation_notes": "",
        "reviewed": False,
        "planner_notes": "",
    }


def _summarize_materials(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {
        "material": "",
        "stock_form": "",
        "components": 0,
        "sheets_required": 0.0,
        "total_weight_kg": 0.0,
        "stock_qty": 0.0,
    })
    for row in rows:
        key = (row.get("material") or "", row.get("stock_form") or "")
        acc = grouped[key]
        acc["material"] = key[0]
        acc["stock_form"] = key[1]
        acc["components"] += 1
        acc["sheets_required"] += float(row.get("sheets_required") or 0)
        acc["total_weight_kg"] += float(row.get("total_weight_kg") or 0)
        try:
            acc["stock_qty"] += float(row.get("stock_qty") or 0)
        except (TypeError, ValueError):
            pass
    return sorted(grouped.values(), key=lambda r: (r["material"], r["stock_form"]))


def _item_dimensions(item: dict[str, Any], *, preferred_face: str) -> tuple[tuple[float, float] | None, set[str], list[str]]:
    assumptions: set[str] = set()
    warnings: list[str] = []
    od = _optional_float(item.get("od_mm"))
    id_ = _optional_float(item.get("id_mm"))
    if od and id_ and od > id_:
        return (od, id_), assumptions, warnings

    dims = item.get("dimensions")
    if isinstance(dims, dict):
        od = _optional_float(dims.get("od"))
        id_ = _optional_float(dims.get("id"))
        if od and id_ and od > id_:
            return (od, id_), assumptions, warnings

    size_norm = item.get("size_norm") or normalize_size(item.get("size"))
    rating_norm = item.get("rating_norm") or normalize_rating(item.get("rating"))
    if size_norm and rating_norm:
        ref = lookup_dimensions(size_norm, rating_norm, preferred_face)
        if ref:
            od = _optional_float(ref.get("od"))
            id_ = _optional_float(ref.get("id"))
            if od and id_ and od > id_:
                assumptions.add(f"Line {item.get('line_no') or '?'} dimensions looked up from {preferred_face} standard table.")
                return (od, id_), assumptions, warnings

    return None, assumptions, warnings


def _annulus_area_mm2(od_mm: float, id_mm: float) -> float:
    if od_mm <= 0 or id_mm < 0 or od_mm <= id_mm:
        return 0.0
    return math.pi * (od_mm ** 2 - id_mm ** 2) / 4


def _blank_area_mm2(od_mm: float) -> float:
    return max(od_mm, 0) ** 2


def _annulus_weight_kg(od_mm: float, id_mm: float, thk_mm: float, material: str) -> float:
    return _annulus_area_mm2(od_mm, id_mm) * max(thk_mm, 0) * _density_kg_per_mm3(material)


def _sheets_required(area_mm2: float, config: dict[str, Any]) -> float:
    usable = config["sheet_width_mm"] * config["sheet_length_mm"] * config["nesting_efficiency"]
    if area_mm2 <= 0 or usable <= 0:
        return 0.0
    return math.ceil(area_mm2 / usable * 100) / 100


def _density_g_cm3(material: str) -> float:
    mat = _material(material)
    if mat in _DENSITIES_G_PER_CM3:
        return _DENSITIES_G_PER_CM3[mat]
    for token, density in _DENSITIES_G_PER_CM3.items():
        if token and token in mat:
            return density
    return 7.85 if _looks_metal(mat) else 1.85


def _density_kg_per_mm3(material: str) -> float:
    return _density_g_cm3(material) / 1_000_000


def _material(value: Any) -> str:
    mat = str(value or "UNSPECIFIED").strip().upper()
    mat = re.sub(r"\s+", " ", mat)
    mat = mat.replace("SS 316", "SS316").replace("SS 304", "SS304")
    if "FLEXIBLE INHIBITED GRAPHITE" in mat:
        return "GRAPHITE"
    if mat in ("G-10", "GRE G-10", "GRE G10"):
        return "G10"
    if mat in ("G-11", "GRE G-11", "GRE G11"):
        return "G11"
    return mat


def _looks_metal(material: str) -> bool:
    metal_tokens = ("SS", "STEEL", "CS", "LTCS", "INCONEL", "MONEL", "HASTELLOY", "ALLOY", "UNS", "TITANIUM", "BRASS", "BRONZE")
    return any(tok in material for tok in metal_tokens)


def _rtj_mean_diameter_mm(item: dict[str, Any]) -> float:
    size_norm = item.get("size_norm") or normalize_size(item.get("size"))
    nps = _nps_float(size_norm)
    rating = str(item.get("rating") or "")
    pressure = _first_number(rating) or 150
    if nps:
        return nps * 25.4 + 35 + min(pressure / 100, 25)
    ring_no = str(item.get("ring_no") or "")
    ring_num = _first_number(ring_no)
    if ring_num:
        prefix_factor = 6.0 if ring_no.upper().startswith("BX") else 5.2
        return max(55.0, 12.0 + ring_num * prefix_factor)
    return 150.0


def _rtj_cross_section_area_mm2(item: dict[str, Any]) -> float:
    ring_no = str(item.get("ring_no") or "").upper()
    size_norm = item.get("size_norm") or normalize_size(item.get("size"))
    nps = _nps_float(size_norm) or 4.0
    if ring_no.startswith("BX"):
        return 14.0 * 18.0
    if nps <= 2:
        return 6.0 * 8.0
    if nps <= 8:
        return 8.0 * 11.0
    if nps <= 16:
        return 10.0 * 13.0
    return 12.0 * 16.0


def _nps_float(size_norm: Any) -> float | None:
    if not size_norm:
        return None
    s = str(size_norm).replace('"', "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _first_number(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else None


def _quantity(item: dict[str, Any]) -> float:
    return _positive_float(item.get("quantity"), 1.0)


def _positive_float(value: Any, fallback: float) -> float:
    parsed = _optional_float(value)
    if parsed is None or parsed <= 0:
        return fallback
    return parsed


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(val):
        return None
    return val


def _line_warning(item: dict[str, Any], text: str) -> str:
    return f"Line {item.get('line_no') or '?'}: {text}"


def _fmt_num(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")
