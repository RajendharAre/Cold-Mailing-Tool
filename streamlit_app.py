"""Convenience launcher for the Streamlit UI. Run: streamlit run streamlit_app.py"""
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))

from closer.ui.app import main  # noqa: E402

main()
