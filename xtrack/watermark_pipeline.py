"""Inline watermark during download: serial jobs, wait-queue size 1, pause downloads."""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from .watermark import IMAGE_EXTS, VIDEO_EXTS, WatermarkProcessor


_MEDIA_SUFFIXES = IMAGE_EXTS + VIDEO_EXTS


def extract_downloaded_media_path(line: str) -> Optional[str]:
    """Best-effort parse of gallery-dl stdout (UTF-8). Prefer DestMediaWatcher."""
    if not line:
        return None
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if s.startswith("[") or "HTTP/" in s or "urllib3" in s:
        return None
    if ":" in s and not re.match(r"^[A-Za-z]:[\\/]", s):
        parts = s.split()
        s = parts[-1] if parts else s

    s = s.strip().strip('"').strip("'")
    lower = s.lower()
    if not any(lower.endswith(ext) for ext in _MEDIA_SUFFIXES):
        return None
    base = os.path.basename(s)
    if base.startswith(("_xtrack", "_gdl_ui", "_wm_")) or ".wm_tmp" in base:
        return None
    if not os.path.isfile(s):
        return None
    return os.path.abspath(s)


def _is_media_file(path: str) -> bool:
    name = os.path.basename(path)
    if name.startswith(("_xtrack", "_gdl_ui", "_wm_", ".")) or ".wm_tmp" in name:
        return False
    lower = name.lower()
    return any(lower.endswith(ext) for ext in _MEDIA_SUFFIXES)


