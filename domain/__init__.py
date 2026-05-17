"""Compatibility package for modules moved to packages/domain."""
from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "packages" / "domain"
__path__ = [str(_PACKAGE_DIR)]
