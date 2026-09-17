import os
import shutil
import subprocess
import sys
from typing import Callable, List, Optional, Tuple

from .download_paths import FILENAME_FORMAT, download_archive_path
from .paths import is_frozen, project_root
from .procutil import no_window_kwargs


class CommandBuilder:
    def __init__(self):
        self.gallery_dl_prefix = self._find_gallery_dl_prefix()

    def _find_gallery_dl_prefix(self) -> List[str]:
        """Return argv prefix to invoke gallery-dl (never re-launch the GUI exe)."""
        if is_frozen():
            companion = os.path.join(project_root(), "gallery-dl.exe")
            if os.path.isfile(companion):
                return [companion]
        which = shutil.which("gallery-dl")
        if which:
            return [which]
        # Dev fallback
        return ["gallery-dl"]

    def build(
        self,
        url: str,
        config,
        last_download_time: str = "",
        url_item=None,
    ) -> List[str]:
        cmd = list(self.gallery_dl_prefix)

        if config.dest_folder:
            os.makedirs(config.dest_folder, exist_ok=True)
            cmd.extend(["--dest", config.dest_folder])
            cmd.extend(["--download-archive", download_archive_path(config.dest_folder)])

        cmd.extend(["-f", FILENAME_FORMAT])
        cmd.append("--windows-filenames")

        cookies_file = getattr(config, "cookies_file", "") or ""
        if cookies_file and os.path.isfile(cookies_file):
            cmd.extend(["--cookies", cookies_file])

        if config.sleep_min and config.sleep_max:
            cmd.extend(["--sleep", f"{config.sleep_min}-{config.sleep_max}"])

        if config.sleep_request_min and config.sleep_request_max:
            cmd.extend(["--sleep-request", f"{config.sleep_request_min}-{config.sleep_request_max}"])

        if config.sleep_429:
            cmd.extend(["--sleep-429", str(config.sleep_429)])

        filter_source = url_item if url_item is not None else config
        filter_expr = self._build_filter(filter_source, last_download_time)
        if filter_expr:
            cmd.extend(["--filter", filter_expr])

        if getattr(config, "write_metadata", True):
            cmd.append("--write-metadata")
        if getattr(config, "write_info_json", True):
            cmd.append("--write-info-json")

        if config.verbose:
            cmd.append("-v")

        max_items = int(getattr(config, "max_items", 0) or 0)
        if max_items > 0:
            cmd.extend(["--range", f"1-{max_items}"])

        cmd.append(url)
        return cmd

    IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp", "bmp", "avif", "heic", "svg")
    VIDEO_EXTENSIONS = ("mp4", "webm", "mov", "mkv", "avi", "m4v", "flv")

    def _build_media_type_filter(self, media_type: str) -> str:
        if media_type == "image":
            exts = ", ".join(f'"{e}"' for e in self.IMAGE_EXTENSIONS)
            return f"extension in ({exts})"
        if media_type == "video":
            exts = ", ".join(f'"{e}"' for e in self.VIDEO_EXTENSIONS)
            return f"extension in ({exts})"
        return ""

    def _build_date_range_filter(self, config) -> str:
        from datetime import datetime, timedelta

        # Support old configs that used filter_date_mode / filter_date_enabled
        start_enabled = getattr(config, "filter_date_start_enabled", False)
        end_enabled = getattr(config, "filter_date_end_enabled", False)
        mode = getattr(config, "filter_date_mode", None)
        if mode and not start_enabled and not end_enabled:
            if mode == "after":
                start_enabled = True
            elif mode == "before":
                end_enabled = True
            elif mode == "range":
                start_enabled = True
                end_enabled = True
            elif getattr(config, "filter_date_enabled", False):
                start_enabled = True
                end_enabled = True

        start_s = getattr(config, "filter_date_start", "") or ""
        end_s = getattr(config, "filter_date_end", "") or ""
        start_dt = None
        end_dt = None

        if start_enabled and start_s:
            try:
                start_dt = datetime.strptime(start_s, "%Y-%m-%d")
            except ValueError:
                start_dt = None

        if end_enabled and end_s:
            try:
                end_dt = datetime.strptime(end_s, "%Y-%m-%d")
            except ValueError:
                end_dt = None

        if not start_dt and not end_dt:
            return ""

        # Twitter/X (and many sites) walk newest→oldest. With an end date we must
        # *skip* newer items (filter false), and only abort once past the start.
        if start_dt and end_dt:
            end_exclusive = end_dt + timedelta(days=1)
            return (
                f"date < datetime({end_exclusive.year}, {end_exclusive.month}, {end_exclusive.day}) "
                f"and (date >= datetime({start_dt.year}, {start_dt.month}, {start_dt.day}) or abort())"
            )
        if start_dt:
            return (
                f"date >= datetime({start_dt.year}, {start_dt.month}, {start_dt.day}) or abort()"
            )
        # end only: skip newer, keep downloading older (no abort)
        end_exclusive = end_dt + timedelta(days=1)
        return (
            f"date < datetime({end_exclusive.year}, {end_exclusive.month}, {end_exclusive.day})"
        )

    def _build_filter(self, config, last_download_time: str = "") -> str:
        parts = []

        date_from_url = None
        if last_download_time:
            try:
                from datetime import datetime
                date_from_url = datetime.fromisoformat(last_download_time)
            except ValueError:
                date_from_url = None

        range_filter = self._build_date_range_filter(config)

        if date_from_url and not range_filter:
            parts.append(
                f"date >= datetime({date_from_url.year}, {date_from_url.month}, {date_from_url.day}, "
                f"{date_from_url.hour}, {date_from_url.minute}, {date_from_url.second}) or abort()"
            )
        elif range_filter and not date_from_url:
            parts.append(range_filter)
        elif date_from_url and range_filter:
            from datetime import datetime, timedelta

            start_enabled = getattr(config, "filter_date_start_enabled", False)
            end_enabled = getattr(config, "filter_date_end_enabled", False)
            start_s = getattr(config, "filter_date_start", "") or ""
            end_s = getattr(config, "filter_date_end", "") or ""
            start_dt = None
            end_dt = None
            if start_enabled and start_s:
                try:
                    start_dt = datetime.strptime(start_s, "%Y-%m-%d")
                except ValueError:
                    pass
            if end_enabled and end_s:
                try:
                    end_dt = datetime.strptime(end_s, "%Y-%m-%d")
                except ValueError:
                    pass

            effective_start = date_from_url
            if start_dt:
                start_midnight = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                if start_midnight > date_from_url.replace(hour=0, minute=0, second=0, microsecond=0):
                    effective_start = start_dt

            start_expr = (
                f"date >= datetime({effective_start.year}, {effective_start.month}, "
                f"{effective_start.day}, {getattr(effective_start, 'hour', 0)}, "
                f"{getattr(effective_start, 'minute', 0)}, {getattr(effective_start, 'second', 0)})"
            )
            if end_dt:
                end_exclusive = end_dt + timedelta(days=1)
                parts.append(
                    f"date < datetime({end_exclusive.year}, {end_exclusive.month}, {end_exclusive.day}) "
                    f"and ({start_expr} or abort())"
                )
            else:
                parts.append(f"{start_expr} or abort()")

        media_filter = self._build_media_type_filter(getattr(config, "media_type", "all"))
        if media_filter:
            parts.append(media_filter)

        if not parts:
            return ""

        if len(parts) == 1:
            return parts[0]
        return " and ".join(f"({p})" for p in parts)

    def validate(self, config) -> Tuple[bool, str]:
        if not config.dest_folder:
            return False, "dest_required"
        return True, ""


