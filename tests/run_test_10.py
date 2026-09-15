# -*- coding: utf-8 -*-
"""Download ~10 media (images + videos) with updated watermark scaling."""

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from xtrack.command_builder import CommandBuilder, CommandExecutor, check_gallery_dl_installed
from xtrack.config_store import AppConfig, UrlItem, WatermarkSettings
from xtrack.watermark import default_watermark_path, ensure_default_watermark_png, find_douyin_font
from xtrack.watermark_pipeline import DestMediaWatcher, InlineWatermarkPipeline

DEST = Path(r"D:/BaiduNetdiskDownload/xtrack_test10")
TARGET = 10
TIME_LIMIT = 600  # 10 min hard cap


def log(msg: str) -> None:
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg.encode('ascii','replace').decode()}", flush=True)


def find_cookies() -> str:
    cfg = ROOT / "data" / "config.json"
    if cfg.is_file():
        c = json.loads(cfg.read_text(encoding="utf-8")).get("cookies_file") or ""
        if c and os.path.isfile(c):
            return c
    p = Path(r"C:/Users/Idea Beyond/Downloads/x.com_cookies.txt")
    if p.is_file():
        return str(p)
    raise FileNotFoundError("cookies not found")


def list_media() -> list[Path]:
    img = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    vid = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}
    out = []
    if not DEST.is_dir():
        return out
    for p in DEST.rglob("*"):
        if p.is_file() and p.suffix.lower() in (img | vid) and not p.name.startswith(("_", ".")):
            out.append(p)
    return sorted(out)


def kind(p: Path) -> str:
    return "video" if p.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv", ".m4v"} else "image"


def run_phase(cookies: str, mode: str, urls: list[dict], deadline: float, remaining: int) -> dict:
    if remaining <= 0 or time.time() >= deadline:
        return {"mode": mode, "wm_done": [], "skipped": True}

    ensure_default_watermark_png("X-Track水印")
    png = str(default_watermark_path())
    font = find_douyin_font()
    log(f"=== {mode.upper()} watermark, need up to {remaining} more ===")

    cfg = AppConfig(
        dest_folder=str(DEST),
        cookies_file=cookies,
        write_metadata=False,
        write_info_json=False,
        sleep_min=1,
        sleep_max=2,
        sleep_request_min=1,
        sleep_request_max=2,
        sleep_429=45,
        verbose=True,
        max_parallel=1,
        max_items=4,
        watermark=WatermarkSettings(
            enabled=True,
            mode=mode,
            image_path=png,
            text="X-Track水印",
            font_path=font,
            scale_ratio=15,
            outline_width=2,
            adaptive=True,
            position="bottom-right",
        ),
        urls=[
            UrlItem(
                url=u["url"],
                selected=True,
                filter_date_start=u["start"],
                filter_date_end=u["end"],
                media_type=u.get("media", "all"),
            )
            for u in urls
        ],
    )

    builder = CommandBuilder()
    executor = CommandExecutor()
    pipeline = InlineWatermarkPipeline()
    pipeline.reset()
    pipeline.configure(
        enabled=True,
        settings={
            "mode": mode,
            "watermark_path": png,
            "text": "X-Track水印",
            "font_path": font,
            "scale_ratio": 15,
            "outline_width": 2,
            "position": "bottom-right",
            "adaptive": True,
        },
        on_log=log,
        suspend=executor.suspend_all,
        resume=executor.resume_all,
    )

    stop = threading.Event()
    before = {p.resolve() for p in list_media()}

    def on_limit():
        log(f">>> reached watermark limit for this phase ({remaining})")
        stop.set()
        executor.cancel()

    watcher = DestMediaWatcher(
        str(DEST), pipeline, stop, max_files=remaining, on_limit=on_limit
    )
    # seed existing so we only count NEW watermarks this phase
    seeded = watcher.seed_existing()
    log(f"watcher seeded {seeded}")
    # DestMediaWatcher max_files counts pipeline.done_files which starts empty after reset
    # but seed marks seeded 鈥?submit skips seeded. done_files only grows on new submits.
    # However max_files compares len(done_files) 鈥?good for this phase only.
    watcher.start()

    def killer():
        remain = max(0.1, deadline - time.time())
        if stop.wait(remain):
            return
        log(">>> time limit")
        stop.set()
        executor.cancel()

    threading.Thread(target=killer, daemon=True).start()

    def on_output(line: str):
        s = line.strip()
        if s.startswith("#") or "Watermark" in s or s.lower().endswith(
            (".jpg", ".png", ".mp4", ".webp", ".mov", ".mkv")
        ):
            log(s[:220])
        pipeline.handle_output_line(line)

    codes = {}

    def job(i: int, item: UrlItem):
        if stop.is_set():
            codes[item.url] = -1
            return
        cmd = builder.build(item.url, cfg, "", url_item=item)
        log(f"CMD[{i}] {item.url} type={item.media_type} range/--filter via builder")

        def done(code, url=item.url):
            codes[url] = code
            log(f"DONE {url} code={code}")

        executor.run(cmd, on_output, done)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=1) as pool:
        futs = [pool.submit(job, i, u) for i, u in enumerate(cfg.urls)]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                log(f"err {e}")
            if stop.is_set():
                executor.cancel()
                break

    stop.set()
    watcher.join(3)
    done_paths = [Path(p) for p in pipeline.done_files]
    new_files = [p for p in list_media() if p.resolve() not in before]
    return {
        "mode": mode,
        "seconds": round(time.time() - t0, 1),
        "codes": codes,
        "wm_done": done_paths,
        "new_files": new_files,
    }


