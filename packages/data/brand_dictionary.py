"""GGPL brand & trade-name cross-reference (Master Spec v3.2).

Three buckets:
  1. STYLE CODES  — construction in disguise (Flexitallic CGI = SPW + IR + OR):
     translate to the normal GGPL construction; brand goes to a deviation note.
  2. MATERIAL TRADE NAMES — grade in disguise (Klingersil C-4400 = CNAF BS7531
     GR Y): translate to the generic material, keep the cert grade, deviation.
  3. PRODUCT-IDENTITY BRANDS — the brand IS the spec (Kroll & Ziller): kept
     verbatim (handled in parser material aliases, not here).

This module is DATA + one apply function so sales can extend the tables
without touching the engine.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Bucket 2 — material trade names.  (pattern, field, value, deviation)
# field: 'moc' (soft cut / sheet material) or 'sw_filler' (SPW/KAMM filler)
# ---------------------------------------------------------------------------
MATERIAL_TRADE_NAMES: list[tuple[str, str, str, str]] = [
    (r'KLINGERSIL\s*C[-\s]?4400', 'moc',
     'CNAF (ARAMID FIBRE WITH NBR BINDER) BS7531 GR Y', 'GGPL MAKE, EQUIVALENT TO KLINGERSIL C-4400'),
    (r'KLINGERSIL\s*C[-\s]?4430', 'moc',
     'CNAF (GLASS/SYNTHETIC FIBRE WITH NBR BINDER) BS7531 GR X', 'GGPL MAKE, EQUIVALENT TO KLINGERSIL C-4430'),
    (r'KLINGERSIL\s*C[-\s]?4500', 'moc',
     'CNAF (CARBON FIBRE WITH NBR BINDER)', 'GGPL MAKE, EQUIVALENT TO KLINGERSIL C-4500'),
    (r'KLINGERSIL\s*C[-\s]?8200', 'moc',
     'PTFE BONDED CNAF', 'GGPL MAKE, EQUIVALENT TO KLINGERSIL C-8200'),
    (r'DURLON\s*8600', 'moc', 'CNAF (FOOD GRADE, WHITE)', 'GGPL MAKE, EQUIVALENT TO DURLON 8600'),
    (r'DURLON\s*(?:8300|8500)', 'moc', 'CNAF', 'GGPL MAKE, EQUIVALENT TO DURLON 8300/8500'),
    (r'DURLON\s*9000', 'moc', 'FILLED PTFE', 'GGPL MAKE, EQUIVALENT TO DURLON 9000'),
    (r'GYLON\s*3500', 'moc', 'FILLED PTFE (SILICA FILLED, FAWN)', 'GGPL MAKE, EQUIVALENT TO GYLON 3500'),
    (r'GYLON\s*3504', 'moc', 'FILLED PTFE (GLASS MICROSPHERE, BLUE)', 'GGPL MAKE, EQUIVALENT TO GYLON 3504'),
    (r'GYLON\s*3510', 'moc', 'FILLED PTFE (BARIUM SULPHATE, OFF-WHITE)', 'GGPL MAKE, EQUIVALENT TO GYLON 3510'),
    (r'BLUE[-\s]?GARD\s*3000|GARLOCK\s*3000', 'moc', 'CNAF', 'GGPL MAKE, EQUIVALENT TO GARLOCK BLUE-GARD 3000'),
    (r'TEADIT\s*NA[-\s]?\d{3,4}', 'moc', 'CNAF', 'GGPL MAKE, EQUIVALENT TO TEADIT NA GRADE'),
    (r'GORE\s+(?:GR\b|UNIVERSAL)', 'moc', 'EXPANDED PTFE (ePTFE)', 'GGPL MAKE, EQUIVALENT TO GORE GR'),
    (r'TEALON\s*TF\s*\d+', 'moc', 'FILLED PTFE', 'GGPL MAKE, EQUIVALENT TO TEALON'),
    (r'KALREZ|CHEMRAZ|PERLAST', 'moc', 'FFKM',
     'EQUIVALENT TO KALREZ/CHEMRAZ — PREMIUM FFKM, CONFIRM GRADE & PRICE'),
    (r'\bAFLAS\b', 'moc', 'AFLAS (FEPM)', 'GGPL MAKE, EQUIVALENT TO AFLAS'),
    (r'\bSANTOPRENE\b', 'moc', 'TPV (SANTOPRENE)', 'GGPL MAKE, EQUIVALENT TO SANTOPRENE'),
    (r'\bHYPALON\b', 'moc', 'CSM (HYPALON)', 'GGPL MAKE, EQUIVALENT TO HYPALON'),
    (r'THERMICULITE\s*(715)', 'moc', 'VERMICULITE SHEET (THERMICULITE 715)',
     'GGPL MAKE, EQUIVALENT TO THERMICULITE 715'),
    (r'THERMICULITE\s*(835|845|855)', 'sw_filler', 'VERMICULITE FILLER (THERMICULITE {g})',
     'GGPL MAKE, EQUIVALENT TO THERMICULITE {g}'),
    # CAF = asbestos (banned/legacy) — always quote CNAF with the safety note
    (r'\bCAF\b(?!\w)|COMPRESSED\s+ASBESTOS', 'moc', 'CNAF',
     'CAF (ASBESTOS) REQUESTED — GGPL OFFERS NON-ASBESTOS (CNAF) EQUIVALENT'),
]

# ---------------------------------------------------------------------------
# Bucket 1 — SPW style-code interchange.  Effects on construction:
#   'both'    = IR + OR (CGI class)     'or_only' = OR only, no IR (CG class)
#   'ir_only' = IR only (RIR)           'winding' = winding only, no rings
#   'low_stress' = standard + (LOW STRESS)
# Unambiguous multi-letter codes match bare; one/two-letter codes only with a
# brand or the word STYLE in front.
# ---------------------------------------------------------------------------
_BRANDS = r'(?:FLEXITALLIC|GARLOCK|LAMONS|TEADIT|KLINGER|LEADER|GRI|STYLE)'
SPW_STYLE_CODES: list[tuple[str, str, str]] = [
    (r'\b(?:CGI|RWI|WRI|CRIR|913M|DRI|SRI)\b', 'both', 'EQUIVALENT TO {code} STYLE (IR + OR)'),
    (rf'{_BRANDS}\s+(?:STYLE\s+)?(?:CG|RW|WR|913|CR)\b(?![I])', 'or_only', 'EQUIVALENT TO {code} STYLE (NO INNER RING)'),
    (r'\bRIR\b', 'ir_only', 'EQUIVALENT TO RIR STYLE (INNER RING ONLY)'),
    (rf'{_BRANDS}\s+(?:STYLE\s+)?(?:R|SW|W|911)\b(?![A-Z0-9])', 'winding', 'EQUIVALENT TO {code} STYLE (WINDING ONLY)'),
    (rf'\bLSI\b|\bWRI-L[CE]\b|{_BRANDS}\s+(?:STYLE\s+)?(?:LS|LE)\b', 'low_stress', 'EQUIVALENT TO {code} LOW-STRESS STYLE'),
]

# ---------------------------------------------------------------------------
# ISK brand map — brand alone maps to STYLE; construction details win over brand
# ---------------------------------------------------------------------------
ISK_BRANDS: list[tuple[str, str, str]] = [
    (r'PIKOTEK\s*VCFS|\bVCFS\b', 'FCS', 'EQUIVALENT TO PIKOTEK VCFS (FIRE SAFE)'),
    (r'PIKOTEK\s*VCS|\bVCS\b', 'CS', 'EQUIVALENT TO PIKOTEK VCS'),
    (r'PIKOTEK\s*PGE|\bPGE\s+TYPE\b|LINE\s?BACKER', 'STYLE-N', 'EQUIVALENT TO PIKOTEK PGE / GPT LINEBACKER'),
    (r'PGS\s+COMMANDER|COMMANDER\s+EXTREME', 'CS', 'EQUIVALENT TO PGS COMMANDER (STYLE-CS)'),
    (r'ISOFLEX|ISOPRO[-\s]?IP', 'STYLE-N', 'EQUIVALENT TO FLEXITALLIC ISOFLEX/ISOPRO'),
]

# Equivalence permission — when present, brand translation carries no
# mandatory-make flag (Rule G)
EQUIVALENCE_PERMISSION_RE = re.compile(
    r'OR\s+EQUIVALENT|/\s*EQUIVALENT|/\s*EQV\b|OR\s+APPROVED\s+EQUAL|PROVEN\s+SUPERIOR\s+EQUIVALENT|OR\s+EQUAL\b',
    re.IGNORECASE,
)
NO_SUBSTITUTE_RE = re.compile(r'NO\s+SUBSTITUTE|NO\s+EQUIVALENT|ONLY\s+MAKE', re.IGNORECASE)


def _add_deviation(item: dict, flags: list, note: str) -> None:
    notes = item.setdefault('deviation_notes', [])
    if note not in notes:
        notes.append(note)
        flags.append(f'DEVIATION: {note}')


def apply_brand_rules(item: dict, flags: list, applied_defaults: list) -> None:
    """Translate brand/style/trade names into GGPL construction fields."""
    desc = str(item.get('raw_description') or item.get('description') or '')
    if not desc:
        return
    upper = desc.upper()
    gtype = item.get('gasket_type', 'SOFT_CUT')
    permission = bool(EQUIVALENCE_PERMISSION_RE.search(upper))
    no_substitute = bool(NO_SUBSTITUTE_RE.search(upper))

    # Bucket 2 — material trade names
    for pattern, field, value, deviation in MATERIAL_TRADE_NAMES:
        m = re.search(pattern, upper)
        if not m:
            continue
        grade = m.group(1) if m.groups() and m.group(1) else ''
        resolved_value = value.replace('{g}', grade)
        resolved_dev = deviation.replace('{g}', grade)
        if field == 'moc' and gtype in ('SOFT_CUT', 'SHEET_GASKET', 'SHEET', 'O_RING', 'ENVELOPE'):
            item['moc'] = resolved_value
            _add_deviation(item, flags, resolved_dev)
        elif field == 'sw_filler' and gtype in ('SPIRAL_WOUND', 'KAMM'):
            item['sw_filler'] = resolved_value
            _add_deviation(item, flags, resolved_dev)
        elif field == 'moc' and gtype in ('SPIRAL_WOUND', 'KAMM'):
            # trade sheet name inside SPW/KAMM context describes the filler family
            if 'PTFE' in resolved_value.upper():
                item.setdefault('sw_filler', 'PTFE')
                _add_deviation(item, flags, resolved_dev)
        if no_substitute or not permission:
            note = f'CUSTOMER SPECIFIES BRAND MAKE — OFFERED GGPL EQUIVALENT, SUBJECT TO CUSTOMER APPROVAL'
            if no_substitute and note not in flags:
                flags.append(note)
        break

    # Bucket 1 — SPW style codes
    if gtype == 'SPIRAL_WOUND':
        for pattern, effect, deviation in SPW_STYLE_CODES:
            m = re.search(pattern, upper)
            if not m:
                continue
            code = m.group(0).strip()
            item['sw_style_hint'] = effect
            _add_deviation(item, flags, deviation.replace('{code}', code))
            if effect == 'low_stress' and not item.get('special'):
                item['special'] = 'LOW STRESS'
            break

    # ISK brand → style
    if gtype in ('ISK', 'ISK_RTJ') and not item.get('isk_style'):
        for pattern, style, deviation in ISK_BRANDS:
            if re.search(pattern, upper):
                item['isk_style'] = style
                if style == 'FCS':
                    item.setdefault('isk_fire_safety', 'FIRE SAFE')
                _add_deviation(item, flags, deviation)
                break
