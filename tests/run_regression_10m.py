# -*- coding: utf-8 -*-
"""
Regression test after restructure (<10 min, ≤20 media).

1. Date filter
2. Multi-URL parallel download
3. Pause + resume
4. Text watermark (image + video)
5. Image watermark (image + video)
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from xtrack.command_builder import CommandBuilder, CommandExecutor, check_gallery_dl_installed
from xtrack.config_store import AppConfig, UrlItem, WatermarkSettings
from xtrack.watermark import default_watermark_path, ensure_default_watermark_png, find_douyin_font
from xtrack.watermark_pipeline import DestMediaWatcher, InlineWatermarkPipeline

DEST = Path(r"D:/BaiduNetdiskDownload/xtrack_retest10m")
REPORT = DEST / "_xtrack_retest_report.json"
TIME_LIMIT = 580  # leave a little headroom under 10 min
MAX_MEDIA = 20
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VID_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}


def log(msg: str) -> None:
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"{msg.encode('ascii', 'replace').decode()}",
            flush=True,
        )


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
    out: list[Path] = []
    if not DEST.is_dir():
        return out
    for p in DEST.rglob("*"):
        if p.is_file() and p.suffix.lower() in (IMG_EXTS | VID_EXTS) and not p.name.startswith(("_", ".")):
            out.append(p)
    return sorted(out)


def kind(p: Path) -> str:
    return "video" if p.suffix.lower() in VID_EXTS else "image"


def build_cfg(cookies: str, mode: str, urls: list[dict], max_items: int, parallel: int) -> AppConfig:
    ensure_default_watermark_png("X-Track水印")
    png = str(default_watermark_path())
    font = find_douyin_font()
    return AppConfig(
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
        max_parallel=parallel,
        max_items=max_items,
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


def run_download(
    cookies: str,
    *,
    mode: str,
    urls: list[dict],
    deadline: float,
    remaining: int,
    max_items: int,
    parallel: int,
    pause_after: float | None = None,
    pause_secs: float = 3.0,
    label: str = "",
) -> dict:
    if remaining <= 0 or time.time() >= deadline:
        return {"label": label, "skipped": True, "wm_done": [], "media_new": []}

    cfg = build_cfg(cookies, mode, urls, max_items=max_items, parallel=parallel)
    png = str(default_watermark_path())
    font = find_douyin_font() or ""
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
    cmds: list[str] = []
    codes: dict[str, int] = {}
    pause_info = {"did_pause": False, "media_at_pause": 0, "media_after_resume": 0}

    def on_limit():
        log(f"[{label}] media limit reached ({remaining})")
        stop.set()
        executor.cancel()

    watcher = DestMediaWatcher(
        str(DEST), pipeline, stop, max_files=remaining, on_limit=on_limit
    )
    seeded = watcher.seed_existing()
    log(f"[{label}] watcher seeded={seeded} remaining={remaining} mode={mode}")
    watcher.start()

    def killer():
        remain = max(0.1, deadline - time.time())
        if stop.wait(remain):
            return
        log(f"[{label}] TIME STOP")
        stop.set()
        executor.cancel()

    threading.Thread(target=killer, daemon=True).start()

    def pauser():
        if pause_after is None:
            return
        if stop.wait(pause_after):
            return
        if stop.is_set():
            return
        pause_info["media_at_pause"] = len(list_media())
        log(f"[{label}] PAUSE suspend_all (media={pause_info['media_at_pause']})")
        executor.suspend_all()
        pause_info["did_pause"] = True
        time.sleep(pause_secs)
        if stop.is_set():
            return
        log(f"[{label}] RESUME resume_all")
        executor.resume_all()
        # give downloads a moment, then sample
        time.sleep(2.0)
        pause_info["media_after_resume"] = len(list_media())

    if pause_after is not None:
        threading.Thread(target=pauser, daemon=True).start()

    def on_output(line: str):
        s = line.strip()
        if s.startswith("#") or "Watermark" in line or s.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".mkv")
        ):
            log(line[:220])
        pipeline.handle_output_line(line)

    def job(i: int, item: UrlItem):
        if stop.is_set() or time.time() >= deadline:
            codes[item.url] = -1
            return
        cmd = builder.build(item.url, cfg, "", url_item=item)
        cmds.append(" ".join(cmd))
        log(f"[{label}] CMD[{i}] filter/date snippet: ...{' '.join(cmd)[-200:]}")

        def done(code, url=item.url):
            codes[url] = code
            log(f"[{label}] DONE {url} code={code}")

        executor.run(cmd, on_output, done)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=min(parallel, len(cfg.urls))) as pool:
        futs = [pool.submit(job, i, u) for i, u in enumerate(cfg.urls)]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                log(f"[{label}] worker err {e}")
            if stop.is_set():
                executor.cancel()
                break

    stop.set()
    try:
        executor.resume_all()
    except Exception:
        pass
    watcher.join(2)
    after = list_media()
    new_files = [p for p in after if p.resolve() not in before]
    return {
        "label": label,
        "mode": mode,
        "seconds": round(time.time() - t0, 1),
        "codes": codes,
        "cmds": cmds,
        "wm_done": list(pipeline.done_files),
        "media_new": [str(p) for p in new_files],
        "media_new_kinds": {kind(p): sum(1 for x in new_files if kind(x) == kind(p)) for p in new_files},
        "kinds_detail": [{"path": str(p), "kind": kind(p)} for p in new_files],
        "has_date_filter": all("--filter" in c and "datetime(" in c for c in cmds) if cmds else False,
        "filter_ok_urls": [u for u, c in zip((u["url"] for u in urls), cmds) if "--filter" in c and "datetime(" in c],
        "pause": pause_info,
    }


def main() -> int:
    t_start = time.time()
    deadline = t_start + TIME_LIMIT
    ok, gdl = check_gallery_dl_installed()
    if not ok:
        log("gallery-dl missing")
        return 1
    cookies = find_cookies()
    font = find_douyin_font()
    log(f"gallery-dl={gdl}")
    log(f"font={font}")
    log(f"png={default_watermark_path()}")
    log(f"clear {DEST}")
    if DEST.exists():
        shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True, exist_ok=True)

    budget = MAX_MEDIA
    results: dict = {"phases": []}

    # --- Phase A: date filter + multi-URL parallel + pause/resume + TEXT wm ---
    # Tight windows; mix image/video accounts. max_items keeps volume down.
    phase_a_urls = [
        {
            "url": "https://x.com/Lisa_West_Pix",
            "start": "2026-09-01",
            "end": "2026-09-14",
            "media": "image",
        },
        {
            "url": "https://x.com/HIDEO_KOJIMA_EN",
            "start": "2026-08-01",
            "end": "2026-09-14",
            "media": "all",
        },
        {
            "url": "https://x.com/Kojima_Hideo",
            "start": "2026-07-01",
            "end": "2026-09-14",
            "media": "video",
        },
    ]
    log("=" * 50)
    log("PHASE A: date filter + multi-URL + pause/resume + TEXT watermark")
    a = run_download(
        cookies,
        mode="text",
        urls=phase_a_urls,
        deadline=deadline,
        remaining=min(12, budget),
        max_items=3,
        parallel=3,
        pause_after=8.0,
        pause_secs=3.0,
        label="A-text",
    )
    results["phases"].append(a)
    budget -= len(a.get("wm_done") or [])
    # also subtract new media if wm_done lagging
    budget = max(0, min(budget, MAX_MEDIA - len(list_media())))

    # --- Phase B: IMAGE watermark, need image + video ---
    if time.time() < deadline and budget > 0:
        log("=" * 50)
        log("PHASE B: IMAGE watermark (image + video)")
        phase_b_urls = [
            {
                "url": "https://x.com/Lisa_West_Pix",
                "start": "2026-08-15",
                "end": "2026-09-14",
                "media": "image",
            },
            {
                "url": "https://x.com/HIDEO_KOJIMA_EN",
                "start": "2026-07-01",
                "end": "2026-09-14",
                "media": "video",
            },
        ]
        b = run_download(
            cookies,
            mode="image",
            urls=phase_b_urls,
            deadline=deadline,
            remaining=min(8, budget),
            max_items=3,
            parallel=2,
            pause_after=None,
            label="B-image",
        )
        results["phases"].append(b)
    else:
        b = {"skipped": True}
        results["phases"].append({"label": "B-image", "skipped": True})

    all_media = list_media()
    text_done = list((a.get("wm_done") or []))
    image_done = list((b.get("wm_done") or [])) if isinstance(b, dict) else []

    # Classify watermarked files by phase membership when possible
    def classify(paths: list[str]) -> dict:
        imgs = vids = 0
        for s in paths:
            p = Path(s)
            if p.suffix.lower() in VID_EXTS:
                vids += 1
            elif p.suffix.lower() in IMG_EXTS:
                imgs += 1
        return {"images": imgs, "videos": vids, "total": len(paths), "files": paths}

    summary = {
        "elapsed_sec": round(time.time() - t_start, 1),
        "media_total": len(all_media),
        "media_cap": MAX_MEDIA,
        "time_cap_sec": TIME_LIMIT,
        "date_filter_ok": bool(a.get("has_date_filter")),
        "multi_url_ok": len(a.get("codes") or {}) >= 2,
        "parallel_cmds": len(a.get("cmds") or []),
        "pause_ok": bool((a.get("pause") or {}).get("did_pause")),
        "pause_detail": a.get("pause"),
        "text_wm": classify(text_done),
        "image_wm": classify(image_done),
        "all_media_kinds": {
            "images": sum(1 for p in all_media if kind(p) == "image"),
            "videos": sum(1 for p in all_media if kind(p) == "video"),
        },
        "phases": results["phases"],
    }

    # Pass/fail heuristics
    checks = {
        "1_date_filter": summary["date_filter_ok"],
        "2_multi_url": summary["multi_url_ok"],
        "3_pause_resume": summary["pause_ok"],
        "4_text_wm_any": summary["text_wm"]["total"] > 0,
        "4_text_wm_image": summary["text_wm"]["images"] > 0,
        "4_text_wm_video": summary["text_wm"]["videos"] > 0,
        "5_image_wm_any": summary["image_wm"]["total"] > 0,
        "5_image_wm_image": summary["image_wm"]["images"] > 0,
        "5_image_wm_video": summary["image_wm"]["videos"] > 0,
        "budget_media": summary["media_total"] <= MAX_MEDIA,
        "budget_time": summary["elapsed_sec"] <= 600,
    }
    summary["checks"] = checks
    summary["passed"] = all(
        [
            checks["1_date_filter"],
            checks["2_multi_url"],
            checks["3_pause_resume"],
            checks["4_text_wm_any"],
            checks["5_image_wm_any"],
            checks["budget_media"],
            checks["budget_time"],
        ]
    )

    DEST.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log("=" * 50)
    log(json.dumps(checks, ensure_ascii=False, indent=2))
    log(f"elapsed={summary['elapsed_sec']}s media={summary['media_total']} passed={summary['passed']}")
    log(f"report={REPORT}")
    return 0 if summary["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
