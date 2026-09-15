import os
from typing import Tuple


def cookies_status(path: str) -> Tuple[bool, str]:
    if path and os.path.isfile(path) and os.path.getsize(path) > 0:
        return True, path
    return False, "missing"
