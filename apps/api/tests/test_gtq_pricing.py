"""GTQ ("Get The Quote") lines: the price is not known when the quotation goes
out, so estimation marks the line and the documents say "Will quote soon"
instead of showing a figure.

Covers the three places a missing price would otherwise be wrong: the
workflow gate that demands a positive price before a quotation can be marked
sent, the PDF item table/totals, and the Excel quotation sheet.
"""
from __future__ import annotations

import sys
from pathlib import Path

from core.quote_pdf import build_quotation_pdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.pop("app", None)

from app.schemas.quotes import QuoteRead  # noqa: E402
from app.services.export_parity import extract_pdf_text  # noqa: E402
from app.services.export_service import _logo_path  # noqa: E402
from app.services.quote_rules import workflow_transition_blockers  # noqa: E402


def _items() -> list[dict]:
    return [
        {
            "line_no": 1,
            "quantity": 2,
            "uom": "NOS",
            "ggpl_description": 'GASKET, SIZE : 4", RATING : 150#, TYPE : SOFT CUT, MOC : CNAF, THK : 3 MM',
            "status": "ready",
        },
        {
            "line_no": 2,
            "quantity": 4,
            "uom": "NOS",
            "ggpl_description": 'GASKET, SIZE : 6", RATING : 300#, TYPE : SPIRAL WOUND, MOC : SS316, THK : 4.5 MM',
            "status": "ready",
        },
    ]


def _quote(quote_data: dict) -> QuoteRead:
    return QuoteRead(
        id="q-gtq",
        org_id="org-gtq",
        quote_no="GTQ-TEST",
        customer="ACME",
        project_ref="P-GTQ",
        items=_items(),
        quote_data=quote_data,
        stage="quote_prep",
        stage_meta={},
        created_by="estimation",
        created_at="2026-05-16T00:00:00+00:00",
        updated_at="2026-05-16T00:00:00+00:00",
        version=1,
    )


def test_unpriced_line_blocks_sent():
    blockers = workflow_transition_blockers(_quote({"unit_prices": [100, 0]}), "sent")
    assert any("positive unit price" in blocker for blocker in blockers)


def test_gtq_line_may_be_sent_unpriced():
    """A line flagged GTQ is quoted later, so it does not have to carry a price."""
    quote = _quote({"unit_prices": [100, 0], "line_gtq": [False, True]})
    assert not [blocker for blocker in workflow_transition_blockers(quote, "sent") if "unit price" in blocker]


def test_gtq_flag_does_not_excuse_other_lines():
    quote = _quote({"unit_prices": [0, 0], "line_gtq": [False, True]})
    assert any("positive unit price" in blocker for blocker in workflow_transition_blockers(quote, "sent"))


def _pdf_text(quote_data: dict) -> str:
    base = {
        "quote_no": "GTQ-TEST",
        "quote_date": "16 May 2026",
        "currency": "INR",
        "gst_type": "IGST",
        "gst_pct": 18,
    }
    return extract_pdf_text(build_quotation_pdf(_items(), {**base, **quote_data}, logo_path=_logo_path()))


def test_pdf_shows_will_quote_soon_and_excludes_gtq_from_totals():
    priced = _pdf_text({"unit_prices": [100, 50]})
    gtq = _pdf_text({"unit_prices": [100, 50], "line_gtq": [False, True]})
    assert "Will quote soon" not in priced
    assert "Will quote soon" in gtq.replace("\n", " ")
    # Line 2 (4 x 50 = 200) drops out of the priced subtotal: 400 -> 200.
    assert "400.00" in priced
    assert "400.00" not in gtq
    assert "200.00" in gtq
