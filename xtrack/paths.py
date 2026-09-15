"""Project layout helpers: xtrack / resources / data.

Frozen (PyInstaller) layout::

    X-Track/
      X-Track.exe          # GUI
      gallery-dl.exe       # CLI helper (same folder)
      data/                # writable user config
      _internal/
        resources/         # ffmpeg, fonts, default_watermark.png
"""

from __future__ import annotations

import os
import sys

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_PACKAGE_DIR)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> str:
    """Writable app root: folder containing the exe (frozen) or repo root."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return _PROJECT_ROOT


def bundle_dir() -> str:
    """Read-only bundle content (_MEIPASS / _internal) when frozen."""
    if is_frozen():
        return getattr(sys, "_MEIPASS", project_root())
    return _PROJECT_ROOT


def package_dir() -> str:
    return _PACKAGE_DIR


def resources_dir() -> str:
    """Prefer bundled resources; allow override next to the exe."""
    candidates = [
        os.path.join(bundle_dir(), "resources"),
        os.path.join(project_root(), "resources"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    # Default target (may be created for writable copies)
    return candidates[0] if is_frozen() else candidates[1]


# Back-compat alias
def resource_dir() -> str:
    return resources_dir()


def data_dir() -> str:
    """Always writable — next to the exe / project root, never inside _MEIPASS."""
    path = os.path.join(project_root(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(data_dir(), "config.json")
