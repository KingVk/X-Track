"""Batch watermark a folder of images and videos with ffmpeg.

Still images get one position and a constant opacity. Fade and timed
position changes apply to video only: a still frame has no timeline, and a
fade-in at t=0 would hide the mark.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .procutil import no_window_kwargs
from .installer import DependencyInstaller
from .watermark import (
    H264_VIDEO_EXTS,
    IMAGE_EXTS,
    VIDEO_EXTS,
    WatermarkProcessor,
    _escape_drawtext,
    _escape_fontfile,
    find_douyin_font,
    probe_media,
    target_video_kbps,
    video_encode_args,
)

ProgressCb = Callable[[int, int, str, str, str], None]

_POSITIONS = ("top-left", "top-right", "bottom-right", "bottom-left", "center")
_CORNERS = ("top-left", "top-right", "bottom-right", "bottom-left")

_NAMED_COLORS = frozenset(
    {
        "white",
        "black",
        "yellow",
        "red",
        "cyan",
        "gray",
        "grey",
        "green",
        "blue",
        "orange",
        "purple",
        "pink",
        "brown",
    }
)


def normalize_ffmpeg_color(raw: str, default: str = "white") -> Optional[str]:
    """Return an ffmpeg-safe color (name or 0xRRGGBB), or None if invalid."""
    text = (raw or "").strip()
    if not text:
        return default
    low = text.lower()
    if low in _NAMED_COLORS:
        return "gray" if low == "grey" else low
    hexpart = low
    if hexpart.startswith("#"):
        hexpart = hexpart[1:]
    elif hexpart.startswith("0x"):
        hexpart = hexpart[2:]
    if re.fullmatch(r"[0-9a-f]{3}", hexpart):
        hexpart = "".join(ch * 2 for ch in hexpart)
    if re.fullmatch(r"[0-9a-f]{6}", hexpart):
        return f"0x{hexpart}"
    return None


def display_color(raw: str) -> str:
    """UI-friendly form: named colors stay names, hex becomes #RRGGBB."""
    norm = normalize_ffmpeg_color(raw, "")
    if not norm:
        return (raw or "").strip()
    if norm.startswith("0x"):
        return f"#{norm[2:]}"
    return norm


@dataclass
class BatchJob:
    source_dir: str
    include_subdirs: bool = True
    kind: str = "text"  # text | image
    text: str = ""
    text_color: str = "white"
    font_path: str = ""  # empty = auto Douyin / main config
    outline_color: str = "black"
    outline_width: int = 3
    shadow_enabled: bool = False
    shadow_color: str = "black"
    image_path: str = ""
    scale_percent: int = 8
    pad_percent: float = 20.0  # margin as % of watermark width
    opacity: float = 0.8
    fade_sec: float = 0.4
    placement: str = "fixed"  # fixed | corners | random
    fixed_position: str = "bottom-right"
    refresh_sec: float = 4.0
    output_mode: str = "copy"  # overwrite | copy
    output_dir: str = ""
    ffmpeg_path: str = ""


@dataclass
class BatchResult:
    ok: int = 0
    failed: int = 0
    cancelled: bool = False
    error_key: str = ""
    files: List[str] = field(default_factory=list)


def _esc(expr: str) -> str:
    """Escape commas for ffmpeg filtergraph / expression contexts."""
    return expr.replace(",", "\\,")


def _is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS


def _is_media(name: str) -> bool:
    lower = name.lower()
    return lower.endswith(IMAGE_EXTS) or lower.endswith(VIDEO_EXTS)


def _under(path: str, root: str) -> bool:
    try:
        path_n = os.path.normcase(os.path.abspath(path))
        root_n = os.path.normcase(os.path.abspath(root))
        return os.path.commonpath([path_n, root_n]) == root_n
    except ValueError:
        return False


