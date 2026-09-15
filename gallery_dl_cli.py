"""Console entry for the companion gallery-dl.exe shipped next to X-Track.exe."""

from __future__ import annotations

import sys

import gallery_dl


def main() -> None:
    sys.argv[0] = "gallery-dl"
    raise SystemExit(gallery_dl.main())


if __name__ == "__main__":
    main()
