from pathlib import Path
import sys


def app_base_dir() -> Path:
    """
    Return the base directory in both normal Python mode and EXE mode.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = app_base_dir()
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"
RECEIPTS_DIR = BASE_DIR / "receipts"

ASSETS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
RECEIPTS_DIR.mkdir(exist_ok=True)