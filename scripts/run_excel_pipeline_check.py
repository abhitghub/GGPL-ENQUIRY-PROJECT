from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for path in (ROOT, PACKAGES):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from core.formatter import format_description
from core.parser import parse_excel_file
from core.rules import apply_rules
from services import extraction

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _client():
    if load_dotenv:
        load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        return None
    from openai import OpenAI

    return OpenAI()


def _fast_items(path: Path) -> list[dict]:
    items = []
    for raw in parse_excel_file(path.read_bytes()):
        item = apply_rules(dict(raw))
        item["ggpl_description"] = format_description(item)
        items.append(item)
    return items


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_excel_pipeline_check.py <xlsx-path>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    start = time.perf_counter()
    fast_items = _fast_items(path)
    review_rows = sum(extraction._needs_smart_parse_review(item) for item in fast_items)

    client = _client()
    if client:
        items, skipped, error = extraction.process_document(path.read_bytes(), "excel", client)
        used_openai = True
    else:
        items, skipped, error = fast_items, 0, None
        used_openai = False

    duration = time.perf_counter() - start
    result = {
        "file": str(path),
        "fast_rows": len(fast_items),
        "review_rows": review_rows,
        "pipeline_rows": len(items),
        "skipped": skipped,
        "error": error,
        "used_openai": used_openai,
        "duration_sec": round(duration, 3),
        "status_counts": dict(Counter(item.get("status") for item in items)),
        "first_items": [
            {
                "idx": idx + 1,
                "line_no": item.get("line_no"),
                "status": item.get("status"),
                "flags": item.get("flags"),
                "description": item.get("ggpl_description") or item.get("raw_description"),
            }
            for idx, item in enumerate(items[:12])
        ],
        "issue_items": [
            {
                "idx": idx + 1,
                "line_no": item.get("line_no"),
                "status": item.get("status"),
                "flags": item.get("flags"),
                "description": item.get("ggpl_description") or item.get("raw_description"),
            }
            for idx, item in enumerate(items)
            if item.get("status") != "ready" or item.get("flags")
        ],
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if not error and items else 1


if __name__ == "__main__":
    raise SystemExit(main())
