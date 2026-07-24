"""Nightly job: export every enquiry to the Google Drive folder — one folder
per enquiry ('<enq no> - <customer>/') holding 'Enquiry Details.xlsx' (full
context, line items, workflow history) plus the quotation Excel once generated,
and the org-wide 'Enquiry Register.xlsx' at the root.
Run: python -m app.scripts.export_all_to_drive

Safe no-op when Drive export isn't configured. Files are upserted by name, so
re-running refreshes everything in place.
"""

from __future__ import annotations

import os

from app.db import repo
from app.services.gdrive_export import export_enquiry_package, export_enquiry_register, is_configured


def main() -> None:
    if not is_configured():
        print("[export_all_to_drive] Drive export not configured — skipping.")
        return
    org_id = os.environ.get("EXPORT_ORG_ID", "local-org")
    quotes = repo.list_quotes(org_id, is_admin=True)
    by_id = {quote.id: quote for quote in quotes}
    exported = 0
    enquiries = [
        quote for quote in quotes
        if not str((quote.stage_meta or {}).get("source_enquiry_id") or "").strip()
    ]
    for quote in enquiries:
        linked = by_id.get(str((quote.stage_meta or {}).get("linked_quote_id") or "").strip())
        if export_enquiry_package(quote, linked):
            exported += 1
    export_enquiry_register(quotes)
    print(f"[export_all_to_drive] Exported {exported}/{len(enquiries)} enquiry folders to Drive for org '{org_id}'.")


if __name__ == "__main__":
    main()