def paths_overlap(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return _under(a, b) or _under(b, a)


def list_media(root: str, recursive: bool, skip_file: str = "", exclude_dir: str = "") -> List[str]:
    if not root or not os.path.isdir(root):
        return []
    skip = os.path.normcase(os.path.abspath(skip_file)) if skip_file else ""
    exclude = os.path.abspath(exclude_dir) if exclude_dir else ""
    found: List[str] = []

    def take(dirpath: str, name: str) -> None:
        if name.startswith(("._xtrack", "_xtrack", "_gdl_ui", "_wm_")) or ".wm_tmp" in name:
            return
        if not _is_media(name):
            return
        path = os.path.join(dirpath, name)
        if skip and os.path.normcase(os.path.abspath(path)) == skip:
            return
        if exclude and _under(path, exclude):
            return
        try:
            if os.path.getsize(path) < 32:
                return
        except OSError:
            return
        found.append(path)

    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            if exclude and _under(dirpath, exclude):
                dirnames.clear()
                continue
            for name in filenames:
                take(dirpath, name)
    else:
        try:
            names = os.listdir(root)
        except OSError:
            return []
        for name in names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                take(root, name)
    found.sort(key=lambda p: os.path.normcase(p))
    return found


def _hash_units(path: str) -> Tuple[float, float]:
    digest = hashlib.md5(os.path.abspath(path).encode("utf-8", "replace")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF, int(digest[8:16], 16) / 0xFFFFFFFF


def _hash_corner(path: str) -> str:
    digest = hashlib.md5(os.path.abspath(path).encode("utf-8", "replace")).hexdigest()
    return _CORNERS[int(digest[:2], 16) % 4]


def _dims(kind: str) -> Tuple[str, str, str, str]:
    if kind == "text":
        return "w", "h", "tw", "th"
    return "W", "H", "w", "h"


def _pad_expr(kind: str, pad_percent: float) -> str:
    """Margin = watermark width × ratio."""
    _, _, mw, _ = _dims(kind)
    pct = max(0.0, min(200.0, float(pad_percent))) / 100.0
    return f"({mw}*{pct:.4f})"


def _fixed_xy(kind: str, position: str, pad_percent: float = 20.0) -> Tuple[str, str]:
    fw, fh, mw, mh = _dims(kind)
    pad = _pad_expr(kind, pad_percent)
    position = position if position in _POSITIONS else "bottom-right"
    # max(0, …) keeps oversized watermarks from going fully off-screen
    table = {
        "top-left": (pad, pad),
        "top-right": (f"max(0,{fw}-{mw}-{pad})", pad),
        "bottom-left": (pad, f"max(0,{fh}-{mh}-{pad})"),
        "bottom-right": (f"max(0,{fw}-{mw}-{pad})", f"max(0,{fh}-{mh}-{pad})"),
        "center": (f"max(0,({fw}-{mw})/2)", f"max(0,({fh}-{mh})/2)"),
    }
    return table[position]


def _corner_xy_expr(kind: str, pad_percent: float, refresh: float) -> Tuple[str, str]:
    """Animated x/y that cycle TL → TR → BR → BL. One overlay, no enable=."""
    fw, fh, mw, mh = _dims(kind)
    pad = _pad_expr(kind, pad_percent)
    step = max(0.5, float(refresh))
    span = step * 4
    # 0=TL 1=TR 2=BR 3=BL — right when idx in {1,2}, bottom when idx in {2,3}
    idx = f"floor(mod(t,{span:.3f})/{step:.3f})"
    span_x = f"max(0,{fw}-{mw}-2*{pad})"
    span_y = f"max(0,{fh}-{mh}-2*{pad})"
    x = f"{pad}+{span_x}*between({idx},1,2)"
    y = f"{pad}+{span_y}*between({idx},2,3)"
    return _esc(x), _esc(y)


def _random_xy(kind: str, job: BatchJob, path: str, is_video: bool) -> Tuple[str, str]:
    fw, fh, mw, mh = _dims(kind)
    pad = _pad_expr(kind, job.pad_percent)
    span_x = f"max(0,{fw}-{mw}-2*{pad})"
    span_y = f"max(0,{fh}-{mh}-2*{pad})"
    if is_video:
        step = max(0.5, float(job.refresh_sec))
        # no commas in these expressions except inside max() — escaped via quotes at use site
        x = f"{pad}+{span_x}*random(floor(t/{step:.3f})*2)"
        y = f"{pad}+{span_y}*random(floor(t/{step:.3f})*2+1)"
    else:
        ux, uy = _hash_units(path)
        x = f"{pad}+{span_x}*{ux:.4f}"
        y = f"{pad}+{span_y}*{uy:.4f}"
    return x, y


def _alpha_expr(job: BatchJob, is_video: bool) -> str:
    opacity = max(0.02, min(1.0, float(job.opacity)))
    fade = max(0.0, float(job.fade_sec))
    if not is_video or fade < 0.05:
        return f"{opacity:.3f}"
    if job.placement == "fixed":
        return _esc(f"{opacity:.3f}*if(lt(t,{fade:.3f}),t/{fade:.3f},1)")
    step = max(0.5, float(job.refresh_sec))
    fade = min(fade, step / 2.0 - 0.05)
    if fade < 0.05:
        return f"{opacity:.3f}"
    stamp = f"mod(t,{step:.3f})"
    return _esc(
        f"{opacity:.3f}*if(lt({stamp},{fade:.3f}),{stamp}/{fade:.3f},"
        f"if(gt({stamp},{step - fade:.3f}),({step:.3f}-{stamp})/{fade:.3f},1))"
    )


def _shadow_args(job: BatchJob) -> str:
    if not job.shadow_enabled:
        return ""
    color = normalize_ffmpeg_color(job.shadow_color, "black") or "black"
    return f":shadowcolor={color}@0.65:shadowx=3:shadowy=3"


def _drawtext_one(
    job: BatchJob,
    font: str,
    fontsize: str,
    x: str,
    y: str,
    alpha: str,
    enable: str = "",
) -> str:
    color = normalize_ffmpeg_color(job.text_color, "white") or "white"
    outline = normalize_ffmpeg_color(job.outline_color, "black") or "black"
    border = max(0, min(12, int(job.outline_width)))
    en = f":enable='{enable}'" if enable else ""
    return (
        f"drawtext=fontfile='{_escape_fontfile(font)}':text='{_escape_drawtext(job.text)}':"
        f"fontsize='{fontsize}':fontcolor={color}:borderw={border}:bordercolor={outline}:"
        f"alpha='{alpha}':x='{x}':y='{y}'{_shadow_args(job)}{en}"
    )


def _text_filter(job: BatchJob, path: str, is_video: bool, font: str) -> str:
    ratio = max(1, min(50, int(job.scale_percent)))
    # Font size ≈ short-side * ratio% (same visual share as image watermarks).
    # Pass raw commas into _esc once — do not pre-escape.
    fontsize = _esc(f"max(16,min(w,h)*{ratio}/100)")
    alpha = _alpha_expr(job, is_video)

    if job.placement == "corners" and is_video:
        x, y = _corner_xy_expr("text", job.pad_percent, job.refresh_sec)
        return _drawtext_one(job, font, fontsize, x, y, alpha)

    if job.placement == "random":
        x, y = _random_xy("text", job, path, is_video)
    elif job.placement == "corners":
        x, y = _fixed_xy("text", _hash_corner(path), job.pad_percent)
    else:
        x, y = _fixed_xy("text", job.fixed_position, job.pad_percent)
    return _drawtext_one(job, font, fontsize, x, y, alpha)


def _geq_fade(job: BatchJob) -> str:
    """Periodic alpha on the watermark stream. geq's clock is ``T``, not ``t``."""
    opacity = max(0.02, min(1.0, float(job.opacity)))
    fade = max(0.0, float(job.fade_sec))
    clock = "T"
    if job.placement == "fixed":
        inner = f"{opacity:.3f}*if(lt({clock},{fade:.3f}),{clock}/{fade:.3f},1)"
    else:
        step = max(0.5, float(job.refresh_sec))
        fade = min(fade, step / 2.0 - 0.05)
        if fade < 0.05:
            return f",colorchannelmixer=aa={opacity:.3f}"
        stamp = f"mod({clock},{step:.3f})"
        inner = (
            f"{opacity:.3f}*if(lt({stamp},{fade:.3f}),{stamp}/{fade:.3f},"
            f"if(gt({stamp},{step - fade:.3f}),({step:.3f}-{stamp})/{fade:.3f},1))"
        )
    pixel = _esc(f"alpha(X,Y)*({inner})")
    return (
        f",geq=r='{_esc('r(X,Y)')}':g='{_esc('g(X,Y)')}':b='{_esc('b(X,Y)')}':a='{pixel}'"
    )


def _image_filter(job: BatchJob, path: str, is_video: bool, fade_tone: bool) -> str:
    ratio = max(1, min(50, int(job.scale_percent)))
    # Match text-mode semantics: scale% ≈ glyph height on the short side.
    # Width = height * mdar; cap so the mark never exceeds the frame.
    # ffmpeg min() is binary only — nest pairwise.
    # (Old iw*R/100 made wide logos ~20px tall at 8% — easy to miss on video.)
    size_w = f"min(iw,min(ih*mdar,min(iw,ih)*{ratio}/100*mdar))"
    opacity = max(0.02, min(1.0, float(job.opacity)))
    fade = max(0.0, float(job.fade_sec))
    # Fade needs a timed watermark stream (looped still). Otherwise keep static alpha.
    if is_video and fade >= 0.05 and fade_tone:
        tone = _geq_fade(job)
    else:
        tone = "" if opacity >= 0.999 else f",colorchannelmixer=aa={opacity:.3f}"

    head = (
        f"[1:v][0:v]scale2ref=w='{size_w}':h='ow/mdar':flags=lanczos[wm][base];"
        f"[wm]format=rgba{tone}"
    )
    # Never use overlay shortest=1: without a reliable loop it truncates the
    # whole video to one still frame (~tens of KB) while ffmpeg still exits 0.
    # Looped stills are capped with -t <source duration> in _command instead.
    end_flags = "eof_action=repeat"

    if job.placement == "corners" and is_video:
        # One overlay with time-based x/y — avoids split+enable graphs that some
        # Windows ffmpeg builds reject as Invalid argument on filter_complex.
        x, y = _corner_xy_expr("overlay", job.pad_percent, job.refresh_sec)
        return (
            f"{head}[mk];"
            f"[base][mk]overlay=x='{x}':y='{y}':{end_flags}[vout]"
        )

    if job.placement == "random":
        x, y = _random_xy("overlay", job, path, is_video)
    elif job.placement == "corners":
        x, y = _fixed_xy("overlay", _hash_corner(path), job.pad_percent)
    else:
        x, y = _fixed_xy("overlay", job.fixed_position, job.pad_percent)
    return (
        f"{head}[mk];"
        f"[base][mk]overlay=x='{x}':y='{y}':{end_flags}[vout]"
    )


def resolve_font(explicit: str = "") -> str:
    """Prefer an explicit local font file; otherwise Douyin / system fallback."""
    path = (explicit or "").strip().strip('"')
    if path and os.path.isfile(path):
        return os.path.abspath(path)
    return find_douyin_font(path)


def _image_encode(ext: str) -> List[str]:
    if ext in (".jpg", ".jpeg"):
        return ["-q:v", "3"]
    if ext == ".webp":
        return ["-c:v", "libwebp", "-q:v", "90"]
    return []


def _video_encode(ext: str, use_gpu: bool, accel: dict, audio: str, target_kbps: int = 0) -> List[str]:
    encoder = "libx264"
    if use_gpu and accel.get("mode") == "gpu" and ext in H264_VIDEO_EXTS:
        encoder = str(accel.get("encoder") or "libx264")
    args = video_encode_args(encoder, target_kbps)
    if audio == "aac":
        args.extend(["-c:a", "aac", "-b:a", "160k"])
    else:
        args.extend(["-c:a", "copy"])
    if ext in (".mp4", ".mov", ".m4v"):
        args.extend(["-movflags", "+faststart"])
    return args


def _stderr_text(raw: bytes) -> str:
    text = (raw or b"").decode("utf-8", "replace").strip()
    text = " ".join(text.split())
    if len(text) > 360:
        text = text[:120] + " … " + text[-240:]
    return text


def _probe_duration(ffmpeg: str, path: str) -> float:
    """Return media duration in seconds, or 0 if unknown."""
    return float(probe_media(ffmpeg, path).get("duration") or 0.0)


def _file_digest(path: str) -> str:
    digest = hashlib.md5()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def _video_output_ok(src: str, dest: str, src_dur: float, ffmpeg: str) -> bool:
    """Reject truncated encodes that ffmpeg still reports as success (~tens of KB)."""
    if not os.path.isfile(dest):
        return False
    try:
        dest_sz = os.path.getsize(dest)
        src_sz = os.path.getsize(src)
    except OSError:
        return False
    if dest_sz < 2048:
        return False
    # Duration is the reliable signal; size alone false-positives on NVENC of easy content.
    if src_dur >= 1.0:
        dest_dur = _probe_duration(ffmpeg, dest)
        if dest_dur <= 0:
            return dest_sz >= max(80_000, int(src_sz * 0.02)) if src_sz >= 200_000 else True
        if dest_dur < max(0.4, src_dur * 0.85):
            return False
        return True
    if src_sz >= 200_000 and dest_sz < max(80_000, int(src_sz * 0.02)):
        return False
    return True


def _still_output_ok(src: str, dest: str) -> bool:
    """Stills only check size would accept untouched copies; require a real rewrite."""
    if not os.path.isfile(dest):
        return False
    try:
        if os.path.getsize(dest) < 32:
            return False
    except OSError:
        return False
    src_hash = _file_digest(src)
    dest_hash = _file_digest(dest)
    if not src_hash or not dest_hash:
        return True
    return src_hash != dest_hash


def _run_ffmpeg(cmd: List[str], cancel: threading.Event, timeout_sec: float = 0) -> Tuple[str, str]:
    """Return (status, detail). status is ok | fail | cancelled."""
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        **no_window_kwargs(),
    )
    chunks: List[bytes] = []

    def _read() -> None:
        if proc.stderr is not None:
            chunks.append(proc.stderr.read())

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()
    killed = False
    started = time.time()
    while proc.poll() is None:
        if cancel.is_set() or (timeout_sec > 0 and time.time() - started > timeout_sec):
            killed = True
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=4)
            break
        time.sleep(0.2)
    reader.join(timeout=3)
    if killed or cancel.is_set():
        return "cancelled", ""
    if proc.returncode == 0:
        return "ok", ""
    return "fail", _stderr_text(b"".join(chunks))