class CommandExecutor:
    """Runs gallery-dl processes; supports multiple concurrent jobs."""

    def __init__(self):
        self._lock = __import__("threading").Lock()
        self._processes: List[subprocess.Popen] = []
        self.is_running = False
        # backwards-compat for code that still looks at .process
        self.process: Optional[subprocess.Popen] = None
        self._suspended = False

    def run(
        self,
        cmd: List[str],
        on_output: Callable[[str], None],
        on_complete: Callable[[int], None],
    ):
        process: Optional[subprocess.Popen] = None
        return_code = 1
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **no_window_kwargs(),
            )
            with self._lock:
                self._processes.append(process)
                self.process = process
                self.is_running = True
                if self._suspended:
                    self._suspend_process(process)

            assert process.stdout is not None
            for line in iter(process.stdout.readline, ""):
                with self._lock:
                    still = process in self._processes and self.is_running
                if not still:
                    break
                if line:
                    on_output(line.rstrip())

            process.stdout.close()
            return_code = process.wait()

        except Exception as e:
            on_output(f"Error executing command: {e}")
            return_code = 1
        finally:
            with self._lock:
                if process in self._processes:
                    self._processes.remove(process)
                if self.process is process:
                    self.process = self._processes[0] if self._processes else None
                if not self._processes:
                    self.is_running = False

        on_complete(return_code)

    def suspend_all(self):
        """Pause all gallery-dl processes (Windows NtSuspendProcess / POSIX SIGSTOP)."""
        with self._lock:
            self._suspended = True
            procs = list(self._processes)
        for process in procs:
            self._suspend_process(process)

    def resume_all(self):
        with self._lock:
            self._suspended = False
            procs = list(self._processes)
        for process in procs:
            self._resume_process(process)

    @staticmethod
    def _suspend_process(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "nt":
                import ctypes

                handle = getattr(process, "_handle", None)
                if handle:
                    ctypes.windll.ntdll.NtSuspendProcess(int(handle))
            else:
                process.send_signal(__import__("signal").SIGSTOP)
        except Exception:
            pass

    @staticmethod
    def _resume_process(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "nt":
                import ctypes

                handle = getattr(process, "_handle", None)
                if handle:
                    ctypes.windll.ntdll.NtResumeProcess(int(handle))
            else:
                process.send_signal(__import__("signal").SIGCONT)
        except Exception:
            pass

    def cancel(self):
        with self._lock:
            self.is_running = False
            self._suspended = False
            procs = list(self._processes)
        for process in procs:
            try:
                # Ensure resumed so terminate works after suspend
                self._resume_process(process)
                process.terminate()
            except Exception:
                pass
        for process in procs:
            try:
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass


def check_gallery_dl_installed() -> Tuple[bool, str]:
    if is_frozen():
        companion = os.path.join(project_root(), "gallery-dl.exe")
        if os.path.isfile(companion):
            return True, companion
    cmd = shutil.which("gallery-dl")
    if cmd:
        return True, cmd
    return False, "gallery-dl not found"


def check_ffmpeg_installed() -> Tuple[bool, str]:
    from .installer import DependencyInstaller

    cmd = DependencyInstaller.find_ffmpeg_path()
    if cmd:
        return True, cmd
    return False, "ffmpeg not found"
