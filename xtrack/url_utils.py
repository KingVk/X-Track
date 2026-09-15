"""URL normalization and local media counting helpers."""

from __future__ import annotations

import os
import re
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif", ".heic"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".flv"}


def normalize_url(url: str) -> str:
    """Canonical form for duplicate checks (host aliases, trailing slash, case)."""
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in ("twitter.com", "mobile.twitter.com", "mobile.x.com"):
        host = "x.com"

    path = parsed.path or ""
    path = re.sub(r"/+", "/", path).rstrip("/")
    # drop query/fragment for identity
    return urlunparse(("https", host, path, "", "", "")).lower()


def urls_equal(a: str, b: str) -> bool:
    na, nb = normalize_url(a), normalize_url(b)
    return bool(na) and na == nb


def _twitter_screen_name(url: str) -> Optional[str]:
    n = normalize_url(url)
    m = re.match(r"^https://x\.com/([^/]+)(?:/.*)?$", n)
    if not m:
        return None
    name = m.group(1)
    if name in ("i", "home", "explore", "search", "settings", "intent", "share"):
        return None
    return name


def resolve_media_dir(dest_folder: str, url: str) -> Optional[str]:
    """Best-effort local folder for a source URL (gallery-dl layout)."""
    if not dest_folder or not os.path.isdir(dest_folder):
        return None

    screen = _twitter_screen_name(url)
    if screen:
        # gallery-dl twitter default: {category}/{author[name]}/
        candidates = [
            os.path.join(dest_folder, "twitter", screen),
            os.path.join(dest_folder, "twitter", screen.lower()),
        ]
        # case-insensitive match on Windows already; also scan twitter/
        tw = os.path.join(dest_folder, "twitter")
        if os.path.isdir(tw):
            for name in os.listdir(tw):
                if name.lower() == screen.lower():
                    candidates.insert(0, os.path.join(tw, name))
                    break
        for path in candidates:
            if os.path.isdir(path):
                return path

    # generic: last path segment under dest
    n = normalize_url(url)
    segment = n.rstrip("/").rsplit("/", 1)[-1]
    if segment:
        for dirpath, dirnames, _ in os.walk(dest_folder):
            for d in dirnames:
                if d.lower() == segment.lower():
                    return os.path.join(dirpath, d)
    return None


def count_media_files(root_dir: str) -> Tuple[int, int]:
    """Return (image_count, video_count) under root_dir."""
    images = 0
    videos = 0
    if not root_dir or not os.path.isdir(root_dir):
        return 0, 0
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if name.startswith(("_xtrack", "_gdl_ui", "_wm_")) or name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in IMAGE_EXTS:
                images += 1
            elif ext in VIDEO_EXTS:
                videos += 1
    return images, videos


def count_media_for_url(dest_folder: str, url: str) -> Tuple[int, int]:
    media_dir = resolve_media_dir(dest_folder, url)
    if not media_dir:
        return 0, 0
    return count_media_files(media_dir)
