"""GitHub Releases auto-update for the frozen Windows onedir build."""

from __future__ import annotations

import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from . import __version__
from .paths import is_frozen, project_root
from .procutil import no_window_kwargs

GITHUB_OWNER = "KingVk"
GITHUB_REPO = "X-Track"
ASSET_PREFIX = "X-Track-"
ASSET_SUFFIX = "-windows.zip"
USER_AGENT = f"X-Track/{__version__} (+https://github.com/{GITHUB_OWNER}/{GITHUB_REPO})"

_API_PATH = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Direct API first, then China-friendly GitHub proxies (same idea as ffmpeg installer).
RELEASE_API_URLS: Sequence[str] = (
    _API_PATH,
    f"https://ghproxy.net/{_API_PATH}",
    f"https://mirror.ghproxy.com/{_API_PATH}",
    f"https://gh.ddlc.top/{_API_PATH}",
)

PRESERVE_DIRS = ("data",)


@dataclass
class ReleaseInfo:
    version: str
    tag: str
    notes: str
    asset_name: str
    download_url: str
    size: int = 0


def updates_supported() -> bool:
    """Auto-update only makes sense for the packaged Windows build."""
    if os.environ.get("XTRACK_UPDATE_TEST", "").strip() in ("1", "true", "yes"):
        return True
    return is_frozen() and sys.platform.startswith("win")


def parse_version(text: str) -> Tuple[int, ...]:
    raw = (text or "").strip().lstrip("vV")
    parts: List[int] = []
    for chunk in raw.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def is_newer(remote: str, local: str = __version__) -> bool:
    return parse_version(remote) > parse_version(local)


def _mirror_download_urls(url: str) -> List[str]:
    urls = [url]
    if url.startswith("https://github.com/"):
        urls.extend(
            [
                f"https://ghproxy.net/{url}",
                f"https://mirror.ghproxy.com/{url}",
                f"https://gh.ddlc.top/{url}",
            ]
        )
    # Keep order: official first for API-provided browser_download_url retries
    # Prefer mirrors first when the host is github.com (often blocked).
    if url.startswith("https://github.com/"):
        return urls[1:] + [urls[0]]
    return urls


def _http_get_json(url: str, timeout: int = 20) -> dict:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


def _pick_windows_asset(release: dict) -> Optional[dict]:
    assets = release.get("assets") or []
    candidates = []
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.startswith(ASSET_PREFIX) and name.endswith(ASSET_SUFFIX):
            candidates.append(asset)
    if not candidates:
        return None
    # Prefer asset whose name contains the tag version
    tag = str(release.get("tag_name") or "").lstrip("vV")
    for asset in candidates:
        if tag and tag in str(asset.get("name") or ""):
            return asset
    return candidates[0]


def fetch_latest_release() -> ReleaseInfo:
    last_error: Optional[BaseException] = None
    for url in RELEASE_API_URLS:
        try:
            data = _http_get_json(url)
            tag = str(data.get("tag_name") or "").strip()
            if not tag:
                raise RuntimeError("release missing tag_name")
            asset = _pick_windows_asset(data)
            if not asset:
                raise RuntimeError("no Windows zip asset on latest release")
            download = str(asset.get("browser_download_url") or "").strip()
            if not download:
                raise RuntimeError("asset missing browser_download_url")
            version = tag.lstrip("vV")
            notes = str(data.get("body") or "").strip()
            return ReleaseInfo(
                version=version,
                tag=tag,
                notes=notes,
                asset_name=str(asset.get("name") or ""),
                download_url=download,
                size=int(asset.get("size") or 0),
            )
        except Exception as exc:  # noqa: BLE001 — try next mirror
            last_error = exc
            continue
    raise RuntimeError(f"failed to query GitHub releases: {last_error}")


def check_for_update(current: str = __version__) -> Tuple[Optional[ReleaseInfo], str]:
    """Return (release, status). release is set only when a newer build exists."""
    info = fetch_latest_release()
    if is_newer(info.version, current):
        return info, "available"
    return None, "up_to_date"


def _download_file(
    url: str,
    dest_path: str,
    on_progress: Optional[Callable[[str, int], None]] = None,
    retries: int = 3,
    min_bytes: int = 1024 * 1024,
) -> None:
    ctx = ssl.create_default_context()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Connection": "close",
    }
    last_error: Optional[BaseException] = None
    for attempt in range(1, retries + 1):
        try:
            if on_progress:
                on_progress(f"Downloading (attempt {attempt}/{retries})...", 0)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                total = int(resp.headers.get("Content-Length", 0) or 0)
                downloaded = 0
                last_pct = -1
                with open(dest_path, "wb") as out:
                    while True:
                        chunk = resp.read(256 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if on_progress and total > 0:
                            pct = min(100, int(downloaded * 100 / total))
                            if pct >= last_pct + 1 or pct == 100:
                                last_pct = pct
                                mb = downloaded / (1024 * 1024)
                                total_mb = total / (1024 * 1024)
                                on_progress(
                                    f"Downloading... {pct}% ({mb:.1f}/{total_mb:.1f} MB)",
                                    pct,
                                )
            size = os.path.getsize(dest_path)
            if size < min_bytes:
                raise RuntimeError(f"downloaded file too small ({size} bytes)")
            if on_progress:
                on_progress("Download complete", 100)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if on_progress:
                on_progress(f"Download error: {exc}", -1)
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"download failed: {last_error}")


