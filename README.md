# X-Track

**X 媒体下载工具** / **X (Twitter) media downloader**

基于 [gallery-dl](https://github.com/mikf/gallery-dl) 的 Windows 桌面客户端：批量追更、按日期与类型过滤、并行下载、暂停续传，并用 [FFmpeg](https://ffmpeg.org/) 边下边加水印。

A Windows desktop GUI for gallery-dl — batch downloads from **X (Twitter)** (and other gallery-dl sites) with per-URL date/type filters, parallel jobs, pause/resume, and inline FFmpeg watermarks.

**Version:** 1.0.0 · **License:** [GPL-2.0](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

---

## Features

- Multi-URL queue with checkbox selection
- Parallel downloads (default up to 3 URLs)
- Per-URL date range + media type (all / images / videos)
- Skip already downloaded items via `--download-archive`
- Pause / resume / stop
- Inline watermark (queue size 1; downloads suspend while watermarking)
- Default text & image watermark: `X-Track水印`
- Chinese / English UI

## 功能

- 多 URL 队列，勾选后批量下载
- 并行下载（默认最多 3 路）
- 每个 URL 独立设置日期区间与媒体类型
- archive 增量跳过、暂停 / 继续 / 停止
- 边下边串行加水印（等待队列最多 1）
- 中英文界面

---

## Download (Windows one-click)

1. Open [Releases](https://github.com/KingVk/X-Track/releases)
2. Download `X-Track-1.0.0-windows.zip`
3. Unzip and run `X-Track.exe` (keep the whole folder, including `_internal/` and `gallery-dl.exe`)

First run may be blocked by SmartScreen — choose **More info → Run anyway**.

### 一键包

1. 打开 [Releases](https://github.com/KingVk/X-Track/releases)
2. 下载 `X-Track-1.0.0-windows.zip`
3. 解压后运行 `X-Track.exe`（勿只拷贝单个 exe）

---

## Run from source

Requirements: Windows 10+, Python 3.8+, [gallery-dl](https://github.com/mikf/gallery-dl), FFmpeg (bundled under `resources/ffmpeg-9.0.1` or PATH).

```bat
run.bat
```

Or:

```bat
pip install -r requirements.txt gallery-dl
python main.py
```

Cookies: export a Netscape `cookies.txt` (e.g. browser extension “Get cookies.txt LOCALLY”) and select it in the app.

---

## Build release zip

```bat
scripts\build_release.bat
```

Outputs `release/X-Track-1.0.0-windows.zip` (upload to GitHub Releases; do not commit the zip).

Tag-triggered CI recipe is saved as `docs/release-workflow.yml` (copy to `.github/workflows/` if your token has the `workflow` scope).

---

## Project layout

```
X-Track/
├── main.py                 # entry
├── xtrack/                 # application package
├── resources/              # ffmpeg, fonts, default_watermark.png
├── data/                   # runtime config (gitignored)
├── tests/                  # manual integration scripts
├── scripts/build_release.bat
├── LICENSE                 # GPL-2.0
└── THIRD_PARTY_NOTICES.md
```

---

## Packaging notes

| Item | Note |
|------|------|
| Folder | Ship `X-Track.exe` + `gallery-dl.exe` + `_internal/` together |
| FFmpeg | Bundled under `_internal/resources/ffmpeg-9.0.1/` |
| Config | Written to `data/` next to the exe |
| gallery-dl | Use the companion `gallery-dl.exe`, not `X-Track.exe -m …` |

---

## Disclaimer

Respect site terms and local law. Only download content you have the right to access. X-Track is an independent wrapper and is not affiliated with gallery-dl, FFmpeg, or X Corp.

请遵守各站点服务条款与当地法律；仅下载你有权获取的内容。X-Track 与 gallery-dl / FFmpeg / X 官方无隶属关系。

---

## License

This project is licensed under the **GNU General Public License v2.0 only**. See [LICENSE](LICENSE).

Bundled/dependent components (gallery-dl GPL-2.0, FFmpeg LGPL/GPL, PyQt6, fonts) are described in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
