import sys
import logging
from PySide6.QtWidgets import QApplication
from views.main_window import MainWindow
from controllers.main_controller import MainController


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Downtube")
    app.setOrganizationName("Downtube")
    app.setApplicationVersion("2.0")

    window = MainWindow()
    controller = MainController(window)

    if not controller.cfg.get("start_minimized", False):
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
