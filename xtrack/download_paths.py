"""Paths and gallery-dl naming conventions used by the UI."""

import os

DOWNLOAD_ARCHIVE_NAME = "_xtrack_download.sqlite"
MANIFEST_NAME = "_xtrack_manifest.json"
LEGACY_ARCHIVE_NAME = "_gdl_ui_download.sqlite"
LEGACY_MANIFEST_NAME = "_gdl_ui_manifest.json"
INTERNAL_PREFIXES = ("_xtrack", "_gdl_ui", "_wm_")


def is_internal_filename(name: str) -> bool:
    return name.startswith(INTERNAL_PREFIXES)

# date + text (fallback tweet_id when empty) + zero-based media index + extension
# Leading form-feed + "F " selects gallery-dl's f-string formatter.
FILENAME_FORMAT = (
    "\fF {date:%Y-%m-%d}_{str(content or tweet_id or id or 'media')[:50]}_{num-1}.{extension}"
)


def download_archive_path(dest_folder: str) -> str:
    """Prefer the new archive name; reuse legacy file if present so resumes keep working."""
    new_path = os.path.join(dest_folder, DOWNLOAD_ARCHIVE_NAME)
    legacy_path = os.path.join(dest_folder, LEGACY_ARCHIVE_NAME)
    if not os.path.exists(new_path) and os.path.exists(legacy_path):
        return legacy_path
    return new_path


def manifest_path(dest_folder: str) -> str:
    new_path = os.path.join(dest_folder, MANIFEST_NAME)
    legacy_path = os.path.join(dest_folder, LEGACY_MANIFEST_NAME)
    if not os.path.exists(new_path) and os.path.exists(legacy_path):
        return legacy_path
    return new_path
