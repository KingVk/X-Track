# -*- coding: utf-8 -*-
"""5-minute capped smoke test: 鈮?0 media, text+image watermark, watcher hook."""

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

DEST = Path(r"D:/BaiduNetdiskDownload/xtrack_smoke20")
TIME_LIMIT = 300  # 5 minutes
MAX_MEDIA = 20


def log(msg: str) -> None:
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        safe = msg.encode(sys.stdout.encoding or "utf-8", "replace").decode(
            sys.stdout.encoding or "utf-8", "replace"
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {safe}", flush=True)


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


def media_files() -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov"}
    out = []
    if not DEST.is_dir():
        return out
    for p in DEST.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and not p.name.startswith(("_", ".")):
            out.append(p)
    return out


def run_phase(cookies: str, mode: str, urls: list[dict], deadline: float) -> dict:
    ensure_default_watermark_png("X-Track水印")
    png = str(default_watermark_path())
    font = find_douyin_font()
    log(f"phase mode={mode} font={font}")

    cfg = AppConfig(
        dest_folder=str(DEST),
        cookies_file=cookies,
        write_metadata=False,
        write_info_json=False,
        sleep_min=1,
        sleep_max=2,
        sleep_request_min=1,
        sleep_request_max=2,
        sleep_429=30,
        verbose=True,
        max_parallel=2,
        max_items=5,  # few tweets 鈫?keep under ~20 media
        watermark=WatermarkSettings(
            enabled=True,
            mode=mode,
            image_path=png,
            text="X-Track水印",
            font_path=font,
            scale_ratio=12,
            outline_width=3,
        ),
        urls=[
            UrlItem(
                url=u["url"],
                selected=True,
                filter_date_start=u["start"],
                filter_date_end=u["end"],
                media_type=u.get("media", "image"),
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
            "scale_ratio": 12,
            "outline_width": 3,
            "position": "bottom-right",
            "adaptive": True,
        },
        on_log=log,
        suspend=executor.suspend_all,
        resume=executor.resume_all,
    )

    stop = threading.Event()
    results = {}

    def on_limit():
        log(f">>> media watermark limit {MAX_MEDIA} 鈥?stop downloads")
        stop.set()
        executor.cancel()

    watcher = DestMediaWatcher(
        str(DEST), pipeline, stop, max_files=MAX_MEDIA, on_limit=on_limit
    )
    seeded = watcher.seed_existing()
    log(f"watcher seeded {seeded}")
    watcher.start()

    def killer():
        remain = max(0.1, deadline - time.time())
        if stop.wait(remain):
            return
        log(">>> TIME LIMIT 5min 鈥?stop")
        stop.set()
        executor.cancel()

    threading.Thread(target=killer, daemon=True).start()

    def on_output(line: str):
        if line.strip().startswith("#") or "Watermark" in line or line.lower().endswith(
            (".jpg", ".png", ".mp4", ".webp")
        ):
            log(line[:200])
        # stdout hook secondary
        pipeline.handle_output_line(line)

    def job(i: int, item: UrlItem):
        if stop.is_set() or time.time() >= deadline:
            results[item.url] = -1
            return
        cmd = builder.build(item.url, cfg, "", url_item=item)
        log(f"CMD[{i}] {' '.join(cmd)[-180:]}")

        def done(code, url=item.url):
            results[url] = code
            log(f"DONE {url} code={code}")

        executor.run(cmd, on_output, done)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=min(2, len(cfg.urls))) as pool:
        futs = [pool.submit(job, i, u) for i, u in enumerate(cfg.urls)]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                log(f"worker err {e}")
            if stop.is_set():
                executor.cancel()
                break

    stop.set()
    watcher.join(2)
    return {
        "mode": mode,
        "seconds": round(time.time() - t0, 1),
        "codes": results,
        "wm_done": pipeline.done_files,
        "media_total": len(media_files()),
        "timed_out": time.time() >= deadline,
    }


def main() -> int:
    deadline = time.time() + TIME_LIMIT
    ok, gdl = check_gallery_dl_installed()
    if not ok:
        log("no gallery-dl")
        return 1
    cookies = find_cookies()
    font = find_douyin_font()
    log(f"gallery-dl={gdl}")
    log(f"font={font}")
    log(f"clear {DEST}")
    if DEST.exists():
        shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True, exist_ok=True)

    # TEXT: 1 account first (stable), tiny window
    text_urls = [
        {"url": "https://x.com/Lisa_West_Pix", "start": "2026-09-12", "end": "2026-09-14", "media": "image"},
    ]
    log("=" * 40)
    log("TEXT watermark phase")
    text = run_phase(cookies, "text", text_urls, deadline)

    # IMAGE: another account
    if time.time() < deadline:
        log("=" * 40)
        log("IMAGE watermark phase")
        img_urls = [
            {"url": "https://x.com/HIDEO_KOJIMA_EN", "start": "2026-09-12", "end": "2026-09-14", "media": "image"},
        ]
        image = run_phase(cookies, "image", img_urls, deadline)
    else:
        image = {"mode": "image", "wm_done": [], "skipped": True}

    report = {
        "text": {
            "count": len(text.get("wm_done") or []),
            "files": [str(Path(p).relative_to(DEST)).replace("\\", "/") for p in text.get("wm_done") or []],
            "seconds": text.get("seconds"),
            "codes": text.get("codes"),
        },
        "image": {
            "count": len(image.get("wm_done") or []),
            "files": [str(Path(p).relative_to(DEST)).replace("\\", "/") for p in image.get("wm_done") or []],
            "seconds": image.get("seconds"),
            "codes": image.get("codes"),
            "png": str(default_watermark_path()),
        },
        "media_total": len(media_files()),
        "font": font,
        "finished_at": datetime.now().isoformat(),
    }
    out = DEST / "_smoke_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n==== SMOKE RESULT ====")
    print(f"font: {font}")
    print(f"media_total: {report['media_total']}")
    print(f"[TEXT] {report['text']['count']} files")
    for f in report["text"]["files"]:
        print(f"  TEXT  {f}")
    print(f"[IMAGE] {report['image']['count']} files  png={report['image']['png']}")
    for f in report["image"]["files"]:
        print(f"  IMAGE {f}")
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
