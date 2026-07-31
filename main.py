"""Project entrypoint. Run from repo root: python main.py"""
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from closer.cli.main import main  # noqa: E402

if __name__ == "__main__":
    main()
