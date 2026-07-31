from __future__ import annotations
"""
Applies business rules: defaults, normalization, validation, and status flagging.
Each item gets a 'status' (ready/check/missing) and 'flags' list.
"""
import re
from data.reference_data import (
    normalize_size, normalize_rating, lookup_dimensions, ACCEPTED_MOC,
    lookup_rtj_ring,
)
from data.brand_dictionary import apply_brand_rules
from data.customer_gasket_codes import apply_gasket_code
from core.formatter import NON_STANDARD, is_non_standard

# GGPL escalation phrases (exact house strings — never paraphrased)
ESC_WILL_QUOTE_SOON = 'WILL QUOTE SOON'
ESC_RING_NO = 'KINDLY PROVIDE RING NO'
ESC_RING_DIMS = 'AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS'
ESC_DRAWING = 'KINDLY PROVIDE DRAWING'
ESC_DRAWING_DIMS = 'KINDLY PROVIDE DRAWING WITH DIMENSION'
ESC_CLEAR_SPEC = 'KINDLY PROVIDE CLEAR SPEC'
ESC_DATASHEET = 'KINDLY PROVIDE DATASHEET / DETAILED MATERIAL DESCRIPTION'
ESC_DIMENSIONS = 'KINDLY PROVIDE DIMENSIONS'
ESC_REGRET = 'REGRET'

# RULE J-2 Part 2 — mandatory confirmation for ringed SPW quoted by bare OD/ID
# (no drawing): the stated dims may be the sealing element or the overall
# gasket over the rings. Quote issues; order must not release unresolved.
FLAG_SW_ELEMENT_VS_OVERALL = (
    'KINDLY CONFIRM — STATED OD/ID ARE SEALING ELEMENT DIMS OR OVERALL DIMS '
    '(OVER INNER/OUTER RINGS)? CRITICAL AT THESE DIAMETERS — CHANGES MANUFACTURING DIMS'
)

# RULE V catch-all — dimensional-standard slot forms the GGPL library knows.
# Anything else cited by a customer is kept verbatim and flagged for tech
# review, never silently substituted.
_KNOWN_STANDARD_RE = re.compile(
    r'^(?:TO\s+SUIT\s+)?'
    r'(?:NACE\b'                                  # NACE-prefixed combos / RX template
    r'|(?:ASME|ANSI)\s*B\s*16\s*\.\s*(?:20|21|47|5)\b'
    r'|B\s*16\s*\.\s*(?:20|21|47|5)\b'
    r'|API\s*6\s*[AB]\b'
    r'|EN\s*1514\b'
    r'|AS\s+PER\s+DRAWING\b'
    r')'
)

# mm pipe-OD → NPS map (W1 flange context only — Master Spec A1)
_PIPE_OD_TO_NPS = {
    21.3: '1/2"', 26.7: '3/4"', 33.4: '1"', 42.2: '1-1/4"', 48.3: '1-1/2"',
    60.3: '2"', 73.0: '2-1/2"', 76.1: '2-1/2"', 88.9: '3"', 101.6: '3-1/2"',
    114.3: '4"', 141.3: '5"', 168.3: '6"', 219.1: '8"', 273.0: '10"',
    323.9: '12"', 355.6: '14"', 406.4: '16"', 457.0: '18"', 508.0: '20"', 610.0: '24"',
}

# RULE V — register-line prefix for the governance conclusion (see
# _apply_standard_governance and _requires_review_for_default).
_DEV_NO_DIM_STANDARD_PREFIX = 'no dimensional standard applies'

STATUS_READY = 'ready'
STATUS_CHECK = 'check'
STATUS_MISSING = 'missing'
STATUS_REGRET = 'regret'

# Fields that cannot be defaulted — must be provided by customer
CRITICAL_FIELDS = ['size', 'rating', 'moc']

# Minimal MOC normalization — LLM handles the bulk; this catches residual abbreviations
# that may slip through for common short-form codes.
_MOC_CANONICAL = {
    'NBR': 'NITRILE BUTADIENE RUBBER',
    'FKM': 'VITON',
    'VMQ': 'SILICONE RUBBER',
    'IIR': 'BUTYL RUBBER',
    'CNAF': 'CNAF',
    'NAF': 'CNAF',
    'NON ASBESTOS': 'CNAF',
    'NON-ASBESTOS': 'CNAF',
    'NON ASBESTOS FIBRE': 'CNAF',
    'NON ASBESTOS FIBER': 'CNAF',
    'COMPRESSED NON ASBESTOS FIBRE': 'CNAF',
    'COMPRESSED NON ASBESTOS FIBER': 'CNAF',
    'COMPRESSED NON-ASBESTOS FIBRE': 'CNAF',
    'COMPRESSED NON-ASBESTOS FIBER': 'CNAF',
    'CAF': 'COMPRESSED ASBESTOS FIBRE',
    'NR': 'NATURAL RUBBER',
    'CR': 'NEOPRENE',
    'EPDM': 'EPDM',
    'PTFE': 'PTFE',
    'MODIFIED PTFE': 'MODIFIED PTFE',
    'NEOPRENE': 'NEOPRENE',
    'VITON': 'VITON',
    'GRAPHITE': 'GRAPHITE',
    'GRAFOIL': 'GRAPHITE SHEET',
    'GRAPHITE SHEET': 'GRAPHITE SHEET',
    'TEFLON': 'PTFE',
}

# Keep _MOC_ALIASES as an alias for backward compatibility (empty — LLM normalizes)
_MOC_ALIASES = _MOC_CANONICAL


