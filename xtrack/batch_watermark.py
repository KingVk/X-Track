"""Batch watermark a folder of images and videos with ffmpeg.

Still images get one position and a constant opacity. Fade and timed
position changes apply to video only: a still frame has no timeline, and a
fade-in at t=0 would hide the mark.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

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
)

ProgressCb = Callable[[int, int, str, str, str], None]

_POSITIONS = ("top-left", "top-right", "bottom-right", "bottom-left", "center")
_CORNERS = ("top-left", "top-right", "bottom-right", "bottom-left")


@dataclass
class BatchJob:
    source_dir: str
    include_subdirs: bool = True
    kind: str = "text"  # text | image
    text: str = ""
    text_color: str = "white"
    font_path: str = ""  # empty = auto Douyin; same as main X-Track watermark config
    outline_color: str = "black"
    outline_width: int = 3
    image_path: str = ""
    scale_percent: int = 8
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
    """Escape commas so ffmpeg's filtergraph splitter leaves the expression intact."""
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


def _pad_expr(kind: str) -> str:
    fw, fh, _, _ = _dims(kind)
    return f"max(4,min({fw},{fh})/100)"


def _fixed_xy(kind: str, position: str) -> Tuple[str, str]:
    fw, fh, mw, mh = _dims(kind)
    pad = _pad_expr(kind)
    position = position if position in _POSITIONS else "bottom-right"
    table = {
        "top-left": (pad, pad),
        "top-right": (f"{fw}-{mw}-({pad})", pad),
        "bottom-left": (pad, f"{fh}-{mh}-({pad})"),
        "bottom-right": (f"{fw}-{mw}-({pad})", f"{fh}-{mh}-({pad})"),
        "center": (f"({fw}-{mw})/2", f"({fh}-{mh})/2"),
    }
    return table[position]


def _cycle_expr(values: Sequence[str], refresh: float) -> str:
    step = max(0.5, float(refresh))
    span = step * 4
    stamp = f"mod(t,{span:.3f})"
    expr = values[3]
    for i in range(2, -1, -1):
        expr = f"if(lt({stamp},{(i + 1) * step:.3f}),{values[i]},{expr})"
    return expr


def _placement_xy(kind: str, job: BatchJob, path: str, is_video: bool) -> Tuple[str, str]:
    """Return comma-escaped x/y expressions (no surrounding quotes)."""
    if job.placement == "fixed" or (job.placement == "corners" and not is_video):
        position = job.fixed_position if job.placement == "fixed" else _hash_corner(path)
        x, y = _fixed_xy(kind, position)
        return _esc(x), _esc(y)

    if job.placement == "corners":
        xs, ys = [], []
        for pos in _CORNERS:
            x, y = _fixed_xy(kind, pos)
            xs.append(x)
            ys.append(y)
        return _esc(_cycle_expr(xs, job.refresh_sec)), _esc(_cycle_expr(ys, job.refresh_sec))

    fw, fh, mw, mh = _dims(kind)
    pad = _pad_expr(kind)
    span_x = f"({fw}-{mw}-2*({pad}))"
    span_y = f"({fh}-{mh}-2*({pad}))"
    if is_video:
        step = max(0.5, float(job.refresh_sec))
        x = f"{pad}+{span_x}*random(floor(t/{step:.3f})*2)"
        y = f"{pad}+{span_y}*random(floor(t/{step:.3f})*2+1)"
    else:
        ux, uy = _hash_units(path)
        x = f"{pad}+{span_x}*{ux:.4f}"
        y = f"{pad}+{span_y}*{uy:.4f}"
    return _esc(x), _esc(y)


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


