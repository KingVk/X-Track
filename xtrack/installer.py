import os
import sys
import shutil
import subprocess
import time
from typing import Callable, List, Optional, Tuple

from .paths import is_frozen, project_root, resource_dir


class DependencyInstaller:
    # Primary GitHub asset + China-friendly mirrors (tried in order)
    FFMPEG_ASSET = "ffmpeg-master-latest-win64-gpl.zip"
    FFMPEG_URLS_WINDOWS = [
        f"https://ghproxy.net/https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/{FFMPEG_ASSET}",
        f"https://mirror.ghproxy.com/https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/{FFMPEG_ASSET}",
        f"https://gh.ddlc.top/https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/{FFMPEG_ASSET}",
        f"https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/{FFMPEG_ASSET}",
        # gyan.dev builds (often more reachable)
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    ]

    LOCAL_BIN_DIR = os.path.join(os.path.expanduser("~"), ".xtrack", "bin")
    _LEGACY_BIN_DIR = os.path.join(os.path.expanduser("~"), ".gallery-dl-ui", "bin")

    @staticmethod
    def _host_python() -> Optional[List[str]]:
        """Python usable for pip when the app itself is a frozen exe."""
        if not is_frozen():
            return [sys.executable]
        candidates = [
            ["py", "-3"],
            ["python"],
            ["python3"],
        ]
        for prefix in candidates:
            try:
                r = subprocess.run(
                    prefix + ["-c", "import sys; print(sys.executable)"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if r.returncode == 0 and (r.stdout or "").strip():
                    return prefix
            except Exception:
                continue
        return None

    @classmethod
    def gallery_dl_install_cmd(cls) -> Optional[List[str]]:
        if is_frozen():
            # Bundled companion exe — no pip install needed
            companion = os.path.join(project_root(), "gallery-dl.exe")
            if os.path.isfile(companion):
                return None
        py = cls._host_python()
        if not py:
            return None
        return py + ["-m", "pip", "install", "gallery-dl"]

    @staticmethod
    def get_platform() -> str:
        if sys.platform.startswith("win"):
            return "windows"
        elif sys.platform.startswith("linux"):
            return "linux"
        elif sys.platform.startswith("darwin"):
            return "darwin"
        return "unknown"

    @classmethod
    def find_ffmpeg_path(cls) -> Optional[str]:
        """Locate ffmpeg: resources/, project folder, ~/.xtrack/bin, then PATH."""
        name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
        root = project_root()
        res = resource_dir()
        candidates = [
            os.path.join(res, "ffmpeg-9.0.1", "bin", name),
            os.path.join(res, "ffmpeg", "bin", name),
            os.path.join(res, "bin", name),
            os.path.join(res, name),
            os.path.join(root, name),
            os.path.join(root, "bin", name),
            os.path.join(root, "ffmpeg", "bin", name),
            os.path.join(cls.LOCAL_BIN_DIR, name),
            os.path.join(cls._LEGACY_BIN_DIR, name),
        ]
        # Bundles like ffmpeg-9.0.1/bin/ffmpeg.exe under resources/ or project root
        for base in (res, root):
            try:
                for entry in sorted(os.listdir(base)):
                    if entry.lower().startswith("ffmpeg"):
                        bundled = os.path.join(base, entry, "bin", name)
                        if bundled not in candidates:
                            candidates.append(bundled)
            except OSError:
                pass

        which = shutil.which("ffmpeg")
        if which:
            candidates.append(which)

        seen = set()
        for path in candidates:
            if not path or path in seen:
                continue
            seen.add(path)
            if os.path.isfile(path):
                return path
        return None

    def _ensure_local_bin_on_path(self):
        dirs = []
        found = self.find_ffmpeg_path()
        if found:
            dirs.append(os.path.dirname(found))
        if os.path.isdir(self.LOCAL_BIN_DIR):
            dirs.append(self.LOCAL_BIN_DIR)

        path = os.environ.get("PATH", "")
        parts = path.split(os.pathsep) if path else []
        for d in dirs:
            if d and d not in parts:
                parts.insert(0, d)
        os.environ["PATH"] = os.pathsep.join(parts)

    def check_gallery_dl(self) -> Tuple[bool, str]:
        if is_frozen():
            companion = os.path.join(project_root(), "gallery-dl.exe")
            if os.path.isfile(companion):
                try:
                    result = subprocess.run(
                        [companion, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    version = (result.stdout or result.stderr or "").strip() or companion
                    return True, version.split("\n")[0]
                except Exception:
                    return True, companion
        cmd = shutil.which("gallery-dl")
        if cmd:
            try:
                result = subprocess.run(
                    ["gallery-dl", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                version = result.stdout.strip() if result.stdout else "unknown"
                return True, version
            except Exception:
                pass
        return False, "not found"

    def install_gallery_dl(self, on_progress: Optional[Callable] = None) -> Tuple[bool, str]:
        if is_frozen() and os.path.isfile(os.path.join(project_root(), "gallery-dl.exe")):
            if on_progress:
                on_progress("Bundled gallery-dl.exe is ready")
            return True, "bundled"

        install_cmd = self.gallery_dl_install_cmd()
        if not install_cmd:
            msg = (
                "Cannot install gallery-dl: no system Python found. "
                "Install Python 3 or use the release that includes gallery-dl.exe."
            )
            if on_progress:
                on_progress(msg)
            return False, msg

        if on_progress:
            on_progress("Installing gallery-dl via pip...")

        try:
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                if on_progress:
                    on_progress("gallery-dl installed successfully")
                return True, "installed"
            else:
                error = result.stderr or "Unknown error"
                if on_progress:
                    on_progress(f"Failed: {error[:200]}")
                return False, error
        except subprocess.TimeoutExpired:
            if on_progress:
                on_progress("Installation timed out")
            return False, "timeout"
        except Exception as e:
            if on_progress:
                on_progress(f"Error: {e}")
            return False, str(e)

    def check_ffmpeg(self) -> Tuple[bool, str]:
        self._ensure_local_bin_on_path()
        cmd = self.find_ffmpeg_path()
        if not cmd:
            return False, "not found"
        try:
            result = subprocess.run(
                [cmd, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                first_line = (result.stderr or result.stdout or "").split("\n")[0]
                return True, first_line or cmd
        except Exception:
            pass
        return False, "not found"

    def install_ffmpeg(self, on_progress: Optional[Callable] = None) -> Tuple[bool, str]:
        platform = self.get_platform()

        if platform == "windows":
            return self._install_ffmpeg_windows(on_progress)
        elif platform == "linux":
            return self._install_ffmpeg_linux(on_progress)
        elif platform == "darwin":
            return self._install_ffmpeg_macos(on_progress)
        else:
            return False, f"Unsupported platform: {platform}"

    def _download_file(
        self,
        url: str,
        dest_path: str,
        on_progress: Optional[Callable] = None,
        retries: int = 2,
    ) -> bool:
        import urllib.request
        import ssl

        # Avoid SSL issues on some Windows setups
        ctx = ssl.create_default_context()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) X-Track/1.0",
            "Accept": "*/*",
            "Connection": "close",
        }

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                if on_progress:
                    on_progress(f"Downloading (attempt {attempt}/{retries})...")

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                    total = int(resp.headers.get("Content-Length", 0) or 0)
                    downloaded = 0
                    last_pct = -1
                    chunk_size = 256 * 1024
                    with open(dest_path, "wb") as out:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            out.write(chunk)
                            downloaded += len(chunk)
                            if on_progress and total > 0:
                                pct = min(100, int(downloaded * 100 / total))
                                if pct >= last_pct + 5 or pct == 100:
                                    last_pct = pct
                                    mb = downloaded / (1024 * 1024)
                                    total_mb = total / (1024 * 1024)
                                    on_progress(f"Downloading... {pct}% ({mb:.1f}/{total_mb:.1f} MB)")

                if os.path.getsize(dest_path) < 1024 * 100:
                    raise RuntimeError("Downloaded file too small, likely incomplete")
                return True
            except Exception as e:
                last_error = e
                if on_progress:
                    on_progress(f"Download error: {e}")
                time.sleep(1.5 * attempt)
                continue

        if on_progress and last_error:
            on_progress(f"All retries failed: {last_error}")
        return False

    def _try_winget(self, on_progress: Optional[Callable] = None) -> bool:
        winget = shutil.which("winget")
        if not winget:
            return False
        if on_progress:
            on_progress("Trying winget install ffmpeg...")
        try:
            result = subprocess.run(
                [
                    winget, "install", "--id", "Gyan.FFmpeg",
                    "-e", "--accept-package-agreements", "--accept-source-agreements",
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                return True
            # Already installed counts as success for some winget versions
            out = (result.stdout or "") + (result.stderr or "")
            if "already installed" in out.lower():
                return True
            if on_progress:
                on_progress(f"winget failed: {(result.stderr or result.stdout or '')[:180]}")
        except Exception as e:
            if on_progress:
                on_progress(f"winget error: {e}")
        return False

    def _try_choco(self, on_progress: Optional[Callable] = None) -> bool:
        choco = shutil.which("choco")
        if not choco:
            return False
        if on_progress:
            on_progress("Trying chocolatey install ffmpeg...")
        try:
            result = subprocess.run(
                [choco, "install", "ffmpeg", "-y"],
                capture_output=True,
                text=True,
                timeout=600,
            )
            return result.returncode == 0
        except Exception as e:
            if on_progress:
                on_progress(f"choco error: {e}")
        return False

    def _extract_and_install_zip(self, zip_path: str, on_progress: Optional[Callable] = None) -> Tuple[bool, str]:
        import zipfile
        import tempfile

        extract_dir = os.path.join(tempfile.gettempdir(), "ffmpeg_extracted_xtrack")
        if os.path.isdir(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)

        if on_progress:
            on_progress("Extracting ffmpeg...")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        bin_dir = None
        for root, dirs, files in os.walk(extract_dir):
            if "ffmpeg.exe" in files:
                bin_dir = root
                break

        if not bin_dir:
            shutil.rmtree(extract_dir, ignore_errors=True)
            return False, "ffmpeg.exe not found in archive"

        os.makedirs(self.LOCAL_BIN_DIR, exist_ok=True)
        shutil.copy(os.path.join(bin_dir, "ffmpeg.exe"), os.path.join(self.LOCAL_BIN_DIR, "ffmpeg.exe"))
        ffprobe = os.path.join(bin_dir, "ffprobe.exe")
        if os.path.exists(ffprobe):
            shutil.copy(ffprobe, os.path.join(self.LOCAL_BIN_DIR, "ffprobe.exe"))

        shutil.rmtree(extract_dir, ignore_errors=True)
        self._ensure_local_bin_on_path()
        return True, self.LOCAL_BIN_DIR

    def _install_ffmpeg_windows(self, on_progress: Optional[Callable] = None) -> Tuple[bool, str]:
        # Already installed locally?
        ok, ver = self.check_ffmpeg()
        if ok:
            if on_progress:
                on_progress(f"ffmpeg already available: {ver}")
            return True, ver

        # 1) Package managers (more reliable in restricted networks)
        if self._try_winget(on_progress):
            ok, ver = self.check_ffmpeg()
            if ok:
                if on_progress:
                    on_progress("ffmpeg installed via winget")
                return True, ver

        if self._try_choco(on_progress):
            ok, ver = self.check_ffmpeg()
            if ok:
                if on_progress:
                    on_progress("ffmpeg installed via chocolatey")
                return True, ver

        # 2) Direct download with mirrors + retries
        import tempfile

        tmp_path = os.path.join(tempfile.gettempdir(), "ffmpeg_xtrack_download.zip")
        last_err = "Download failed"

        for i, url in enumerate(self.FFMPEG_URLS_WINDOWS, 1):
            if on_progress:
                on_progress(f"Trying download source {i}/{len(self.FFMPEG_URLS_WINDOWS)}...")
                # Don't spam full URL if mirror is long; show host
                try:
                    host = url.split("/")[2]
                    on_progress(f"Source: {host}")
                except Exception:
                    pass

            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            success = self._download_file(url, tmp_path, on_progress, retries=2)
            if not success:
                last_err = f"Failed: {url[:80]}"
                continue

            try:
                ok, dest = self._extract_and_install_zip(tmp_path, on_progress)
                if ok:
                    if on_progress:
                        on_progress(f"ffmpeg installed to {dest}")
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    return True, dest
                last_err = dest
            except Exception as e:
                last_err = str(e)
                if on_progress:
                    on_progress(f"Extract error: {e}")

        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        tip = (
            "所有下载源均失败。可手动安装：\n"
            "1) winget install Gyan.FFmpeg\n"
            "2) 或从 https://www.gyan.dev/ffmpeg/builds/ 下载 zip，\n"
            f"   将整个文件夹放到 resources/ 目录（如 {resource_dir()}\\ffmpeg-x.y.z），\n"
            f"   或把 ffmpeg.exe 放到 {self.LOCAL_BIN_DIR}"
        )
        if on_progress:
            on_progress(tip)
        return False, tip

    def _install_ffmpeg_linux(self, on_progress: Optional[Callable] = None) -> Tuple[bool, str]:
        if on_progress:
            on_progress("Installing ffmpeg via package manager...")

        cmds = [
            ["sudo", "apt", "install", "-y", "ffmpeg"],
            ["sudo", "dnf", "install", "-y", "ffmpeg"],
            ["sudo", "yum", "install", "-y", "ffmpeg"],
        ]

        for cmd in cmds:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    if on_progress:
                        on_progress("ffmpeg installed successfully")
                    return True, "installed"
            except Exception:
                continue

        return False, "Package manager installation failed. Try: sudo apt install ffmpeg"

    def _install_ffmpeg_macos(self, on_progress: Optional[Callable] = None) -> Tuple[bool, str]:
        if on_progress:
            on_progress("Installing ffmpeg via Homebrew...")

        try:
            result = subprocess.run(
                ["brew", "install", "ffmpeg"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                if on_progress:
                    on_progress("ffmpeg installed successfully")
                return True, "installed"
        except Exception:
            pass

        return False, "Homebrew installation failed. Try: brew install ffmpeg"

    def get_missing_dependencies(self) -> dict:
        missing = {}

        gdl_ok, _ = self.check_gallery_dl()
        if not gdl_ok:
            missing["gallery-dl"] = "Download media from websites"

        ffmpeg_ok, _ = self.check_ffmpeg()
        if not ffmpeg_ok:
            missing["ffmpeg"] = "Video/audio processing (for watermark)"

        return missing


def check_all_dependencies() -> Tuple[dict, dict]:
    installer = DependencyInstaller()

    gallery_dl_ok, gallery_dl_ver = installer.check_gallery_dl()
    ffmpeg_ok, ffmpeg_ver = installer.check_ffmpeg()

    status = {
        "gallery-dl": {"installed": gallery_dl_ok, "version": gallery_dl_ver},
        "ffmpeg": {"installed": ffmpeg_ok, "version": ffmpeg_ver},
    }

    missing = installer.get_missing_dependencies()

    return status, missing
