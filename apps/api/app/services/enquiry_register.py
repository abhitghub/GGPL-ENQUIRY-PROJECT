"""Enquiry register: one Excel sheet with a row per enquiry whose quotation
has been generated, carrying the enquiry context (customer, quote type,
project, owner, value) so colleagues can browse past enquiries at a glance.

The register is rebuilt from the database on every request/export, so it is
always current — nothing is appended incrementally or can drift out of sync.
"""

from __future__ import annotations

import io
from typing import Any

import xlsxwriter

from app.schemas.quotes import QuoteRead
from app.services.enquiry_workflow import active_steps, current_workflow_step
from app.services.quote_rules import quote_estimated_value

REGISTER_FILENAME = "Enquiry Register.xlsx"

# (header, width) for each register column, in output order.
_COLUMNS: list[tuple[str, int]] = [
    ("Enq No", 12),
    ("Enquiry Date", 13),
    ("Customer", 28),
    ("Contact Person", 20),
    ("Contact Email", 26),
    ("Quote Type", 12),
    ("Bidding / Firm", 13),
    ("Project Name", 28),
    ("EPC / Project Company", 24),
    ("Country", 14),
    ("City", 14),
    ("Sales Rep", 18),
    ("Created By", 18),
    ("No. of Items", 12),
    ("Quotation Ref", 16),
    ("Quotation Generated On", 20),
    ("Quotation Value", 15),
    ("Currency", 10),
    ("Current Status", 20),
    ("Notes", 36),
]


