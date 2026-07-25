"""Customer/project gasket-code dictionary (Rule K: per-customer taxonomies).

EPC contractors (Toyo Engineering, HSEPL, ...) issue project gasket lists that
assign a code (G111A, G214ACN, ...) to a full construction. Enquiries then
reference only the code. This table resolves a code into GGPL construction
fields; row text always outranks the code (fields are only filled when the
enquiry itself left them blank).

Sources: BKEP_6490 HZ-103 (Toyo), AXHF001 work 6454 (Toyo),
A-6399-PI-5103 (HSEPL LNG Chhara). The codes are consistent across these
projects, so they are kept in one shared table. This is editable DATA —
extend it whenever a new project gasket list arrives.
"""
from __future__ import annotations

import re

# code → field updates applied when the enquiry doesn't state them itself.
# 'gasket_type' uses the engine's family names.
GASKET_CODE_TABLE: dict[str, dict] = {
    # --- Non-metallic (ASME B16.21) ---
    'G111A': {'gasket_type': 'SOFT_CUT', 'moc': 'NBR', 'standard': 'ASME B16.21'},
    'G112A': {'gasket_type': 'SOFT_CUT', 'moc': 'NBR WITH CLOTH INSERT', 'standard': 'ASME B16.21'},
    'G112C': {'gasket_type': 'SOFT_CUT', 'moc': 'EPDM WHITE (SHORE A-60) WITH CLOTH INSERT', 'standard': 'ASME B16.21'},
    'G112E': {'gasket_type': 'SOFT_CUT', 'moc': 'WHITE SILICONE RUBBER WITH CLOTH INSERT', 'standard': 'ASME B16.21'},
    'G121': {'gasket_type': 'SOFT_CUT', 'moc': 'NON-ASBESTOS BS7531 GR X', 'standard': 'ASME B16.21'},
    'G122': {'gasket_type': 'SOFT_CUT', 'moc': 'NON-ASBESTOS BS7531 GR X', 'standard': 'ASME B16.21'},
    # --- SPW winding only (tongue & groove, cryogenic) ---
    'G211AA': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS304', 'sw_filler': 'GRAPHITE',
               'sw_style_hint': 'winding', 'standard': 'ASME B16.20'},
    # --- SPW with centering (outer) ring only ---
    'G213AAA': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS304', 'sw_filler': 'GRAPHITE',
                'sw_outer_ring': 'CS', 'sw_style_hint': 'or_only', 'standard': 'ASME B16.20'},
    'G213AAB': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS304', 'sw_filler': 'GRAPHITE',
                'sw_outer_ring': 'SS304', 'sw_style_hint': 'or_only', 'standard': 'ASME B16.20'},
    'G213ACA': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316', 'sw_filler': 'GRAPHITE',
                'sw_outer_ring': 'CS', 'sw_style_hint': 'or_only', 'standard': 'ASME B16.20'},
    'G213ADA': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316L', 'sw_filler': 'GRAPHITE',
                'sw_outer_ring': 'CS', 'sw_style_hint': 'or_only', 'standard': 'ASME B16.20'},
    'G213ADE': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316L', 'sw_filler': 'GRAPHITE',
                'sw_outer_ring': 'SS316L', 'sw_style_hint': 'or_only', 'standard': 'ASME B16.20'},
    # --- SPW with inner + centering rings ---
    'G214AAA': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS304', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'CS', 'sw_outer_ring': 'CS', 'standard': 'ASME B16.20'},
    'G214AAB': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS304', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'SS304', 'sw_outer_ring': 'SS304', 'standard': 'ASME B16.20'},
    'G214AAL': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS304', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'SS304', 'sw_outer_ring': 'CS', 'standard': 'ASME B16.20'},
    'G214ACA': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'CS', 'sw_outer_ring': 'CS', 'standard': 'ASME B16.20'},
    'G214ACD': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'SS316', 'sw_outer_ring': 'SS316', 'standard': 'ASME B16.20'},
    'G214ACN': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'SS316', 'sw_outer_ring': 'CS', 'standard': 'ASME B16.20'},
    'G214ADE': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316L', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'SS316L', 'sw_outer_ring': 'SS316L', 'standard': 'ASME B16.20'},
    'G214ADP': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316L', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'SS316L', 'sw_outer_ring': 'CS', 'standard': 'ASME B16.20'},
    'G214ANX': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'ALLOY 825', 'sw_filler': 'GRAPHITE',
                'sw_inner_ring': 'ALLOY 825', 'sw_outer_ring': 'ALLOY 825', 'standard': 'ASME B16.20'},
    'G214ECD': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS316', 'sw_filler': 'VERMICULITE',
                'sw_inner_ring': 'SS316', 'sw_outer_ring': 'SS316', 'standard': 'ASME B16.20'},
    'G214EEF': {'gasket_type': 'SPIRAL_WOUND', 'sw_winding_material': 'SS321', 'sw_filler': 'VERMICULITE',
                'sw_inner_ring': 'SS321', 'sw_outer_ring': 'SS321', 'standard': 'ASME B16.20'},
    # --- Metallic ---
    'G313E': {'gasket_type': 'RTJ', 'moc': 'SS304', 'rtj_groove_type': 'OCTAGONAL',
              'rtj_hardness_bhn': 140, 'standard': 'ASME B16.20'},
    'G316G': {'gasket_type': 'CMG', 'moc': 'SS316', 'cmg_facing': 'GRAPHITE',
              'special': '3-PLY CORRUGATED METAL GASKET', 'standard': 'ASME B16.20'},
}

_CODE_RE = re.compile(r'\bG\d{3}[A-Z]{0,3}\b')


def apply_gasket_code(item: dict, flags: list, applied_defaults: list) -> None:
    """Resolve a project gasket code into construction fields.

    Row text outranks the code: only fields the enquiry left blank are filled.
    """
    desc = str(item.get('raw_description') or item.get('description') or '').upper()
    if not desc:
        return
    for token in _CODE_RE.findall(desc):
        entry = GASKET_CODE_TABLE.get(token)
        if not entry:
            continue
        filled = []
        for field, value in entry.items():
            current = item.get(field)
            # gasket_type: the untyped fallback is SOFT_CUT — a code that names
            # a different family overrides that fallback (explicit family words
            # in the row text will already have set a non-fallback type).
            if field == 'gasket_type':
                if not current or (current == 'SOFT_CUT' and value != 'SOFT_CUT'):
                    item[field] = value
                    filled.append(field)
                continue
            if not current:
                item[field] = value
                filled.append(field)
        if filled:
            applied_defaults.append(
                f'construction resolved from project gasket code {token} ({", ".join(filled)})')
        break
