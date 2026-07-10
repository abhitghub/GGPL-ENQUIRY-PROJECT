"""Import a CRM contact export (xlsx) into the customer master.

Each row is a contact; contacts are grouped by the ``Account Name`` column into
customers, each holding a ``contacts`` list. Rows without an Account Name are
skipped. Writes into the local API datastore under
``app_settings['<org>:customers']`` (preserving epc_names). Restart the API
afterwards so it reloads the datastore.

Usage:
    python -m scripts.import_customers_from_crm <export.xlsx> [--org local-org] \
        [--store ../../.local/api_repository.json] [--sheet "Master Customers"]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path

import openpyxl


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def build_customers(xlsx: Path, sheet: str) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[sheet] if sheet in wb.sheetnames else wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = [_clean(c) for c in next(rows)]
    idx = {h: i for i, h in enumerate(header)}

    def g(row: tuple, name: str) -> str:
        i = idx.get(name)
        return "" if i is None or i >= len(row) else _clean(row[i])

    customers: "OrderedDict[str, dict]" = OrderedDict()
    seen: dict[str, set] = {}
    seq = 0
    for row in rows:
        account = g(row, "Account Name")
        if not account:
            continue
        key = re.sub(r"\s+", " ", account).strip().upper()
        if key not in customers:
            seq += 1
            customers[key] = {
                "id": f"cust-{seq}",
                "name": re.sub(r"\s+", " ", account).strip(),
                "address_line1": g(row, "Mailing Street"),
                "address_line2": "",
                "city": g(row, "Company City") or g(row, "Mailing City"),
                "state": g(row, "Company State") or g(row, "Mailing State"),
                "pin_code": g(row, "Mailing Zip"),
                "country": g(row, "Company Country") or g(row, "Mailing Country"),
                "contact_name": "", "designation": "", "email": "", "phone": "",
                "gst_no": "", "default_currency": "INR", "payment_terms": "",
                "delivery_terms": "", "active": True, "contacts": [],
            }
            seen[key] = set()
        rec = customers[key]
        name = g(row, "Contact Name") or " ".join(x for x in (g(row, "First Name"), g(row, "Last Name")) if x)
        email = g(row, "Email")
        if not name and not email:
            continue
        dedupe = (name.lower(), email.lower())
        if dedupe in seen[key]:
            continue
        seen[key].add(dedupe)
        contact = {
            "id": f"{rec['id']}-c{len(rec['contacts']) + 1}",
            "name": name, "designation": g(row, "Title"), "department": g(row, "Department"),
            "email": email, "phone": g(row, "Phone"), "mobile": g(row, "Mobile"),
        }
        rec["contacts"].append(contact)
        if not rec["contact_name"] and (name or email):
            rec.update({"contact_name": name, "designation": contact["designation"],
                        "email": email, "phone": contact["phone"] or contact["mobile"]})
    return list(customers.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", type=Path)
    ap.add_argument("--org", default="local-org")
    ap.add_argument("--sheet", default="Master Customers")
    ap.add_argument("--store", type=Path, default=Path(__file__).resolve().parents[1] / ".local" / "api_repository.json")
    args = ap.parse_args()

    customers = build_customers(args.xlsx, args.sheet)
    total_contacts = sum(len(c["contacts"]) for c in customers)
    print(f"companies: {len(customers)}  contacts: {total_contacts}")

    store = json.loads(args.store.read_text(encoding="utf-8")) if args.store.exists() else {}
    settings = store.setdefault("app_settings", {})
    key = f"{args.org}:customers"
    epc_names = (settings.get(key) or {}).get("epc_names") or []
    settings[key] = {"customers": customers, "epc_names": epc_names}
    args.store.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    print("written:", args.store)


if __name__ == "__main__":
    main()
