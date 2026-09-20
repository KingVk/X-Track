"""python -m xtrack.wmtool"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from .config_store import ConfigStore
from .i18n import set_language
from .installer import DependencyInstaller
from .styles import DARK_STYLE
from .wmtool_window import WatermarkToolWindow
from . import __version__


def main() -> None:
    cfg = ConfigStore().config
    set_language(getattr(cfg, "language", "") or "zh")
    if getattr(cfg, "ffmpeg_path", ""):
        DependencyInstaller.set_configured_ffmpeg_path(cfg.ffmpeg_path)

    app = QApplication(sys.argv)
    app.setApplicationName("X-Track")
    app.setApplicationDisplayName(f"X-Track {__version__}")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    window = WatermarkToolWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
