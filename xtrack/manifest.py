"""Scan download folder metadata and maintain download progress manifest."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from .download_paths import DOWNLOAD_ARCHIVE_NAME, is_internal_filename, manifest_path
MEDIA_EXTS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif",
    ".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v",
)


def _rel(root: str, path: str) -> str:
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        return path.replace("\\", "/")


def _load_sidecar(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _pick_text(meta: Dict[str, Any]) -> str:
    for key in (
        "description",
        "content",
        "tweet",
        "text",
        "title",
        "caption",
        "alt_text",
    ):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, dict):
            # twitter sometimes nests
            for sub in ("full_text", "text", "description"):
                s = val.get(sub)
                if isinstance(s, str) and s.strip():
                    return s.strip()
    return ""


def _pick_date(meta: Dict[str, Any]) -> str:
    for key in ("date", "created_at", "timestamp", "upload_date"):
        val = meta.get(key)
        if val is None:
            continue
        return str(val)
    return ""


def scan_media_items(dest_folder: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not dest_folder or not os.path.isdir(dest_folder):
        return items

    for dirpath, _, filenames in os.walk(dest_folder):
        for name in filenames:
            lower = name.lower()
            if not lower.endswith(MEDIA_EXTS):
                continue
            if is_internal_filename(name):
                continue
            media_path = os.path.join(dirpath, name)
            sidecar = media_path + ".json"
            # gallery-dl may use name.json or stem.json
            if not os.path.isfile(sidecar):
                stem, _ = os.path.splitext(media_path)
                alt = stem + ".json"
                if os.path.isfile(alt):
                    sidecar = alt

            meta = _load_sidecar(sidecar) if os.path.isfile(sidecar) else {}
            num = meta.get("num")
            items.append({
                "file": _rel(dest_folder, media_path),
                "metadata_file": _rel(dest_folder, sidecar) if os.path.isfile(sidecar) else "",
                "description": _pick_text(meta),
                "date": _pick_date(meta),
                "id": str(meta.get("id") or meta.get("tweet_id") or meta.get("media_id") or ""),
                "num": num if num is not None else "",
                "extension": os.path.splitext(name)[1].lstrip(".").lower(),
                "size": os.path.getsize(media_path) if os.path.isfile(media_path) else 0,
            })
    items.sort(key=lambda x: x["file"])
    return items


def update_manifest(
    dest_folder: str,
    source_url: str = "",
    status: str = "",
    last_download_time: str = "",
) -> str:
    """
    Rebuild/update the X-Track manifest under dest_folder.
    Returns manifest path.
    """
    if not dest_folder:
        return ""
    os.makedirs(dest_folder, exist_ok=True)
    path = manifest_path(dest_folder)

    data: Dict[str, Any] = {"updated_at": "", "sources": [], "items": []}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            pass

    items = scan_media_items(dest_folder)
    data["items"] = items
    data["updated_at"] = datetime.now().isoformat()
    data["total_files"] = len(items)
    data["total_with_text"] = sum(1 for i in items if i.get("description"))
    data["download_archive"] = os.path.join(dest_folder, DOWNLOAD_ARCHIVE_NAME)

    sources = data.get("sources") or []
    if not isinstance(sources, list):
        sources = []

    if source_url:
        entry = None
        for s in sources:
            if isinstance(s, dict) and s.get("url") == source_url:
                entry = s
                break
        if entry is None:
            entry = {"url": source_url}
            sources.append(entry)
        if status:
            entry["status"] = status
        if last_download_time:
            entry["last_download_time"] = last_download_time
        entry["file_count"] = len(items)
        entry["updated_at"] = data["updated_at"]

    data["sources"] = sources

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return path
