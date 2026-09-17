"""Helpers for launching child processes without flashing a console on Windows."""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict


def no_window_kwargs() -> Dict[str, Any]:
    """Extra kwargs for subprocess.run / Popen to hide console windows on Windows."""
    if not sys.platform.startswith("win"):
        return {}
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