def _text_filter(job: BatchJob, path: str, is_video: bool, font: str) -> str:
    ratio = max(1, min(50, int(job.scale_percent)))
    # Font size = long-side * ratio% so a short label still reads as that share of the frame.
    fontsize = _esc(f"max(16,max(w,h)*{ratio}/100)")
    x, y = _placement_xy("text", job, path, is_video)
    color = (job.text_color or "white").strip() or "white"
    outline = (job.outline_color or "black").strip() or "black"
    alpha = _alpha_expr(job, is_video)
    border = max(0, min(12, int(job.outline_width)))
    return (
        f"drawtext=fontfile='{_escape_fontfile(font)}':text='{_escape_drawtext(job.text)}':"
        f"fontsize='{fontsize}':fontcolor={color}:borderw={border}:bordercolor={outline}:"
        f"alpha='{alpha}':x='{x}':y='{y}'"
    )


def _image_filter(job: BatchJob, path: str, is_video: bool, looped: bool) -> str:
    ratio = max(1, min(50, int(job.scale_percent)))
    size = _esc(f"max(rw,rh)*{ratio}/100")
    x, y = _placement_xy("overlay", job, path, is_video)
    opacity = max(0.02, min(1.0, float(job.opacity)))
    fade = max(0.0, float(job.fade_sec))
    if is_video and fade >= 0.05:
        tone = _geq_fade(job)
    else:
        tone = "" if opacity >= 0.999 else f",colorchannelmixer=aa={opacity:.3f}"
    shortest = ":shortest=1" if looped else ""
    return (
        f"[1:v][0:v]scale2ref=w='{size}':h=-1:flags=lanczos[wm][base];"
        f"[wm]setsar=1,format=rgba{tone}[mk];"
        f"[base][mk]overlay=x='{x}':y='{y}'{shortest}[vout]"
    )


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


def _image_encode(ext: str) -> List[str]:
    if ext in (".jpg", ".jpeg"):
        return ["-q:v", "3"]
    if ext == ".webp":
        return ["-c:v", "libwebp", "-q:v", "90"]
    return []


def _video_encode(ext: str, use_gpu: bool, accel: dict, audio: str) -> List[str]:
    if use_gpu and accel.get("mode") == "gpu" and ext in H264_VIDEO_EXTS:
        args = list(accel.get("args") or [])
    else:
        args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
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
    if len(text) > 280:
        text = text[-280:]
    return text


def _run_ffmpeg(cmd: List[str], cancel: threading.Event) -> Tuple[str, str]:
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
    while proc.poll() is None:
        if cancel.is_set():
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
            if not find_douyin_font(job.font_path):
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

        font = find_douyin_font(job.font_path) if job.kind == "text" else ""
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
        for use_gpu, audio in attempts:
            if cancel.is_set():
                return "cancelled", ""
            cmd = self._command(job, src, dest, font, is_video, use_gpu, accel, audio)
            status, detail = _run_ffmpeg(cmd, cancel)
            if status == "ok" and os.path.isfile(dest) and os.path.getsize(dest) > 32:
                return "ok", ""
            if status == "cancelled":
                return "cancelled", ""
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
            cmd.extend(["-i", src, "-vf", _text_filter(job, src, is_video, font)])
            if is_video:
                cmd.extend(["-map", "0:v:0", "-map", "0:a?"])
                cmd.extend(_video_encode(ext, use_gpu, accel, audio))
            else:
                cmd.extend(_image_encode(ext))
                cmd.extend(["-frames:v", "1"])
            cmd.append(dest)
            return cmd

        fade = max(0.0, float(job.fade_sec))
        looped = is_video and fade >= 0.05
        cmd.extend(["-i", src])
        if looped:
            cmd.extend(["-framerate", "15", "-loop", "1"])
        cmd.extend(["-i", job.image_path, "-filter_complex", _image_filter(job, src, is_video, looped)])
        cmd.extend(["-map", "[vout]"])
        if is_video:
            cmd.extend(["-map", "0:a?"])
            cmd.extend(_video_encode(ext, use_gpu, accel, audio))
        else:
            cmd.extend(_image_encode(ext))
            cmd.extend(["-frames:v", "1"])
        cmd.append(dest)
        return cmd
