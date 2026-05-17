from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for path in (ROOT, PACKAGES):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from core.formatter import format_description
from core.parser import _enrich_from_description, _infer_gasket_type
from core.rules import apply_rules


TYPE_MAP = {
    "SOFT CUT": "SOFT_CUT",
    "SPW": "SPIRAL_WOUND",
    "RTJ": "RTJ",
    "KAMM": "KAMM",
    "DJI": "DJI",
    "ISK": "ISK",
    "ISK - RTJ": "ISK_RTJ",
}


def _norm_type(value: str) -> str:
    return TYPE_MAP.get(value.strip().upper(), value.strip().upper())


def _norm_text(value: Any) -> str:
    text = str(value or "").upper()
    text = text.replace(" ", "")
    text = text.replace("SS 316", "SS316").replace("SS 304", "SS304")
    text = text.replace("INCOLY", "INCOLOY")
    return re.sub(r"[^A-Z0-9#.\"]+", "", text)


def _critical_ok(item: dict[str, Any]) -> bool:
    gtype = item.get("gasket_type")
    if gtype == "SPIRAL_WOUND":
        return all(item.get(k) for k in ("size", "rating", "sw_winding_material", "sw_filler", "sw_inner_ring", "sw_outer_ring"))
    if gtype == "RTJ":
        return bool(item.get("moc") and (item.get("ring_no") or (item.get("size") and item.get("rating"))))
    if gtype == "KAMM":
        if item.get("size_type") == "OD_ID":
            return bool(item.get("od_mm") and item.get("id_mm") and (item.get("kamm_core_material") or item.get("moc")))
        return bool(item.get("size") and item.get("rating") and (item.get("kamm_core_material") or item.get("moc")))
    if gtype == "DJI":
        return bool(item.get("od_mm") and item.get("id_mm") and item.get("moc"))
    if gtype in ("ISK", "ISK_RTJ"):
        return bool(item.get("size") and item.get("rating"))
    if gtype == "SOFT_CUT":
        return bool(item.get("size") and item.get("rating") and item.get("moc"))
    return False


def main() -> int:
    path = ROOT / "packages" / "data" / "reference" / "ground_truth.csv"
    start = time.perf_counter()
    rows = list(csv.DictReader(path.open(encoding="latin-1")))
    wanted = {"RTJ", "KAMM", "DJI", "ISK", "ISK_RTJ"}

    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "rows": 0,
        "type_correct": 0,
        "critical_fields_present": 0,
        "nonempty_description": 0,
        "exact_description": 0,
        "status_counts": Counter(),
        "examples": [],
    })

    for row in rows:
        expected_type = _norm_type(row.get("TYPE OF PRODUCT") or "")
        if expected_type not in wanted:
            continue
        desc = row.get("Customer Enquiry Description") or ""
        expected_desc = row.get("GGPL Quote Description (Ground Truth)") or ""
        inferred_type = _infer_gasket_type(desc) or "SOFT_CUT"
        raw = {
            "description": desc,
            "raw_description": desc,
            "gasket_type": inferred_type,
            "quantity": 1,
            "uom": "NOS",
        }
        item = apply_rules(_enrich_from_description(raw))
        item["ggpl_description"] = format_description(item)

        bucket = stats[expected_type]
        bucket["rows"] += 1
        bucket["type_correct"] += int(item.get("gasket_type") == expected_type)
        bucket["critical_fields_present"] += int(_critical_ok(item))
        bucket["nonempty_description"] += int(bool(item.get("ggpl_description")))
        bucket["exact_description"] += int(_norm_text(item.get("ggpl_description")) == _norm_text(expected_desc))
        bucket["status_counts"][item.get("status") or "unknown"] += 1
        if len(bucket["examples"]) < 5 and not _critical_ok(item):
            bucket["examples"].append({
                "input": desc[:180],
                "expected_type": expected_type,
                "got_type": item.get("gasket_type"),
                "status": item.get("status"),
                "flags": item.get("flags"),
                "output": item.get("ggpl_description"),
            })

    output = {}
    for gtype, data in stats.items():
        rows_n = data["rows"] or 1
        output[gtype] = {
            "rows": data["rows"],
            "type_accuracy_pct": round(data["type_correct"] / rows_n * 100, 2),
            "critical_field_coverage_pct": round(data["critical_fields_present"] / rows_n * 100, 2),
            "nonempty_description_pct": round(data["nonempty_description"] / rows_n * 100, 2),
            "exact_description_pct": round(data["exact_description"] / rows_n * 100, 2),
            "status_counts": dict(data["status_counts"]),
            "sample_failures": data["examples"],
        }

    print(json.dumps({"duration_sec": round(time.perf_counter() - start, 3), "types": output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
