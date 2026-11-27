import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow
from .styles import DARK_STYLE
from . import __version__
from . import updater as app_updater


def main():
    if "--wmtool" in sys.argv:
        from .wmtool import main as wmtool_main
        wmtool_main()
        return
    app = QApplication(sys.argv)
    app.setApplicationName("X-Track")
    app.setApplicationDisplayName(f"X-Track {__version__}")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("X-Track")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.setWindowTitle(f"X-Track {__version__}")
    window.show()

    if app_updater.updates_supported():
        # Defer so first paint / deps chips are not blocked by network.
        QTimer.singleShot(1800, lambda: window.start_update_check(manual=False))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
