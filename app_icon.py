from pathlib import Path

from PySide6.QtGui import QIcon

from app_paths import ASSETS_DIR


def get_app_icon_path() -> Path | None:
    """
    Return the first existing icon path.
    Prefer .ico for Windows executable/icon usage.
    """
    candidates = [
        ASSETS_DIR / "icon.ico",
        ASSETS_DIR / "icon.png",
        ASSETS_DIR / "logo.png",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def get_app_icon() -> QIcon:
    """
    Return a QIcon instance for the application.
    """
    icon_path = get_app_icon_path()
    if icon_path is None:
        return QIcon()
    return QIcon(str(icon_path))