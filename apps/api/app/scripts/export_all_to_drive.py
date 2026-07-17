"""Nightly job: export every enquiry/quotation as Excel to the Google Drive
folder. Run: python -m app.scripts.export_all_to_drive

Safe no-op when Drive export isn't configured. Files are upserted by name
("<customer> - <date>.xlsx"), so re-running the same day overwrites that day's set.
"""

from __future__ import annotations

import os

from app.db import repo
from app.services.gdrive_export import export_quote, is_configured


def main() -> None:
    if not is_configured():
        print("[export_all_to_drive] Drive export not configured — skipping.")
        return
    org_id = os.environ.get("EXPORT_ORG_ID", "local-org")
    quotes = repo.list_quotes(org_id, is_admin=True)
    exported = 0
    for quote in quotes:
        if export_quote(quote):
            exported += 1
    print(f"[export_all_to_drive] Exported {exported}/{len(quotes)} records to Drive for org '{org_id}'.")


if __name__ == "__main__":
    main()