class DestMediaWatcher:
    """Watch dest for new media files — avoids Windows stdout mojibake on CJK paths."""

    def __init__(
        self,
        dest_folder: str,
        pipeline: "InlineWatermarkPipeline",
        stop_event: threading.Event,
        *,
        max_files: int = 0,
        on_limit: Optional[Callable[[], None]] = None,
        poll_interval: float = 0.35,
    ):
        self.dest_folder = dest_folder
        self.pipeline = pipeline
        self.stop_event = stop_event
        self.max_files = max(0, int(max_files or 0))
        self.on_limit = on_limit
        self.poll_interval = poll_interval
        self._known_size: Dict[str, int] = {}
        self._stable_since: Dict[str, float] = {}
        self._handled: Set[str] = set()
        self._thread: Optional[threading.Thread] = None

    def seed_existing(self) -> int:
        count = 0
        if not self.dest_folder or not os.path.isdir(self.dest_folder):
            return 0
        for dirpath, _, filenames in os.walk(self.dest_folder):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not _is_media_file(path):
                    continue
                try:
                    abspath = os.path.abspath(path)
                    size = os.path.getsize(abspath)
                except OSError:
                    continue
                self._known_size[abspath] = size
                self._handled.add(abspath)
                self.pipeline.mark_seeded(abspath)
                count += 1
        return count

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="DestMediaWatcher", daemon=True)
        self._thread.start()

    def join(self, timeout: float = 2.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            if self.dest_folder and os.path.isdir(self.dest_folder):
                try:
                    self._scan_once()
                except OSError:
                    pass
            if self.max_files and len(self.pipeline.done_files) >= self.max_files:
                if self.on_limit:
                    self.on_limit()
                self.stop_event.set()
                return
            self.stop_event.wait(self.poll_interval)

    def _scan_once(self) -> None:
        now = time.time()
        for dirpath, _, filenames in os.walk(self.dest_folder):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not _is_media_file(path):
                    continue
                try:
                    abspath = os.path.abspath(path)
                    size = os.path.getsize(abspath)
                except OSError:
                    continue

                if abspath in self._handled:
                    continue
                if self.pipeline.is_seeded(abspath) or self.pipeline.was_done(abspath):
                    self._handled.add(abspath)
                    continue

                prev = self._known_size.get(abspath)
                if prev is None or prev != size:
                    self._known_size[abspath] = size
                    self._stable_since[abspath] = now
                    continue

                t0 = self._stable_since.get(abspath, now)
                if now - t0 < 0.3:
                    continue

                self._handled.add(abspath)
                self._stable_since.pop(abspath, None)
                if not self.pipeline.enabled:
                    continue
                self.pipeline.submit(abspath)
                if self.max_files and len(self.pipeline.done_files) >= self.max_files:
                    if self.on_limit:
                        self.on_limit()
                    self.stop_event.set()
                    return


class InlineWatermarkPipeline:
    """Serial inline watermark; wait-queue max 1; pause downloads while running."""

    def __init__(self):
        self._lock = threading.Condition()
        self._busy = False
        self._waiting = 0
        self._enabled = False
        self._settings: dict = {}
        self._processor = WatermarkProcessor()
        self._on_log: Optional[Callable[[str], None]] = None
        self._suspend: Optional[Callable[[], None]] = None
        self._resume: Optional[Callable[[], None]] = None
        self._wait_if_paused: Optional[Callable[[], None]] = None
        self._done: List[str] = []
        self._seeded: Set[str] = set()
        self._claimed: Set[str] = set()
        self._mode_tag = "text"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def reset(self) -> None:
        with self._lock:
            self._busy = False
            self._waiting = 0
            self._done = []
            self._seeded = set()
            self._claimed = set()

    def mark_seeded(self, path: str) -> None:
        with self._lock:
            self._seeded.add(os.path.abspath(path))

    def is_seeded(self, path: str) -> bool:
        with self._lock:
            return os.path.abspath(path) in self._seeded

    def was_done(self, path: str) -> bool:
        abspath = os.path.abspath(path)
        with self._lock:
            return any(os.path.abspath(p) == abspath for p in self._done)

    def configure(
        self,
        *,
        enabled: bool,
        settings: dict,
        on_log: Optional[Callable[[str], None]] = None,
        suspend: Optional[Callable[[], None]] = None,
        resume: Optional[Callable[[], None]] = None,
        wait_if_paused: Optional[Callable[[], None]] = None,
    ) -> None:
        with self._lock:
            self._enabled = enabled
            self._settings = dict(settings or {})
            self._on_log = on_log
            self._suspend = suspend
            self._resume = resume
            self._wait_if_paused = wait_if_paused
            self._mode_tag = (self._settings.get("mode") or "image").lower()

    @property
    def done_files(self) -> List[str]:
        with self._lock:
            return list(self._done)

    @property
    def mode_tag(self) -> str:
        return self._mode_tag

    def _log(self, msg: str) -> None:
        if not self._on_log:
            return
        try:
            self._on_log(msg)
        except Exception:
            try:
                self._on_log(msg.encode("ascii", "replace").decode("ascii"))
            except Exception:
                pass

    def handle_output_line(self, line: str) -> None:
        if not self._enabled:
            return
        path = extract_downloaded_media_path(line)
        if path:
            self.submit(path)

    def submit(self, path: str) -> bool:
        path = os.path.abspath(path)
        if self._wait_if_paused:
            try:
                self._wait_if_paused()
            except Exception:
                pass
        with self._lock:
            if not self._enabled:
                return False
            if path in self._seeded:
                return True
            if any(os.path.abspath(p) == path for p in self._done):
                return True

            if path in self._claimed:
                while path in self._claimed and not any(os.path.abspath(p) == path for p in self._done):
                    self._lock.wait(timeout=0.5)
                return any(os.path.abspath(p) == path for p in self._done)

            while self._busy and self._waiting >= 1:
                self._log(
                    f"Watermark queue full — pausing until slot frees: {os.path.basename(path)}"
                )
                self._lock.wait(timeout=0.5)

            if path in self._seeded or any(os.path.abspath(p) == path for p in self._done):
                return True
            if path in self._claimed:
                while path in self._claimed and not any(os.path.abspath(p) == path for p in self._done):
                    self._lock.wait(timeout=0.5)
                return True

            if self._busy:
                self._waiting += 1
                self._log(f"Watermark queued (1/1): {os.path.basename(path)}")
                try:
                    while self._busy:
                        self._lock.wait(timeout=0.5)
                finally:
                    self._waiting -= 1

            if path in self._seeded or any(os.path.abspath(p) == path for p in self._done):
                return True
            if path in self._claimed:
                while path in self._claimed and not any(os.path.abspath(p) == path for p in self._done):
                    self._lock.wait(timeout=0.5)
                return True

            self._busy = True
            self._claimed.add(path)

        if self._suspend:
            try:
                self._suspend()
            except Exception as e:
                self._log(f"suspend downloads: {e}")

        ok = False
        try:
            self._log(f"Watermark start [{self._mode_tag}]: {path}")
            ok, msg = self._processor.apply_to_file(path, **self._settings)
            self._log(f"Watermark done [{self._mode_tag}]: {os.path.basename(path)} — {msg}")
            with self._lock:
                if ok:
                    self._done.append(path)
        except Exception as e:
            self._log(f"Watermark error: {path} — {e}")
            ok = False
        finally:
            if self._resume:
                try:
                    self._resume()
                except Exception as e:
                    self._log(f"resume downloads: {e}")
            with self._lock:
                self._claimed.discard(path)
                self._busy = False
                self._lock.notify_all()
        return ok