class BatchWatermarker:
    def __init__(self) -> None:
        self._processor = WatermarkProcessor()

    def validate(self, job: BatchJob) -> str:
        if not job.source_dir or not os.path.isdir(job.source_dir):
            return "wmtool_need_folder"
        if job.kind == "text":
            if not (job.text or "").strip():
                return "wmtool_need_text"
            if not resolve_font(job.font_path):
                return "wmtool_font_missing"
        else:
            if not job.image_path or not os.path.isfile(job.image_path):
                return "wmtool_need_image"
        if job.output_mode == "copy":
            if not (job.output_dir or "").strip():
                return "wmtool_need_out"
            if paths_overlap(job.source_dir, job.output_dir):
                return "wmtool_overlap"
        installed, _msg = self._processor.is_installed()
        if not installed:
            return "wmtool_ffmpeg_bad"
        return ""

    def _prepare_ffmpeg(self, job: BatchJob) -> None:
        if job.ffmpeg_path:
            DependencyInstaller.set_configured_ffmpeg_path(job.ffmpeg_path)
        self._processor.ffmpeg_cmd = self._processor._find_ffmpeg()
        self._processor._accel = None
        self._processor._installed = None

    def run(self, job: BatchJob, cancel: threading.Event, on_progress: Optional[ProgressCb] = None) -> BatchResult:
        result = BatchResult()
        self._prepare_ffmpeg(job)
        key = self.validate(job)
        if key:
            result.error_key = key
            return result

        exclude = job.output_dir if job.output_mode == "copy" else ""
        skip = job.image_path if job.kind == "image" else ""
        files = list_media(job.source_dir, job.include_subdirs, skip_file=skip, exclude_dir=exclude)
        result.files = files
        if not files:
            result.error_key = "wmtool_no_media"
            return result

        font = resolve_font(job.font_path) if job.kind == "text" else ""
        accel = self._processor._detect_acceleration()
        total = len(files)
        if on_progress:
            on_progress(0, total, "", "ready", accel.get("label") or "")

        for index, src in enumerate(files):
            if cancel.is_set():
                result.cancelled = True
                break
            name = os.path.basename(src)
            if on_progress:
                on_progress(index, total, name, "start", "")
            dest = self._dest_path(job, src)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            status, detail = self._one(job, src, dest, font, accel, cancel)
            if status == "cancelled" or cancel.is_set():
                self._cleanup(dest, job, src)
                result.cancelled = True
                break
            if status != "ok":
                self._cleanup(dest, job, src)
                result.failed += 1
                if on_progress:
                    on_progress(index + 1, total, name, "fail", detail)
                continue
            if job.output_mode == "overwrite":
                try:
                    os.replace(dest, src)
                except OSError as exc:
                    self._cleanup(dest, job, src)
                    result.failed += 1
                    if on_progress:
                        on_progress(index + 1, total, name, "fail", str(exc))
                    continue
            result.ok += 1
            if on_progress:
                on_progress(index + 1, total, name, "ok", "")
        return result

    def _dest_path(self, job: BatchJob, src: str) -> str:
        if job.output_mode == "overwrite":
            folder, name = os.path.split(src)
            return os.path.join(folder, "._xtrack_wm_" + name)
        rel = os.path.relpath(src, job.source_dir)
        return os.path.join(job.output_dir, rel)

    def _cleanup(self, dest: str, job: BatchJob, src: str) -> None:
        if not dest or os.path.normcase(dest) == os.path.normcase(src):
            return
        if os.path.isfile(dest):
            try:
                os.remove(dest)
            except OSError:
                pass

    def _one(
        self,
        job: BatchJob,
        src: str,
        dest: str,
        font: str,
        accel: dict,
        cancel: threading.Event,
    ) -> Tuple[str, str]:
        is_video = _is_video(src)
        ext = os.path.splitext(src)[1].lower()
        if os.path.isfile(dest):
            try:
                os.remove(dest)
            except OSError:
                pass

        attempts: List[Tuple[bool, str]]
        if is_video:
            gpu_ok = accel.get("mode") == "gpu" and ext in H264_VIDEO_EXTS
            attempts = []
            if gpu_ok:
                attempts.append((True, "copy"))
                attempts.append((True, "aac"))
            attempts.append((False, "copy"))
            attempts.append((False, "aac"))
        else:
            attempts = [(False, "copy")]

        last = "ffmpeg failed"
        ffmpeg = self._processor.ffmpeg_cmd or "ffmpeg"
        media = probe_media(ffmpeg, src) if is_video else {}
        src_dur = float(media.get("duration") or 0.0) if is_video else 0.0
        target_kbps = (
            target_video_kbps(
                int(media.get("video_kbps") or 0),
                int(media.get("width") or 0),
                int(media.get("height") or 0),
            )
            if is_video
            else 0
        )
        for use_gpu, audio in attempts:
            if cancel.is_set():
                return "cancelled", ""
            cmd = self._command(
                job, src, dest, font, is_video, use_gpu, accel, audio, src_dur, target_kbps
            )
            status, detail = _run_ffmpeg(cmd, cancel)
            if status == "cancelled":
                return "cancelled", ""
            if status == "ok" and os.path.isfile(dest):
                if is_video:
                    if _video_output_ok(src, dest, src_dur, ffmpeg):
                        return "ok", ""
                    detail = detail or "output too small or truncated"
                    try:
                        os.remove(dest)
                    except OSError:
                        pass
                elif _still_output_ok(src, dest):
                    return "ok", ""
                else:
                    detail = detail or "output unchanged"
                    try:
                        os.remove(dest)
                    except OSError:
                        pass
            last = detail or last
        return "fail", last

    def _command(
        self,
        job: BatchJob,
        src: str,
        dest: str,
        font: str,
        is_video: bool,
        use_gpu: bool,
        accel: dict,
        audio: str,
        src_dur: float = 0.0,
        target_kbps: int = 0,
    ) -> List[str]:
        # Always refresh ffmpeg path in case the user just configured it.
        self._processor.ffmpeg_cmd = self._processor._find_ffmpeg()
        ffmpeg = self._processor.ffmpeg_cmd or "ffmpeg"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-nostdin"]
        ext = os.path.splitext(src)[1].lower()
        if is_video:
            # Prefer hardware decode when a GPU encoder is available; filters still run on CPU.
            cmd.extend(["-hwaccel", "auto"])
        if job.kind == "text":
            vf = _text_filter(job, src, is_video, font)
            cmd.extend(["-i", src, "-filter_complex", f"[0:v]{vf}[vout]", "-map", "[vout]"])
            if is_video:
                cmd.extend(["-map", "0:a?"])
                cmd.extend(_video_encode(ext, use_gpu, accel, audio, target_kbps))
                if src_dur > 0:
                    cmd.extend(["-t", f"{src_dur:.3f}"])
            else:
                cmd.extend(_image_encode(ext))
                cmd.extend(["-frames:v", "1"])
            cmd.append(dest)
            return cmd

        fade = max(0.0, float(job.fade_sec))
        # Loop the still whenever duration is known, and cap with -t.
        # Global -shortest is unsafe: a shorter audio track would truncate the video.
        # geq fade uses the looped still's clock, so fixed / corners / random can all fade.
        loop_still = is_video and src_dur > 0
        fade_tone = loop_still and fade >= 0.05
        cmd.extend(["-i", src])
        if loop_still:
            cmd.extend(["-framerate", "15", "-loop", "1"])
        cmd.extend(
            [
                "-i",
                job.image_path,
                "-filter_complex",
                _image_filter(job, src, is_video, fade_tone),
                "-map",
                "[vout]",
            ]
        )
        if is_video:
            cmd.extend(["-map", "0:a?"])
            cmd.extend(_video_encode(ext, use_gpu, accel, audio, target_kbps))
            if src_dur > 0:
                cmd.extend(["-t", f"{src_dur:.3f}"])
        else:
            cmd.extend(_image_encode(ext))
            cmd.extend(["-frames:v", "1"])
        cmd.append(dest)
        return cmd
