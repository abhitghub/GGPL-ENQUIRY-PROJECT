"""Compatibility package for modules moved to packages/data."""
from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "packages" / "data"
__path__ = [str(_PACKAGE_DIR)]
