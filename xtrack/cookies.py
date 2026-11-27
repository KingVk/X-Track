import os
from typing import Tuple


def cookies_status(path: str) -> Tuple[bool, str]:
    """Return (ok, detail). ok means a non-empty Netscape cookies file exists."""
    if path and os.path.isfile(path) and os.path.getsize(path) > 0:
        return True, path
    return False, "missing"


def cookies_look_like_x(path: str) -> bool:
    """True if the file mentions x.com / twitter.com auth cookies."""
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            blob = handle.read(1 << 20).lower()
    except OSError:
        return False
    if "auth_token" not in blob:
        return False
    return ("x.com" in blob) or ("twitter.com" in blob)
