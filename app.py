"""Compatibility entrypoint for the Streamlit app.

The migration keeps the Streamlit shell under apps/streamlit. This wrapper
preserves the historical `streamlit run app.py` workflow during the cutover.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    _streamlit_dir = Path(__file__).resolve().parent / "apps" / "streamlit"
    if str(_streamlit_dir) not in sys.path:
        sys.path.insert(0, str(_streamlit_dir))

    runpy.run_path(str(_streamlit_dir / "app.py"), run_name="__main__")


if __name__ == "__main__":
    main()
