from __future__ import annotations

from pathlib import Path

from core.formatter import format_description
from core.parser import parse_excel_file
from core.rules import apply_rules
from services import extraction


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "excel"

FIXTURES = {
    "260408_Enquiry for gasket.xlsx": 36,
    "test 2 pass.xlsx": 35,
    "U112 BOM - Gaskets.xlsx": 332,
}


def _processed_fast_items(path: Path) -> list[dict]:
    processed = []
    for raw in parse_excel_file(path.read_bytes()):
        item = apply_rules(dict(raw))
        item["ggpl_description"] = format_description(item)
        processed.append(item)
    return processed


def test_customer_excel_fixtures_parse_with_fast_path():
    for filename, expected_count in FIXTURES.items():
        path = FIXTURE_DIR / filename
        raw_items = parse_excel_file(path.read_bytes())

        assert len(raw_items) == expected_count, filename
        assert all(item.get("source_index") for item in raw_items), filename
        assert all(item.get("raw_description") for item in raw_items), filename
        assert all(item.get("quantity") is not None for item in raw_items), filename


def test_customer_excel_fixtures_produce_deterministic_rows_before_llm_review():
    for filename in FIXTURES:
        items = _processed_fast_items(FIXTURE_DIR / filename)
        non_missing = [item for item in items if item.get("status") != "missing"]

        assert len(non_missing) > 0, filename
        assert all(item.get("ggpl_description") for item in non_missing), filename


def test_excel_process_document_reviews_only_ambiguous_rows(monkeypatch):
    reviewed_counts: dict[str, int] = {}

    def fake_read_document_smart(review_text, source_type, openai_client, progress_cb=None, on_chunk_items=None):
        reviewed_counts[current_filename] = review_text.count("source_index:")
        return [], 0

    monkeypatch.setattr(extraction, "read_document_smart", fake_read_document_smart)

    for current_filename, expected_count in FIXTURES.items():
        fast_items = _processed_fast_items(FIXTURE_DIR / current_filename)
        expected_review_count = sum(extraction._needs_smart_parse_review(item) for item in fast_items)
        items, skipped, error = extraction.process_document(
            (FIXTURE_DIR / current_filename).read_bytes(),
            "excel",
            openai_client=None,
        )

        assert error is None, current_filename
        assert skipped == 0, current_filename
        assert len(items) == expected_count, current_filename
        assert reviewed_counts.get(current_filename, 0) == expected_review_count, current_filename
        assert expected_review_count < expected_count, current_filename
