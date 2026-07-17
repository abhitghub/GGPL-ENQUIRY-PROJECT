"""Export quotations as Excel (portal format) to a Google Drive folder.

Uses a Google service account. Completely inert (safe no-op) unless all of
GDRIVE_EXPORT_ENABLED / GDRIVE_FOLDER_ID / GOOGLE_SERVICE_ACCOUNT_FILE are set,
so the app runs normally before Drive is configured. Never raises to callers —
failures are logged and swallowed so they can't break the workflow.
"""

from __future__ import annotations

import io
import logging
import re
from datetime import date
from typing import Any

from app.config import get_settings
from app.services.export_service import build_xlsx

logger = logging.getLogger("gdrive_export")

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_SCOPES = ["https://www.googleapis.com/auth/drive"]


def is_configured() -> bool:
    s = get_settings()
    return bool(s.gdrive_export_enabled and s.gdrive_folder_id and s.google_service_account_file)


def _drive():
    if not is_configured():
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            get_settings().google_service_account_file, scopes=_SCOPES
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as exc:  # missing libs / bad key / etc.
        logger.warning("Google Drive not available: %s", exc)
        return None


def _clean(value: str) -> str:
    # Drive-safe, Windows-safe filename fragment.
    return re.sub(r'[\\/:*?"<>|]+', " ", str(value or "")).strip()


def _filename(quote: Any) -> str:
    qd = getattr(quote, "quote_data", None) or {}
    customer = _clean(getattr(quote, "customer", "") or qd.get("buyer_name") or "Enquiry") or "Enquiry"
    ref = _clean(qd.get("quote_no") or getattr(quote, "quote_no", "") or "")
    stamp = date.today().isoformat()
    return f"{customer} - {stamp}{(' - ' + ref) if ref else ''}.xlsx"


def export_quote(quote: Any) -> str | None:
    """Build the quotation Excel and upsert it (by name) into the Drive folder.
    Returns the filename on success, else None. Never raises."""
    service = _drive()
    if service is None:
        return None
    try:
        content = build_xlsx(quote.items, quote.quote_data)
        name = _filename(quote)
        folder = get_settings().gdrive_folder_id
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=_XLSX_MIME, resumable=False)
        safe = name.replace("'", "\\'")
        query = f"name = '{safe}' and '{folder}' in parents and trashed = false"
        found = service.files().list(q=query, fields="files(id)", pageSize=1).execute().get("files", [])
        if found:
            service.files().update(fileId=found[0]["id"], media_body=media).execute()
        else:
            service.files().create(
                body={"name": name, "parents": [folder]}, media_body=media, fields="id"
            ).execute()
        logger.info("Exported quotation to Drive: %s", name)
        return name
    except Exception as exc:
        logger.warning("Drive export failed for quote %s: %s", getattr(quote, "id", "?"), exc)
        return None