def main() -> int:
    deadline = time.time() + TIME_LIMIT
    ok, gdl = check_gallery_dl_installed()
    if not ok:
        log("gallery-dl missing")
        return 1
    cookies = find_cookies()
    log(f"gallery-dl={gdl}")
    log(f"cookies={cookies}")
    log(f"font={find_douyin_font()}")
    log(f"clear {DEST}")
    if DEST.exists():
        shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True, exist_ok=True)

    # ~6 images with TEXT watermark
    text = run_phase(
        cookies,
        "text",
        [
            {
                "url": "https://x.com/Lisa_West_Pix",
                "start": "2026-09-08",
                "end": "2026-09-14",
                "media": "image",
            }
        ],
        deadline,
        remaining=6,
    )

    have = len(list_media())
    # ~4 videos with IMAGE watermark
    image = run_phase(
        cookies,
        "image",
        [
            {
                "url": "https://x.com/Kojima_Hideo",
                "start": "2026-08-01",
                "end": "2026-09-14",
                "media": "video",
            }
        ],
        deadline,
        remaining=max(0, TARGET - have),
    )

    all_media = list_media()
    text_set = {p.resolve() for p in text.get("wm_done") or []}
    image_set = {p.resolve() for p in image.get("wm_done") or []}

    report = {
        "dest": str(DEST),
        "total": len(all_media),
        "images": sum(1 for p in all_media if kind(p) == "image"),
        "videos": sum(1 for p in all_media if kind(p) == "video"),
        "text_wm": [
            str(p.relative_to(DEST)).replace("\\", "/")
            for p in (text.get("wm_done") or [])
        ],
        "image_wm": [
            str(p.relative_to(DEST)).replace("\\", "/")
            for p in (image.get("wm_done") or [])
        ],
        "files": [
            {
                "path": str(p.relative_to(DEST)).replace("\\", "/"),
                "kind": kind(p),
                "wm": "text" if p.resolve() in text_set else ("image" if p.resolve() in image_set else "unknown"),
                "size": p.stat().st_size,
            }
            for p in all_media
        ],
        "finished_at": datetime.now().isoformat(),
    }
    out = DEST / "_test10_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n==== TEST10 RESULT ====")
    print(f"total={report['total']} images={report['images']} videos={report['videos']}")
    print(f"[TEXT watermark] {len(report['text_wm'])}")
    for f in report["text_wm"]:
        print(f"  TEXT  {f}")
    print(f"[IMAGE watermark] {len(report['image_wm'])}")
    for f in report["image_wm"]:
        print(f"  IMAGE {f}")
    print(f"report: {out}")
    return 0 if report["total"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
