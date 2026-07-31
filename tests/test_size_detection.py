"""Regression fixtures for nominal-size detection.

Every case here is a row that quoted with a confidently wrong size (or no size
at all) rather than failing loudly — the worst failure mode for a gasket quote,
because a 0.75" gasket priced as a 20" one looks perfectly ordinary on the
sheet. Grouped by the stage that dropped the size.
"""
import pytest

from core.document_reader import _sanitize_text
from core.formatter import format_description
from core.parser import (
    _extract_first_size,
    _size_from_text,
    _split_glued_size_class,
)
from core.rules import apply_rules
from data.reference_data import normalize_size


# --- Stage 1: the ASCII fold that feeds Smart Parse ------------------------
# _sanitize_text encodes to ASCII with errors='replace' and then blanks the
# '?'s, so any dimensional character outside ASCII used to become whitespace.

@pytest.mark.parametrize(
    'raw, expected',
    [
        ('¾GASKET RF 150#', '3/4GASKET RF 150#'),
        ('½GASKET', '1/2GASKET'),
        ('¼GASKET', '1/4GASKET'),
        ('1½GASKET', '1-1/2GASKET'),          # mixed number, not "11/2"
        ('4” X 150#', '4" X 150#'),           # curly inch mark
        ('4″ X 150#', '4" X 150#'),           # double prime
        ('4" × 150#', '4" X 150#'),           # multiplication sign
        ('24–inch', '24-inch'),               # en dash
    ],
)
def test_sanitize_preserves_dimensional_typography(raw, expected):
    assert _sanitize_text(raw) == expected


# --- Stage 2: NPS vs NB collision in normalize_size ------------------------
# 20, 32, 40 and 50 are keys in NB_TO_NPS *and* real NPS inch sizes. The inch
# mark was stripped before the NB lookup ran, so 20" answered 0.75".

@pytest.mark.parametrize('raw, expected', [
    ('20"', '20"'), ('32"', '32"'), ('40"', '40"'), ('50"', '50"'),
    ('NPS 20', '20"'), ('20 INCH', '20"'),
])
def test_explicit_inch_sizes_are_not_read_as_nominal_bore(raw, expected):
    assert normalize_size(raw) == expected


@pytest.mark.parametrize('raw, expected', [
    ('DN 20', '0.75"'), ('DN32', '1.25"'), ('20 NB', '0.75"'), ('50NB', '2"'),
    ('150MM', '6"'),
])
def test_metric_sizes_still_resolve_through_the_nb_table(raw, expected):
    assert normalize_size(raw) == expected


# --- Stage 3: alternation order in _extract_first_size ---------------------
# Regex alternation is first-match, so the bare-number branch used to win over
# the fraction branches: `NPS: 3/4` came back 3", `1-1/2IN` came back 1".

@pytest.mark.parametrize('text, expected', [
    ('NPS: 3/4 GASKET 4.5MM THK ASME B16.20', '3/4"'),
    ('NPS: 1+1/2 GASKET 4.5MM THK ASME B16.20', '1-1/2"'),
    ('GASKET SPW;1-1/2IN,150LB,SS 316', '1-1/2"'),
    ('GASKET SPW;3/4IN,CGI,SS 316L', '3/4"'),
    ('1.1/2" X 4.5MM NOM THK GASKET SPIRAL WOUND CL150', '1-1/2"'),
    ('GASKET_SPIRAL-WOUND,*SIZE: 1-1/2 IN,*PRESSURE RATING: CL150', '1-1/2"'),
])
def test_fractions_outrank_the_bare_whole_number(text, expected):
    assert _extract_first_size(text) == expected


def test_decimal_in_a_standard_is_not_mistaken_for_a_mixed_fraction():
    # The whole part of "20 1/2" here belongs to B16.20, not to the size.
    assert _extract_first_size('GASKET ASME B16.20 1/2" CL150') == '1/2"'


@pytest.mark.parametrize('raw, expected', [
    ('¾', '3/4"'), ('½', '1/2"'), ('¼', '1/4"'),
    ('3/4', '3/4"'), ('1 1/2', '1-1/2"'), ('1.1/2', '1-1/2"'), ('4', '4"'),
])
def test_size_from_text_keeps_the_customers_fraction_style(raw, expected):
    assert _size_from_text(raw) == expected


# --- Stage 4: deterministic backstop when Smart Parse returns no size ------
# A size glued to the noun ("4GASKET RF 150#") is read by the LLM only some of
# the time, so identical rows in one sheet came back some filled, some UNKNOWN.

