from __future__ import annotations

import os
from pathlib import Path

from core.quote_exporter import build_quotation_excel
from core.quote_pdf import build_quotation_pdf


def _logo_path() -> str | None:
    configured = os.environ.get("GGPL_LOGO_PATH", "").strip()
    if configured and Path(configured).exists():
        return configured

    root = Path(__file__).resolve().parents[4]
    candidates = [
        root / "apps" / "streamlit" / "logo.png",
        root / "logo.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def build_pdf(items: list[dict], quote_data: dict) -> bytes:
    return build_quotation_pdf(items, quote_data, logo_path=_logo_path())


def build_xlsx(items: list[dict], quote_data: dict) -> bytes:
    return build_quotation_excel(items, quote_data, logo_path=_logo_path())
