import os
import re
import subprocess
from typing import Callable, Dict, List, Optional, Tuple

from .installer import DependencyInstaller
from .paths import data_dir, is_frozen, project_root, resource_dir


POSITION_COORDS = {
    "top-left": "pad:pad",
    "top-right": "(W-w-pad):pad",
    "bottom-left": "pad:(H-h-pad)",
    "bottom-right": "(W-w-pad):(H-h-pad)",
    "center": "(W-w)/2:(H-h)/2",
}

TEXT_POSITIONS = {
    "top-left": "x=pad:y=pad",
    "top-right": "x=w-tw-pad:y=pad",
    "bottom-left": "x=pad:y=h-th-pad",
    "bottom-right": "x=w-tw-pad:y=h-th-pad",
    "center": "x=(w-tw)/2:y=(h-th)/2",
}

PAD = 10
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif")
VIDEO_EXTS = (".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v")
H264_VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".avi", ".m4v")

_DOUYIN_BASENAMES = (
    "DouyinMeihao.otf",
    "DouyinMeihao.ttf",
    "DouyinSans.otf",
    "DouyinSans.ttf",
    "DouyinSansBold.ttf",
    "DouyinSansBold.otf",
    "抖音美好体.otf",
    "抖音美好体.ttf",
)

_GPU_ENCODERS = (
    {
        "name": "h264_nvenc",
        "label": "NVIDIA NVENC",
        "args": ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "23", "-b:v", "0"],
    },
    {
        "name": "h264_amf",
        "label": "AMD AMF",
        "args": ["-c:v", "h264_amf", "-quality", "balanced", "-rc", "cqp", "-qp_i", "23", "-qp_p", "23"],
    },
    {
        "name": "h264_qsv",
        "label": "Intel QSV",
        "args": ["-c:v", "h264_qsv", "-global_quality", "23"],
    },
)

_CPU_VIDEO_ARGS = ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]


DEFAULT_WATERMARK_NAME = "default_watermark.png"
DEFAULT_WATERMARK_TEXT = "X-Track水印"


def default_watermark_path() -> str:
    """Bundled PNG first; writable fallback under data/ for regeneration."""
    bundled = os.path.join(resource_dir(), DEFAULT_WATERMARK_NAME)
    if os.path.isfile(bundled) and os.path.getsize(bundled) > 0:
        return bundled
    return os.path.join(data_dir(), DEFAULT_WATERMARK_NAME)


