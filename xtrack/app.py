import sys
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow
from .styles import DARK_STYLE
from . import __version__


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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
