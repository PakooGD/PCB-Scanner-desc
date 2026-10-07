"""
PCB Microscope Scanner — точка входа.
"""
import sys
from PySide6.QtWidgets import QApplication

from source.config import load_app_icon
from source.ui.main_window import MainWindow
from source.ui.styles import GLOBAL_QSS


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_QSS)

    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    w = MainWindow()
    if icon is not None:
        w.setWindowIcon(icon)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()