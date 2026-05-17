"""Compatibility package for Streamlit UI modules moved to apps/streamlit/ui."""
from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit" / "ui"
__path__ = [str(_PACKAGE_DIR)]