def ensure_default_watermark_png(text: str = DEFAULT_WATERMARK_TEXT, *, force: bool = False) -> str:
    """Create a transparent PNG watermark with the given text using ffmpeg + Douyin font."""
    bundled = os.path.join(resource_dir(), DEFAULT_WATERMARK_NAME)
    if not force and os.path.isfile(bundled) and os.path.getsize(bundled) > 0:
        return bundled

    # Never write into read-only PyInstaller _MEIPASS
    out = os.path.join(data_dir(), DEFAULT_WATERMARK_NAME) if is_frozen() else bundled
    if not is_frozen():
        parent = os.path.dirname(bundled)
        if parent and not os.access(parent, os.W_OK):
            out = os.path.join(data_dir(), DEFAULT_WATERMARK_NAME)

    if not force and os.path.isfile(out) and os.path.getsize(out) > 0:
        return out

    font = find_douyin_font()
    if not font:
        raise FileNotFoundError("Douyin font not found; place DouyinMeihao.otf in resources/fonts")

    ffmpeg = DependencyInstaller.find_ffmpeg_path() or "ffmpeg"
    escaped_text = _escape_drawtext(text)
    font_esc = _escape_fontfile(font)
    # Transparent canvas + white text + black outline; SAR=1 avoids later squash
    vf = (
        f"drawtext=fontfile='{font_esc}':text='{escaped_text}':"
        f"fontsize=64:fontcolor=white:borderw=3:bordercolor=black:"
        f"x=(w-tw)/2:y=(h-th)/2,setsar=1,format=rgba"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=black@0.0:s=640x160,format=rgba",
        "-vf",
        vf,
        "-frames:v",
        "1",
        out,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.isfile(out):
        raise RuntimeError(f"Failed to create default watermark: {proc.stderr or proc.stdout}")
    return out


def find_douyin_font(explicit: str = "") -> str:
    """Resolve Douyin font path: explicit → ASCII copy in fonts/ → project → Windows Fonts."""
    if explicit and os.path.isfile(explicit):
        return os.path.abspath(explicit)

    root = project_root()
    res = resource_dir()
    # Ensure ASCII copy exists so ffmpeg can load CJK glyphs
    try:
        _ensure_ascii_font_copy()
    except OSError:
        pass

    search_dirs = [
        os.path.join(res, "fonts"),
        os.path.join(data_dir(), "fonts"),
        res,
        root,
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
    ]
    for d in search_dirs:
        if not d or not os.path.isdir(d):
            continue
        # Prefer ASCII basenames first
        for name in _DOUYIN_BASENAMES:
            if any(ord(c) > 127 for c in name):
                continue
            path = os.path.join(d, name)
            if os.path.isfile(path):
                return os.path.abspath(path)
        for name in _DOUYIN_BASENAMES:
            path = os.path.join(d, name)
            if os.path.isfile(path):
                return os.path.abspath(path)
        try:
            ascii_hit = ""
            cjk_hit = ""
            for fname in os.listdir(d):
                lower = fname.lower()
                if not (("douyin" in lower or "抖音" in fname) and lower.endswith((".ttf", ".otf", ".ttc"))):
                    continue
                full = os.path.abspath(os.path.join(d, fname))
                if any(ord(c) > 127 for c in fname):
                    cjk_hit = cjk_hit or full
                else:
                    ascii_hit = full
                    break
            if ascii_hit:
                return ascii_hit
            if cjk_hit:
                return cjk_hit
        except OSError:
            pass

    windir = os.environ.get("WINDIR", r"C:\Windows")
    for name in ("msyhbd.ttc", "msyh.ttc", "simhei.ttf"):
        path = os.path.join(windir, "Fonts", name)
        if os.path.isfile(path):
            return os.path.abspath(path)
    return ""


def _ensure_ascii_font_copy() -> str:
    """Copy 抖音美好体.otf → resources/fonts/DouyinMeihao.otf for ffmpeg-safe paths."""
    # Prefer existing bundled ASCII font (frozen-safe)
    bundled = os.path.join(resource_dir(), "fonts", "DouyinMeihao.otf")
    if os.path.isfile(bundled) and os.path.getsize(bundled) > 1000:
        return bundled

    fonts_dir = os.path.join(data_dir() if is_frozen() else resource_dir(), "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    dst = os.path.join(fonts_dir, "DouyinMeihao.otf")
    if os.path.isfile(dst) and os.path.getsize(dst) > 1000:
        return dst
    import shutil

    for base in (resource_dir(), project_root()):
        for name in ("抖音美好体.otf", "抖音美好体.ttf"):
            src = os.path.join(base, name)
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, dst)
                    return dst
                except OSError:
                    continue
    return dst


def _escape_drawtext(text: str) -> str:
    # ffmpeg drawtext escaping
    out = text.replace("\\", "\\\\")
    out = out.replace(":", "\\:")
    out = out.replace("'", "\\'")
    out = out.replace("%", "\\%")
    out = out.replace("\n", "\\n")
    return out


def _escape_fontfile(path: str) -> str:
    # filter graph path: use forward slashes, escape drive colon
    p = os.path.abspath(path).replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", p):
        p = p[0] + "\\:" + p[2:]
    return p.replace("'", "\\'")


class WatermarkProcessor:
    def __init__(self):
        self.ffmpeg_cmd = self._find_ffmpeg()
        self._installed = None
        self._accel: Optional[Dict] = None

    def _find_ffmpeg(self) -> str:
        return DependencyInstaller.find_ffmpeg_path() or "ffmpeg"

    def is_installed(self) -> Tuple[bool, str]:
        if self._installed is not None:
            return self._installed

        try:
            result = subprocess.run(
                [self.ffmpeg_cmd, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self._installed = True, self.ffmpeg_cmd
            else:
                self._installed = False, "ffmpeg not working"
        except Exception as e:
            self._installed = False, str(e)

        return self._installed

    def get_acceleration_info(self) -> Dict[str, str]:
        accel = self._detect_acceleration()
        return {"mode": accel["mode"], "label": accel["label"]}

    def _detect_acceleration(self) -> Dict:
        if self._accel is not None:
            return self._accel

        listed = self._listed_encoders()
        for enc in _GPU_ENCODERS:
            if enc["name"] not in listed:
                continue
            if self._probe_encoder(enc["name"]):
                self._accel = {
                    "mode": "gpu",
                    "label": enc["label"],
                    "encoder": enc["name"],
                    "args": list(enc["args"]),
                }
                return self._accel

        self._accel = {
            "mode": "cpu",
            "label": "CPU (libx264)",
            "encoder": "libx264",
            "args": list(_CPU_VIDEO_ARGS),
        }
        return self._accel

    def _listed_encoders(self) -> set:
        try:
            result = subprocess.run(
                [self.ffmpeg_cmd, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            text = (result.stdout or "") + (result.stderr or "")
            return {line.split()[1] for line in text.splitlines() if line.startswith(" V")}
        except Exception:
            return set()

    def _probe_encoder(self, encoder: str) -> bool:
        try:
            result = subprocess.run(
                [
                    self.ffmpeg_cmd,
                    "-hide_banner",
                    "-loglevel", "error",
                    "-f", "lavfi",
                    "-i", "color=c=black:s=256x256:d=0.2",
                    "-frames:v", "1",
                    "-c:v", encoder,
                    "-f", "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_position_overlay(self, position: str) -> str:
        position_str = POSITION_COORDS.get(position, POSITION_COORDS["bottom-right"])
        return position_str.replace("pad", str(PAD))

    def _probe_wh(self, path: str) -> Tuple[int, int]:
        """Return (width, height) of a media file; (0, 0) on failure."""
        # Fast path for PNG IHDR
        try:
            with open(path, "rb") as f:
                sig = f.read(24)
            if sig[:8] == b"\x89PNG\r\n\x1a\n" and sig[12:16] == b"IHDR":
                w = int.from_bytes(sig[16:20], "big")
                h = int.from_bytes(sig[20:24], "big")
                if w > 0 and h > 0:
                    return w, h
        except OSError:
            pass
        try:
            result = subprocess.run(
                [
                    self.ffmpeg_cmd,
                    "-hide_banner",
                    "-i",
                    path,
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            blob = (result.stderr or "") + (result.stdout or "")
            m = re.search(r"Video:.*?\s(\d{2,5})x(\d{2,5})\b", blob)
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception:
            pass
        return 0, 0

    def get_filter_complex(
        self,
        position: str,
        scale_ratio: int,
        adaptive: bool = True,
        main_w: int = 0,
        main_h: int = 0,
        wm_w: int = 0,
        wm_h: int = 0,
    ) -> str:
        """Overlay PNG watermark without distorting aspect ratio.

        ``scale_ratio`` = watermark **width** as percent of the main frame's
        shorter side (adaptive) or of the main width (non-adaptive).
        """
        overlay = self.get_position_overlay(position)
        ratio = max(1, min(50, int(scale_ratio)))

        if main_w > 0 and main_h > 0:
            base = min(main_w, main_h) if adaptive else main_w
            if wm_w > 0 and wm_h > 0:
                aspect = wm_w / float(wm_h)
                if aspect >= 1.6:
                    # Wide banner (e.g. text PNG): size by height so glyphs stay readable
                    # ratio 15 → ~ height 15/3.2 % of short side ≈ 4.7%
                    target_h = max(10, int(base * ratio / 320))
                    target_w = max(8, int(round(target_h * aspect)))
                else:
                    # Square/tall logo: size by width = ratio% of short side
                    target_w = max(8, int(base * ratio / 100))
                    target_h = max(1, int(round(target_w / aspect)))
                scale = (
                    f"scale={target_w}:{target_h}:flags=lanczos:"
                    f"force_original_aspect_ratio=disable"
                )
            else:
                target_w = max(8, int(base * ratio / 100))
                scale = f"scale={target_w}:-1:flags=lanczos"
            return (
                f"[1:v]{scale},setsar=1,format=rgba[wm];"
                f"[0:v][wm]overlay={overlay}"
            )

        # Fallback: ffmpeg scale with reference size (rw/rh); scale2ref is deprecated on ffmpeg 7+
        if adaptive:
            size_expr = f"min(rw\\,rh)*{ratio}/100"
        else:
            size_expr = f"rw*{ratio}/100"
        return (
            f"[1:v][0:v]scale=w='{size_expr}':h=-1:flags=lanczos[wm][base];"
            f"[wm]setsar=1,format=rgba[wm2];"
            f"[base][wm2]overlay={overlay}"
        )

    def get_text_filter(
        self,
        text: str,
        position: str,
        scale_ratio: int,
        font_path: str,
        text_color: str = "white",
        outline_color: str = "black",
        outline_width: int = 3,
    ) -> str:
        """drawtext with outline.

        UI ``scale_ratio`` matches image mode visually: target text *block*
        width ≈ scale% of the shorter side (font size derived from glyph count).
        """
        ratio = max(1, min(50, int(scale_ratio)))
        # Approximate CJK/latin mix advance width ≈ 0.95 * fontsize per char
        glyphs = max(4, len(text.strip()) or 4)
        # fontsize so (glyphs * 0.95 * fs) ≈ short * ratio/100
        # → fs ≈ short * ratio / (100 * glyphs * 0.95)
        denom = max(1.0, glyphs * 0.95)
        fontsize = f"min(w\\,h)*{ratio}/({100 * denom:.2f})"
        pos = TEXT_POSITIONS.get(position, TEXT_POSITIONS["bottom-right"]).replace("pad", str(PAD))
        escaped = _escape_drawtext(text)
        font_esc = _escape_fontfile(font_path)
        border = max(1, int(outline_width))
        return (
            f"drawtext=fontfile='{font_esc}':text='{escaped}':"
            f"fontsize='{fontsize}':fontcolor={text_color}:"
            f"borderw={border}:bordercolor={outline_color}:"
            f"{pos}"
        )

    def _collect_media_files(self, root_dir: str, skip_path: str = "") -> List[str]:
        skip_norm = os.path.normcase(os.path.abspath(skip_path)) if skip_path else ""
        files = []
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                if name.startswith(("_xtrack", "_gdl_ui", "_wm_")):
                    continue
                lower = name.lower()
                if lower.endswith(IMAGE_EXTS) or lower.endswith(VIDEO_EXTS):
                    path = os.path.join(dirpath, name)
                    if skip_norm and os.path.normcase(os.path.abspath(path)) == skip_norm:
                        continue
                    files.append(path)
        return files

    def _build_image_cmd(
        self,
        input_path: str,
        watermark_path: str,
        output_path: str,
        filter_complex: str,
        use_gpu: bool,
    ) -> List[str]:
        ext = os.path.splitext(input_path)[1].lower()
        is_video = ext in VIDEO_EXTS
        accel = self._detect_acceleration()

        cmd = [self.ffmpeg_cmd, "-y", "-hide_banner", "-loglevel", "error"]
        if is_video:
            cmd.extend(["-hwaccel", "auto"])
        cmd.extend(["-i", input_path, "-i", watermark_path, "-filter_complex", filter_complex])
        if is_video:
            if use_gpu and accel["mode"] == "gpu" and ext in H264_VIDEO_EXTS:
                cmd.extend(accel["args"])
            else:
                cmd.extend(_CPU_VIDEO_ARGS)
            cmd.extend(["-codec:a", "copy"])
        cmd.append(output_path)
        return cmd

    def _build_text_cmd(
        self,
        input_path: str,
        output_path: str,
        vf: str,
        use_gpu: bool,
    ) -> List[str]:
        ext = os.path.splitext(input_path)[1].lower()
        is_video = ext in VIDEO_EXTS
        accel = self._detect_acceleration()

        cmd = [self.ffmpeg_cmd, "-y", "-hide_banner", "-loglevel", "error"]
        if is_video:
            cmd.extend(["-hwaccel", "auto"])
        cmd.extend(["-i", input_path, "-vf", vf])
        if is_video:
            if use_gpu and accel["mode"] == "gpu" and ext in H264_VIDEO_EXTS:
                cmd.extend(accel["args"])
            else:
                cmd.extend(_CPU_VIDEO_ARGS)
            cmd.extend(["-codec:a", "copy"])
        cmd.append(output_path)
        return cmd

    def apply_watermark(
        self,
        image_dir: str,
        position: str,
        scale_ratio: int = 15,
        adaptive: bool = True,
        mode: str = "image",
        watermark_path: str = "",
        text: str = "",
        font_path: str = "",
        text_color: str = "white",
        outline_color: str = "black",
        outline_width: int = 3,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[bool, str]:
        installed, msg = self.is_installed()
        if not installed:
            return False, f"ffmpeg not available: {msg}"

        if not os.path.isdir(image_dir):
            return False, f"Image directory not found: {image_dir}"

        mode = (mode or "image").lower()
        if mode == "text":
            text = (text or "").strip()
            if not text:
                return False, "Watermark text is empty"
            resolved_font = find_douyin_font(font_path)
            if not resolved_font:
                return False, "Douyin font not found (place 抖音美好体.otf in app folder)"
            skip = ""
            filter_or_vf = self.get_text_filter(
                text, position, scale_ratio, resolved_font, text_color, outline_color, outline_width
            )
        else:
            if not watermark_path or not os.path.exists(watermark_path):
                return False, f"Watermark image not found: {watermark_path}"
            skip = watermark_path
            filter_or_vf = ""  # built per-file with probed size

        media_files = self._collect_media_files(image_dir, skip_path=skip)
        if not media_files:
            return True, "No images found to watermark"

        accel = self._detect_acceleration()
        total = len(media_files)
        success_count = 0

        if on_progress:
            on_progress(0, total, f"Accel: {accel['label']}")

        for i, input_path in enumerate(media_files):
            filename = os.path.basename(input_path)
            output_path = input_path + ".wm_tmp" + os.path.splitext(input_path)[1]
            ext = os.path.splitext(input_path)[1].lower()
            try_gpu = accel["mode"] == "gpu" and ext in H264_VIDEO_EXTS

            if mode != "text":
                mw, mh = self._probe_wh(input_path)
                ww, wh = self._probe_wh(watermark_path)
                filter_or_vf = self.get_filter_complex(
                    position, scale_ratio, adaptive, main_w=mw, main_h=mh, wm_w=ww, wm_h=wh
                )

            ok = self._run_one(
                input_path, output_path, mode, watermark_path, filter_or_vf, use_gpu=try_gpu
            )
            if not ok and try_gpu:
                ok = self._run_one(
                    input_path, output_path, mode, watermark_path, filter_or_vf, use_gpu=False
                )

            if not ok:
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                if on_progress:
                    on_progress(i + 1, total, f"Error: {filename}")
                continue

            try:
                os.replace(output_path, input_path)
                success_count += 1
                if on_progress:
                    on_progress(i + 1, total, f"Processed: {filename}")
            except OSError as e:
                if on_progress:
                    on_progress(i + 1, total, f"Error: {filename} - {e}")

        return True, f"Watermark applied to {success_count}/{total} files ({accel['label']})"

    def apply_to_file(
        self,
        input_path: str,
        *,
        position: str = "bottom-right",
        scale_ratio: int = 15,
        adaptive: bool = True,
        mode: str = "image",
        watermark_path: str = "",
        text: str = "",
        font_path: str = "",
        text_color: str = "white",
        outline_color: str = "black",
        outline_width: int = 3,
        **_extra,
    ) -> Tuple[bool, str]:
        """Apply watermark to a single media file in place."""
        installed, msg = self.is_installed()
        if not installed:
            return False, f"ffmpeg not available: {msg}"
        if not input_path or not os.path.isfile(input_path):
            return False, f"File not found: {input_path}"

        mode = (mode or "image").lower()
        if mode == "text":
            text = (text or "").strip()
            if not text:
                return False, "Watermark text is empty"
            resolved_font = find_douyin_font(font_path)
            if not resolved_font:
                return False, "Douyin font not found (place 抖音美好体.otf in app folder)"
            filter_or_vf = self.get_text_filter(
                text, position, scale_ratio, resolved_font, text_color, outline_color, outline_width
            )
            watermark_path = ""
        else:
            if not watermark_path or not os.path.exists(watermark_path):
                return False, f"Watermark image not found: {watermark_path}"
            mw, mh = self._probe_wh(input_path)
            ww, wh = self._probe_wh(watermark_path)
            filter_or_vf = self.get_filter_complex(
                position, scale_ratio, adaptive, main_w=mw, main_h=mh, wm_w=ww, wm_h=wh
            )

        accel = self._detect_acceleration()
        ext = os.path.splitext(input_path)[1].lower()
        output_path = input_path + ".wm_tmp" + ext
        try_gpu = accel["mode"] == "gpu" and ext in H264_VIDEO_EXTS

        ok = self._run_one(
            input_path, output_path, mode, watermark_path, filter_or_vf, use_gpu=try_gpu
        )
        if not ok and try_gpu:
            ok = self._run_one(
                input_path, output_path, mode, watermark_path, filter_or_vf, use_gpu=False
            )
        if not ok:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            return False, f"ffmpeg failed on {os.path.basename(input_path)}"

        try:
            os.replace(output_path, input_path)
        except OSError as e:
            return False, str(e)
        return True, f"ok ({accel['label']})"

    def _run_one(
        self,
        input_path: str,
        output_path: str,
        mode: str,
        watermark_path: str,
        filter_or_vf: str,
        use_gpu: bool,
    ) -> bool:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass

        if mode == "text":
            cmd = self._build_text_cmd(input_path, output_path, filter_or_vf, use_gpu)
        else:
            cmd = self._build_image_cmd(
                input_path, watermark_path, output_path, filter_or_vf, use_gpu
            )
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0 and os.path.isfile(output_path)
        except (subprocess.TimeoutExpired, OSError):
            return False
