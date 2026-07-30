"""Hand-keyed lines must always show something in the GGPL Description column.

A manually added row reaches the portal with only raw_description/qty/uom — no
classifier has run on it — so format_description() has nothing to build a house
format from and returns ''. describe_item() is the portal-facing wrapper that
falls back to the operator's own wording so the column is never blank.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.formatter import describe_item, format_description
from core.rules import apply_rules


def _manual_row(raw: str) -> dict:
    """Mirror the bulk-recompute path for a hand-keyed row."""
    item = apply_rules({'raw_description': raw, 'quantity': 1, 'uom': 'NOS'})
    return describe_item(item)


def test_one_off_product_with_no_ggpl_format_echoes_typed_wording():
    raw = 'SIZE : 0.1 THK x 1736 LG x 45 W , DUPLEX  S31803 LAMIFLEX SEALING STRIP'
    assert format_description(apply_rules({'raw_description': raw})) == ''
    assert _manual_row(raw) == (
        'SIZE : 0.1 THK X 1736 LG X 45 W , DUPLEX S31803 LAMIFLEX SEALING STRIP'
    )


def test_unclassified_manual_row_is_never_blank():
    assert _manual_row('SOME TOTALLY UNKNOWN WIDGET') == 'SOME TOTALLY UNKNOWN WIDGET'


def test_house_format_wins_over_the_raw_fallback():
    item = apply_rules({
        'gasket_type': 'SOFT_CUT', 'size': '2"', 'rating': '150#',
        'moc': 'CNAF', 'thickness_mm': 3,
        'raw_description': 'some sloppy customer wording',
    })
    described = describe_item(item)
    assert described == format_description(item)
    assert 'sloppy' not in described


def test_blank_row_stays_blank():
    assert describe_item({}) == ''
    assert describe_item({'raw_description': '   '}) == ''
