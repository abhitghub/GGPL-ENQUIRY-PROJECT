"""PDF item-table flags: customer SL No., customer item code, GGPL serial no."""
from __future__ import annotations

import sys
from pathlib import Path

from core.quote_pdf import build_quotation_pdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.services.export_parity import extract_pdf_text
from app.services.export_service import _logo_path


def _items() -> list[dict]:
    return [
        {
            "line_no": 1,
            "customer_sl_no": "C-10",
            "customer_item_code": "ITEM-777",
            "quantity": 2,
            "uom": "NOS",
            "raw_description": '4" 150# CNAF RF gasket 3mm ASME B16.21',
            "ggpl_description": 'GASKET, SIZE : 4", RATING : 150#, TYPE : SOFT CUT, MOC : CNAF, THK : 3 MM',
            "status": "ready",
        },
        {
            "line_no": 2,
            "customer_sl_no": "C-11",
            "customer_item_code": "ITEM-888",
            "quantity": 1,
            "uom": "NOS",
            "raw_description": '6" 300# CNAF RF gasket 3mm ASME B16.21',
            "ggpl_description": 'GASKET, SIZE : 6", RATING : 300#, TYPE : SOFT CUT, MOC : CNAF, THK : 3 MM',
            "status": "ready",
        },
    ]


def _quote_data(**flags) -> dict:
    return {
        "quote_no": "FLAGS-TEST",
        "quote_date": "16 May 2026",
        "currency": "INR",
        "unit_prices": [100, 200],
        "gst_type": "IGST",
        "gst_pct": 18,
        **flags,
    }


def _pdf_text(**flags) -> str:
    return extract_pdf_text(build_quotation_pdf(_items(), _quote_data(**flags), logo_path=_logo_path()))


def test_default_serial_without_flags():
    text = _pdf_text()
    assert "Sl." in text
    assert "C-10" not in text
    assert "ITEM-777" not in text
    assert "GGPL SL.NO" not in text.replace("\n", " ")


def test_customer_sl_no_replaces_serial():
    text = _pdf_text(include_customer_sl_no=True)
    assert "Cust" in text
    assert "C-10" in text
    assert "C-11" in text
    assert "ITEM-777" not in text


def test_customer_item_code_adds_column():
    text = _pdf_text(include_customer_item_code=True)
    assert "Item Code" in text.replace("\n", " ")
    assert "ITEM-777" in text
    assert "ITEM-888" in text
    assert "C-10" not in text


def test_ggpl_serial_only_relabels_serial_column():
    text = _pdf_text(include_ggpl_sl_no=True)
    assert "GGPL" in text
    assert "C-10" not in text


def test_ggpl_and_customer_sl_show_both_columns():
    text = _pdf_text(include_ggpl_sl_no=True, include_customer_sl_no=True)
    flat = text.replace("\n", " ")
    assert "GGPL" in flat
    assert "Cust" in flat
    assert "C-10" in text
    assert "C-11" in text


def test_all_three_flags_together():
    text = _pdf_text(
        include_ggpl_sl_no=True,
        include_customer_sl_no=True,
        include_customer_item_code=True,
    )
    assert "GGPL" in text
    assert "C-10" in text
    assert "ITEM-777" in text
