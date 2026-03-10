"""
Entry point used by both:
  - the `downtube` console script (after pip install)
  - `python -m downtube`
"""
import sys
import os

# When running as an installed package, the sub-packages (core, models, …)
# live inside the same namespace.  When running from the source tree they
# are siblings of this package.  We add the project root to sys.path so
# that both scenarios work without any code change.
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _here not in sys.path:
    sys.path.insert(0, _here)


def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from views.main_window import MainWindow
    from controllers.main_controller import MainController

    app = QApplication(sys.argv)
    app.setApplicationName("Downtube")
    app.setOrganizationName("Downtube")
    app.setApplicationVersion("2.0.0")

    window     = MainWindow()
    controller = MainController(window)

    if not controller.cfg.get("start_minimized", False):
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
