import sys

from PySide6.QtWidgets import QApplication

from app_icon import get_app_icon
from database import init_db
from ui.main_window import MainWindow


if __name__ == "__main__":
    init_db()

    app = QApplication(sys.argv)

    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    window = MainWindow()

    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    window.show()

    sys.exit(app.exec())