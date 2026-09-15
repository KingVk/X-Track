"""
Lightweight X-Track integration test (inline watermark + parallel + resume).

Keeps date windows tight so it finishes quickly.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from xtrack.command_builder import CommandBuilder, CommandExecutor, check_gallery_dl_installed
from xtrack.config_store import AppConfig, UrlItem, WatermarkSettings
from xtrack.download_paths import download_archive_path
from xtrack.watermark import default_watermark_path, ensure_default_watermark_png
from xtrack.watermark_pipeline import InlineWatermarkPipeline


DEST = Path(r"D:/BaiduNetdiskDownload/xtrack_quicktest")
REPORT = DEST / "_xtrack_test_report.json"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def find_cookies() -> str:
    cfg = ROOT / "data" / "config.json"
    if cfg.is_file():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        c = data.get("cookies_file") or ""
        if c and os.path.isfile(c):
            return c
    for p in (
        Path(r"C:/Users/Idea Beyond/Downloads/x.com_cookies.txt"),
        ROOT / "cookies.txt",
    ):
        if p.is_file():
            return str(p)
    raise FileNotFoundError("cookies not found")


def media_files(folder: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov", ".mkv"}
    out: List[Path] = []
    if not folder.is_dir():
        return out
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and not p.name.startswith(("_xtrack", "_gdl", "_wm", ".")):
            out.append(p)
    return out


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(DEST)).replace("\\", "/")
    except ValueError:
        return str(p)


def run_batch(
    cookies: str,
    items: List[dict],
    *,
    wm_mode: str | None,
    cancel_after: float | None = None,
    keep_archive: bool = True,
) -> dict:
    if not keep_archive and DEST.exists():
        shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True, exist_ok=True)

    wm_enabled = wm_mode is not None
    png = str(default_watermark_path())
    cfg = AppConfig(
        dest_folder=str(DEST),
        cookies_file=cookies,
        write_metadata=True,
        write_info_json=False,
        sleep_min=1,
        sleep_max=2,
        sleep_request_min=2,
        sleep_request_max=3,
        sleep_429=45,
        verbose=True,
        max_parallel=3,
        watermark=WatermarkSettings(
            enabled=wm_enabled,
            mode=wm_mode or "text",
            image_path=png,
            text="X-Track水印",
            outline_width=3,
            scale_ratio=12,
            position="bottom-right",
        ),
        urls=[
            UrlItem(
                url=u["url"],
                selected=True,
                filter_date_start=u["start"],
                filter_date_end=u["end"],
                media_type=u.get("media", "image"),
            )
            for u in items
        ],
    )

    builder = CommandBuilder()
    executor = CommandExecutor()
    pipeline = InlineWatermarkPipeline()
    pipeline.reset()
    if wm_enabled:
        pipeline.configure(
            enabled=True,
            settings={
                "mode": wm_mode,
                "watermark_path": png,
                "text": "X-Track水印",
                "outline_width": 3,
                "scale_ratio": 12,
                "position": "bottom-right",
                "adaptive": True,
            },
            on_log=log,
            suspend=executor.suspend_all,
            resume=executor.resume_all,
        )

    results: Dict[str, int] = {}
    lock = threading.Lock()
    stop = {"v": False}

    def on_output(line: str) -> None:
        if any(k in line for k in ("# ", "Downloaded", "error", "Error", "429", "Watermark")):
            log(line[:220])
        elif line.strip().lower().endswith((".jpg", ".jpeg", ".png", ".mp4", ".webp")):
            log(line[:220])
        pipeline.handle_output_line(line)

    def job(idx: int, item: UrlItem) -> None:
        if stop["v"]:
            with lock:
                results[item.url] = -1
            return
        cmd = builder.build(item.url, cfg, "", url_item=item)
        log(f"CMD[{idx}] {item.url} type={item.media_type} {item.filter_date_start}..{item.filter_date_end}")

        def on_complete(code: int, url=item.url) -> None:
            with lock:
                results[url] = code
            log(f"DONE {url} code={code}")

        executor.run(cmd, on_output, on_complete)

    if cancel_after:
        def killer():
            time.sleep(cancel_after)
            log(">>> STOP (simulate UI Stop)")
            stop["v"] = True
            executor.cancel()

        threading.Thread(target=killer, daemon=True).start()

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=min(3, len(cfg.urls))) as pool:
        futs = [pool.submit(job, i, u) for i, u in enumerate(cfg.urls)]
        for f in as_completed(futs):
            f.result()

    return {
        "seconds": round(time.time() - t0, 1),
        "codes": results,
        "media": len(media_files(DEST)),
        "wm_done": [rel(Path(p)) for p in pipeline.done_files],
        "wm_mode": wm_mode,
        "archive": download_archive_path(str(DEST)),
        "stopped": stop["v"],
    }


def main() -> int:
    ok, path = check_gallery_dl_installed()
    if not ok:
        log("gallery-dl missing")
        return 1
    cookies = find_cookies()
    ensure_default_watermark_png("X-Track水印")
    log(f"gallery-dl={path}")
    log(f"cookies={cookies}")
    log(f"wm_png={default_watermark_path()}")

    if DEST.exists():
        shutil.rmtree(DEST, ignore_errors=True)

    report: dict = {"started_at": datetime.now().isoformat(), "dest": str(DEST), "phases": {}}

    # Tiny windows (~few days) to keep runtime short
    parallel_items = [
        {
            "url": "https://x.com/HIDEO_KOJIMA_EN",
            "start": "2026-09-10",
            "end": "2026-09-14",
            "media": "image",
        },
        {
            "url": "https://x.com/Kojima_Hideo",
            "start": "2026-09-08",
            "end": "2026-09-14",
            "media": "all",
        },
        {
            "url": "https://x.com/Lisa_West_Pix",
            "start": "2026-09-08",
            "end": "2026-09-14",
            "media": "image",
        },
    ]

    log("=" * 50)
    log("A: parallel + different filters + TEXT watermark inline")
    phase_a = run_batch(cookies, parallel_items, wm_mode="text", keep_archive=False)
    report["phases"]["A_parallel_text_wm"] = phase_a
    text_files = list(phase_a["wm_done"])
    after_a = {str(p) for p in media_files(DEST)}

    log("=" * 50)
    log("B: continue download (archive skip)")
    phase_b = run_batch(cookies, parallel_items, wm_mode="text", keep_archive=True)
    after_b = {str(p) for p in media_files(DEST)}
    phase_b["new_files"] = len(after_b - after_a)
    report["phases"]["B_continue"] = phase_b

    log("=" * 50)
    log("C: stop then resume (short cancel)")
    wide = [
        {
            "url": "https://x.com/Kojima_Hideo",
            "start": "2026-08-20",
            "end": "2026-09-14",
            "media": "image",
        }
    ]
    before_c = {str(p) for p in media_files(DEST)}
    phase_c1 = run_batch(cookies, wide, wm_mode="text", cancel_after=18, keep_archive=True)
    mid = {str(p) for p in media_files(DEST)}
    phase_c1["new_partial"] = len(mid - before_c)
    phase_c2 = run_batch(cookies, wide, wm_mode="text", keep_archive=True)
    after_c = {str(p) for p in media_files(DEST)}
    phase_c2["new_resume"] = len(after_c - mid)
    text_files.extend(phase_c1.get("wm_done") or [])
    text_files.extend(phase_c2.get("wm_done") or [])
    report["phases"]["C_stop"] = phase_c1
    report["phases"]["C_resume"] = phase_c2

    log("=" * 50)
    log("D: IMAGE watermark on a fresh tiny Lisa pull (separate dest sub-run)")
    # Use a slightly older day window unlikely fully covered, image mode
    lisa_img = [
        {
            "url": "https://x.com/Lisa_West_Pix",
            "start": "2026-09-01",
            "end": "2026-09-07",
            "media": "image",
        }
    ]
    phase_d = run_batch(cookies, lisa_img, wm_mode="image", keep_archive=True)
    image_files = list(phase_d["wm_done"])
    report["phases"]["D_image_wm"] = phase_d

    # Also image-watermark one Kojima day if any new
    kojima_img = [
        {
            "url": "https://x.com/Kojima_Hideo",
            "start": "2026-09-01",
            "end": "2026-09-07",
            "media": "image",
        }
    ]
    phase_d2 = run_batch(cookies, kojima_img, wm_mode="image", keep_archive=True)
    image_files.extend(phase_d2["wm_done"])
    report["phases"]["D2_image_wm"] = phase_d2

    # Deduplicate lists preserving order
    def uniq(seq: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    text_files = uniq(text_files)
    image_files = uniq(image_files)
    # Prefer image tag if a file was processed in both (shouldn't happen often)
    text_only = [f for f in text_files if f not in set(image_files)]

    report["watermark_summary"] = {
        "text": text_only,
        "image": image_files,
        "text_content": "X-Track水印",
        "image_png": str(default_watermark_path()),
    }
    report["finished_at"] = datetime.now().isoformat()
    report["total_media"] = len(media_files(DEST))
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    print(f"dest: {DEST}")
    print(f"total media: {report['total_media']}")
    print(f"A parallel: {phase_a['media']} files in {phase_a['seconds']}s codes={phase_a['codes']}")
    print(f"B continue new_files: {phase_b.get('new_files')}")
    print(f"C stop partial +{phase_c1.get('new_partial')} then resume +{phase_c2.get('new_resume')}")
    print(f"\n[TEXT watermark] ({len(text_only)} files) text='X-Track水印'")
    for f in text_only:
        print(f"  TEXT  {f}")
    print(f"\n[IMAGE watermark] ({len(image_files)} files) png={default_watermark_path()}")
    for f in image_files:
        print(f"  IMAGE {f}")
    print(f"\nreport: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