def _extract_release_zip(zip_path: str, staging_dir: str) -> None:
    if os.path.isdir(staging_dir):
        shutil.rmtree(staging_dir, ignore_errors=True)
    os.makedirs(staging_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(staging_dir)

    # Zip is flat (exe at root). If a single top-level folder wraps files, unwrap it.
    entries = [e for e in os.listdir(staging_dir) if e not in (".", "..")]
    if len(entries) == 1:
        only = os.path.join(staging_dir, entries[0])
        if os.path.isdir(only) and os.path.isfile(os.path.join(only, "X-Track.exe")):
            for name in os.listdir(only):
                shutil.move(os.path.join(only, name), os.path.join(staging_dir, name))
            shutil.rmtree(only, ignore_errors=True)

    exe = os.path.join(staging_dir, "X-Track.exe")
    if not os.path.isfile(exe):
        raise RuntimeError("extracted update is missing X-Track.exe")


def download_and_stage(
    info: ReleaseInfo,
    on_progress: Optional[Callable[[str, int], None]] = None,
) -> str:
    """Download release zip and extract to a staging folder. Returns staging path."""
    work = tempfile.mkdtemp(prefix="xtrack_update_")
    zip_path = os.path.join(work, info.asset_name or "update.zip")
    staging = os.path.join(work, "staging")
    last_error: Optional[BaseException] = None
    for url in _mirror_download_urls(info.download_url):
        try:
            if on_progress:
                on_progress("Starting download...", 0)
            _download_file(url, zip_path, on_progress=on_progress)
            if on_progress:
                on_progress("Extracting...", 100)
            _extract_release_zip(zip_path, staging)
            try:
                os.remove(zip_path)
            except OSError:
                pass
            return staging
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    raise RuntimeError(f"could not download/extract update: {last_error}")


def _bat_escape(path: str) -> str:
    """Value safe inside set "VAR=..." (no surrounding quotes)."""
    return path.replace('"', "")


def write_apply_script(
    staging_dir: str,
    install_dir: Optional[str] = None,
    exe_name: str = "X-Track.exe",
    pid: Optional[int] = None,
) -> str:
    """Write a detached .bat that waits for this process, mirrors files, relaunches."""
    install_dir = install_dir or project_root()
    pid = os.getpid() if pid is None else pid
    exe_path = os.path.join(install_dir, exe_name)
    script = os.path.join(
        tempfile.gettempdir(), f"xtrack_apply_update_{pid}.bat"
    )
    xd = " ".join(f'"{d}"' for d in PRESERVE_DIRS)
    src = _bat_escape(staging_dir)
    dest = _bat_escape(install_dir)
    exe = _bat_escape(exe_path)
    lines = [
        "@echo off",
        "setlocal EnableExtensions",
        f"set PID={pid}",
        f'set "SRC={src}"',
        f'set "DEST={dest}"',
        f'set "EXE={exe}"',
        "",
        ":wait",
        'tasklist /FI "PID eq %PID%" 2>NUL | find "%PID%" >NUL',
        "if not errorlevel 1 (",
        "  ping -n 2 127.0.0.1 >NUL",
        "  goto wait",
        ")",
        "",
        f'robocopy "%SRC%" "%DEST%" /E /MIR /XD {xd} /R:2 /W:1 /NFL /NDL /NJH /NJS /NC /NS /NP',
        "set RC=%ERRORLEVEL%",
        "if %RC% GEQ 8 (",
        "  echo Update copy failed with code %RC%",
        "  exit /b %RC%",
        ")",
        "",
        'start "" "%EXE%"',
        "ping -n 2 127.0.0.1 >NUL",
        'rmdir /s /q "%SRC%" 2>NUL',
        'del "%~f0" >NUL 2>&1',
        "endlocal",
        "exit /b 0",
        "",
    ]
    with open(script, "w", encoding="utf-8", newline="\r\n") as handle:
        handle.write("\n".join(lines))
    return script


def launch_apply_script(script_path: str) -> None:
    flags = 0
    if sys.platform.startswith("win"):
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    kwargs = {}
    if flags:
        kwargs["creationflags"] = flags
    else:
        kwargs.update(no_window_kwargs())
    subprocess.Popen(
        ["cmd.exe", "/c", script_path],
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )


def short_release_notes(notes: str, limit: int = 400) -> str:
    text = re.sub(r"\r\n?", "\n", notes or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