def _recovered(description, **extra):
    item = {'raw_description': description, 'description': description,
            'size_type': 'UNKNOWN', 'size': None, 'rating': None,
            'quantity': 1, 'uom': 'NOS'}
    item.update(extra)
    return apply_rules(item)


@pytest.mark.parametrize('description, size, rating', [
    ('4GASKET RF 150#, ASME B16.20 SPRL WND, SS 316/ SS 316L WDG GPH FLR', '4"', '150#'),
    ('2GASKET RF 600#, ASME B16.20 SPRL WND, SS 316/ SS 316L WDG GPH FLR', '2"', '600#'),
    ('24GASKET RF 600#, ASME B16.20 Gasket Cam profile, SS 316/ SS 316L GPH', '24"', '600#'),
    ('32GASKET RF 600#, ASME B16.20 Gasket Cam profile, SS 316/ SS 316L GPH', '32"', '600#'),
    ('3/4GASKET RF 150#, ASME B16.20 SPRL WND, SS 316/ SS 316L WDG GPH FLR', '3/4"', '150#'),
])
def test_size_glued_to_the_noun_is_recovered(description, size, rating):
    item = _recovered(description)
    assert item['size'] == size
    assert item['rating'] == rating
    assert item['size_type'] == 'NPS'


def test_recovery_never_overrides_a_supplied_size():
    item = _recovered('4GASKET RF 150#, ASME B16.20 SPRL WND', size='6"', rating='300#')
    assert item['size'] == '6"'
    assert item['rating'] == '300#'


def test_recovery_declines_rather_than_inventing_a_size():
    # A material grade is not a size; a blank beats a wrong number.
    item = _recovered('GASKET, SS 316 IN GRAPHITE FILLER, 150#')
    assert item['size'] is None


def test_recovery_leaves_od_id_rows_alone():
    item = _recovered('GASKET 4MM THK', size_type='OD_ID', od_mm=200.0, id_mm=150.0)
    assert item['size'] is None


# --- Stage 5: glued size+class (RULE Y) ------------------------------------
# ERP exports drop the separator: "24600#" is 24" at class 600. The rule was
# documented but never implemented, so these rows produced no size at all.

@pytest.mark.parametrize('digits, size, rating', [
    ('24600#', '24"', '600#'),
    ('30900#', '30"', '900#'),
    ('0.75150#', '0.75"', '150#'),
    ('1.5150#', '1.5"', '150#'),
    ('12500#', '1"', '2500#'),
])
def test_glued_size_and_class_are_split(digits, size, rating):
    item = _recovered(f'{digits} SPIRAL WOUND GASKET SS316 GRAPHITE')
    assert item['size'] == size
    assert item['rating'] == rating


@pytest.mark.parametrize('text', [
    '1500# SPIRAL WOUND GASKET',   # a class on its own is not a glued pair
    '2500# GASKET',
    '150# GASKET',
    '600600# GASKET',              # 600" is not an NPS size — refuse the split
    'GASKET 24600#',               # not at the start of the row
])
def test_a_bare_class_is_never_read_as_a_glued_size(text):
    assert _split_glued_size_class(text) is None


# --- Stage 6: B16.20 cannot govern a 26"+ gasket ---------------------------
# SPW already overrode a customer-cited B16.20 above 26"; KAMM skipped the
# check whenever any standard was present and printed 32" as B16.20.

def _kamm(description):
    return apply_rules({
        'raw_description': description, 'description': description,
        'gasket_type': 'KAMM', 'size_type': 'UNKNOWN',
        'kamm_core_material': 'SS316', 'kamm_surface_material': 'GRAPHITE',
        'moc': 'SS316', 'quantity': 1, 'uom': 'NOS',
    })


def test_large_bore_kamm_overrides_a_cited_b1620():
    item = _kamm('32GASKET RF 600#, ASME B16.20 Gasket Cam profile, SS 316/ SS 316L GPH')
    assert item['size'] == '32"'
    assert item['standard'] == 'ASME B16.47 (SERIES-B)'
    assert 'ASME B16.47 (SERIES-B)' in format_description(item)


def test_in_range_kamm_keeps_the_cited_b1620():
    item = _kamm('24GASKET RF 600#, ASME B16.20 Gasket Cam profile, SS 316/ SS 316L GPH')
    assert item['size'] == '24"'
    assert item['standard'] == 'ASME B16.20'
