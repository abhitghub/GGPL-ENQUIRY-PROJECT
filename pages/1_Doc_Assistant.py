"""Compatibility page wrapper for the moved Streamlit app."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


_STREAMLIT_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit"
if str(_STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(_STREAMLIT_DIR))

runpy.run_path(str(_STREAMLIT_DIR / "pages" / "1_Doc_Assistant.py"), run_name="__main__")
