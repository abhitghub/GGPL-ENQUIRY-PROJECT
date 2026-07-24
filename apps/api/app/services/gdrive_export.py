"""Export quotations as Excel (portal format) to a Google Drive folder.

Uses a Google service account. Completely inert (safe no-op) unless all of
GDRIVE_EXPORT_ENABLED / GDRIVE_FOLDER_ID / GOOGLE_SERVICE_ACCOUNT_FILE are set,
so the app runs normally before Drive is configured. Never raises to callers —
failures are logged and swallowed so they can't break the workflow.
"""

from __future__ import annotations

import io
import logging
import os
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
    if not s.gdrive_export_enabled:
        return False
    # Folder mode (Google Drive for Desktop) or service-account API mode.
    return bool(s.gdrive_local_dir or (s.gdrive_folder_id and s.google_service_account_file))


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


def _enquiry_folder_name(quote: Any) -> str:
    """One stable folder per enquiry: '<enq no> - <customer>'."""
    qd = getattr(quote, "quote_data", None) or {}
    enq_no = _clean(getattr(quote, "quote_no", "") or "") or _clean(str(getattr(quote, "id", ""))[:8])
    customer = _clean(getattr(quote, "customer", "") or qd.get("buyer_name") or "")
    return f"{enq_no} - {customer}" if customer else enq_no


def _find_or_create_drive_folder(service: Any, parent_id: str, name: str) -> str | None:
    safe = name.replace("'", "\\'")
    query = (
        f"name = '{safe}' and '{parent_id}' in parents"
        " and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    found = service.files().list(q=query, fields="files(id)", pageSize=1).execute().get("files", [])
    if found:
        return found[0]["id"]
    created = service.files().create(
        body={"name": name, "parents": [parent_id], "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    return created.get("id")


def _save_xlsx(name: str, content: bytes, subfolder: str | None = None) -> str | None:
    """Save an Excel file to the configured Drive destination (update-or-create),
    optionally inside a subfolder. Returns the filename on success, else None.
    Never raises.

    Folder mode (Google Drive for Desktop): writes the file into GDRIVE_LOCAL_DIR,
    which Drive for Desktop syncs to Drive. Otherwise uses the Drive API."""
    if not is_configured():
        return None
    local_dir = get_settings().gdrive_local_dir
    if local_dir:
        try:
            target_dir = os.path.join(local_dir, subfolder) if subfolder else local_dir
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, name), "wb") as fh:
                fh.write(content)
            logger.info("Exported to %s", os.path.join(target_dir, name))
            return name
        except Exception as exc:
            logger.warning("Local Drive export failed for %s: %s", name, exc)
            return None
    service = _drive()
    if service is None:
        return None
    try:
        folder = get_settings().gdrive_folder_id
        if subfolder:
            folder = _find_or_create_drive_folder(service, folder, subfolder) or folder
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
        logger.info("Exported to Drive: %s", name)
        return name
    except Exception as exc:
        logger.warning("Drive export failed for %s: %s", name, exc)
        return None


def export_quote(quote: Any) -> str | None:
    """Build the quotation Excel and save it into the enquiry's Drive folder.
    Returns the filename on success, else None. Never raises."""
    if not is_configured():
        return None
    try:
        content = build_xlsx(quote.items, quote.quote_data)
    except Exception as exc:
        logger.warning("Could not build quotation Excel for quote %s: %s", getattr(quote, "id", "?"), exc)
        return None
    qd = getattr(quote, "quote_data", None) or {}
    ref = _clean(qd.get("quote_no") or getattr(quote, "quote_no", "") or "")
    name = f"Quotation{(' - ' + ref) if ref else ''}.xlsx"
    return _save_xlsx(name, content, subfolder=_enquiry_folder_name(quote))


def export_enquiry_package(quote: Any, linked: Any = None) -> str | None:
    """Save the full record of one enquiry into its own Drive folder
    ('<enq no> - <customer>/'): an 'Enquiry Details.xlsx' with every context
    field, all line items, and the workflow history — plus the quotation Excel
    once one exists. Returns the folder name on success, else None. Never raises."""
    if not is_configured():
        return None
    folder = _enquiry_folder_name(quote)
    try:
        from app.services.enquiry_register import build_enquiry_detail_xlsx, has_generated_quotation

        detail = build_enquiry_detail_xlsx(quote, linked)
    except Exception as exc:
        logger.warning("Could not build enquiry details for %s: %s", getattr(quote, "id", "?"), exc)
        return None
    saved = _save_xlsx("Enquiry Details.xlsx", detail, subfolder=folder)
    if saved and has_generated_quotation(quote):
        value_source = linked if linked is not None else quote
        try:
            content = build_xlsx(value_source.items, value_source.quote_data)
            qd = getattr(value_source, "quote_data", None) or {}
            ref = _clean(qd.get("quote_no") or getattr(value_source, "quote_no", "") or "")
            _save_xlsx(f"Quotation{(' - ' + ref) if ref else ''}.xlsx", content, subfolder=folder)
        except Exception as exc:
            logger.warning("Could not build quotation Excel for enquiry %s: %s", getattr(quote, "id", "?"), exc)
    return folder if saved else None


def export_enquiry_register(quotes: list[Any]) -> str | None:
    """Rebuild the org-wide enquiry register and mirror it to Drive as a single
    always-current workbook. Returns the filename on success, else None.
    Never raises."""
    if not is_configured():
        return None
    try:
        from app.services.enquiry_register import REGISTER_FILENAME, build_enquiry_register_xlsx

        content = build_enquiry_register_xlsx(quotes)
    except Exception as exc:
        logger.warning("Could not build the enquiry register: %s", exc)
        return None
    return _save_xlsx(REGISTER_FILENAME, content)