def _normalize_moc(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().upper()
    return _MOC_CANONICAL.get(key, key)

# Generic "RUBBER" is ambiguous — must ask customer
_AMBIGUOUS_MOC = {'RUBBER'}

# ---------------------------------------------------------------------------
# Thickness normalisation — inch fractions and decimal inches → mm
# ---------------------------------------------------------------------------

# Fractional inch strings → mm  (e.g. "1/8" → 3.2)
_FRAC_INCH_TO_MM: dict[str, float] = {
    '1/64': 0.40,  '1/32': 0.80,  '3/64': 1.20,  '1/16': 1.60,
    '5/64': 2.00,  '3/32': 2.40,  '1/8':  3.20,  '5/32': 4.00,
    '11/64': 4.50, '3/16': 4.80,  '9/32': 7.20,  '1/4':  6.40,
    '5/16': 8.00,
}

# Decimal inch values → mm  (exact matches only — avoids false conversion of valid mm values)
_DECIMAL_INCH_TO_MM: dict[float, float] = {
    0.0039: 0.10,  0.0100: 0.25,  0.0157: 0.40,  0.0197: 0.50,
    0.0312: 0.80,  0.0468: 1.20,  0.0625: 1.60,  0.0781: 2.00,
    0.0937: 2.40,  0.1250: 3.20,  0.1574: 4.00,  0.1750: 4.50,
    0.1875: 4.80,  0.2500: 6.40,  0.2834: 7.20,  0.3150: 8.00,
    # rounded variants that appear in supplier data
    0.020:  0.50,  0.031:  0.80,  0.039:  1.00,  0.060:  1.50,
    0.079:  2.00,  0.098:  2.50,  0.118:  3.00,  0.125:  3.20,
    0.157:  4.00,  0.177:  4.50,  0.188:  4.80,  0.197:  5.00,
    0.236:  6.00,  0.250:  6.40,  0.276:  7.00,  0.315:  8.00,
}


def _parse_thickness_to_mm(raw: str) -> float | None:
    """Parse a thickness string that may be in mm or inches, return mm float or None."""
    s = raw.strip().rstrip('"\'').strip()
    # Strip unit suffix but remember if inch unit was explicit
    inch_explicit = bool(re.search(r'["\'"]|\bIN(CH(ES?)?)?\b', s, re.IGNORECASE))
    cleaned = re.sub(r'\s*(?:MM|THK|THICK|INCH(ES?)?|IN|"|\')\s*', '', s, flags=re.IGNORECASE).strip()

    # Try fractional form first: "1/8", "3/16", "1 1/8" (whole + fraction)
    frac_m = re.fullmatch(r'(\d+)\s+(\d+)/(\d+)', cleaned)
    if frac_m:
        whole, num, den = int(frac_m.group(1)), int(frac_m.group(2)), int(frac_m.group(3))
        inch_val = whole + num / den
        return round(inch_val * 25.4, 2)
    frac_m = re.fullmatch(r'(\d+)/(\d+)', cleaned)
    if frac_m:
        key = f'{frac_m.group(1)}/{frac_m.group(2)}'
        if key in _FRAC_INCH_TO_MM:
            return _FRAC_INCH_TO_MM[key]
        return round(int(frac_m.group(1)) / int(frac_m.group(2)) * 25.4, 2)

    # Plain number
    try:
        val = float(cleaned)
    except ValueError:
        return None

    if inch_explicit:
        return round(val * 25.4, 2)

    # No explicit unit — check if value matches a known decimal-inch entry
    rounded = round(val, 4)
    if rounded in _DECIMAL_INCH_TO_MM:
        return _DECIMAL_INCH_TO_MM[rounded]

    return val  # assume mm


# ---------------------------------------------------------------------------
# Spiral wound helpers
# ---------------------------------------------------------------------------

_SW_RING_ALIASES = {
    # --- Carbon/mild steel ---
    'CARBON STEEL': 'CS', 'C.S.': 'CS', 'MS': 'CS', 'M.S.': 'CS',
    'MILD STEEL': 'CS', 'CS': 'CS',
    # --- SS300-series austenitic ---
    'SS304': 'SS304', 'SS 304': 'SS304', '304': 'SS304', '304SS': 'SS304',
    '304 SS': 'SS304', 'AISI 304': 'SS304', 'TYPE 304': 'SS304', 'AISI 304': 'SS304',
    'SS304L': 'SS304L', 'SS 304L': 'SS304L', '304L': 'SS304L', 'AISI 304L': 'SS304L', '304L SS': 'SS304L',
    'SS310': 'SS310', 'SS 310': 'SS310', '310': 'SS310', 'AISI 310': 'SS310',
    'SS310S': 'SS310S', 'SS 310S': 'SS310S', '310S': 'SS310S',
    'SS316': 'SS316', 'SS 316': 'SS316', 'SS-316': 'SS316', '316': 'SS316', '316SS': 'SS316',
    '316 SS': 'SS316', 'AISI 316': 'SS316', 'TYPE 316': 'SS316',
    'SS316L': 'SS316L', 'SS 316L': 'SS316L', '316L': 'SS316L', 'AISI 316L': 'SS316L', '316L SS': 'SS316L',
    'SS316H': 'SS316H', 'SS 316H': 'SS316H', '316H': 'SS316H',
    'SS317': 'SS317', 'SS 317': 'SS317', '317': 'SS317',
    'SS317L': 'SS317L', 'SS 317L': 'SS317L', '317L': 'SS317L',
    'SS321': 'SS321', 'SS 321': 'SS321', '321': 'SS321',
    'SS321H': 'SS321H', 'SS 321H': 'SS321H', '321H': 'SS321H',
    'SS347': 'SS347', 'SS 347': 'SS347', '347': 'SS347',
    'SS347H': 'SS347H', 'SS 347H': 'SS347H', '347H': 'SS347H',
    # --- SS400-series ferritic/martensitic ---
    'SS410': 'SS410', 'SS 410': 'SS410', '410': 'SS410',
    'SS410S': 'SS410S', 'SS 410S': 'SS410S', '410S': 'SS410S',
    # --- Nickel alloys ---
    'INCOLOY 825': 'INCOLOY 825', 'INCOLOY825': 'INCOLOY 825', 'INCOLY 825': 'INCOLOY 825',
    'INC 825': 'INCOLOY 825', 'INC825': 'INCOLOY 825', 'INCOLOY': 'INCOLOY 825',
    'INCOLOY 800': 'INCOLOY 800', 'INCOLOY800': 'INCOLOY 800', 'INCOLY 800': 'INCOLOY 800',
    'INC 800': 'INCOLOY 800', 'INC800': 'INCOLOY 800',
    'INCONEL 625': 'INCONEL 625', 'INCONEL625': 'INCONEL 625',
    'INC 625': 'INCONEL 625', 'INC625': 'INCONEL 625', 'ALLOY 625': 'INCONEL 625',
    'INCOLY 625': 'INCONEL 625', 'INCONEL': 'INCONEL 625',
    'UNS N06625': 'UNS N06625', 'N06625': 'UNS N06625',
    'UNS N08825': 'UNS N08825', 'N08825': 'UNS N08825',
    # --- Other nickel/high alloys ---
    'HASTELLOY C276': 'HASTELLOY C276', 'HAST ALLOY C276': 'HASTELLOY C276',
    'HASTELLOY C-276': 'HASTELLOY C276', 'C276': 'HASTELLOY C276',
    'MONEL 400': 'MONEL 400', 'MONEL400': 'MONEL 400', 'MONEL': 'MONEL 400', 'ALLOY 400': 'MONEL 400',
    'MONEL 800': 'MONEL 800', 'MONEL800': 'MONEL 800',
    'ALLOY 20': 'ALLOY 20', 'ALLOY20': 'ALLOY 20', 'CARPENTER 20': 'ALLOY 20',
    '6MO': '6MO', '6 MO': '6MO', '6-MO': '6MO', '6% MO': '6MO',
    '254 SMO': 'UNS S31254', '254SMO': 'UNS S31254', 'AVESTA 254 SMO': 'UNS S31254',
    # --- UNS designations ---
    'UNS S31254': 'UNS S31254', 'S31254': 'UNS S31254', 'UNS31254': 'UNS S31254', '31254': 'UNS S31254',
    'UNS S31803': 'UNS S31803', 'S31803': 'UNS S31803', 'UNS31803': 'UNS S31803', '31803': 'UNS S31803',
    'UNS S32205': 'UNS S32205', 'S32205': 'UNS S32205', 'UNS32205': 'UNS S32205', '32205': 'UNS S32205',
    'UNS S32750': 'UNS S32750', 'S32750': 'UNS S32750', 'UNS32750': 'UNS S32750', '32750': 'UNS S32750',
    # --- Titanium ---
    'TITANIUM GR.2': 'TITANIUM GR.2', 'TITANIUM GRADE 2': 'TITANIUM GR.2', 'TI GR2': 'TITANIUM GR.2',
    'TITANIUM GR.12': 'TITANIUM GR.12', 'TITANIUM GRADE 12': 'TITANIUM GR.12', 'TI GR12': 'TITANIUM GR.12',
    # --- Non-ferrous metals ---
    'CU-NI 70/30': 'CU-NI 70/30', 'CUNI 70/30': 'CU-NI 70/30', 'CU-NI/70-30': 'CU-NI 70/30',
    'COPPER NICKEL 70/30': 'CU-NI 70/30',
    'BRASS': 'BRASS',
    'BRONZE': 'BRONZE',
    'ALUMINIUM': 'ALUMINIUM', 'ALUMINUM': 'ALUMINIUM', 'AL': 'ALUMINIUM',
    # --- Low temperature / special ---
    'LTCS': 'LTCS', 'LOW TEMP CARBON STEEL': 'LTCS', 'LOW TEMPERATURE CARBON STEEL': 'LTCS',
    # --- Soft iron (also used as winding/ring in some contexts) ---
    'SOFT IRON': 'SOFT IRON', 'SI': 'SOFT IRON', 'S.I.': 'SOFT IRON',
    # --- Zinc plated / galvanised carbon steel ring ---
    'ZINC PLATED CARBON STEEL': 'ZINC PLATED CARBON STEEL',
    'ZINC-PLATED CARBON STEEL': 'ZINC PLATED CARBON STEEL',
    'ZINC PLATED CS': 'ZINC PLATED CARBON STEEL',
    'ZINC PLATED MS': 'ZINC PLATED CARBON STEEL',
    'ZINC COATED CARBON STEEL': 'ZINC COATED CARBON STEEL',
    'ZINC-COATED CARBON STEEL': 'ZINC COATED CARBON STEEL',
    'ZINC COATED CS': 'ZINC COATED CARBON STEEL',
    'ZINC COATED MS': 'ZINC COATED CARBON STEEL',
    # --- Duplex / super duplex (common aliases) ---
    'DUPLEX': 'UNS S31803', '2205': 'UNS S32205',
    'SUPER DUPLEX': 'UNS S32750', 'SDSS': 'UNS S32750', '2507': 'UNS S32750',
}


# Filler material codes/aliases for spiral wound and KAMM gaskets
# Source: Customer Enq - Quote Data - Material .csv (Filler Material section)
_SW_FILLER_ALIASES = {
    'FG': 'FLEXIBLE GRAPHITE', 'FLEXIBLE GRAPHITE': 'FLEXIBLE GRAPHITE', 'GRAPHITE': 'GRAPHITE',
    'GRAPH': 'GRAPHITE', 'GR': 'GRAPHITE',
    'FLEXICARB': 'FLEXIBLE GRAPHITE', 'FLEXI-CARB': 'FLEXIBLE GRAPHITE',
    'SIGRAFLEX': 'FLEXIBLE GRAPHITE', 'GRAFOIL': 'GRAPHITE', 'GRAFIL': 'GRAPHITE', 'GRAPHOIL': 'GRAPHITE',
    'FLEX INHIB GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'FLEX INHIBITED GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'FLEXIBLE INHIB GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'FLEX. INHIB. GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'FLEX INHIB': 'FLEXIBLE INHIBITED GRAPHITE',
    'EXFOLIATED GRAPHITE': 'EXFOLIATED GRAPHITE',
    'EXFOLIATED EXPANDED GRAPHITE': 'EXFOLIATED EXPANDED GRAPHITE',
    'EXPANDED GRAPHITE': 'GRAPHITE',
    # Flexible inhibited graphite (corrosion-inhibited grade — noted explicitly in GGPL descriptions)
    'FLEXIBLE INHIBITED GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'FLEX INHIB GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'FLEXITALLIC INHIBITED GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'INHIBITED GRAPHITE': 'FLEXIBLE INHIBITED GRAPHITE',
    'PTFE': 'PTFE', 'TEFLON': 'PTFE', 'VIRGIN PTFE': 'PTFE',
    'CNAF': 'CNAF', 'NON ASBESTOS': 'CNAF', 'NAF': 'CNAF',
    'CAF': 'COMPRESSED ASBESTOS FIBRE', 'ASBESTOS': 'COMPRESSED ASBESTOS FIBRE',
    'ARA': 'ARAMID', 'ARAMID': 'ARAMID', 'ARAMID FIBER': 'ARAMID', 'ARAMID FIBRE': 'ARAMID',
    'CER': 'CERAMIC', 'CERAMIC': 'CERAMIC', 'CERAMIC FIBER': 'CERAMIC', 'CERAMIC FIBRE': 'CERAMIC',
    'MICA': 'MICA', 'FLEXIBLE MICA': 'MICA', 'PHLOGOPITE MICA': 'MICA',
    'VERM': 'VERMICULITE', 'VERMICULITE': 'VERMICULITE',
    'GF': 'GLASS FIBER', 'GLASS FIBER': 'GLASS FIBER', 'GLASS FIBRE': 'GLASS FIBER', 'FIBERGLASS': 'GLASS FIBER',
    # RULE Z Part 4 — filler fidelity: a stated filler is copied exactly.
    'GRAPHITE TAPE': 'GRAPHITE TAPE',
    'STANDARD PURITY GRAPHITE': 'STANDARD PURITY GRAPHITE',
    'EXFOLIATED EXPANDED GRAPHITE FILLER': 'EXFOLIATED EXPANDED GRAPHITE',
    'NON-ASBESTOS': 'CNAF', 'NON ASBESTOS FIBRE': 'CNAF',
    'NONE': None,
}

# RULE Z Part 9.5 — transcription damage seen in the source set.
_SW_TRANSCRIPTION_FIXES = {
    'TITATNIUM': 'TITANIUM',
    'TITANIUM GRADE 2': 'TITANIUM GR.2',
    'GROOOVED': 'GROOVED',
    'LOSSE': 'LOOSE',
}


def _norm_ring(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().upper()
    return _SW_RING_ALIASES.get(key, key)


def _norm_filler(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().upper()
    return _SW_FILLER_ALIASES.get(key, key)


def _size_nps_value(size_norm: str | None) -> float | None:
    """Return numeric NPS value from a size string like '28"' or '28 NB'.
    For NB strings, returns None (NB number ≠ NPS number — must go through normalize_size first).
    """
    if not size_norm:
        return None
    s = str(size_norm)
    # If it's an NB string (e.g. "450 NB"), return None — the NPS equivalent
    # is stored in size_norm after normalize_size conversion.
    if re.search(r'\bNB\b', s, re.IGNORECASE):
        return None
    m = re.search(r'([\d.]+)', s)
    return float(m.group(1)) if m else None


def _size_nps_value_from_item(item: dict) -> float | None:
    """Return NPS value, trying size_norm first then raw size (for un-mapped large NPS)."""
    val = _size_nps_value(item.get('size_norm'))
    if val is not None:
        return val
    # Fallback: parse raw size string if it contains '"' (NPS inches, just not in size_map)
    raw = str(item.get('size') or '')
    if '"' in raw and 'NB' not in raw.upper():
        m = re.search(r'([\d.]+)', raw)
        return float(m.group(1)) if m else None
    return None


_MOC_IR_RE = re.compile(r'(\bSS\d{3}L?\b|\bCS\b|\bLTCS\b|\bINCONEL\s*\d*\b|\bMONEL\b|\bHASTELLOY\s*[A-Z0-9]*\b)\s+INNER\s+RING', re.IGNORECASE)
_MOC_OR_RE = re.compile(r'(\bSS\d{3}L?\b|\bCS\b|\bLTCS\b|\bINCONEL\s*\d*\b|\bMONEL\b|\bHASTELLOY\s*[A-Z0-9]*\b)\s+OUTER\s+RING', re.IGNORECASE)
_MOC_IR_ABBR_RE = re.compile(r'\+\s*(\bSS\d{3}L?\b|\bCS\b|\bLTCS\b)\s+IR\b', re.IGNORECASE)
_MOC_OR_ABBR_RE = re.compile(r'&\s*(\bSS\d{3}L?\b|\bCS\b|\bLTCS\b)\s+OR\b', re.IGNORECASE)


def _recover_rings_from_moc(moc_str: str) -> tuple[str | None, str | None]:
    """Try to extract inner_ring and outer_ring from a GPT-4o-generated moc string."""
    ir = or_ = None
    m = _MOC_IR_RE.search(moc_str)
    if m:
        ir = m.group(1).upper()
    else:
        m = _MOC_IR_ABBR_RE.search(moc_str)
        if m:
            ir = m.group(1).upper()
    m = _MOC_OR_RE.search(moc_str)
    if m:
        or_ = m.group(1).upper()
    else:
        m = _MOC_OR_ABBR_RE.search(moc_str)
        if m:
            or_ = m.group(1).upper()
    return ir, or_


def _build_sw_moc(winding_mat: str, filler: str, inner_ring: str | None, outer_ring: str | None) -> str:
    # If filler has a parenthetical qualifier (e.g. "GRAPHITE (98% PURE GRAPHITE)"),
    # place the FILLER keyword before the parenthetical for correct GGPL format.
    paren_m = re.match(r'^(.*?)\s*(\(.*\))\s*$', filler.strip())
    if paren_m:
        filler_str = f'{paren_m.group(1).strip()} FILLER {paren_m.group(2).strip()}'
    else:
        filler_str = f'{filler} FILLER'
    moc = f'{winding_mat} SPIRAL WOUND GASKET WITH {filler_str}'
    if inner_ring and outer_ring:
        moc += f' + {inner_ring} INNER RING & {outer_ring} OUTER RING'
    elif inner_ring:
        moc += f' + {inner_ring} INNER RING'
    elif outer_ring:
        moc += f' + {outer_ring} OUTER RING'
    return moc


_FACE_MATERIAL_RE = re.compile(
    r'\b(?:RF|FF|RAISED[\s\-]+FACE|FULL[\s\-]+FACE|REAR[\s\-]+FACE)\b',
    re.IGNORECASE,
)


def _face_from_text(value: str | None) -> str | None:
    if not value:
        return None
    m = _FACE_MATERIAL_RE.search(str(value))
    if not m:
        return None
    token = re.sub(r'[\s\-]+', ' ', m.group(0).upper())
    if token in ('FF', 'FULL FACE'):
        return 'FF'
    return 'RF'


def _strip_face_tokens(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _FACE_MATERIAL_RE.sub('', str(value))
    cleaned = re.sub(r'\s*[/+,&-]\s*(?=$)', '', cleaned)
    cleaned = re.sub(r'(?<=^)\s*[/+,&-]\s*', '', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = cleaned.strip(' ,/+&-')
    return cleaned or None


def _remove_face_tokens_from_material_fields(item: dict) -> None:
    """Keep RF/FF face tokens out of material and component fields.

    RF/FF describe gasket face only. For SPW/KAMM/RTJ/DJI they are flange context,
    so they should not be preserved as face_type or material text.
    """
    gasket_type = item.get('gasket_type', 'SOFT_CUT')
    material_fields = (
        'moc',
        'sw_winding_material',
        'sw_filler',
        'sw_inner_ring',
        'sw_outer_ring',
        'isk_gasket_material',
        'isk_core_material',
        'isk_sleeve_material',
        'isk_washer_material',
        'isk_insulating_washer',
        'kamm_core_material',
        'kamm_surface_material',
        'kamm_covering_layer',
        'dji_filler',
    )

    detected_face = None
    for field in material_fields:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        detected_face = detected_face or _face_from_text(value)
        item[field] = _strip_face_tokens(value)

    if gasket_type == 'SOFT_CUT' and not item.get('face_type') and detected_face:
        item['face_type'] = detected_face
    elif gasket_type not in ('SOFT_CUT', 'ISK', 'ISK_RTJ'):
        item['face_type'] = None


_B1647_FLAG = (
    'Missing critical field: B16.47 Series A or B not specified — '
    'Series A (ex-API 605, larger OD) and Series B (ex-MSS SP-44, smaller OD) '
    'have DIFFERENT gasket dimensions — customer must confirm'
)


def _set_b1647_standard(
    item: dict,
    flags: list,
    applied_defaults: list,
    default_series: str = 'B',
) -> None:
    """Normalize B16.47 standard and apply the house Series default.

    The default is family-specific: RULE Z Part 5 defaults SPW to SERIES A,
    RULE Y Part 8 defaults KAMM to SERIES B. Either way, a defaulted series is
    a GGPL choice and produces a customer-facing register line.
    """
    std = (item.get('standard') or '').upper()
    # Also check the dedicated series field set by regex_extractor
    series_field = (item.get('series') or '').upper()
    if 'SERIES A' in std or 'SERIES-A' in std or series_field == 'A':
        item['standard'] = 'ASME B16.47 (SERIES-A)'
        item['series'] = 'A'
        return
    if 'SERIES B' in std or 'SERIES-B' in std or series_field == 'B':
        item['standard'] = 'ASME B16.47 (SERIES-B)'
        item['series'] = 'B'
        return
    series = 'A' if str(default_series).upper() == 'A' else 'B'
    item['standard'] = f'ASME B16.47 (SERIES-{series})'
    item['series'] = series
    applied_defaults.append(f'B16.47 series defaulted to SERIES-{series} (house practice)')
    # The _B1647_FLAG below already stops the row; the register line is the
    # customer-facing half and must not double-flag.
    _add_item_deviation(item, flags, f'WE ARE PROCEEDING AS "SERIES-{series}"', blocking=False)
    if _B1647_FLAG not in flags:
        flags.append(_B1647_FLAG)  # Contains "missing critical" → triggers STATUS_MISSING


# RULE Z Part 7 — verbatim house register phrases.
DEV_SPW_STD_THK = 'WE ARE PROCEEDING STANDARD THICKNESS AS "4.5MM"'
DEV_QTY_MISSING = 'KINDLY PROVIDE QUANTITY'


def _reject_non_gasket_thickness(item: dict, flags: list, raw_desc_upper: str) -> None:
    """RULE Z Part 4 — a figure next to a ring, or a compressed/seated service
    dimension, is not the gasket thickness. Move it to the notes and let the
    4.5MM default stand.
    """
    thk = item.get('thickness_mm')
    if not thk:
        return
    try:
        thk_val = float(thk)
    except (TypeError, ValueError):
        return

    # RULE Z Part 4 / 9.5 — `635` is 6.35MM with the decimal lost in
    # transcription. No spiral wound gasket is 635MM thick.
    if thk_val >= 100:
        recovered = thk_val / 100 if thk_val < 1000 else None
        if recovered and 1 <= recovered <= 12:
            item['thickness_mm'] = round(recovered, 2)
            flags.append(
                f'THICKNESS {thk_val:g} READ AS {recovered:g}MM — DECIMAL LOST IN TRANSCRIPTION')
            thk_val = recovered
        else:
            item['thickness_mm'] = None
            flags.append(f'THICKNESS {thk_val:g}MM IS NOT CREDIBLE FOR A SPIRAL WOUND GASKET — VERIFY')
            return

    num = re.escape(f'{thk_val:g}')

    # "3.2 compressed", "seated thickness 3.2" — a service dimension.
    service_re = (
        r'(?:COMPRESS(?:ED)?|SEATED|IN\s+SERVICE|WORKING)\s*(?:THK|THICKNESS)?\s*[:=]?\s*'
        + num
        + r'|' + num + r'\s*(?:MM)?\s*(?:COMPRESS(?:ED)?|SEATED)'
    )
    if re.search(service_re, raw_desc_upper):
        item['thickness_mm'] = None
        flags.append(
            f'{thk_val:g}MM IS A COMPRESSED/SEATED SERVICE DIMENSION — '
            f'GASKET QUOTED AT STANDARD THICKNESS')
        return

    # A ring thickness quoted beside the gasket (3.2 / 0.125" are the common
    # centering-ring gauges). Only reject when the figure is explicitly tied to
    # a ring; a bare 3.2MM gasket is legitimate.
    ring_re = (
        r'(?:CENTERING|CENTRING|OUTER|INNER)\s+RING\s+(?:THK|THICKNESS)\s*[:=]?\s*' + num
        + r'|' + num + r'\s*MM\s+(?:THK\s+)?(?:CENTERING|CENTRING|OUTER|INNER)\s+RING'
    )
    if re.search(ring_re, raw_desc_upper):
        item['thickness_mm'] = None
        flags.append(f'{thk_val:g}MM IS THE RING THICKNESS — GASKET QUOTED AT STANDARD THICKNESS')


def _split_element_vs_overall_dims(item: dict, flags: list, raw_desc_upper: str) -> None:
    """RULE Z Part 6 — customers supply four diameters; GGPL quotes the sealing
    element.

        OROD 576  = outer ring OD      -> notes
        GOD  404  = gasket/winding OD  -> od_mm   (quoted)
        GID  330  = gasket/winding ID  -> id_mm   (quoted)
        IRID 310  = inner ring ID      -> notes
    """
    labelled = dict(re.findall(
        r'\b(OROD|GOD|GID|IRID)\s*[:=]?\s*(\d+(?:\.\d+)?)', raw_desc_upper))
    if not labelled:
        return

    if 'GOD' in labelled:
        item['od_mm'] = float(labelled['GOD'])
    if 'GID' in labelled:
        item['id_mm'] = float(labelled['GID'])
    if 'GOD' in labelled or 'GID' in labelled:
        item['size_type'] = 'OD_ID'
        # These are element dims by construction — the Rule J-2 confirmation
        # does not apply.
        item['dims_are_element'] = True

    ring_dims = [f'{k} {labelled[k]}' for k in ('OROD', 'IRID') if k in labelled]
    if ring_dims:
        flags.append(f'OVERALL RING DIMS (NOT QUOTED): {" / ".join(ring_dims)}')

    ring_thk = re.search(
        r'(?:CENTERING|CENTRING|OUTER|INNER)\s+RING\s+THICKNESS\s*[:=]?\s*(\d+(?:\.\d+)?)',
        raw_desc_upper,
    )
    if ring_thk:
        flags.append(f'RING THICKNESS: {ring_thk.group(1)}MM (NOT THE GASKET THICKNESS)')


def _apply_sw_rules(item: dict, flags: list, applied_defaults: list) -> None:
    """Apply spiral wound-specific defaults and validation (mutates item in place)."""
    winding_mat = _norm_ring(item.get('sw_winding_material'))
    filler = _norm_filler(item.get('sw_filler'))
    filler_stated = bool(filler)
    outer_ring = _norm_ring(item.get('sw_outer_ring'))
    inner_ring = _norm_ring(item.get('sw_inner_ring'))
    raw_desc_upper = (item.get('raw_description') or item.get('description') or '').upper()

    # RULE Z Part 6 — resolve the four-diameter form before anything reads OD/ID.
    _split_element_vs_overall_dims(item, flags, raw_desc_upper)

    # If GPT-4o set moc directly but didn't fill the dedicated ring fields,
    # try to recover inner/outer ring from the moc string before we rebuild it.
    if (not inner_ring or not outer_ring) and item.get('moc'):
        rec_ir, rec_or = _recover_rings_from_moc(item['moc'])
        if not inner_ring and rec_ir:
            inner_ring = rec_ir
        if not outer_ring and rec_or:
            outer_ring = rec_or

    if not filler:
        filler = 'GRAPHITE'
        if inner_ring and outer_ring:
            applied_defaults.append('filler defaulted to GRAPHITE (IR + OR present — industry standard)')
        elif outer_ring:
            applied_defaults.append('filler defaulted to GRAPHITE')
        else:
            applied_defaults.append('filler defaulted to GRAPHITE')

    size_val = _size_nps_value(item.get('size_norm'))

    # A specific SS grade stated on a ring is adopted by the generic "SS"
    # winding and sibling ring; per GGPL quoting convention the reverse also
    # holds — a generic "SS inner/outer ring" beside a graded winding is
    # quoted as the winding grade (e.g. "AISI 316 ... SS INNER RING" →
    # "SS316 INNER RING").
    ring_ss_grades = {
        value for value in (inner_ring, outer_ring)
        if isinstance(value, str) and re.fullmatch(r'SS\d{3}[A-Z]?', value)
    }
    if len(ring_ss_grades) == 1:
        ss_grade = next(iter(ring_ss_grades))
        if winding_mat == 'SS':
            winding_mat = ss_grade
            applied_defaults.append(f'generic SS winding resolved to {ss_grade} from same SPW row')
        if inner_ring == 'SS':
            inner_ring = ss_grade
            applied_defaults.append(f'generic SS inner ring resolved to {ss_grade} from same SPW row')
        if outer_ring == 'SS':
            outer_ring = ss_grade
            applied_defaults.append(f'generic SS outer ring resolved to {ss_grade} from same SPW row')
    if isinstance(winding_mat, str) and re.fullmatch(r'SS\d{3}[A-Z]?(?:/SS\d{3}[A-Z]?)?', winding_mat):
        if inner_ring == 'SS':
            inner_ring = winding_mat
            applied_defaults.append(f'generic SS inner ring resolved to winding grade {winding_mat}')
        if outer_ring == 'SS':
            outer_ring = winding_mat
            applied_defaults.append(f'generic SS outer ring resolved to winding grade {winding_mat}')

    item['sw_winding_material'] = winding_mat or None
    item['sw_outer_ring'] = outer_ring or None
    item['sw_inner_ring'] = inner_ring or None
    item['sw_filler'] = filler

    is_pn_sw = str(item.get('rating') or '').upper().startswith('PN')

    source_mentions_inner = bool(re.search(r'\bINNER\s+R(?:I|L)?NG\b|\bI\.?R\.?\b|\bIR\b', raw_desc_upper))
    if not inner_ring and source_mentions_inner:
        flags.append('Missing critical field: inner ring (mentioned in source but not extracted)')

    # Handle "SS" without grade — ambiguous, cannot build valid MOC
    grade_flag_fired = False
    if winding_mat == 'SS':
        flags.append('Spiral wound: winding grade not specified — confirm SS304/SS316/SS316L/etc.')
        grade_flag_fired = True
        winding_mat = None
        item['sw_winding_material'] = None

    # Infer winding material from ring material when not explicitly stated
    if not winding_mat and not grade_flag_fired:
        inferred = inner_ring or outer_ring
        if inferred and inferred not in ('CS', 'LTCS'):
            # CS/LTCS rings are always the outer ring only; winding is a different alloy
            winding_mat = inferred
            item['sw_winding_material'] = winding_mat
            applied_defaults.append(f'winding material inferred from ring material: {winding_mat}')

    # B16.20 inner-ring MANDATE — beats every omission rule below:
    # CL900 NPS≥24, CL1500 NPS≥12, CL2500 NPS≥4, and ALL PTFE-filled gaskets.
    cls_m = re.search(r'(\d+)', str(item.get('rating') or ''))
    pressure_cls = int(cls_m.group(1)) if cls_m else 0
    ir_mandate = (
        'PTFE' in (filler or '').upper()
        or (pressure_cls == 900 and size_val is not None and size_val >= 24)
        or (pressure_cls == 1500 and size_val is not None and size_val >= 12)
        or (pressure_cls == 2500 and size_val is not None and size_val >= 4)
    )

    # Exhaustive-list rule (Master Spec Rule F): when the enquiry enumerates the
    # full construction (winding + filler + outer ring all customer-stated) and
    # stays silent on the inner ring, that silence is a deliberate omission.
    exhaustive_no_ir = bool(
        winding_mat and filler_stated and outer_ring
        and not inner_ring and not source_mentions_inner
    )
    style_hint = (item.get('sw_style_hint') or '').lower()

    # GGPL standard construction: unless excluded (explicitly, by style code,
    # or by the exhaustive-list rule), SPW gaskets are quoted with an inner
    # ring in the winding material and a CS outer (centering) ring.
    if winding_mat:
        excludes_ir = bool(
            re.search(r'W/?O\.?\s+(?:INNER|IR)|WITHOUT\s+(?:INNER|IR)|NO\s+INNER', raw_desc_upper)
            or exhaustive_no_ir
            or style_hint in ('or_only', 'winding')
        )
        if not inner_ring and (not excludes_ir or ir_mandate):
            inner_ring = winding_mat
            item['sw_inner_ring'] = inner_ring
            if excludes_ir and ir_mandate:
                applied_defaults.append(
                    f'inner ring ADDED per ASME B16.20 mandate ({item.get("rating")}, PTFE/size rule) despite omission')
            else:
                applied_defaults.append(f'inner ring defaulted to winding material {winding_mat} (GGPL standard construction)')
        excludes_or = bool(
            re.search(r'W/?O\.?\s+(?:OUTER|OR|CENTERING)|WITHOUT\s+(?:OUTER|OR|CENTERING)|NO\s+OUTER', raw_desc_upper)
            or style_hint in ('ir_only', 'winding')
        )
        if not outer_ring and not excludes_or:
            outer_ring = 'CS'
            item['sw_outer_ring'] = outer_ring
            applied_defaults.append('outer ring defaulted to CS (GGPL standard construction)')

    # Always rebuild MOC from structured component fields to ensure consistent
    # GGPL format — never use whatever string GPT-4o placed in the moc field
    if winding_mat:
        item['moc'] = _build_sw_moc(winding_mat, filler, inner_ring, outer_ring)
        if style_hint == 'winding' and not inner_ring and not outer_ring:
            item['moc'] += ' (WINDING ONLY)'
    elif not grade_flag_fired:
        flags.append('Missing critical field: winding material (spiral wound)')
        item['escalation'] = ESC_DATASHEET

    # --- RULE Z Part 4 — thickness, and the figures that are NOT the thickness -
    # 4.5MM in 20,828 of 21,814 rows. A ring thickness or a compressed/seated
    # service dimension standing next to the gasket must never become the
    # quoted thickness.
    _reject_non_gasket_thickness(item, flags, raw_desc_upper)

    if not item.get('thickness_mm'):
        item['thickness_mm'] = 4.5
        applied_defaults.append('thickness defaulted to 4.5mm (spiral wound)')
        _add_item_deviation(item, flags, DEV_SPW_STD_THK, blocking=False)

    # Echo LOW STRESS construction note when the enquiry states it
    if not item.get('special') and re.search(r'LOW\s+STRESS|LOW\s+SEATING\s+STRESS', raw_desc_upper):
        item['special'] = 'LOW STRESS'
        item['special_low_stress'] = True

    # RULE Z Part 5 — a quoted molybdenum content qualifies the standard slot.
    mo_match = re.search(
        r'(\d+(?:\.\d+)?)\s*%?\s*MO\w*\s*(?:TO|-|–)\s*(\d+(?:\.\d+)?)\s*%\s*MOLL?Y?',
        raw_desc_upper,
    )
    if mo_match:
        item['standard_qualifier'] = (
            f'( {mo_match.group(1)} %MO TO {mo_match.group(2)}% MOLLY CONTENT )')

    # No face type for spiral wound
    item['face_type'] = None

    # B16.5 is a flange standard (not a gasket standard) — if it appears in a SPW
    # description it was referenced for the flange class, not the gasket. Clear it
    # so the correct gasket standard (B16.20) is applied below.
    if (item.get('standard') or '').upper() in ('ASME B16.5', 'B16.5'):
        item['standard'] = None

    # RULE Z Part 9.3/9.4 + Part 5 — standards that cannot appear on an SPW line.
    # B16.21 is the sheet-gasket standard (67 such rows in the source set) and
    # API 6A/6B is the RTJ standard; Series belongs to B16.47, never B16.20.
    std_now = (item.get('standard') or '').upper().replace(' ', '')
    if not is_non_standard(item.get('standard')):
        if re.search(r'B16\.?21', std_now):
            item['standard'] = 'ASME B16.20'
            applied_defaults.append('B16.21 is a sheet-gasket standard — corrected to ASME B16.20 (SPW)')
        elif re.search(r'API6[AB]', std_now):
            item['standard'] = None
            applied_defaults.append('API 6A/6B is an RTJ standard — cleared on a spiral wound line')
        elif re.search(r'B16\.?20\(SERIES-?([AB])\)', std_now):
            series = re.search(r'B16\.?20\(SERIES-?([AB])\)', std_now).group(1)
            item['standard'] = f'ASME B16.47 (SERIES-{series})'
            item['series'] = series
            applied_defaults.append(
                f'Series belongs to B16.47, not B16.20 — corrected to ASME B16.47 (SERIES-{series})')

    # Standard: EN 1514-2 for PN-rated; B16.47 always enforced for ≥26" NPS (even if
    # customer stated B16.20 — GGPL convention overrides customer spec for large bore).
    # An operator-selected NON STANDARD overrides every convention here.
    if is_non_standard(item.get('standard')):
        pass
    elif is_pn_sw:
        if not item.get('standard'):
            item['standard'] = 'EN 1514-2'
            applied_defaults.append('standard defaulted to EN 1514-2 (SPW on PN-rated flanges)')
    elif size_val is not None and size_val >= 26:
        # RULE Z Part 5 — SPW house default is SERIES A (KAMM defaults to B).
        _set_b1647_standard(item, flags, applied_defaults, default_series='A')
    elif item.get('size_type') == 'OD_ID' and not item.get('rating'):
        # RULE V OD×ID law (W3 world): a dims-only SPW has no size+class to key
        # a dimensional table — no standard is defaulted (KAMM/DJI already
        # follow this convention; the formatter simply omits the tag).
        pass
    elif not item.get('standard'):
        item['standard'] = 'ASME B16.20'
        applied_defaults.append('standard defaulted to ASME B16.20')

    # --- RULE J-2 Part 2: element-vs-overall OD/ID ambiguity (ringed SPW, W3) ---
    # For a ringed spiral wound quoted by bare OD/ID, "OD/ID" can mean the
    # sealing element or the overall gasket over the rings — a 20–30mm
    # manufacturing difference. Quote as stated but demand confirmation,
    # unless a drawing governs or the text itself disambiguates.
    if item.get('size_type') == 'OD_ID':
        od_v, id_v = item.get('od_mm'), item.get('id_mm')
        if od_v and id_v and float(od_v) > float(id_v):
            width = (float(od_v) - float(id_v)) / 2
            thk_v = item.get('thickness_mm')
            # Advisory coherence check: radial width vs thickness sanity
            if (thk_v and float(thk_v) > width) or (width < 8 and float(od_v) >= 300):
                flags.append(
                    f'SPW OD/ID coherence: radial width {width:g}MM vs '
                    f'{thk_v or "?"}MM THK — possible typo in OD/ID, verify'
                )
        if od_v and id_v and (inner_ring or outer_ring):
            special_txt = str(item.get('special') or '').upper()
            has_drawing = bool(
                re.search(r'\bDRAWING\b|\bDRG\b|\bDWG\b', raw_desc_upper)
                or 'DRAWING' in special_txt
            )
            text_disambiguates = bool(re.search(
                r'(?:WINDING|ELEMENT|OVERALL|SEALING)\s+(?:ELEMENT\s+)?[OI]\.?D'
                r'|SEALING\s+ELEMENT'
                r'|OVER\s+(?:THE\s+)?(?:CENTERING|CENTRING|OUTER|INNER)\s+RING',
                raw_desc_upper,
            ))
            # Labelled GOD/GID dims are element dims by construction (Rule Z
            # Part 6) — there is nothing left to confirm.
            if (not has_drawing and not text_disambiguates
                    and not item.get('dims_are_element')
                    and FLAG_SW_ELEMENT_VS_OVERALL not in flags):
                flags.append(FLAG_SW_ELEMENT_VS_OVERALL)


# ---------------------------------------------------------------------------
# RTJ helpers
# ---------------------------------------------------------------------------

_RTJ_HARDNESS_DEFAULTS = {
    'SOFTIRON': 90,
    'SOFTIRON GALVANISED': 90,
    'SOFTIRON ELECTROPLATED': 90,
    'LOW CARBON STEEL': 120,
    'LTCS': 120,
    # SS300-series austenitic
    'SS304': 160, 'SS304L': 160, 'F304': 160,
    'SS310': 160, 'SS310S': 160,
    'SS316': 160, 'SS316L': 160, 'SS316H': 160, 'F316': 160, 'F316L': 160,
    'SS317': 160, 'SS317L': 160,
    'SS321': 160, 'SS321H': 160,
    'SS347': 160, 'SS347H': 160,
    # SS400-series ferritic/martensitic (harder)
    'SS410': 170, 'SS410S': 150,
    # Nickel alloys (GGPL RTJ hardness master table)
    'MONEL 400': 130, 'MONEL 800': 150,
    'INCONEL 600': 180,                          # Alloy 600 (UNS N06600)
    'INCONEL 625': 210,                          # Alloy 625 (UNS N06625) — GGPL standard
    'INCONEL 718': 160,
    'HASTELLOY B2': 230,                         # UNS N10001
    'HASTELLOY C276': 210,                       # UNS N10276
    'HASTELLOY C22': 210,
    'ALLOY 20': 160,
    'INCOLOY 825': 195, 'ALLOY 825': 195,        # Alloy 825 (UNS N08825)
    'INCOLOY 800': 180,                          # Alloy 800 (UNS N08800)
    '6MO': 230,                                  # UNS S31254 (6% Mo super austenitic)
    # Chrome-moly (ASME B16.20 Table 1 / API 6A) — all 130 BHN max
    'F5': 130,                                   # 4–6% Cr, 0.5% Mo
    '4-6% CR 0.5% MO': 130,
    'F9': 130,                                   # 9% Cr, 1% Mo
    'F11': 130,                                  # 1-1/4% Cr, 1/2% Mo
    'F22': 130,                                  # 2-1/4% Cr, 1% Mo
    'F91': 130,                                  # 9% Cr, 1% Mo, V (Grade 91)
    # UNS designations
    'UNS N06600': 180,  # Inconel 600
    'UNS N08825': 195,  # Incoloy 825
    'UNS N08800': 180,  # Incoloy 800
    'UNS G10100': 120,  # Low carbon steel
    'UNS S31600': 160,  # SS316
    'UNS S31603': 160,  # SS316L
    'UNS S30400': 160,  # SS304
    'UNS N06625': 210,  # Inconel 625
    'UNS S31254': 230,  # 6Mo / 254 SMO
    # Titanium
    'TITANIUM GR.2': 215, 'TITANIUM GR.12': 215,
    # Duplex / super duplex (GGPL RTJ hardness master table)
    'UNS S31803': 235, 'UNS S32205': 230,        # Duplex 2205
    'UNS S32750': 240, 'UNS S32760': 240,        # Super Duplex
    # Non-ferrous
    'CU-NI 70/30': 100, 'BRASS': 80, 'BRONZE': 80, 'ALUMINIUM': 35,
}

# Max BHN per material — used to validate customer-supplied hardness
_RTJ_MAX_BHN = _RTJ_HARDNESS_DEFAULTS.copy()

_RTJ_MOC_ALIASES = {
    # Soft iron
    'SOFT IRON': 'SOFTIRON', 'SOFTIRON': 'SOFTIRON', 'SI': 'SOFTIRON', 'S.I.': 'SOFTIRON',
    'SOFT IRON GALVANISED': 'SOFTIRON GALVANISED',
    'SOFT IRON GALVANIZED': 'SOFTIRON GALVANISED',
    'GALVANISED SOFT IRON': 'SOFTIRON GALVANISED',
    'GALVANIZED SOFT IRON': 'SOFTIRON GALVANISED',
    'SOFT IRON ELECTROPLATED': 'SOFTIRON ELECTROPLATED',
    'SOFTIRON ELECTROPLATED': 'SOFTIRON ELECTROPLATED',
    'SOFT IRON ZINC PLATED': 'SOFTIRON GALVANISED',
    'SOFT IRON CN+ZN PLATED': 'SOFTIRON GALVANISED',
    # Carbon/low-alloy steel
    'LOW CARBON STEEL': 'LOW CARBON STEEL', 'LCS': 'LOW CARBON STEEL',
    'CARBON STEEL': 'LOW CARBON STEEL',
    'UNS G10100': 'LOW CARBON STEEL', 'G10100': 'LOW CARBON STEEL',
    'LTCS': 'LTCS', 'LOW TEMPERATURE CARBON STEEL': 'LTCS', 'LOW TEMP CARBON STEEL': 'LTCS',
    # SS austenitic
    'SS304': 'SS304', 'SS 304': 'SS304', '304SS': 'SS304', '304 SS': 'SS304', 'AISI 304': 'SS304',
    'UNS S30400': 'SS304', 'S30400': 'SS304',
    'SS304L': 'SS304L', 'SS 304L': 'SS304L', '304L': 'SS304L',
    'SS310': 'SS310', 'SS 310': 'SS310', 'SS310S': 'SS310S', 'SS 310S': 'SS310S',
    'SS316': 'SS316', 'SS 316': 'SS316', '316SS': 'SS316', '316 SS': 'SS316', 'AISI 316': 'SS316',
    'UNS S31600': 'SS316', 'S31600': 'SS316',
    'STAINLESS STEEL 316': 'SS316', 'STAINLESS STEEL 316L': 'SS316L',
    'STAINLESS STEEL 304': 'SS304', 'STAINLESS STEEL 304L': 'SS304L',
    'STAINLESS STEEL 321': 'SS321', 'STAINLESS STEEL 347': 'SS347',
    'SS316L': 'SS316L', 'SS 316L': 'SS316L', '316L': 'SS316L',
    'SS316H': 'SS316H', 'SS 316H': 'SS316H', '316H': 'SS316H',
    'SS317': 'SS317', 'SS317L': 'SS317L',
    'SS321': 'SS321', 'SS321H': 'SS321H',
    'SS347': 'SS347', 'SS347H': 'SS347H',
    'SS410': 'SS410', 'SS410S': 'SS410S',
    'F304': 'F304', 'F316': 'F316', 'F316L': 'F316L',
    # Nickel alloys
    'MONEL': 'MONEL 400', 'MONEL 400': 'MONEL 400', 'MONEL400': 'MONEL 400', 'ALLOY 400': 'MONEL 400',
    'MONEL 800': 'MONEL 800', 'MONEL800': 'MONEL 800',
    'INCONEL 600': 'INCONEL 600', 'INCONEL600': 'INCONEL 600', 'INC 600': 'INCONEL 600', 'ALLOY 600': 'INCONEL 600',
    'UNS N06600': 'UNS N06600', 'N06600': 'UNS N06600',
    'INCONEL 718': 'INCONEL 718', 'INCONEL718': 'INCONEL 718',
    'INCONEL': 'INCONEL 625', 'INCONEL 625': 'INCONEL 625', 'INCONEL625': 'INCONEL 625',
    'INC 625': 'INCONEL 625', 'INC625': 'INCONEL 625',
    'INCOLOY 825': 'INCOLOY 825', 'INCOLOY825': 'INCOLOY 825', 'INCOLY 825': 'INCOLOY 825',
    'ALLOY 825': 'INCOLOY 825',
    'INCOLOY': 'INCOLOY 825',   # bare "Incoloy" is most commonly 825 in RTJ context
    'INCOLOY 800': 'INCOLOY 800', 'INCOLOY800': 'INCOLOY 800', 'INCOLY 800': 'INCOLOY 800',
    'HASTELLOY C276': 'HASTELLOY C276', 'HAST ALLOY C276': 'HASTELLOY C276', 'C276': 'HASTELLOY C276',
    'HASTELLOY C22': 'HASTELLOY C22', 'C22': 'HASTELLOY C22',
    'F5': 'F5', '4-6% CR 0.5% MO': 'F5', '4-6CR 0.5MO': 'F5', 'CHROME MOLY': 'F5', 'CR-MO': 'F5',
    'F9': 'F9', '9% CR 1% MO': 'F9', '9CR 1MO': 'F9',
    'F11': 'F11', '1-1/4% CR 1/2% MO': 'F11', '1-1/4 CR - 1/2 MO': 'F11', '1.25 CR 0.5 MO': 'F11',
    'F22': 'F22', '2-1/4% CR 1% MO': 'F22', '2-1/4 CR - 1 MO': 'F22', '2-1/4 CR 1 MO': 'F22',
    '2 1/4 CR 1 MO': 'F22', '2.25 CR 1 MO': 'F22', '2-1/4CR-1MO': 'F22',
    'F91': 'F91', '9% CR 1% MO V': 'F91', 'GRADE 91': 'F91', 'GR 91': 'F91',
    'ALLOY 20': 'ALLOY 20', 'ALLOY20': 'ALLOY 20', 'CARPENTER 20': 'ALLOY 20',
    '6MO': '6MO', '6 MO': '6MO',
    '254 SMO': 'UNS S31254', '254SMO': 'UNS S31254', 'AVESTA 254 SMO': 'UNS S31254',
    # UNS numbers
    'UNS N06625': 'UNS N06625', 'N06625': 'UNS N06625',
    'UNS N08825': 'UNS N08825', 'N08825': 'UNS N08825',
    'UNS S31254': 'UNS S31254', 'S31254': 'UNS S31254',
    'UNS S31803': 'UNS S31803', 'S31803': 'UNS S31803',
    'UNS S32205': 'UNS S32205', 'S32205': 'UNS S32205',
    'UNS S32750': 'UNS S32750', 'S32750': 'UNS S32750',
    # Duplex aliases
    'DUPLEX': 'UNS S31803', '2205': 'UNS S32205',
    'SUPER DUPLEX': 'UNS S32750', 'SDSS': 'UNS S32750', '2507': 'UNS S32750',
    # Titanium
    'TITANIUM GR.2': 'TITANIUM GR.2', 'TI GR2': 'TITANIUM GR.2', 'TITANIUM GRADE 2': 'TITANIUM GR.2',
    'TITANIUM GR.12': 'TITANIUM GR.12', 'TI GR12': 'TITANIUM GR.12', 'TITANIUM GRADE 12': 'TITANIUM GR.12',
    # Non-ferrous
    'CU-NI 70/30': 'CU-NI 70/30', 'CUNI 70/30': 'CU-NI 70/30', 'COPPER NICKEL 70/30': 'CU-NI 70/30',
    'BRASS': 'BRASS', 'BRONZE': 'BRONZE',
    'ALUMINIUM': 'ALUMINIUM', 'ALUMINUM': 'ALUMINIUM',
}

_RTJ_MOC_PATTERN = (
    r'SOFT\s+IRON|G10100|UNS\s+G10100|S30400|UNS\s+S30400|S31600|UNS\s+S31600|'
    r'UNS\s*N\s*0\d{4}|INCOLOY\s*825|INCOLY\s*825|ALLOY\s*825|INCONEL\s*625|UNS\s*S\s*3\d{4}|'
    r'STAINLESS\s+STEEL\s+3\d{2}L?|'
    r'SS[-\s]*316L?|316L?SS|SS[-\s]*304L?|304L?SS|SS[-\s]*321|SS[-\s]*347|F\d{1,2}|'
    r'LOW\s+CARBON\s+STEEL|LCS|LTCS|MONEL\s*400|HASTELLOY\s*C[-\s]*276'
)


def _recover_rtj_fields_from_description(item: dict) -> None:
    raw_desc = (item.get('raw_description') or item.get('description') or '').upper()
    if not raw_desc:
        return

    if not item.get('ring_no'):
        ring = re.search(r'\b(?P<prefix>BX|RX|R)\s*[- ]?\s*(?P<num>\d{1,4})\b', raw_desc)
        if ring:
            item['ring_no'] = f'{ring.group("prefix")}-{ring.group("num")}'

    if not item.get('rtj_groove_type'):
        if re.search(r'\bOCT(?:AGONAL)?\b|TYPE\s*O\b|8[-\s]*SIDED', raw_desc):
            item['rtj_groove_type'] = 'OCTAGONAL'
        elif re.search(r'\bOVAL\b|ELLIPTICAL|TYPE\s*R\b', raw_desc):
            item['rtj_groove_type'] = 'OVAL'

    if not item.get('standard'):
        if re.search(r'\bAPI\s*6\s*A\b', raw_desc):
            item['standard'] = 'API 6A'
        elif re.search(r'\bAPI\s*6\s*B(?:X)?\b', raw_desc):
            item['standard'] = 'API 6A'

    if not item.get('moc'):
        paren = re.search(rf'\((?P<mat>{_RTJ_MOC_PATTERN})\)', raw_desc)
        explicit = re.search(rf'\b(?P<mat>{_RTJ_MOC_PATTERN})\b', raw_desc)
        match = paren or explicit
        if match:
            item['moc'] = match.group('mat')


def _apply_rtj_rules(item: dict, flags: list, applied_defaults: list) -> None:
    _recover_rtj_fields_from_description(item)

    # Normalize MOC — if LLM returned null, try to recover from raw_description via aliases
    raw_moc = (item.get('moc') or '').strip().upper()
    if not raw_moc:
        raw_desc_upper = (item.get('raw_description') or item.get('description') or '').upper()
        for alias_key in sorted(_RTJ_MOC_ALIASES, key=len, reverse=True):
            if re.search(r'\b' + re.escape(alias_key) + r'\b', raw_desc_upper):
                raw_moc = alias_key
                break
    if raw_moc.startswith('UNS '):
        norm_moc = raw_moc
    else:
        norm_moc = _RTJ_MOC_ALIASES.get(raw_moc, raw_moc) if raw_moc else None
    item['moc'] = norm_moc

    # Groove type — normalise abbreviation then default
    _groove_norm = {'OCT': 'OCTAGONAL', 'OVAL': 'OVAL'}
    if item.get('rtj_groove_type'):
        item['rtj_groove_type'] = _groove_norm.get(
            item['rtj_groove_type'].upper(), item['rtj_groove_type'].upper()
        )
    elif not str(item.get('ring_no') or '').upper().startswith('RX-'):
        # BX rings are also quoted with the OCTAGONAL groove label per GGPL convention
        item['rtj_groove_type'] = 'OCTAGONAL'
        applied_defaults.append('groove type defaulted to OCTAGONAL')

    # Convert HRBW (Rockwell B) to BHN if the description contains HRB/HRBW values
    # (customer spec sheets sometimes use HRB instead of BHN)
    _HRBW_TO_BHN = {68: 120, 83: 160}
    raw_desc = (item.get('raw_description') or '').upper()
    if not item.get('rtj_hardness_bhn'):
        hrb_m = re.search(r'(\d+)\s*HRB(?:W)?\b', raw_desc)
        if hrb_m:
            hrb_val = int(hrb_m.group(1))
            bhn_converted = _HRBW_TO_BHN.get(hrb_val)
            if bhn_converted:
                item['rtj_hardness_bhn'] = bhn_converted
                item['rtj_hardness_spec'] = f'{bhn_converted}BHN HARDNESS'
                applied_defaults.append(f'converted {hrb_val} HRBW → {bhn_converted} BHN')

    # BHN hardness — default from MOC, then validate against material maximum
    if not item.get('rtj_hardness_bhn') and not item.get('rtj_hardness_spec') and norm_moc:
        bhn = _RTJ_HARDNESS_DEFAULTS.get(norm_moc)
        if bhn:
            item['rtj_hardness_bhn'] = bhn
            item['rtj_hardness_spec'] = f"{bhn} BHN HARDNESS"
            applied_defaults.append(f'BHN hardness defaulted to {bhn} for {norm_moc}')
        else:
            # BHN is mandatory on all RTJ gaskets (ASME B16.20)
            flags.append(
                f'Missing critical field: BHN hardness — not known for "{norm_moc}", confirm with customer (ASME B16.20)'
            )
    elif item.get('rtj_hardness_bhn') and not item.get('rtj_hardness_spec'):
        item['rtj_hardness_spec'] = f"{int(item['rtj_hardness_bhn'])} BHN HARDNESS"
    elif not item.get('rtj_hardness_bhn') and not item.get('rtj_hardness_spec') and not norm_moc:
        flags.append('Missing critical field: BHN hardness not specified — confirm with customer (ASME B16.20)')

    # Validate supplied BHN does not exceed material maximum (ASME B16.20)
    if norm_moc and item.get('rtj_hardness_bhn'):
        max_bhn = _RTJ_MAX_BHN.get(norm_moc)
        if max_bhn and float(item['rtj_hardness_bhn']) > max_bhn:
            flags.append(
                f'RTJ BHN {int(item["rtj_hardness_bhn"])} exceeds max allowed {max_bhn} BHN '
                f'for {norm_moc} (ASME B16.20) — verify with customer'
            )

    # Normalize ring_no: "BX 156" / "R 24" / "RX53" / "R14" → "BX-156" / "R-24" / "RX-53" / "R-14"
    if item.get('ring_no'):
        rn = str(item['ring_no']).strip()
        # Space separator: "BX 156" → "BX-156"
        rn = re.sub(r'\b(BX|RX|R)\s+(\d+)\b', r'\1-\2', rn, flags=re.IGNORECASE)
        # No separator: "R14" → "R-14", "BX156" → "BX-156"
        rn = re.sub(r'\b(BX|RX)(\d+)\b', r'\1-\2', rn, flags=re.IGNORECASE)
        rn = re.sub(r'\bR(\d+)\b', r'R-\1', rn, flags=re.IGNORECASE)
        item['ring_no'] = rn.upper()

    # Ring number lookup
    if not item.get('ring_no'):
        ring = lookup_rtj_ring(item.get('size_norm'), item.get('rating'))
        if ring:
            item['ring_no'] = ring
            applied_defaults.append(f'ring number looked up: {ring}')
        else:
            flags.append('Ring number not in lookup table — enter manually (check ASME B16.20)')
            item['ring_no'] = None
            # Exact GGPL escalation phrases: compact-flange specs need dims;
            # a B16.5-range size (≤24") with no table ring asks for the ring
            # number. ≥26" falls through to the large-bore SIZE format instead.
            raw_all = (item.get('raw_description') or item.get('description') or '').upper()
            size_val_rtj = _size_nps_value_from_item(item)
            _cls_rtj = re.search(r'(\d{3,4})', str(item.get('rating') or ''))
            _cls_rtj = int(_cls_rtj.group(1)) if _cls_rtj else None
            if re.search(r'ISO\s*27509|COMPACT\s+FLANGE|\bSP-\d+', raw_all):
                item['escalation'] = ESC_RING_DIMS
            elif size_val_rtj is not None and size_val_rtj <= 24:
                # B16.5-range size with no table ring (gap sizes like 22",
                # 2500# above 12") — per the size gate, never invent a ring
                item['escalation'] = ESC_RING_NO
            elif size_val_rtj is not None and size_val_rtj >= 26 and _cls_rtj not in (300, 600, 900):
                # B16.47 rings (R93–R105) exist only for classes 300–900
                item['escalation'] = ESC_RING_NO

    # Normalize flange-style API codes (API 6B, API 6BX are flange types, not gasket standards;
    # the actual gasket standard for wellhead RTJ rings is API 6A)
    cited_std_upper = (item.get('standard') or '').upper().replace('-', ' ')
    cited_std_upper = ' '.join(cited_std_upper.split())  # collapse whitespace
    if cited_std_upper in ('API 6BX', 'API 6B', 'API 6 BX', 'API 6 B'):
        item['standard'] = 'API 6A'

    # Set standard based on ring prefix, rating, or bore size.
    # GGPL convention: BX (wellhead) rings are quoted to API 6A; R-series
    # rings are quoted to ASME B16.20 even when the enquiry cites an API
    # flange (API 3000/5000 etc. describe the flange, not the gasket).
    rn_upper = (item.get('ring_no') or '').upper()
    rating = item.get('rating') or ''
    explicit_api6a = item.get('standard') == 'API 6A' or bool(
        re.search(r'\bAPI\s*6\s*A\b', (item.get('raw_description') or item.get('description') or '').upper())
    )
    if is_non_standard(item.get('standard')):
        pass  # operator marked NON STANDARD — never assign a standard tag
    elif rn_upper.startswith('BX-'):
        item['standard'] = 'API 6A'
    elif rn_upper.startswith('RX-'):
        item['standard'] = 'API 6A' if explicit_api6a else 'NACE MR-01-75 / ISO 15156, API 6B'
    elif rn_upper.startswith('R-'):
        # An explicitly cited API 6A standard is honoured; a mere API flange
        # rating (API 3000/5000) is not — R-series rings quote to B16.20.
        item['standard'] = 'API 6A' if explicit_api6a else 'ASME B16.20'
    elif rating.startswith('API ') or item.get('standard') == 'API 6A':
        item['standard'] = 'API 6A'
    else:
        size_val = _size_nps_value_from_item(item)
        if size_val is not None and size_val >= 26:
            _set_b1647_standard(item, flags, applied_defaults)
        else:
            item['standard'] = 'ASME B16.20'
    item['face_type'] = None
    item['thickness_mm'] = None


# ---------------------------------------------------------------------------
# KAMM helpers
# ---------------------------------------------------------------------------

_KAMM_MATERIAL_RE = (
    r'SS\s*3\d{2}L?|3\d{2}L?\s*SS|SS\s*4\d{2}|CS|CARBON\s+STEEL|'
    r'LTCS|DUPLEX|SUPER\s+DUPLEX|INCONEL\s*\d+|INCOLOY\s*\d+|'
    r'HASTELLOY\s*C276|MONEL\s*\d*|TITANIUM(?:\s+GR\.?\s*\d+)?|GRAPHITE|PTFE|MICA'
)


def _kamm_number(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(str(raw).replace(',', '.'))
    except ValueError:
        return None


def _kamm_norm_material(raw: str | None) -> str | None:
    if not raw:
        return None
    value = re.sub(r'\s+', ' ', raw.strip().upper())
    return _norm_ring(value) or _norm_filler(value) or value


def _append_kamm_special(item: dict, value: str) -> None:
    if not value:
        return
    special = (item.get('special') or '').strip()
    if value.upper() in special.upper():
        return
    item['special'] = f'{special}, {value}' if special else value


def _recover_kamm_fields_from_description(item: dict) -> None:
    raw = item.get('raw_description') or item.get('description') or ''
    if not raw:
        return
    upper = raw.upper()

    if not item.get('od_mm') or not item.get('id_mm'):
        dim_match = re.search(
            r'\bOD\s*[:=]?\s*(?P<od>\d+(?:[.,]\d+)?)\s*(?:MM)?\b.*?'
            r'\bID\s*[:=]?\s*(?P<id>\d+(?:[.,]\d+)?)\s*(?:MM)?\b',
            upper,
            re.DOTALL,
        )
        if dim_match:
            item['od_mm'] = item.get('od_mm') or _kamm_number(dim_match.group('od'))
            item['id_mm'] = item.get('id_mm') or _kamm_number(dim_match.group('id'))
            item['size_type'] = 'OD_ID'

    # Prefer total gasket thickness stated in the SIZE block over core-only
    # thickness from "CORE MAT'L ... 3.0MM THICKNESS".
    size_section = re.search(r'\bSIZE\s*:\s*(?P<size>.*?)(?:\bMATERIAL\s*:|$)', upper, re.DOTALL)
    size_text = size_section.group('size') if size_section else upper
    total_thk = None
    th_match = re.search(r'\bTH\s*[:=]?\s*(?P<thk>\d+(?:[.,]\d+)?)\s*(?:MM)?\b', size_text)
    if not th_match:
        th_match = re.search(
            r'\bOD\s*[:=]?\s*\d+(?:[.,]\d+)?\s*(?:MM)?\b.*?'
            r'\bID\s*[:=]?\s*\d+(?:[.,]\d+)?\s*(?:MM)?\b.*?'
            r'(?:\bB\s*[:=]?\s*\d+(?:[.,]\d+)?\s*(?:MM)?\b\s*X\s*)?'
            r'(?P<thk>\d+(?:[.,]\d+)?)\s*(?:MM)?\b',
            size_text,
            re.DOTALL,
        )
    if th_match:
        total_thk = _kamm_number(th_match.group('thk'))

    core_thk = None
    core_thk_match = re.search(
        r'\b(?:CORE\s+)?(?:MAT[\'’]?L|MATERIAL)?\s*:?\s*(?:' + _KAMM_MATERIAL_RE + r')?\s*,?\s*'
        r'(?P<core>\d+(?:[.,]\d+)?)\s*MM\s+THICKNESS\b',
        upper,
    )
    if not core_thk_match:
        core_thk_match = re.search(r'\((?P<core>\d+(?:[.,]\d+)?)\s*\+\s*2\s*X\s*\d+(?:[.,]\d+)?\)', upper)
    if core_thk_match:
        core_thk = _kamm_number(core_thk_match.group('core'))

    cover_thk_match = re.search(r'\bWITH\s+(?P<cover>\d+(?:[.,]\d+)?)\s*MM\s+(?:GRAPHITE|PTFE|MICA)\b', upper)
    cover_thk = _kamm_number(cover_thk_match.group('cover')) if cover_thk_match else None

    # RULE Y Part 2 — "(3.2 CORE + 0.5 FACING) THK": core and layer stated
    # together in brackets. TOTAL = CORE + 2 x FACING.
    cf_match = re.search(
        r'\(\s*(?P<core>\d+(?:[.,]\d+)?)\s*(?:MM\s*)?CORE\s*\+\s*'
        r'(?P<facing>\d+(?:[.,]\d+)?)\s*(?:MM\s*)?(?:FACING|LAYER|COVERING)\s*\)',
        upper,
    )
    if cf_match:
        core_thk = _kamm_number(cf_match.group('core'))
        cover_thk = _kamm_number(cf_match.group('facing'))
        total_thk = None  # recomputed from the pair by the thickness engine

    # "{n}T" = total thickness in MM (e.g. "4.5T SOFT IRON GASKET").
    if total_thk is None:
        t_match = re.search(r'\b(?P<t>\d+(?:[.,]\d+)?)\s*T\b(?!\w)', upper)
        if t_match and not re.search(r'\bTHK\b|\bTHICK', upper[:t_match.start()]):
            total_thk = _kamm_number(t_match.group('t'))

    # "0.5 mm Graphite/PTFE covering layers" — layer stated without the CORE pair.
    if cover_thk is None:
        layer_match = re.search(
            r'\b(?P<cover>\d+(?:[.,]\d+)?)\s*MM\s+(?:[A-Z/ ]{0,20}?)'
            r'(?:GRAPHITE|PTFE|EPTFE|MICA)[A-Z/ ]{0,20}?\s*(?:COVERING\s+)?LAYERS?\b',
            upper,
        )
        if layer_match:
            cover_thk = _kamm_number(layer_match.group('cover'))

    if cover_thk is not None:
        item['kamm_layer_thk'] = cover_thk

    if total_thk is None and core_thk is not None and cover_thk is not None:
        total_thk = core_thk + (2 * cover_thk)
    if total_thk is not None:
        item['thickness_mm'] = total_thk
    if core_thk is not None and not item.get('kamm_core_thk'):
        item['kamm_core_thk'] = core_thk

    if not item.get('kamm_surface_material') and not item.get('sw_filler'):
        surface_match = re.search(r'\b(?P<surface>GRAPHITE|PTFE|MICA)\s+(?:ON\s+BOTH\s+SIDES|LAYER|LAYERS|FACING|COVERING)\b', upper)
        if not surface_match:
            surface_match = re.search(r'\bMATERIAL\s*:\s*(?P<surface>GRAPHITE|PTFE|MICA)\s*/\s*(?:' + _KAMM_MATERIAL_RE + r')\b', upper)
        if surface_match:
            surface = _kamm_norm_material(surface_match.group('surface'))
            item['kamm_surface_material'] = surface
            item['sw_filler'] = surface

    if not item.get('kamm_core_material') and not item.get('sw_winding_material'):
        core_match = re.search(r'\bCORE\s+MAT[\'’]?L\s*:\s*(?P<core>' + _KAMM_MATERIAL_RE + r')\b', upper)
        if not core_match:
            core_match = re.search(r'\bMATERIAL\s*:\s*(?:GRAPHITE|PTFE|MICA)\s*/\s*(?P<core>' + _KAMM_MATERIAL_RE + r')\b', upper)
        if core_match:
            core = _kamm_norm_material(core_match.group('core'))
            item['kamm_core_material'] = core
            item['sw_winding_material'] = core

    rib_match = re.search(r'\bB\s*[:=]?\s*(?P<rib>\d+(?:[.,]\d+)?)\s*MM\b', upper)
    if rib_match and not item.get('kamm_rib'):
        item['kamm_rib'] = f'{_kamm_number(rib_match.group("rib")):g}MM'

    type_match = re.search(r'\bTYPE\s*[-:]?\s*(?P<type>\d+)\b', upper)
    if type_match:
        _append_kamm_special(item, f'TYPE-{type_match.group("type")}')
    if item.get('kamm_rib'):
        _append_kamm_special(item, f'B={item["kamm_rib"]}')

    # --- RULE Y Part 2 — three bare numbers = OD / ID / SEAL WIDTH -----------
    # "1216 1184 16 SS 347 KAMM PROFILE". (OD-ID)/2 must confirm the width,
    # otherwise the third number is something else and is left alone.
    if not item.get('od_mm') and not item.get('id_mm'):
        triple = re.match(
            r'^\s*(?P<a>\d{2,5}(?:\.\d+)?)\s+(?P<b>\d{2,5}(?:\.\d+)?)\s+(?P<c>\d{1,3}(?:\.\d+)?)\b',
            upper,
        )
        if triple:
            a, b, c = (_kamm_number(triple.group(g)) for g in ('a', 'b', 'c'))
            if a and b and c and a > b and abs(((a - b) / 2) - c) < 0.51:
                item['od_mm'], item['id_mm'] = a, b
                item['kamm_seal_width_mm'] = c
                item['size_type'] = 'OD_ID'

    # --- RULE Y Part 7 — geometry variants ----------------------------------
    if re.search(r'\bCONVEX\b|\bCROWNED\b', upper):
        item['kamm_geometry'] = 'CONVEX'
    elif re.search(r'\bOBROUND\b|\bRACETRACK\b|\bMANWAY\b', upper):
        item['kamm_geometry'] = 'OBROUND'
    elif re.search(r'\bOVAL\b', upper):
        item['kamm_geometry'] = 'OVAL'

    if not item.get('kamm_rib') and re.search(r'\bW/\s*RIB\b|\bWITH\s+RIB\b', upper):
        item['kamm_rib'] = 'WITH RIB'

    crossbar = re.search(
        r'\b(?P<n>\d+)?\s*CROSS\s*BARS?\b(?:[^.]{0,20}?(?P<t>\d+(?:\.\d+)?)\s*MM\s*THK)?'
        r'|\bPASS\s+PARTITIONS?\b',
        upper,
    )
    if crossbar and not item.get('kamm_crossbar'):
        count = crossbar.groupdict().get('n')
        thk = crossbar.groupdict().get('t')
        parts = [p for p in (
            f'{count} CROSSBAR' if count else 'CROSSBAR',
            f'{thk}MM THK' if thk else '',
        ) if p]
        item['kamm_crossbar'] = ' '.join(parts)


# --- RULE Y Part 4 — the thickness engine (total <-> core) -------------------
#
# A kammprofile is core + one covering layer per side: TOTAL = CORE + 2 x LAYER.
# The GGPL string must always carry ({core}MM CORE THK).

# GGPL builds kammprofile cores from its own stock thicknesses. A customer core
# GGPL does not stock is supplied as the nearest stock core and the total is
# recomputed — house practice, not an error (Rule Y Part 4.1).
_KAMM_CORE_STOCK = (2.0, 3.0, 3.2, 3.3, 3.5, 4.0, 5.0)
_KAMM_STD_FACING = 0.5   # MM per side

# Rule Y Part 4.1 lists 3.5 as an observed stock core *and* states that a
# customer-stated `(3.5 CORE + 0.5 FACING)` is supplied as GGPL's 3.2MM core
# for a 4.2MM total. Both hold, because they are different pathways: a 3.5 core
# is what GGPL derives from a 4.5MM total (Part 4.2, 10 rows), but a core the
# customer states alongside a facing is built to this map. Keep them separate.
_KAMM_STATED_CORE_SUBSTITUTION = {3.5: 3.2}

DEV_KAMM_THK = (
    'WE ARE PROCEEDING WITH GASKET THICKNESS AS {total}MM '
    '(CORE THICKNESS AS {core}MM) AS PER MANUFACTURING PRACTICE'
)
# Three cores appear against a 4.5MM total in house data — 3.5 (0.5 facing),
# 3.3 (0.6) and 3.0 (0.75). Apply 3.5 and say so (Rule Y Part 4.2).
FLAG_KAMM_LAYER_AMBIGUOUS = (
    'LAYER THK NOT STATED — 0.5MM/SIDE APPLIED (CORE {core}MM). CONFIRM IF 0.6 OR 0.75MM.'
)
FLAG_KAMM_THIN_CORE = 'CONFIRM GROOVE DEPTH / SPACE LIMIT'


def _fmt_mm(value: float) -> str:
    """Trim trailing zeros: 4.0 -> '4', 4.20 -> '4.2'."""
    return f'{float(value):g}'


def _nearest_kamm_core(core: float) -> float:
    """Nearest GGPL stock core; ties resolve downward (the buildable side)."""
    return min(_KAMM_CORE_STOCK, key=lambda stock: (abs(stock - core), stock))


def _apply_kamm_thickness_engine(item: dict, flags: list, applied_defaults: list) -> None:
    """Resolve total <-> core, substitute non-stock cores, and emit the register
    line for every value GGPL chose rather than the customer.
    """
    total = _kamm_number(item.get('thickness_mm'))
    core = _kamm_number(item.get('kamm_core_thk'))
    facing = _kamm_number(item.get('kamm_layer_thk')) or _KAMM_STD_FACING

    if core is None and total is None:
        return

    # A core can never equal or exceed the total — a kammprofile always carries a
    # covering layer per side. Such a pair is a mis-parse, so the core is dropped
    # and re-derived from the total below.
    if core is not None and total is not None and core >= total - 0.01:
        core = None

    substituted = False
    if core is not None:
        # Core stated — honour it only if GGPL stocks it, and apply the confirmed
        # stated-core substitutions first.
        for stated, built in _KAMM_STATED_CORE_SUBSTITUTION.items():
            if abs(core - stated) < 0.01:
                core = built
                substituted = True
                applied_defaults.append(
                    f'stated {stated:g}MM core supplied as GGPL {built:g}MM stock core')
                break
        stock_core = _nearest_kamm_core(core)
        if abs(stock_core - core) > 0.01:
            applied_defaults.append(
                f'core {_fmt_mm(core)}MM is not GGPL stock — supplied as '
                f'{_fmt_mm(stock_core)}MM stock core (manufacturing practice)'
            )
            core = stock_core
            substituted = True
        # Total is always recomputed from the core actually being built.
        recomputed = round(core + 2 * facing, 3)
        if total is None or substituted or abs(recomputed - total) > 0.01:
            if total is not None and abs(recomputed - total) > 0.01 and not substituted:
                # Customer's own core + total disagree; trust the pair as stated.
                recomputed = total
            total = recomputed
    else:
        # Total only — back-derive the core (0.5MM layer per side, GGPL standard).
        core = round(total - 2 * _KAMM_STD_FACING, 3)
        if abs(total - 4.5) < 0.01:
            # The 4.5MM ambiguity: 3.5 core is the house pick, but say so.
            core = 3.5
            _add_item_deviation(item, flags, FLAG_KAMM_LAYER_AMBIGUOUS.format(core=_fmt_mm(core)))
        stock_core = _nearest_kamm_core(core)
        if abs(stock_core - core) > 0.01:
            core = stock_core
            total = round(core + 2 * _KAMM_STD_FACING, 3)
            substituted = True
        applied_defaults.append(
            f'core thickness derived as {_fmt_mm(core)}MM from {_fmt_mm(total)}MM total '
            f'({_fmt_mm(_KAMM_STD_FACING)}MM layer per side)'
        )

    item['thickness_mm'] = total
    item['kamm_core_thk'] = core

    if substituted:
        # Accepted house practice — told to the customer, but not a review stop.
        _add_item_deviation(item, flags, DEV_KAMM_THK.format(
            total=_fmt_mm(total), core=_fmt_mm(core)), blocking=False)

    # Thin-core caution: manufacturable but weak (Rule Y Part 4.2).
    if core < 3.0:
        _add_item_deviation(item, flags, f'{_fmt_mm(core)}MM CORE — {FLAG_KAMM_THIN_CORE}')


def _apply_kamm_rules(item: dict, flags: list, applied_defaults: list) -> None:
    _recover_kamm_fields_from_description(item)

    winding_mat = item.get('sw_winding_material') or item.get('kamm_core_material')
    if winding_mat and not item.get('sw_winding_material'):
        item['sw_winding_material'] = winding_mat
    filler = _norm_filler(item.get('sw_filler')) or 'GRAPHITE'
    outer_ring = _norm_ring(item.get('sw_outer_ring'))
    inner_ring = _norm_ring(item.get('sw_inner_ring'))

    if not filler:
        applied_defaults.append('filler defaulted to GRAPHITE')

    item['sw_filler'] = filler
    item['sw_outer_ring'] = outer_ring or None
    item['sw_inner_ring'] = inner_ring or None

    # Build MOC string from component fields (moc is always cleared before apply_rules for KAMM)
    if not item.get('moc') and winding_mat:
        if inner_ring and outer_ring:
            item['moc'] = f'{winding_mat} KAMMPROFILE GASKET WITH {filler} FILLER + {inner_ring} INNER RING & {outer_ring} OUTER RING'
        elif outer_ring:
            item['moc'] = f'{winding_mat} KAMMPROFILE GASKET WITH {filler} FILLER + {outer_ring} OUTER RING'
        else:
            item['moc'] = f'KAMMPROFILE {winding_mat} WITH {filler} LAYER ON BOTH SIDES'
    elif not item.get('moc'):
        flags.append('KAMM: winding material not identified — verify SS316/SS304/etc.')

    if not item.get('thickness_mm') and not item.get('kamm_core_thk'):
        item['thickness_mm'] = 4.5
        applied_defaults.append('thickness defaulted to 4.5mm (KAMM)')

    # RULE Y Part 4 — resolve total <-> core and substitute non-stock cores.
    # Every KAMM line must carry ({core}MM CORE THK); this is what fills it.
    _apply_kamm_thickness_engine(item, flags, applied_defaults)

    # RULE Y Part 6 — ring logic. On a W1 flange item (size + class) with the
    # customer silent on rings, GGPL's default construction is an integral outer
    # ring. W3 equipment gaskets sitting in a groove get no ring unless stated.
    is_w1 = item.get('size_type') != 'OD_ID' and bool(item.get('rating'))
    if is_w1 and not inner_ring and not outer_ring and not item.get('kamm_integral_outer_ring'):
        raw_desc_upper = (item.get('raw_description') or item.get('description') or '').upper()
        excludes_ring = bool(re.search(
            r'W/?O\.?\s+(?:OUTER|OR|CENTERING|RING)|WITHOUT\s+(?:OUTER|OR|CENTERING|RING)'
            r'|NO\s+(?:OUTER|CENTERING)\s+RING',
            raw_desc_upper,
        ))
        if not excludes_ring:
            item['kamm_integral_outer_ring'] = 'INTEGRAL'
            applied_defaults.append('integral outer ring applied (GGPL default for flange KAMM)')

    # RULE Y Part 7 — never invent a crown, rib or crossbar count; these come
    # from the drawing or a confirmation.
    raw_upper = (item.get('raw_description') or item.get('description') or '').upper()
    has_drawing = bool(re.search(r'\bDRAWING\b|\bDRG\b|\bDWG\b|\bSK-\w+', raw_upper))
    geometry = item.get('kamm_geometry')
    if geometry == 'CONVEX':
        _add_item_deviation(
            item, flags,
            'CONVEX / CROWNED PROFILE — CONFIRM CROWN GEOMETRY AGAINST DRAWING; TOOLING CHECK')
    if geometry in ('OVAL', 'OBROUND') and not has_drawing and not item.get('kamm_seal_width_mm'):
        item['escalation'] = ESC_DRAWING_DIMS
    if item.get('kamm_crossbar') and not has_drawing:
        # Crossbar layout is drawing-governed — echo the spec, do not invent it.
        item['escalation'] = ESC_DRAWING
    # A rib the customer stated is simply carried. It is the *absence* of a rib
    # statement on an exchanger item that needs confirming (Rule Y Part 7).
    is_exchanger = bool(re.search(
        r'\bEXCHANGER\b|\bCH\.?\s*CVR\b|\bCHANNEL\s+COVER\b|\bTUBE\s*SHEET\b|\bSHELL\b',
        raw_upper,
    ))
    if is_exchanger and not item.get('kamm_rib') and not has_drawing:
        _add_item_deviation(item, flags, 'KINDLY CONFIRM RIB DETAILS', blocking=False)

    # No standard for custom OD/ID KAMM; only for NPS-rated KAMM
    if item.get('size_type') != 'OD_ID' and not item.get('standard'):
        is_pn_kamm = str(item.get('rating') or '').upper().startswith('PN')
        size_val = _size_nps_value(item.get('size_norm'))
        if is_pn_kamm:
            item['standard'] = 'EN 1514-6'
            applied_defaults.append('standard defaulted to EN 1514-6 (KAMM on PN-rated flanges)')
        elif size_val is not None and size_val >= 26:
            # RULE Y Part 8 — house practice for KAMM is SERIES B (SPW defaults A).
            _set_b1647_standard(item, flags, applied_defaults, default_series='B')
        else:
            item['standard'] = 'ASME B16.20'
            applied_defaults.append('standard defaulted to ASME B16.20')

    item['face_type'] = None


# ---------------------------------------------------------------------------
# DJI helpers
# ---------------------------------------------------------------------------

def _apply_dji_rules(item: dict, flags: list, applied_defaults: list) -> None:
    if not item.get('od_mm') or not item.get('id_mm'):
        flags.append('DJI: OD and ID dimensions required')
    if not item.get('thickness_mm'):
        flags.append('DJI: thickness not specified — confirm with customer')
    item['face_type'] = None
    # Default filler to GRAPHITE if not extracted by LLM
    if not item.get('dji_filler'):
        item['dji_filler'] = 'GRAPHITE'
        applied_defaults.append('DJI filler defaulted to GRAPHITE')
    # EN 1514-4 for PN-rated flanges; no standard otherwise (DJI is OD/ID based).
    # Operator-selected NON STANDARD is kept as-is.
    if not is_non_standard(item.get('standard')):
        is_pn_dji = str(item.get('rating') or '').upper().startswith('PN')
        item['standard'] = 'EN 1514-4' if is_pn_dji else None
        if is_pn_dji:
            applied_defaults.append('standard set to EN 1514-4 (DJI on PN-rated flanges)')
    item['rating'] = None  # DJI has no pressure class


# ---------------------------------------------------------------------------
# ISK helpers
# ---------------------------------------------------------------------------

_FIRE_SAFE_RE = re.compile(r'\bFIRE\s*SAFE\b', re.IGNORECASE)
_NON_FIRE_SAFE_RE = re.compile(r'\bNON[-\s]FIRE\s*SAFE\b', re.IGNORECASE)
# Spring-energised seal patterns → NON FIRE SAFE
_SPRING_SEAL_RE = re.compile(
    r'\bPRES\s+ENRG\b|\bPRESSURE\s+ENERGI[SZ]ED\b|\bSPRING[\s-]ENERGI[SZ]ED\b|'
    r'\bSPIRL\s+SPRING\b|\bSPIRAL\s+SPRING\b|\bSPRING\s+SEAL\b|\bSS\s+PRES\s+ENRG\b',
    re.IGNORECASE,
)
# TEFLON/PTFE flat seal patterns → FIRE SAFE
_TEFLON_SEAL_RE = re.compile(
    r'\bW/TEFLON\s+SEALS?\b|\bTEFLON\s+SEALS?\b|\bPTFE/EPDM\s+SEAL\b|\bW/TEFLON\b',
    re.IGNORECASE,
)


def _infer_isk_fire_safety(item: dict) -> str | None:
    """Infer ISK fire safety from description and special field using regex patterns.
    Returns 'FIRE SAFE', 'NON FIRE SAFE', or None if undeterminable.
    """
    combined = ' '.join(filter(None, [
        item.get('raw_description', ''),
        item.get('special', ''),
    ]))
    if _NON_FIRE_SAFE_RE.search(combined):
        return 'NON FIRE SAFE'
    if _FIRE_SAFE_RE.search(combined):
        return 'FIRE SAFE'
    # Domain rules
    if _SPRING_SEAL_RE.search(combined):
        return 'NON FIRE SAFE'
    if _TEFLON_SEAL_RE.search(combined):
        return 'FIRE SAFE'
    return None


_ISK_MATERIAL_RE = re.compile(
    r'(GLASS\s+REINFORCED\s+EPOXY\b.*|GRE\s*\(?\s*G[-\s]?1[01]\s*\)?.*)',
    re.IGNORECASE,
)
# Boilerplate in WAFER-format descriptions that should be stripped
_ISK_WAFER_BOILERPLATE_RE = re.compile(
    r'(?:MANUFACTURE\s+STD\s+WAFER\s+\d+\s+R\.?F\.?\s*\(125-250\s+AARH\)\s*_?\s*|'
    r'Standard\s+MANUFACTURE\s+STD\s+WAFER\s+\d+\s+R\.?F\.?\s*)',
    re.IGNORECASE,
)


def _extract_isk_special_from_desc(item: dict) -> str | None:
    """When LLM fails to populate 'special' for ISK, try to extract material
    description from the raw_description. Handles WAFER-format ISK descriptions like:
    'NPS: 16 ... MANUFACTURE STD WAFER 300 R.F. (125-250 AARH) _ GLASS REINFORCED EPOXY (NEMA G10) W/TEFLON SEALS SS 316 METAL CORE REINFORCEMENT'
    → 'GLASS REINFORCED EPOXY (NEMA G10) W/TEFLON SEALS SS 316 METAL CORE REINFORCEMENT'
    """
    raw = (item.get('raw_description') or '').strip()
    # Strip the WAFER boilerplate then check for GRE/GLASS REINFORCED EPOXY
    cleaned = _ISK_WAFER_BOILERPLATE_RE.sub('', raw)
    m = _ISK_MATERIAL_RE.search(cleaned)
    if m:
        return m.group(0).strip()
    return None


# Matches core material in raw ISK descriptions: "316 SS CORE", "SS316 CORE", "SS 316 CORE",
# "SS316L CORE", "DUPLEX CORE", "INCONEL CORE", "CS CORE", etc.
_ISK_CORE_RE = re.compile(
    r'\b(?:SS\s*3\d{2}L?|3\d{2}L?\s*SS|DUPLEX|SUPER\s+DUPLEX|INCONEL|HASTELLOY|CS|CARBON\s+STEEL|ALLOY\s+\w+)\s+CORE\b',
    re.IGNORECASE,
)


def _recover_isk_core(item: dict) -> None:
    """If core material appears in raw description but is absent from special, append it.
    Skipped when isk_core_material is already populated (regex extractor already handled it)."""
    if item.get('isk_core_material'):
        return  # dedicated field already populated — no need to duplicate into special
    raw = (item.get('raw_description') or '').strip()
    special = (item.get('special') or '').upper()
    m = _ISK_CORE_RE.search(raw)
    if m and 'CORE' not in special:
        core_str = m.group(0).upper()
        # Normalise "316 SS CORE" → "SS316 CORE"
        core_str = re.sub(r'^(\d{3}L?)\s*(SS)', r'SS\1', core_str)
        item['special'] = (item['special'] + ', ' + core_str).lstrip(', ') if item.get('special') else core_str


_ISK_ABBREV = [
    # Abbreviation → full GGPL-standard term (applied to special field post-LLM)
    (re.compile(r'\bPRES(?:SURE)?\s+ENRG(?:IZED)?\b', re.IGNORECASE), 'PRESSURE ENERGIZED'),
    (re.compile(r'\bSPIRL\b', re.IGNORECASE), 'SPIRAL'),
    (re.compile(r'\bSPNG\b', re.IGNORECASE), 'SPRING'),
    (re.compile(r'\bENRG(?:IZED)?\b', re.IGNORECASE), 'ENERGIZED'),
    (re.compile(r'\bSPRING\s+ENRG(?:IZED)?\b', re.IGNORECASE), 'SPRING ENERGIZED'),
]


def _normalize_isk_special(special: str) -> str:
    """Expand common LLM abbreviations in ISK special field to full GGPL terms."""
    s = special
    for pattern, replacement in _ISK_ABBREV:
        s = pattern.sub(replacement, s)
    return s


def _recover_isk_fields_from_description(item: dict) -> None:
    raw = (item.get('raw_description') or item.get('description') or '')
    if not raw:
        return
    upper = raw.upper()

    if not item.get('size'):
        size_match = re.search(
            r'\b(?P<size>\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(?:"|INCHES?\b|IN\b)',
            upper,
        )
        if size_match:
            item['size'] = f'{size_match.group("size")}"'
            item['size_type'] = 'NPS'

    if not item.get('rating'):
        rating_match = re.search(r'\b(?P<rating>150|300|400|600|900|1500|2500)\s*#', upper)
        if rating_match:
            item['rating'] = f'{rating_match.group("rating")}#'
        else:
            pn_match = re.search(r'\bPN\s*-?\s*(?P<rating>\d{1,2})\b', upper)
            if pn_match:
                item['rating'] = f'PN {pn_match.group("rating")}'

    if not item.get('isk_style'):
        style_match = re.search(r'\bSTYLE\s*[-:]?\s*(?P<style>FCS|N|CS|VCS)\b', upper)
        if style_match:
            style = style_match.group('style')
            item['isk_style'] = f'STYLE-{style}' if style in ('N', 'CS') else style
        elif re.search(r'\bTYPE\s*[- ]?F\b', upper):
            item['isk_style'] = 'TYPE-F'
        elif re.search(r'\bTYPE\s*[- ]?E\b', upper):
            item['isk_style'] = 'TYPE-E'

    if re.search(r'\bTYPE\s*[- ]?F\b', upper):
        item['isk_type'] = 'TYPE-F'
        item['face_type'] = item.get('face_type') or 'RF'
    elif re.search(r'\bTYPE\s*[- ]?E\b', upper):
        item['isk_type'] = 'TYPE-E'
        item['face_type'] = item.get('face_type') or 'FF'

    if not item.get('face_type'):
        if re.search(r'\bRF\b|\bRAISED\s+FACE\b', upper):
            item['face_type'] = 'RF'
        elif re.search(r'\bFF\b|\bFULL\s+FACE\b', upper):
            item['face_type'] = 'FF'

    if not item.get('special'):
        set_match = re.search(r'\(\s*SET\s*:\s*(?P<set>.*?)\s*\)', raw, re.IGNORECASE)
        if set_match:
            item['special'] = set_match.group('set').strip()

    if not item.get('standard'):
        if re.search(r'\b(?:ASME|ANSI)\s+B\s*16\.5\b', upper):
            item['standard'] = 'ASME B16.5'
        elif re.search(r'\b(?:ASME|ANSI)\s+B\s*16\.47\b', upper):
            item['standard'] = 'ASME B16.47'

    if not item.get('isk_gasket_material'):
        grade_match = re.search(r'\b(?:GRE\s*)?G\s*-?\s*10\s*/\s*G\s*-?\s*11\b|\b(?:GRE\s*)?G\s*-?\s*10\b|\b(?:GRE\s*)?G\s*-?\s*11\b', upper)
        if grade_match:
            grade = re.sub(r'\s+', '', grade_match.group(0).upper())
            grade = grade.replace('GRE', '').replace('G-', 'G')
            item['isk_gasket_material'] = f'GRE {grade}'

    if not item.get('isk_core_material'):
        core_match = re.search(r'\b(?:WITH\s+)?(?P<core>SS\s*3\d{2}L?|3\d{2}L?\s*SS)\s+\d+(?:\.\d+)?\s*MM\s+THK\b', upper)
        if core_match:
            core = re.sub(r'\s+', '', core_match.group('core').upper())
            core = re.sub(r'^(\d{3}L?)SS$', r'SS\1', core)
            item['isk_core_material'] = core

    if not item.get('isk_primary_seal') and re.search(r'\bPTFE\s+PRIMARY\s+SEAL\b', upper):
        item['isk_primary_seal'] = 'PTFE PRIMARY SEAL'
    if not item.get('isk_secondary_seal') and re.search(r'\bMICA\s+SECONDARY\s+SEAL\b', upper):
        item['isk_secondary_seal'] = 'MICA SECONDARY SEAL'

    if not item.get('isk_sleeve_material') and re.search(r'\bWASHER\s*&\s*SLEEVES\b|\bWASHER\s+AND\s+SLEEVES\b', upper):
        item['isk_sleeve_material'] = item.get('isk_gasket_material')
        item['isk_insulating_washer'] = item.get('isk_insulating_washer') or item.get('isk_gasket_material')

    if not item.get('isk_washer_material'):
        washer_match = re.search(r'\b(?P<washer>HARDENED\s+DIELECTRIC\s+COATED\s+(?:SS\s*)?3\d{2}L?|(?:SS\s*)?3\d{2}L?)\s+METALLIC\s+WASHER\b', upper)
        if washer_match:
            washer = washer_match.group('washer').strip().upper()
            washer = re.sub(r'\b(?<!SS)(3\d{2}L?)\b', r'SS\1', washer)
            item['isk_washer_material'] = re.sub(r'\s+', ' ', washer)


def _apply_isk_rules(item: dict, flags: list, applied_defaults: list) -> None:
    _recover_isk_fields_from_description(item)

    gtype = item.get('gasket_type', 'ISK')

    # For STYLE-CS kits the cited B16.5 flange standard is replaced by the
    # gasket standard B16.20; other styles echo it as "TO SUIT ASME B16.5".
    _style_now = (item.get('isk_style') or '').upper()
    if (item.get('standard') or '').upper() in ('ASME B16.5', 'B16.5') and _style_now in (
            'CS', 'STYLE-CS', 'VCS', 'STYLE-VCS'):
        item['standard'] = 'ASME B16.20'

    # TYPE-E = full face (FF) by definition; TYPE-F/D = raised face (RF) always
    # VCS is equivalent to STYLE-CS (RF by default)
    isk_style_raw = (item.get('isk_style') or '').upper()
    isk_type_raw  = (item.get('isk_type')  or '').upper()
    _is_type = lambda t: t in isk_style_raw or t in isk_type_raw
    if _is_type('TYPE-E') or isk_style_raw == 'TYPE E':
        item['face_type'] = 'FF'
    elif _is_type('TYPE-F') or isk_style_raw == 'TYPE F':
        item['face_type'] = 'RF'  # Type F = raised face = always RF
    elif _is_type('TYPE-D') or isk_style_raw == 'TYPE D':
        item['face_type'] = 'RF'  # Type D = raised face

    # Face type: extract from LLM or default RF
    if not item.get('face_type'):
        item['face_type'] = 'RF'
        applied_defaults.append('face type defaulted to RF (ISK)')

    item['thickness_mm'] = None

    # Normalize rating: ASME class numbers without '#' → add '#' (e.g. "300" → "300#")
    raw_rating = str(item.get('rating') or '').strip()
    if raw_rating and not raw_rating.upper().startswith('PN') and not raw_rating.endswith('#'):
        _ASME_CLASSES_ISK = {150, 300, 600, 900, 1500, 2500, 3000}
        try:
            if int(raw_rating) in _ASME_CLASSES_ISK:
                item['rating'] = raw_rating + '#'
        except ValueError:
            pass

    # If LLM failed to extract special, try regex extraction from raw description.
    # Skip when regex_extractor already populated the dedicated component fields.
    if not item.get('special') and not item.get('isk_gasket_material'):
        extracted_special = _extract_isk_special_from_desc(item)
        if extracted_special:
            item['special'] = extracted_special

    # Normalize common ISK component abbreviations in special field
    if item.get('special'):
        item['special'] = _normalize_isk_special(item['special'])

    has_component_evidence = any(item.get(key) for key in (
        'isk_core_material',
        'isk_sleeve_material',
        'isk_washer_material',
        'isk_primary_seal',
        'isk_insulating_washer',
    ))

    # Default seal/gasket material only when the row already contains kit
    # component evidence. Vague ISK rows need clarification, not a polished
    # assumed kit description.
    if not item.get('isk_gasket_material') and not item.get('special'):
        if has_component_evidence:
            item['isk_gasket_material'] = 'PTFE SPRING ENERGIZED SEAL'
            applied_defaults.append('ISK gasket material defaulted to PTFE SPRING ENERGIZED SEAL')
        else:
            flags.append('Missing critical field: ISK component specification')

    # Recover core material the LLM may have dropped (e.g. "316 SS CORE" → appended to special)
    _recover_isk_core(item)

    # Fire safety: regex inference is more reliable than LLM for this field
    # (LLM can cross-contaminate values across batched items).
    # Inference overrides LLM when it finds a clear pattern.
    inferred_fs = _infer_isk_fire_safety(item)
    if inferred_fs:
        item['isk_fire_safety'] = inferred_fs
        item.pop('isk_fire_safety_defaulted', None)
    elif item.get('isk_fire_safety'):
        item.pop('isk_fire_safety_defaulted', None)
    elif not item.get('isk_fire_safety'):
        item['isk_fire_safety'] = 'NON FIRE SAFE'
        item['isk_fire_safety_defaulted'] = True

    # Track whether the customer explicitly stated a standard (used by formatter)
    customer_standard = item.get('standard')
    item['isk_standard_explicit'] = bool(
        customer_standard and str(customer_standard).lower() not in ('null', 'none', '')
        and not is_non_standard(customer_standard)
    )

    if gtype == 'ISK_RTJ':
        if not item.get('standard'):
            item['standard'] = 'ASME B16.5'
            applied_defaults.append('standard defaulted to ASME B16.5 (ISK_RTJ)')
    else:
        # Standard ISK: keep explicit flange-fit standards; otherwise default
        # from pressure family and size per GGPL convention.
        is_pn = str(item.get('rating') or '').upper().startswith('PN')
        if customer_standard:
            item['standard'] = customer_standard
        elif is_pn:
            item['standard'] = 'EN 1514-5'
            applied_defaults.append('standard set to EN 1514-5 (ISK on PN-rated flanges)')
        else:
            nps_val = _size_nps_value_from_item(item)
            if nps_val is not None and nps_val >= 26:
                _set_b1647_standard(item, flags, applied_defaults)
            else:
                item['standard'] = 'ASME B16.20'
                applied_defaults.append('standard set to ASME B16.20 (ISK)')


_ORING_MOC_PATTERN = (
    r'VITON|FKM|NBR|EPDM|NEOPRENE|SILICONE|VMQ|PTFE|TEFLON|'
    r'NITRILE(?:\s+BUTADIENE\s+RUBBER)?|BUTYL(?:\s+RUBBER)?|IIR|'
    r'NATURAL\s+RUBBER|NR|FFKM|KALREZ|AFLAS'
)


def _looks_like_oring(raw_desc: str) -> bool:
    if not re.search(r'\bO[\s\-]?RING\b', raw_desc):
        return False
    # In spiral-wound data, "O-RING" often means outer ring. Only classify as
    # a standalone O-ring when elastomer/material or ID/CS sizing context exists.
    if re.search(r'\bSPIRAL\b|\bSPW\b|\bOUTER\s+RING\b', raw_desc):
        return False
    return bool(
        re.search(r'\b(?:MATERIAL|MOC)\s*:', raw_desc)
        or re.search(r'\bID\s*\d', raw_desc)
        or re.search(r'\b(?:CS|C/S|CORD|SECTION|THK|THICKNESS)\s*\d', raw_desc)
        or re.search(rf'\b(?:{_ORING_MOC_PATTERN})\b', raw_desc)
    )


def _extract_oring_number(token: str | None) -> float | None:
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _recover_oring_fields_from_description(item: dict) -> None:
    raw = item.get('raw_description') or item.get('description') or ''
    if not raw:
        return
    upper = raw.upper()

    if not item.get('moc'):
        material_match = re.search(
            rf'\b(?:MATERIAL|MOC)\s*:\s*(?P<mat>{_ORING_MOC_PATTERN})\b',
            upper,
        )
        if not material_match:
            material_match = re.search(rf'\b(?P<mat>{_ORING_MOC_PATTERN})\b', upper)
        if material_match:
            item['moc'] = material_match.group('mat')

    if not item.get('id_mm') or not item.get('thickness_mm'):
        size_patterns = [
            r'\bID\s*(?P<id>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:X|BY|/)\s*(?:C/S|CS|CORD|SECTION|THK|THICK(?:NESS)?)\s*(?P<cs>\d+(?:\.\d+)?)\s*(?:MM)?\b',
            r'\b(?P<id>\d+(?:\.\d+)?)\s*(?:MM)?\s*ID\s*(?:X|BY|/)\s*(?P<cs>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:C/S|CS|CORD|SECTION|THK|THICK(?:NESS)?)\b',
            r'\bID\s*(?P<id>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:X|BY|/)\s*(?P<cs>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:C/S|CS|CORD|SECTION|THK|THICK(?:NESS)?)\b',
            r'\bID\s*(?P<id>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:X|BY|/)\s*(?P<cs>\d+(?:\.\d+)?)\s*(?:MM)?\b',
            r'\b(?P<id>\d+(?:\.\d+)?)\s*(?:MM)?\s*ID\s*(?:X|BY|/)\s*(?P<cs>\d+(?:\.\d+)?)\s*(?:MM)?\b',
            r'\b(?P<id>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:X|BY|/)\s*(?P<cs>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:O[\s\-]?RING|VITON|FKM|NBR|EPDM)\b',
        ]
        for pattern in size_patterns:
            match = re.search(pattern, upper)
            if match:
                item['id_mm'] = item.get('id_mm') or _extract_oring_number(match.group('id'))
                item['thickness_mm'] = item.get('thickness_mm') or _extract_oring_number(match.group('cs'))
                item['size_type'] = 'ID_CS'
                break

    if not item.get('pressure_rating'):
        pressure_match = re.search(
            r'\b(?:PRESSURE\s+RATING|WORKING\s+PRESSURE|PRESSURE)\s*:\s*(?P<pressure>\d+(?:\.\d+)?)\s*(?P<unit>BAR|PSI|KG/CM2|KPA|MPA)\b',
            upper,
        )
        if pressure_match:
            item['pressure_rating'] = (
                f'{pressure_match.group("pressure")} {pressure_match.group("unit")}'
            )


def _apply_oring_rules(item: dict, flags: list, applied_defaults: list) -> None:
    _recover_oring_fields_from_description(item)

    raw_moc = (item.get('moc') or '').strip().upper()
    if raw_moc:
        item['moc'] = _normalize_moc(raw_moc)

    item['size_type'] = item.get('size_type') or 'ID_CS'
    item['size'] = None
    item['rating'] = None
    item['size_norm'] = None
    item['rating_norm'] = None
    item['face_type'] = None
    # An O-ring is sized by ID x CS — no dimensional standard governs it. Keep
    # the NON STANDARD sentinel the governance gate set (Rule V Part 2).
    item['standard'] = NON_STANDARD if is_non_standard(item.get('standard')) else None
    item['dimensions'] = None


def _sanitize_llm_nulls(item: dict) -> dict:
    """Convert LLM-returned string 'null' / 'none' / '' to actual None.
    Parses thickness strings including fractions and inch values; strips unit
    suffixes from other numeric fields.
    """
    _NULL_STRINGS = {'null', 'none', 'n/a', 'na', ''}
    _OTHER_NUMERIC = ('od_mm', 'id_mm', 'rtj_hardness_bhn')
    for key, val in list(item.items()):
        if not isinstance(val, str):
            continue
        stripped = val.strip()
        if stripped.lower() in _NULL_STRINGS:
            item[key] = None
        elif key == 'thickness_mm':
            item[key] = _parse_thickness_to_mm(stripped)
        elif key in _OTHER_NUMERIC:
            cleaned = re.sub(r'\s*(?:MM|THK|INCH|IN|M)\s*$', '', stripped, flags=re.IGNORECASE).strip()
            try:
                item[key] = float(cleaned)
            except ValueError:
                item[key] = None
    return item


def _recover_compact_size_rating(item: dict) -> None:
    """Split compact table values like `2 X 150` into NPS size and ASME class."""
    size_text = str(item.get('size') or '').strip()
    if not size_text or item.get('size_type') == 'OD_ID':
        return

    match = re.match(
        r'^(?P<size>\d+(?:\.\d+)?|\d+\s+\d+/\d+|\d+/\d+)\s*(?:"|INCH|IN)?\s*(?:X|×|BY|-)\s*'
        r'(?P<rating>150|300|400|600|900|1500|2500)\s*#?\s*$',
        size_text,
        re.IGNORECASE,
    )
    if not match:
        return

    item['size'] = f'{match.group("size")}"'
    item['size_type'] = 'NPS'
    if not item.get('rating'):
        item['rating'] = f'{match.group("rating")}#'


def _recover_common_fields_from_description(item: dict) -> None:
    raw = str(item.get('raw_description') or item.get('description') or '')
    if not raw:
        return
    upper = raw.upper()

    if not item.get('standard'):
        standard_match = re.search(r'\b(?:ASME|ANSI)?\s*B\s*16\.(20|21|47)\b', upper)
        if standard_match:
            item['standard'] = f'ASME B16.{standard_match.group(1)}'

    if not item.get('thickness_mm'):
        thickness_match = re.search(
            r'\b(?P<thk>\d+(?:\.\d+)?)\s*(?:MM)?\s*(?:NOM\s+)?(?:GASKET\s+)?(?:THK|THICK)\b'
            r'|\b(?:THK|THICKNESS)\s*[:=]?\s*(?P<thk2>\d+(?:\.\d+)?)\s*(?:MM)?\b',
            upper,
        )
        if thickness_match:
            item['thickness_mm'] = float(thickness_match.group('thk') or thickness_match.group('thk2'))


def _requires_review_for_default(default: str, gasket_type: str, item: dict) -> bool:
    # RULE V governance is a deterministic conclusion, not a guess: there is no
    # table row to look up, so there is nothing for a human to confirm. The
    # cases that DO need review (a cited standard overridden, an out-of-range
    # size) raise their own blocking deviation.
    if default.startswith(_DEV_NO_DIM_STANDARD_PREFIX):
        return False
    if (
        gasket_type == 'SPIRAL_WOUND'
        and default == 'standard defaulted to ASME B16.20'
        and item.get('size_norm')
        and item.get('rating_norm')
        and item.get('moc')
    ):
        return False
    # GGPL standard-construction conventions — deliberate house rules, not
    # guesses that need a human check.
    _CONVENTION_PREFIXES = (
        'generic SS inner ring resolved to winding grade',
        'generic SS outer ring resolved to winding grade',
        'inner ring defaulted to winding material',
        'outer ring defaulted to CS',
    )
    if gasket_type == 'SPIRAL_WOUND' and default.startswith(_CONVENTION_PREFIXES):
        return False
    return True


def _apply_specialty_rules(item: dict, flags: list, applied_defaults: list) -> None:
    """Rules for the beyond-six specialty families (Master Spec v3.1)."""
    gtype = item.get('gasket_type')

    if gtype == 'ADJACENT':
        item['escalation'] = ESC_REGRET
        flags.append('Adjacent/non-gasket product — REGRET per GGPL policy (configurable with sales team)')
        return

    if item.get('moc'):
        item['moc'] = str(item['moc']).strip().upper()

    if gtype == 'LENS':
        if not item.get('standard'):
            item['standard'] = 'DIN 2696'
        if not ((item.get('size') and item.get('rating')) or (item.get('od_mm') and item.get('id_mm'))):
            item['escalation'] = ESC_DRAWING_DIMS
        elif not item.get('moc'):
            flags.append('Missing critical field: lens ring material')
    elif gtype == 'MANHOLE':
        if not (item.get('obround_a_mm') and item.get('obround_b_mm')):
            item['escalation'] = ESC_DRAWING
    elif gtype == 'ENVELOPE':
        if not item.get('thickness_mm'):
            item['thickness_mm'] = 3
            applied_defaults.append('thickness defaulted to 3mm (envelope)')
        if not item.get('standard'):
            is_pn_env = str(item.get('rating') or '').upper().startswith('PN')
            item['standard'] = 'EN 1514-3' if is_pn_env else 'ASME B16.21'
            applied_defaults.append(f'standard defaulted to {item["standard"]} (envelope)')
        if not (item.get('envelope_insert') or item.get('moc')):
            flags.append('Missing critical field: envelope insert material')
    elif gtype == 'CMG':
        if not item.get('thickness_mm'):
            item['thickness_mm'] = 3
            applied_defaults.append('thickness defaulted to 3mm (corrugated metal gasket)')
    elif gtype == 'LIP_SEAL':
        if not (item.get('od_mm') and item.get('id_mm')):
            item['escalation'] = ESC_DRAWING
    elif gtype == 'DIAPHRAGM':
        if not item.get('od_mm'):
            item['escalation'] = ESC_DRAWING_DIMS
    elif gtype == 'SHEET':
        if not item.get('moc'):
            item['escalation'] = ESC_DATASHEET
        elif not (item.get('sheet_length_mm') and item.get('sheet_width_mm')):
            item['escalation'] = ESC_CLEAR_SPEC


def _apply_class_gap_rules(item: dict, flags: list, applied_defaults: list) -> None:
    """ASME class gaps: flanges that do not exist resolve deterministically.
    No CL400 at NPS 1/2–3 (use 600); no CL900 at NPS 1/2–2-1/2 (use 1500);
    no CL2500 at NPS ≥14. Dual classes (CL900/CL1500) resolve via the gaps.
    """
    rating = str(item.get('rating') or '')
    if not rating or rating.upper().startswith('PN'):
        return
    nps = _size_nps_value_from_item(item)
    if nps is None:
        return
    dual = re.fullmatch(r'(\d{3,4})/(\d{3,4})#?', rating.strip())
    if dual:
        a, b = int(dual.group(1)), int(dual.group(2))
        viable = [c for c in (a, b) if not (
            (c == 400 and nps <= 3) or (c == 900 and nps <= 2.5) or (c == 2500 and nps >= 14)
        )]
        if len(viable) == 1:
            item['rating'] = f'{viable[0]}#'
            item['rating_norm'] = item['rating']
            applied_defaults.append(
                f'{rating} stated — no class {a if viable[0] == b else b} flange at {item.get("size")}, resolved to {viable[0]}#')
            _add_item_deviation(item, flags,
                                f'{rating} STATED — RESOLVED TO {viable[0]}# (CLASS GAP RULE)')
        return
    m = re.fullmatch(r'(\d{3,4})#?', rating.strip())
    if not m:
        return
    cls = int(m.group(1))
    if cls == 400 and nps <= 3:
        item['rating'] = '600#'
        item['rating_norm'] = '600#'
        applied_defaults.append('class 400 does not exist at NPS 1/2–3 — 600# gasket dims apply')
        _add_item_deviation(item, flags, 'CLASS 400 STATED — NO CL400 FLANGE AT THIS SIZE, 600# GASKET DIMS APPLY')
    elif cls == 2500 and nps >= 14:
        flags.append('Class 2500 does not exist at NPS ≥14 (ASME B16.5) — confirm flange spec')


def _add_item_deviation(item: dict, flags: list, note: str, blocking: bool = True) -> None:
    """Record a customer-facing deviation line.

    `blocking` also raises a flag, which moves the row to `check` for operator
    review. Accepted house practice (a stock-core substitution, a defaulted
    series) is still told to the customer but does not stop the row — Rule Y
    Part 4.1 is explicit that a stock substitution is practice, not an error.
    """
    notes = item.setdefault('deviation_notes', [])
    if note not in notes:
        notes.append(note)
        if blocking:
            flags.append(f'DEVIATION: {note}')


def _emit_material_register_lines(item: dict, flags: list, applied_defaults: list) -> None:
    """RULE Z Part 7 — the verbatim house register.

    Turn the material/filler defaults GGPL applied into the customer-facing
    phrases the deviation register actually uses. The single most common line
    in the source set (467 occurrences) is the winding+IR / outer-ring pair.
    """
    if item.get('gasket_type') not in ('SPIRAL_WOUND', 'KAMM'):
        return
    defaults = ' '.join(applied_defaults or []).lower()
    if not defaults:
        return

    winding = item.get('sw_winding_material')
    inner = item.get('sw_inner_ring')
    outer = item.get('sw_outer_ring')

    ir_defaulted = 'inner ring defaulted' in defaults or 'inner ring added' in defaults
    or_defaulted = 'outer ring defaulted' in defaults

    if ir_defaulted and or_defaulted and winding and outer:
        _add_item_deviation(
            item, flags,
            f'We are proceeding Winding & Inner ring material as "{winding}" '
            f'and Outer ring material as "{outer}"',
            blocking=False)
    elif ir_defaulted and inner:
        _add_item_deviation(
            item, flags,
            f'WE ARE PROCEEDING INNER RING MATERIAL AS "{inner}"',
            blocking=False)
    elif or_defaulted and outer:
        _add_item_deviation(
            item, flags, f'WE ARE PROCEEDING OUTER RING AS "{outer}"', blocking=False)

    if 'filler defaulted' in defaults and item.get('sw_filler'):
        _add_item_deviation(
            item, flags,
            f'We are proceeding Filler material as "{item["sw_filler"].title()}"',
            blocking=False)


# RULE V Part 2 (specials row) — families for which GGPL's own data shows no
# dimensional standard. These are quoted to their own geometry or to a drawing,
# never to a piping table.
_NO_DIM_STANDARD_FAMILIES = frozenset({
    'O_RING', 'PLUG_GASKET', 'CORRUGATED', 'CMG', 'SHEET',
    'LIP_SEAL', 'DIAPHRAGM', 'MANHOLE', 'LENS', 'TRANSITION',
})

# A cited dimensional standard survives on a non-standard line only as a
# *construction* reference (Rule V Part 5.0 case 3) — never in the slot.
_CITED_DIM_STANDARD_RE = re.compile(
    r'\bB\s*16\s*\.\s*(?:20|21|47)\b|\bAPI\s*6\s*A\b|\bEN\s*1514\b')


def _is_dims_only(item: dict) -> bool:
    """RULE V Part 5.0 — THE OD x ID LAW.

    A dimensional standard is a table keyed by size + class (or DN + PN). When
    the customer supplies raw geometry and no size key there is no row to look
    up, so no standard can govern the dimensions — for every product family
    without exception. The customer gave the dimensions precisely because no
    standard does.
    """
    if item.get('ring_no'):
        return False  # an RTJ ring number is itself the table key
    has_geometry = bool(
        (item.get('od_mm') and item.get('id_mm'))
        or (item.get('obround_a_mm') and item.get('obround_b_mm'))
        or item.get('size_type') in ('OD_ID', 'OBROUND')
    )
    if not has_geometry:
        return False
    # Dims stated alongside a size merely corroborate the table row (case 2).
    return not item.get('size_norm') and _size_nps_value_from_item(item) is None


def _out_of_range_reason(item: dict) -> str | None:
    """RULE V Part 3 + Part 7 rule 1 — range validity beats every other input.

    Returns a customer-facing reason when the stated size/class falls outside
    every dimensional table, else None.
    """
    nps = _size_nps_value_from_item(item)
    if nps is None:
        return None
    rating = str(item.get('rating') or '').strip().upper()
    if rating.startswith('PN'):
        return None
    match = re.fullmatch(r'(\d{3,4})#?', rating)
    cls = int(match.group(1)) if match else None
    size_txt = item.get('size_norm') or item.get('size') or f'NPS {nps:g}'
    if nps > 60:
        return f'{size_txt} EXCEEDS THE ASME B16.47 RANGE (MAX 60")'
    if cls == 2500 and nps >= 14:
        return f'NO CLASS 2500 FLANGE AT {size_txt} (ASME B16.5)'
    # RTJ rings exist only for NPS 1/2-24 (R11-R79) and NPS 26-36 (R93-R105,
    # classes 300-900); NPS 22 has no listed ring.
    if item.get('gasket_type') == 'RTJ' and not item.get('ring_no'):
        if nps > 36 or nps == 22:
            return f'NO ASME RING NUMBER LISTED AT {size_txt}'
        if nps >= 26 and cls is not None and cls not in (300, 400, 600, 900):
            return (f'ASME B16.47 RINGS AT {size_txt} EXIST ONLY FOR CLASSES '
                    f'300-900 — NONE AT {cls}#')
    return None


def _apply_standard_governance(item: dict, flags: list, applied_defaults: list) -> None:
    """RULE V — decide ONCE whether any dimensional standard can govern the
    line, before the family handlers reach their `if not standard` defaults.

    When none can, the slot is set to NON STANDARD. That value is truthy, so
    every `if not item.get('standard')` default below is naturally skipped, and
    `_display_standard` suppresses the tag outright — a non-standard gasket can
    therefore never carry an ASME/API/EN standard in its description.
    """
    if is_non_standard(item.get('standard')):
        return  # already settled by the operator or an earlier pass

    family = item.get('gasket_type') or ''
    if family in _NO_DIM_STANDARD_FAMILIES:
        kind = 'family'
        headline = f'{family.replace("_", " ")} HAS NO DIMENSIONAL STANDARD'
    elif _is_dims_only(item):
        kind = 'dims'
        headline = 'SIZE NOT TABULATED — NO SIZE + CLASS GIVEN'
    else:
        headline = _out_of_range_reason(item)
        if not headline:
            return
        kind = 'range'

    cited = str(item.get('standard') or '').strip()
    item['standard'] = NON_STANDARD
    applied_defaults.append(
        f'{_DEV_NO_DIM_STANDARD_PREFIX} — {headline.lower()} (RULE V)')

    if cited and _CITED_DIM_STANDARD_RE.search(cited.upper()):
        # The citation may govern construction (winding profile, ring thickness,
        # materials); it cannot make a non-tabulated size standard.
        _add_item_deviation(
            item, flags,
            f'{cited} CITED — {headline}; CONSTRUCTION PER {cited} ONLY (NON-STANDARD)')
    elif kind == 'range':
        _add_item_deviation(item, flags, f'{headline} — QUOTED AS NON-STANDARD')


def apply_rules(item: dict) -> dict:
    """
    Normalize, apply defaults, validate, and assign status + flags.
    Returns updated item dict.
    """
    _sanitize_llm_nulls(item)
    # Derived outputs are rebuilt from scratch on every run, never carried over
    # from the stored row. `flags` already worked this way; `escalation` and
    # `deviation_notes` did not, so once a row escalated ("KINDLY PROVIDE
    # DATASHEET…") the phrase outranked the description forever — an operator
    # could fill in every missing column and the GGPL Description cell would
    # never change, because describe_item returns the escalation verbatim and
    # the status stayed `missing`. Clearing them here means a recompute after a
    # column edit re-derives the escalation from the CURRENT field values.
    item.pop('escalation', None)
    item.pop('deviation_notes', None)
    # Operator-selected NON STANDARD: canonicalize early so it stays a truthy
    # value — every `if not item.get('standard')` default is naturally skipped
    # and the formatter suppresses the tag in the description.
    if is_non_standard(item.get('standard')):
        item['standard'] = NON_STANDARD
    _recover_compact_size_rating(item)
    _recover_common_fields_from_description(item)
    flags = []
    applied_defaults = []

    # --- Normalize size ---
    raw_size = item.get('size')
    size_norm = normalize_size(raw_size) if raw_size else None
    item['size_norm'] = size_norm

    # Flag when a metric mm value was rounded down to a standard NPS
    if raw_size and size_norm:
        import re as _re_sz
        _s = str(raw_size).strip().upper().replace(' ', '')
        # Matches bare mm or NB-mm values (e.g. "150MM", "127NB", "127MM")
        _mm_match = _re_sz.match(r'^(\d+(?:\.\d+)?)(?:MM|NB)$', _s)
        if _mm_match:
            from data.reference_data import NB_TO_NPS as _NB_TO_NPS
            _mm_val = float(_mm_match.group(1))
            _nb_int = int(round(_mm_val))
            item['size'] = size_norm
            if _nb_int not in _NB_TO_NPS:
                # Down-rounding was used; add a check flag.
                _lower = [k for k in _NB_TO_NPS if k <= _mm_val]
                _nearest = max(_lower) if _lower else None
                flags.append(
                    f'Size {_nb_int}mm not a standard NB; rounded down to {_nearest}mm ({size_norm})'
                )

    # --- Normalize rating ---
    raw_rating = item.get('rating')
    rating_norm = normalize_rating(raw_rating) if raw_rating else None
    item['rating_norm'] = rating_norm

    is_pn = raw_rating and str(raw_rating).upper().startswith('PN')
    is_asme = raw_rating and '#' in str(raw_rating)

    # mm pipe-OD in a W1 (ANSI class) context maps to NPS (Master Spec A1):
    # e.g. "76.1 mm" + 150# → 2-1/2"
    if raw_size and is_asme:
        _od_m = re.match(r'^(\d+(?:\.\d+)?)\s*MM$', str(raw_size).strip().upper())
        if _od_m:
            _od_val = float(_od_m.group(1))
            for _pipe_od, _nps in _PIPE_OD_TO_NPS.items():
                if abs(_od_val - _pipe_od) <= 0.3:
                    item['size'] = _nps
                    item['size_norm'] = _nps
                    size_norm = _nps
                    applied_defaults.append(f'{_od_val}MM pipe OD mapped to NPS {_nps} (ANSI class context)')
                    break

    # Project gasket codes (Toyo/HSEPL G-codes etc.) — resolve construction
    # for fields the row text left blank; row text always outranks the code.
    apply_gasket_code(item, flags, applied_defaults)

    gasket_type = item.get('gasket_type', 'SOFT_CUT')
    raw_desc = (
        item.get('description')
        or item.get('raw_description')
        or ''
    ).upper()

    # Fields the operator set by hand in the portal outrank anything re-derived
    # from the raw description text — otherwise a recompute silently reverts
    # their edit (e.g. gasket type changed on a "HEAT EXCHANGER GASKET" row).
    manual_fields = set(item.get('manual_fields') or [])
    gasket_type_is_manual = 'gasket_type' in manual_fields and item.get('gasket_type')

    if not gasket_type_is_manual:
        if re.search(r'\bHEAT\s+EXCHANGER\s+GASKET\b', raw_desc):
            gasket_type = 'KAMM'
            item['gasket_type'] = 'KAMM'
        elif re.search(r'\bDOUBLE[\s\-]?JACKET(?:ED)?\b|\bJACKETED\b', raw_desc):
            gasket_type = 'DJI'
            item['gasket_type'] = 'DJI'
        elif gasket_type == 'SOFT_CUT' and re.search(
            r'\b(?:SPIRAL|SPRIAL|SPRIRAL|SPIRIAL|SPLRAL|SPRLAL|SPIRRAL|SPRRAL|SPRL|SPL)\s*[-\s]*(?:W(?:OU)?ND\w*|WIND\w*)\b|\bSPW\b',
            raw_desc,
        ) and 'INSERT' not in str(item.get('moc') or '').upper():
            # LLM missed/misclassified — description text is unambiguous.
            # (Reinforced-graphite-with-insert rows keep their SOFT_CUT family
            # classification even though the enquiry says "spiral wound".)
            gasket_type = 'SPIRAL_WOUND'
            item['gasket_type'] = 'SPIRAL_WOUND'
        elif gasket_type == 'SOFT_CUT' and _looks_like_oring(raw_desc):
            gasket_type = 'O_RING'
            item['gasket_type'] = 'O_RING'
        elif gasket_type == 'SOFT_CUT' and re.search(r'\bKAMMPROFILE\b|\bCAMPROFILE\b', raw_desc):
            gasket_type = 'KAMM'
            item['gasket_type'] = 'KAMM'
        elif gasket_type == 'SOFT_CUT' and re.search(
            r'\b(?:RING\s+JOINT|RING\s+TYPE\s+JOINT|RTJ\s+GASKET)\b', raw_desc
        ) and not re.search(r'\bSPIRAL\b|\bCNAF\b|\bPTFE\b|\bRUBBER\b|\bNEOPRENE\b|\bGRAPHITE\s+SHEET\b', raw_desc):
            gasket_type = 'RTJ'
            item['gasket_type'] = 'RTJ'
        elif gasket_type == 'SOFT_CUT' and re.search(
            r'\b(?:ISK|INSULAT(?:ING|ION)\s+GASKET|INSULAT(?:ING|ION)\s+KIT|FLANGE\s+ISOLAT(?:ING|ION)\s+KIT)\b',
            raw_desc,
        ):
            gasket_type = 'ISK'
            item['gasket_type'] = 'ISK'
        elif gasket_type == 'SOFT_CUT' and re.search(r'\bPLUG\s+GASKET\b|\bPLUG\s+TYPE\s+GASKET\b', raw_desc):
            gasket_type = 'PLUG_GASKET'
            item['gasket_type'] = 'PLUG_GASKET'
        elif gasket_type == 'SOFT_CUT' and re.search(r'\bCORRUGATED(?:\s+METAL(?:LIC)?)?\s+GASKET\b|\bCORRUGATED\s+GASKET\b', raw_desc):
            gasket_type = 'CORRUGATED'
            item['gasket_type'] = 'CORRUGATED'
        elif gasket_type == 'SOFT_CUT' and re.search(r'\bSHEET\s+GASKET\b|\bGASKET\s+SHEET\b', raw_desc):
            gasket_type = 'SHEET_GASKET'
            item['gasket_type'] = 'SHEET_GASKET'

        # If "non-metallic" is mentioned in the original description, force SOFT_CUT
        if re.search(r'NON[\s\-]?METALLIC', raw_desc) and gasket_type not in ('SOFT_CUT', 'SHEET_GASKET', 'O_RING'):
            gasket_type = 'SOFT_CUT'
            item['gasket_type'] = 'SOFT_CUT'

    # Brand & trade-name translation (three-bucket policy, Master Spec v3.2)
    apply_brand_rules(item, flags, applied_defaults)

    # ASME class-gap resolution (nonexistent flange classes)
    _apply_class_gap_rules(item, flags, applied_defaults)

    _remove_face_tokens_from_material_fields(item)

    # RULE V — settle the standard slot BEFORE the family handlers run, so no
    # `if not standard` default can stamp a piping standard onto a gasket that
    # no standard governs. Runs after gasket_type inference (family test) and
    # after class-gap resolution (range test reads the resolved rating).
    _apply_standard_governance(item, flags, applied_defaults)

    if gasket_type == 'SPIRAL_WOUND':
        _apply_sw_rules(item, flags, applied_defaults)
        item['dimensions'] = None
    elif gasket_type == 'RTJ':
        _apply_rtj_rules(item, flags, applied_defaults)
        item['dimensions'] = None
    elif gasket_type == 'KAMM':
        _apply_kamm_rules(item, flags, applied_defaults)
        item['dimensions'] = None
    elif gasket_type == 'DJI':
        _apply_dji_rules(item, flags, applied_defaults)
        item['dimensions'] = None
    elif gasket_type in ('ISK', 'ISK_RTJ'):
        _apply_isk_rules(item, flags, applied_defaults)
        item['dimensions'] = None
    elif gasket_type == 'O_RING':
        _apply_oring_rules(item, flags, applied_defaults)
    elif gasket_type in ('LENS', 'MANHOLE', 'ENVELOPE', 'CMG', 'METAL_CLAD', 'SOLID_METAL',
                         'LIP_SEAL', 'DIAPHRAGM', 'EYELET', 'SHEET', 'ADJACENT'):
        _apply_specialty_rules(item, flags, applied_defaults)
        item['dimensions'] = None
    elif gasket_type not in ('SOFT_CUT', 'SHEET_GASKET', 'CORRUGATED', 'PLUG_GASKET'):
        # Unrecognised gasket type — pass through but flag for manual review
        flags.append(
            f'Unrecognised gasket type "{gasket_type}" — verify and convert to GGPL format manually'
        )
        item['dimensions'] = None
    else:
        # --- Normalize MOC (soft cut) ---
        raw_moc = (item.get('moc') or '').strip().upper()
        # Normalize brand+number codes: "AF 139" → "AF139", "AF 157" → "AF157", etc.
        import re as _re_moc
        raw_moc = _re_moc.sub(r'\bAF\s+(\d)', r'AF\1', raw_moc)
        if raw_moc in _AMBIGUOUS_MOC:
            flags.append('MOC "RUBBER" is ambiguous — confirm: Natural Rubber / EPDM / Neoprene / Chloroprene?')
            item['moc'] = raw_moc
        elif raw_moc:
            # Use _normalize_moc for canonical lookup; fall back to raw value (LLM already normalizes most)
            normalized = _normalize_moc(raw_moc)
            item['moc'] = normalized
            # Don't flag composite MOCs like "EPDM WITH SS304 INSERT" or
            # "EXPANDED GRAPHITE WITH SS316 REINFORCEMENT" — these are valid combinations
            _is_composite = (
                ' WITH ' in raw_moc and (
                    'INSERT' in raw_moc
                    or 'REINFORCEMENT' in raw_moc
                    or 'RENFORCEMENT' in raw_moc
                )
            )
            _is_described_composite = (
                any(token in raw_moc for token in ('GRAPHITE', 'PTFE', 'CNAF', 'RUBBER'))
                and any(token in raw_moc for token in ('SS', '316', '304', 'PERFORATED', 'PLATE', 'COVER', 'INSERT', 'REINFORCEMENT'))
            )
            # "X / EQUIVALENT" or "X OR EQUIVALENT" specs are passed through verbatim — don't flag
            _is_equivalent_spec = (
                '/ EQUIVALENT' in raw_moc
                or '/EQUIVALENT' in raw_moc
                or 'OR EQUIVALENT' in raw_moc
                or '/ EQUAL' in raw_moc
            )
            if not _is_composite and not _is_described_composite and not _is_equivalent_spec and normalized not in ACCEPTED_MOC and raw_moc not in _MOC_CANONICAL:
                flags.append(f'MOC "{normalized}" not in standard list — verify spelling')

        # --- Default: face_type ---
        if gasket_type != 'PLUG_GASKET' and not item.get('face_type'):
            if is_pn:
                item['face_type'] = 'FF'
            else:
                item['face_type'] = 'RF'
            applied_defaults.append('face type defaulted to ' + item['face_type'])

        # --- Default: thickness ---
        if not item.get('thickness_mm'):
            item['thickness_mm'] = 3
            applied_defaults.append('thickness defaulted to 3mm')

        # --- Default: standard ---
        if not item.get('standard'):
            if is_pn:
                item['standard'] = 'EN 1514-1'
                applied_defaults.append('standard defaulted to EN 1514-1')
            else:
                # NPS ≥ 26" → ASME B16.47 (large bore); below 26" → ASME B16.21
                nps_val = _size_nps_value_from_item(item)
                if nps_val is not None and nps_val >= 26:
                    _set_b1647_standard(item, flags, applied_defaults)
                else:
                    item['standard'] = 'ASME B16.21'
                    applied_defaults.append('standard defaulted to ASME B16.21')

        # --- Dimension lookup ---
        dims = None
        if size_norm and rating_norm:
            dims = lookup_dimensions(size_norm, rating_norm, item['face_type'])
        item['dimensions'] = dims
        if not dims and size_norm and rating_norm:
            flags.append('Size/rating not found in standard dimension table — may be non-standard')

    # Business rule: NPS inch size + ASME # pressure class → standard must be ASME (not EN/DIN/BS)
    if size_norm and '"' in str(size_norm) and is_asme:
        current_std = item.get('standard') or ''
        if current_std.startswith('EN') or current_std.startswith('DIN') or current_std.startswith('BS'):
            if gasket_type in ('SPIRAL_WOUND', 'RTJ', 'KAMM'):
                item['standard'] = 'ASME B16.20'
            else:
                nps_val = _size_nps_value_from_item(item)
                if nps_val is not None and nps_val >= 26:
                    _set_b1647_standard(item, flags, applied_defaults)
                else:
                    item['standard'] = 'ASME B16.21'

    # --- Normalize B16.47: always call to normalize format and flag if series missing ---
    std = item.get('standard') or ''
    if 'B16.47' in std:
        _set_b1647_standard(item, flags, applied_defaults)

    # --- Default: UoM ---
    if item.get('uom') == 'M':
        flags.append('UoM is meters (sheet supply) — confirm if individual gaskets or sheet supply')

    # --- Obsolete standards cited (API 601 / API 605 / MSS SP-44) ---
    _raw_all_std = (item.get('raw_description') or item.get('description') or '').upper()
    # If the obsolete citation itself landed in the standard field (LLM path),
    # replace it with the successor before wording the deviation (Rule V Part 4).
    _std_field_upper = str(item.get('standard') or '').upper()
    if is_non_standard(_std_field_upper):
        pass  # no standard governs this line — no successor to substitute
    elif re.search(r'\bAPI\s*601\b', _std_field_upper):
        item['standard'] = 'ASME B16.20'
    elif re.search(r'\bAPI\s*605\b', _std_field_upper):
        item['standard'] = 'ASME B16.47 (SERIES-B)'
    elif re.search(r'\bMSS\s*SP[-\s]?44\b', _std_field_upper):
        item['standard'] = 'ASME B16.47 (SERIES-A)'
    if re.search(r'\bAPI\s*60[15]\b|\bMSS\s*SP[-\s]?44\b', _raw_all_std):
        _successor = item.get('standard')
        _add_item_deviation(
            item, flags,
            f'OBSOLETE STANDARD CITED (API 601/605 / MSS SP-44) — SUPERSEDED; '
            f'QUOTED AS NON-STANDARD (SIZE NOT TABULATED)'
            if is_non_standard(_successor) else
            f'OBSOLETE STANDARD CITED (API 601/605 / MSS SP-44) — SUPERSEDED; '
            f'QUOTED TO {_successor or "CURRENT ASME STANDARD"}')

    # --- Explicit NACE certification demand → 'NACE MR0175,' before the standard ---
    if gasket_type in ('SPIRAL_WOUND', 'SOFT_CUT', 'KAMM', 'SHEET_GASKET', 'CMG'):
        if re.search(r'NACE[^.\n]{0,40}?(?:\bYES\b|REQUIRED|CERTIF)|Q[AS]C?ERT[^\n]{0,40}NACE', _raw_all_std):
            _std_now = item.get('standard')
            if _std_now and 'NACE' not in str(_std_now).upper() and not is_non_standard(_std_now):
                item['standard'] = f'NACE MR0175, {_std_now}'
                applied_defaults.append('NACE MR0175 certification demanded — inserted before the standard')

    # --- RULE V catch-all: cited standard outside the GGPL library ---
    # Keep the citation verbatim in the slot and flag for tech review — never
    # substitute an ASME equivalent by guess. Engine-generated forms always
    # match the library, so only genuine unknown citations fire this.
    _std_final = item.get('standard')
    if (_std_final and not is_non_standard(_std_final)
            and not _KNOWN_STANDARD_RE.match(str(_std_final).strip().upper())):
        _catchall_flag = f'STANDARD "{_std_final}" NOT IN GGPL LIBRARY — KEPT VERBATIM — TECH REVIEW'
        if _catchall_flag not in flags:
            flags.append(_catchall_flag)

    # --- Critical field validation — varies by type ---
    if gasket_type == 'RTJ':
        # Ring number uniquely identifies size+rating — if present, size and rating are not required
        if item.get('ring_no'):
            crit = ['moc']
        else:
            crit = ['size', 'rating', 'moc']
    elif gasket_type == 'KAMM':
        # OD/ID KAMM: check od_mm + id_mm + moc (moc built from sw_winding_material by rules engine)
        # NPS KAMM: check size + rating + moc
        if item.get('size_type') == 'OD_ID':
            crit = ['od_mm', 'id_mm', 'moc']
        else:
            crit = ['size', 'rating', 'moc']
    elif gasket_type == 'DJI':
        crit = ['od_mm', 'id_mm', 'thickness_mm', 'moc']
    elif gasket_type in ('ISK', 'ISK_RTJ'):
        crit = ['size', 'rating']
    elif gasket_type == 'O_RING':
        crit = ['id_mm', 'thickness_mm', 'moc']
    elif gasket_type == 'SPIRAL_WOUND' and item.get('size_type') == 'OD_ID':
        crit = ['od_mm', 'id_mm', 'moc']
    elif gasket_type in ('LENS', 'MANHOLE', 'ENVELOPE', 'CMG', 'METAL_CLAD', 'SOLID_METAL',
                         'LIP_SEAL', 'DIAPHRAGM', 'EYELET', 'SHEET', 'ADJACENT'):
        # Specialty families are governed by their escalation rules
        crit = []
    elif item.get('size_type') == 'OD_ID':
        # Any gasket type with OD/ID dimensions — size (NPS) and rating are not applicable
        crit = ['od_mm', 'id_mm', 'moc']
    else:
        crit = CRITICAL_FIELDS  # ['size', 'rating', 'moc']

    missing_critical = []
    for field in crit:
        val = item.get(field)
        if not val:
            missing_critical.append(field)

    if missing_critical:
        flags.extend([f'Missing critical field: {f}' for f in missing_critical])

    if not item.get('quantity'):
        # RULE Z Part 8 — a missing quantity does not stop the quote. The line is
        # quoted and the customer is asked for the number (136 rows in the set).
        _add_item_deviation(item, flags, DEV_QTY_MISSING, blocking=False)
        flags.append('Quantity not provided')

    # --- Assign status ---
    review_defaults = [
        default for default in applied_defaults
        if _requires_review_for_default(default, gasket_type, item)
    ]

    # Like flags/escalation, the register of what the engine chose is a derived
    # output — write it every run so a row that stops needing a default does not
    # keep showing the old one.
    item['applied_defaults'] = applied_defaults

    if item.get('escalation'):
        # Escalation phrase IS the GGPL description; status reflects the ask
        item['status'] = STATUS_REGRET if item['escalation'] == ESC_REGRET else STATUS_MISSING
    elif missing_critical or any('ambiguous' in f.lower() or 'missing critical' in f.lower() for f in flags):
        item['status'] = STATUS_MISSING
    elif review_defaults or flags:
        item['status'] = STATUS_CHECK
    else:
        item['status'] = STATUS_READY

    # RULE Z Part 7 — every default the code applied produces one register line.
    # Materials, filler, thickness, series, rating: if GGPL chose it, the
    # customer is told. This is the customer-facing half of applied_defaults.
    _emit_material_register_lines(item, flags, applied_defaults)

    # Per-line deviation channel (brand translations, standard overrides,
    # material/thickness register lines). An operator who edited the Deviation
    # cell in the portal owns it — a recompute must not overwrite their wording.
    if 'deviation' not in set(item.get('manual_fields') or []):
        if item.get('deviation_notes'):
            item['deviation'] = ' | '.join(item['deviation_notes'])
        else:
            item['deviation'] = ''

    item['flags'] = flags
    return item