def _meta(quote: QuoteRead) -> dict[str, Any]:
    return quote.stage_meta or {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _date_only(value: Any) -> str:
    """'2026-07-24T09:15:00+00:00' / datetime -> '2026-07-24'."""
    text = value.isoformat() if hasattr(value, "isoformat") else _text(value)
    return text[:10]


def quotation_generated_at(quote: QuoteRead) -> str:
    """ISO timestamp of when this enquiry's quotation was generated via the
    granular workflow, or '' if it has not reached that step."""
    meta = _meta(quote)
    granular = meta.get("granular_workflow") or {}
    for entry in reversed(list(granular.get("history_log") or [])):
        if _text(entry.get("to")) == "quotation_generated":
            return _text(entry.get("at"))
    step = _text(granular.get("current_stage") or meta.get("workflow_stage"))
    if step in {"quotation_generated", "quotation_sent_to_customer"}:
        return quote.updated_at.isoformat()
    return ""


def has_generated_quotation(quote: QuoteRead) -> bool:
    """True for enquiry records whose quotation exists — via the granular
    workflow reaching 'quotation_generated', or the legacy flow creating a
    linked quotation record. Quotation child records themselves are excluded."""
    meta = _meta(quote)
    if _text(meta.get("source_enquiry_id")):
        return False
    if quotation_generated_at(quote):
        return True
    return bool(_text(meta.get("linked_quote_id")))


def _status_label(quote: QuoteRead, linked: QuoteRead | None) -> str:
    if linked:
        return {"quote_prep": "Quotation prep", "repricing": "Repricing", "sent": "Sent to customer", "po": "PO received"}.get(
            linked.stage, linked.stage
        )
    step = current_workflow_step(_meta(quote))
    for entry in active_steps():
        if entry["id"] == step:
            return entry["label"]
    return step or quote.stage


def register_rows(quotes: list[QuoteRead]) -> list[list[Any]]:
    """One row (matching _COLUMNS) per enquiry with a generated quotation,
    oldest first, like a traditional sales register."""
    by_id = {quote.id: quote for quote in quotes}
    rows: list[list[Any]] = []
    for quote in sorted(quotes, key=lambda row: row.created_at):
        if not has_generated_quotation(quote):
            continue
        meta = _meta(quote)
        qd = quote.quote_data or {}
        linked = by_id.get(_text(meta.get("linked_quote_id")))
        value_source = linked or quote
        value_qd = value_source.quote_data or {}
        generated_at = quotation_generated_at(quote) or (linked.created_at.isoformat() if linked else "")
        rows.append([
            quote.quote_no,
            _date_only(quote.created_at),
            _text(quote.customer) or _text(qd.get("buyer_name")),
            _text(qd.get("attention")),
            _text(qd.get("email")),
            _text(meta.get("market_type")).title(),
            _text(meta.get("bid_type")).title(),
            _text(quote.project_ref),
            _text(meta.get("epc_name")),
            _text(meta.get("country")),
            _text(meta.get("city")),
            _text(meta.get("owner_name")) or _text(meta.get("owner_id")),
            _text(meta.get("created_by_name")) or _text(meta.get("created_by_username")) or _text(quote.created_by),
            quote.n_items,
            _text(value_qd.get("quote_no")) or _text(value_source.quote_no),
            _date_only(generated_at),
            round(quote_estimated_value(value_source), 2),
            _text(value_qd.get("currency")),
            _status_label(quote, linked),
            _text(meta.get("sales_notes")),
        ])
    return rows


_ITEM_COLUMNS: list[tuple[str, str, int]] = [
    ("Line", "line_no", 6),
    ("Status", "status", 10),
    ("Cust Sl No", "customer_sl_no", 11),
    ("Customer Item Code", "customer_item_code", 18),
    ("Customer Description", "raw_description", 45),
    ("GGPL Description", "ggpl_description", 45),
    ("Qty", "quantity", 8),
    ("UOM", "uom", 8),
    ("Gasket Type", "gasket_type", 14),
    ("Size", "size", 10),
    ("Rating", "rating", 10),
    ("MoC", "moc", 14),
]


def build_enquiry_detail_xlsx(quote: QuoteRead, linked: QuoteRead | None = None) -> bytes:
    """Full record of one enquiry as a workbook: an 'Enquiry' sheet with every
    context field, a 'Line Items' sheet with every item (and unit prices once
    priced), and a 'Workflow History' sheet with the audit trail."""
    meta = _meta(quote)
    qd = quote.quote_data or {}
    value_source = linked or quote
    value_qd = value_source.quote_data or {}

    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    header_fmt = workbook.add_format(
        {"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "border": 1, "valign": "vcenter", "text_wrap": True}
    )
    label_fmt = workbook.add_format({"bold": True, "border": 1, "bg_color": "#DCE6F1", "valign": "top"})
    cell_fmt = workbook.add_format({"border": 1, "valign": "top", "text_wrap": True})
    money_fmt = workbook.add_format({"border": 1, "valign": "top", "num_format": "#,##0.00"})

    summary = workbook.add_worksheet("Enquiry")
    summary.set_column(0, 0, 26)
    summary.set_column(1, 1, 60)
    fields: list[tuple[str, Any]] = [
        ("Enq No", quote.quote_no),
        ("Enquiry Date", _date_only(quote.created_at)),
        ("Customer", _text(quote.customer) or _text(qd.get("buyer_name"))),
        ("Contact Person", _text(qd.get("attention"))),
        ("Contact Email", _text(qd.get("email"))),
        ("Contact No", _text(qd.get("contact_no"))),
        ("Email Subject", _text(quote.custom_label)),
        ("Customer Enq No", _text(qd.get("customer_enq_no"))),
        ("Quote Type", _text(meta.get("market_type")).title()),
        ("Bidding / Firm", _text(meta.get("bid_type")).title()),
        ("Project Name", _text(quote.project_ref)),
        ("EPC / Project Company", _text(meta.get("epc_name"))),
        ("Country", _text(meta.get("country"))),
        ("City", _text(meta.get("city"))),
        ("Sales Rep", _text(meta.get("owner_name")) or _text(meta.get("owner_id"))),
        ("Created By", _text(meta.get("created_by_name")) or _text(meta.get("created_by_username")) or _text(quote.created_by)),
        ("Due Date", _text(meta.get("due_date"))),
        ("Priority", _text(meta.get("priority")).title()),
        ("No. of Items", quote.n_items),
        ("Quotation Ref", _text(value_qd.get("quote_no")) or _text(value_source.quote_no)),
        ("Quotation Generated On", _date_only(quotation_generated_at(quote) or (linked.created_at.isoformat() if linked else ""))),
        ("Quotation Value", round(quote_estimated_value(value_source), 2)),
        ("Currency", _text(value_qd.get("currency"))),
        ("Current Status", _status_label(quote, linked)),
        ("Notes", _text(meta.get("sales_notes"))),
        ("Last Updated", _date_only(quote.updated_at)),
    ]
    summary.merge_range(0, 0, 0, 1, "Enquiry Details", header_fmt)
    for row_index, (label, value) in enumerate(fields, start=1):
        summary.write(row_index, 0, label, label_fmt)
        summary.write(row_index, 1, value, money_fmt if label == "Quotation Value" else cell_fmt)

    items_sheet = workbook.add_worksheet("Line Items")
    unit_prices = value_qd.get("unit_prices")
    prices = unit_prices if isinstance(unit_prices, list) else []
    for col, (header, _, width) in enumerate(_ITEM_COLUMNS):
        items_sheet.set_column(col, col, width)
        items_sheet.write(0, col, header, header_fmt)
    price_col = len(_ITEM_COLUMNS)
    items_sheet.set_column(price_col, price_col + 1, 12)
    items_sheet.write(0, price_col, "Unit Price", header_fmt)
    items_sheet.write(0, price_col + 1, "Line Total", header_fmt)
    source_items = (linked.items if linked and linked.items else quote.items) or []
    for row_index, item in enumerate(source_items, start=1):
        for col, (_, key, _width) in enumerate(_ITEM_COLUMNS):
            items_sheet.write(row_index, col, item.get(key) if item.get(key) is not None else "", cell_fmt)
        try:
            unit_price = float(prices[row_index - 1] or 0) if row_index - 1 < len(prices) else 0.0
            quantity = float(item.get("quantity") or 0)
        except (TypeError, ValueError):
            unit_price, quantity = 0.0, 0.0
        items_sheet.write(row_index, price_col, unit_price, money_fmt)
        items_sheet.write(row_index, price_col + 1, round(unit_price * quantity, 2), money_fmt)
    items_sheet.freeze_panes(1, 0)
    items_sheet.autofilter(0, 0, max(len(source_items), 1), price_col + 1)

    history_sheet = workbook.add_worksheet("Workflow History")
    history_headers = [("When", 20), ("Action", 26), ("From", 24), ("To", 24), ("By", 18), ("Role", 12), ("Comment", 45)]
    for col, (header, width) in enumerate(history_headers):
        history_sheet.set_column(col, col, width)
        history_sheet.write(0, col, header, header_fmt)
    log = list((meta.get("granular_workflow") or {}).get("history_log") or [])
    for row_index, entry in enumerate(log, start=1):
        values = [
            _text(entry.get("at")).replace("T", " ")[:19],
            _text(entry.get("action")).replace("_", " "),
            _text(entry.get("from")).replace("_", " "),
            _text(entry.get("to")).replace("_", " "),
            _text(entry.get("by")),
            _text(entry.get("role")),
            _text(entry.get("comment")),
        ]
        for col, value in enumerate(values):
            history_sheet.write(row_index, col, value, cell_fmt)
    history_sheet.freeze_panes(1, 0)

    workbook.close()
    return buffer.getvalue()


def build_enquiry_register_xlsx(quotes: list[QuoteRead]) -> bytes:
    """Render the register as a formatted, filterable Excel workbook."""
    rows = register_rows(quotes)
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    sheet = workbook.add_worksheet("Enquiry Register")
    header_fmt = workbook.add_format(
        {"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "border": 1, "valign": "vcenter", "text_wrap": True}
    )
    cell_fmt = workbook.add_format({"border": 1, "valign": "top"})
    value_fmt = workbook.add_format({"border": 1, "valign": "top", "num_format": "#,##0.00"})
    sheet.set_row(0, 30)
    for col, (header, width) in enumerate(_COLUMNS):
        sheet.set_column(col, col, width)
        sheet.write(0, col, header, header_fmt)
    value_col = next(index for index, (header, _) in enumerate(_COLUMNS) if header == "Quotation Value")
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row):
            sheet.write(row_index, col_index, value, value_fmt if col_index == value_col else cell_fmt)
    sheet.freeze_panes(1, 3)
    sheet.autofilter(0, 0, max(len(rows), 1), len(_COLUMNS) - 1)
    workbook.close()
    return buffer.getvalue()
