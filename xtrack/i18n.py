from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Window
        "app_title": "X-Track",

        # URL Panel
        "url_list": "URL List",
        "enter_url": "Enter URL (e.g., https://x.com/username)",
        "add": "Add",
        "remove_selected": "Remove Selected",
        "clear_all": "Clear All",

        # Config Panel
        "configuration": "Configuration",
        "dest_folder": "Dest Folder:",
        "cookies": "Cookies:",
        "cookies_placeholder": "Select cookies.txt (Netscape format)",
        "cookies_missing_tip": "No cookies file selected. Export cookies.txt from a browser extension.",
        "select_cookies": "Select Cookie File",
        "ffmpeg_path": "ffmpeg Path:",
        "ffmpeg_path_placeholder": "Auto-detect (or pick ffmpeg.exe / its bin folder)",
        "ffmpeg_path_tip": "Leave empty to auto-detect. You can select ffmpeg.exe or a folder that contains it.",
        "select_ffmpeg": "Select ffmpeg",
        "media_info": "Media Info:",
        "write_metadata": "Save metadata JSON",
        "write_metadata_tip": "Write a .json sidecar next to each media file (caption/text/date).",
        "write_info_json": "Save info.json",
        "write_info_json_tip": "Write gallery-level info.json under the download folder.",
        "manifest_updated": "Manifest updated: {path}",
        "sleep_range": "Sleep Range:",
        "sleep_request": "Sleep Request:",
        "sleep_429": "Sleep 429:",
        "filter": "Filter:",
        "filter_by_date": "Filter by Date:",
        "filter_date_range": "Date:",
        "filter_date_from": "From",
        "filter_date_to": "To",
        "filter_date_from_ph": "Start date (optional)",
        "filter_date_to_ph": "End date (optional)",
        "date_range_invalid": "Start date cannot be later than end date.",
        "media_type": "Type",
        "col_select": "Run",
        "col_date_start": "Start",
        "col_date_end": "End",
        "col_filter": "Filter",
        "url_filter_title": "URL Filter",
        "url_filter_btn": "Filter",
        "url_filter_summary_empty": "Filter…",
        "url_filter_summary": "{start} → {end} · {media}",
        "url_filter_any": "Any",
        "url_filter_ok": "OK",
        "url_filter_cancel": "Cancel",
        "col_media_count": "Media",
        "media_count_fmt": "{images} img / {videos} vid",
        "media_count_tip": "Local downloaded images / videos for this URL",
        "url_duplicate": "This URL is already in the list.",
        "col_delete": "",
        "row_delete": "Delete",
        "no_selected_urls": "No URLs selected. Check the box on the left to include a URL.",
        "status_missing": "missing",
        "status_ok": "ok",
        "status_config": "cookies",
        "status_account": "status",
        "status_idle": "idle",
        "status_running": "running",
        "status_paused": "paused",
        "status_chip_click_tip": "Click for setup guide",
        "open_settings": "Open Settings",
        "ffmpeg_setup_title": "ffmpeg Setup Guide",
        "ffmpeg_setup_html": (
            "<p><b>1. Download ffmpeg</b></p>"
            "<ul>"
            "<li>Recommended: <a href='https://www.gyan.dev/ffmpeg/builds/'>"
            "https://www.gyan.dev/ffmpeg/builds/</a> → download <b>essentials</b> zip</li>"
            "<li>Or in PowerShell/CMD: <code>winget install Gyan.FFmpeg</code></li>"
            "</ul>"
            "<p><b>2. Configure in X-Track</b></p>"
            "<ul>"
            "<li>Open <b>Settings (⚙)</b> → <b>ffmpeg Path</b> → Browse and select "
            "<code>ffmpeg.exe</code> (or its <code>bin</code> folder)</li>"
            "<li>Or put <code>ffmpeg.exe</code> in "
            "<code>%USERPROFILE%\\.xtrack\\bin</code> and leave the path empty (auto-detect)</li>"
            "<li>Or add ffmpeg to system PATH, then click <b>Check Dependencies</b></li>"
            "</ul>"
        ),
        "cookies_setup_title": "Cookies Setup Guide",
        "cookies_setup_html": (
            "<p><b>1. Install a cookie export extension</b></p>"
            "<ul>"
            "<li>Recommended: <b>Get cookies.txt LOCALLY</b> "
            "(open-source, cookies stay on your PC)</li>"
            "<li>Chrome Web Store: "
            "<a href='https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc'>"
            "Install for Chrome</a></li>"
            "<li>Firefox: "
            "<a href='https://addons.mozilla.org/firefox/addon/get-cookies-txt-locally/'>"
            "Install for Firefox</a></li>"
            "<li>Source: "
            "<a href='https://github.com/kairi003/Get-cookies.txt-LOCALLY'>"
            "GitHub</a></li>"
            "</ul>"
            "<p><b>2. Export cookies</b></p>"
            "<ol>"
            "<li>Open Chrome/Edge and log in to <b>https://x.com</b></li>"
            "<li>Click the extension icon → choose <b>Netscape</b> / cookies.txt format</li>"
            "<li>Export / save as a <code>.txt</code> file (e.g. <code>x.com_cookies.txt</code>)</li>"
            "</ol>"
            "<p><b>3. Configure in X-Track</b></p>"
            "<ul>"
            "<li>Open <b>Settings (⚙)</b> → <b>Cookies</b> → Browse and select that "
            "<code>.txt</code> file</li>"
            "<li>The top-right <b>cookies</b> chip should turn green</li>"
            "</ul>"
        ),
        "media_all": "All",
        "media_image": "Images Only",
        "media_video": "Videos Only",
        "verbose": "Verbose:",
        "min": "Min:",
        "max": "Max:",

        # Watermark Panel
        "watermark": "Watermark",
        "enable_watermark": "Enable Watermark",
        "select_image": "Select Image",
        "scale": "Scale(%):",
        "wm_mode_image": "Image",
        "wm_mode_text": "Text",
        "wm_image": "Image:",
        "wm_text": "Text:",
        "wm_image_ph": "Select watermark PNG",
        "wm_text_ph": "Watermark text",
        "wm_outline": "Outline:",
        "wm_outline_tip": "Text outline width so it stays visible on same-color backgrounds.",
        "wm_font_ok": "Font: {path} (Douyin)",
        "wm_font_missing": "Douyin font missing — place DouyinMeihao.otf in resources/fonts",
        "watermark_adaptive": "Adaptive Size",
        "watermark_adaptive_tip": "Scale by each frame's shorter side so landscape/portrait and 1080p/4K keep the same visual share.",
        "watermark_scale_tip": "Watermark width as % of the frame's shorter side (equal look across aspect ratios and resolutions).",
        "position": "Position:",
        "select_watermark": "Select Watermark Image",

        # Action Panel
        "save_config": "Save Config",
        "load_config": "Load Config",
        "check_deps": "Check Dependencies",
        "check_deps_tip": "Scan for gallery-dl and ffmpeg; install automatically if missing",
        "deps_check_failed": "Dependency check failed: {error}",
        "start": "START",
        "pause": "PAUSE",
        "resume": "RESUME",
        "stop": "STOP",

        # Log Panel
        "log_output": "Log Output",

        # Status
        "pending": "Pending",
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "skipped": "Skipped",
        "last_download": "Last Download",
        "url_col": "URL",
        "status_col": "Status",
        "browse": "Browse",
        "ready": "Ready",
        "pos_tl": "TL",
        "pos_tr": "TR",
        "pos_bl": "BL",
        "pos_br": "BR",
        "pos_center": "Center",
        "filter_placeholder": "e.g., date >= datetime(2026, 7, 5) or abort()",
        "select_file": "Select File",
        "select_folder": "Select Folder",
        "dest_required": "Destination folder is required",

        # Messages
        "no_tasks": "No Tasks",
        "no_pending_urls": "No selected URLs to process.",
        "all_deps_installed": "All dependencies are installed",
        "missing_deps": "Missing: {deps}",
        "auto_installing": "Auto-installing missing dependencies...",
        "checking_deps": "Checking dependencies...",
        "starting_download": "Starting download of {count} URL(s)",
        "pausing": "Paused — click Resume to continue",
        "resuming": "Resumed downloads",
        "processing": "Processing: {url}",
        "auto_filter": "Auto-filter: date >= {time}",
        "download_archive": "Download archive (skip already downloaded): {path}",
        "command": "Command: {cmd}",
        "completed_msg": "Completed: {url}",
        "failed_msg": "Failed (exit code {code}): {url}",
        "stopping": "Stopping...",
        "all_completed": "All tasks completed",
        "watermark_applied": "Watermark applied to {count} images",
        "watermark_skipped": "Watermark skipped: destination folder not found",

        # Dialogs
        "validation_error": "Validation Error",
        "confirm_exit": "Confirm Exit",
        "downloads_in_progress": "Downloads are in progress. Are you sure you want to exit?",
        "yes": "Yes",
        "no": "No",

        # Install
        "installing_gallery_dl": "Installing gallery-dl...",
        "gallery_dl_installed": "gallery-dl installed successfully",
        "gallery_dl_failed": "gallery-dl installation failed: {error}",
        "installing_ffmpeg": "Installing ffmpeg...",
        "ffmpeg_installed": "ffmpeg installed successfully",
        "ffmpeg_path": "ffmpeg path: {path}",
        "ffmpeg_failed": "ffmpeg installation failed: {error}",
        "all_deps_done": "All dependencies installed!",
        "still_missing": "Still missing: {deps}",
        "auto_install_failed_title": "Automatic install failed. Please install manually:",
        "manual_install_ffmpeg": (
            "ffmpeg:\n"
            "  1) winget install Gyan.FFmpeg\n"
            "  2) Or download essentials from https://www.gyan.dev/ffmpeg/builds/\n"
            "     and put ffmpeg.exe in %USERPROFILE%\\.xtrack\\bin\n"
            "  3) Or add ffmpeg to system PATH, then click Check Dependencies again"
        ),
        "manual_install_gallery_dl": (
            "gallery-dl:\n"
            "  1) pip install -U gallery-dl\n"
            "  2) Or download from https://github.com/mikf/gallery-dl/releases\n"
            "     and ensure gallery-dl.exe is on PATH\n"
            "  3) Packaged builds already include gallery-dl.exe next to X-Track.exe"
        ),
        "manual_install_footer": "After installing, click「Check Dependencies」again to verify.",
        "ready_to_download": "Ready to download. Click START again.",
        "ready_for_watermark": "Ready for watermark. Run download again.",
        "watermark_accel": "Watermark acceleration: {mode}",

        # Gallery-dl not found
        "gallery_dl_not_found_title": "gallery-dl Not Found",
        "gallery_dl_not_found_msg": "gallery-dl is not installed or not in PATH.\n\nWould you like to install it now?",

        # ffmpeg not found
        "ffmpeg_not_found_title": "ffmpeg Not Found",
        "ffmpeg_not_found_msg": "ffmpeg is required for watermark feature but was not found.\n\nWould you like to install it now?",

        # Batch watermark tool
        "tools": "Tools",
        "wmtool_menu": "Batch Watermark",
        "wmtool_title": "Batch Watermark",
        "wmtool_sub": "Add a text or image watermark to every picture and video in a folder. Separate from downloads.",
        "wmtool_source": "Source",
        "wmtool_io": "Folders",
        "wmtool_folder": "Folder",
        "wmtool_open": "Open",
        "wmtool_subdirs": "Include subfolders",
        "wmtool_scan": "{images} images · {videos} videos",
        "wmtool_scan_need": "Choose a folder",
        "wmtool_scan_none": "No images or videos",
        "wmtool_mark": "Watermark",
        "wmtool_style": "Watermark & placement",
        "wmtool_style_collapsed": "Watermark & placement  ▸",
        "wmtool_kind_text": "Text",
        "wmtool_kind_image": "Image",
        "wmtool_color": "Color",
        "wmtool_font_inherited": "Using {path} · outline {outline} ({source})",
        "wmtool_font": "Font file",
        "wmtool_font_ph": "Leave empty to use X-Track / Douyin font",
        "wmtool_font_reset": "Default",
        "wmtool_font_local": "local file",
        "wmtool_font_default": "X-Track / Douyin",
        "wmtool_shadow": "Shadow",
        "wmtool_shadow_color": "Shadow color",
        "wmtool_color_ph": "#RRGGBB",
        "wmtool_bad_color": "Enter a preset name or hex color like #808080.",
        "wmtool_white": "White",
        "wmtool_black": "Black",
        "wmtool_gray": "Gray",
        "wmtool_yellow": "Yellow",
        "wmtool_red": "Red",
        "wmtool_cyan": "Cyan",
        "wmtool_scale": "Size",
        "wmtool_pad": "Margin",
        "wmtool_pad_tip": "Distance from the frame edge as a percent of the watermark's own width (0 = flush).",
        "wmtool_scale_tip": "Watermark size as % of the frame's shorter side. Text and image marks both use it as glyph height (image width follows aspect).",
        "wmtool_opacity": "Opacity",
        "wmtool_fade": "Fade",
        "wmtool_suffix_sec": " s",
        "wmtool_fade_tip": "Fade out before each move, then fade in. 0 is a hard cut. Videos only; still images keep a constant opacity. Image watermarks fade in fixed, four-corner, and random modes.",
        "wmtool_hint": "Size follows the shorter side so landscape and portrait look alike. Fade and timed moves apply to video; still images keep opacity and one position.",
        "wmtool_place": "Placement",
        "wmtool_fixed": "Fixed",
        "wmtool_corners": "Four corners",
        "wmtool_random": "Random",
        "wmtool_refresh": "Move every",
        "wmtool_refresh_tip": "How long the watermark stays before the next corner or random spot. Videos only.",
        "wmtool_hint_fixed": "Video fades in, then stays. Images are placed immediately.",
        "wmtool_hint_corners": "Video cycles top-left → top-right → bottom-right → bottom-left, holding {sec}s each. Each image is pinned to one corner.",
        "wmtool_hint_random": "Video jumps to a new on-screen spot every {sec}s. Each image is pinned to one spot.",
        "wmtool_output": "Output",
        "wmtool_overwrite": "Overwrite files",
        "wmtool_copy": "Save to another folder",
        "wmtool_out_dir": "Output folder",
        "wmtool_overwrite_safe": "Overwrite writes a temp file first and replaces the original only after success. A new folder keeps the same relative paths and names.",
        "wmtool_start": "Start",
        "wmtool_ffmpeg_ok": "ffmpeg ready",
        "wmtool_ffmpeg_ok_gpu": "ffmpeg · {mode}",
        "wmtool_ffmpeg_bad": "ffmpeg not found",
        "wmtool_ffmpeg_cfg": "Set ffmpeg",
        "wmtool_accel": "Acceleration: {mode}",
        "wmtool_need_folder": "Choose a source folder.",
        "wmtool_need_text": "Enter the watermark text.",
        "wmtool_need_image": "Choose a watermark image.",
        "wmtool_need_out": "Choose an output folder.",
        "wmtool_overlap": "The output folder cannot contain the source folder, or sit inside it.",
        "wmtool_no_media": "No images or videos to process.",
        "wmtool_font_missing": "No font found for the text watermark.",
        "wmtool_failed": "Watermark failed.",
        "wmtool_running": "Working…",
        "wmtool_processing": "Processing {name}",
        "wmtool_line_ok": "Done  {name}",
        "wmtool_line_fail": "Failed  {name}  {detail}",
        "wmtool_done": "Finished. {ok} succeeded, {fail} failed.",
        "wmtool_cancelled": "Stopped. {ok} succeeded, {fail} failed.",
        "wmtool_stopping": "Stopping after the current file…",
        "wmtool_confirm_stop": "A batch is still running. Stop it and close?",
        "wmtool_overwrite_title": "Overwrite the originals?",
        "wmtool_overwrite_msg": "Files in the source folder will be replaced. This cannot be undone.\n\nContinue?",

        # Menu
        "file": "File",
        "exit": "Exit",
        "language": "Language",
    },
    "zh": {
        # Window
        "app_title": "X-Track",

        # URL Panel
        "url_list": "URL 列表",
        "enter_url": "输入 URL (例如: https://x.com/username)",
        "add": "添加",
        "remove_selected": "删除选中",
        "clear_all": "清空全部",

        # Config Panel
        "configuration": "配置",
        "dest_folder": "下载目录:",
        "cookies": "Cookie 文件:",
        "cookies_placeholder": "选择 cookies.txt（Netscape 格式）",
        "cookies_missing_tip": "未选择 Cookie 文件。可用浏览器扩展导出 cookies.txt 后在此指定。",
        "select_cookies": "选择 Cookie 文件",
        "ffmpeg_path": "ffmpeg 路径:",
        "ffmpeg_path_placeholder": "自动检测（或选择 ffmpeg.exe / 其所在目录）",
        "ffmpeg_path_tip": "留空则自动查找。可选择 ffmpeg.exe，或包含它的文件夹。",
        "select_ffmpeg": "选择 ffmpeg",
        "media_info": "媒体信息:",
        "write_metadata": "保存元数据 JSON",
        "write_metadata_tip": "每个媒体旁写入 .json（文案/日期等，方便后续改名）。",
        "write_info_json": "保存 info.json",
        "write_info_json_tip": "在下载目录写入图集级 info.json。",
        "manifest_updated": "清单已更新: {path}",
        "sleep_range": "下载间隔:",
        "sleep_request": "请求间隔:",
        "sleep_429": "429 等待:",
        "filter": "过滤器:",
        "filter_by_date": "按日期过滤:",
        "filter_date_range": "日期:",
        "filter_date_from": "开始",
        "filter_date_to": "结束",
        "filter_date_from_ph": "开始日期（可空）",
        "filter_date_to_ph": "结束日期（可空）",
        "date_range_invalid": "开始日期不能晚于结束日期。",
        "media_type": "类型",
        "col_select": "运行",
        "col_date_start": "开始",
        "col_date_end": "结束",
        "col_filter": "筛选",
        "url_filter_title": "URL 筛选",
        "url_filter_btn": "筛选",
        "url_filter_summary_empty": "筛选…",
        "url_filter_summary": "{start} → {end} · {media}",
        "url_filter_any": "不限",
        "url_filter_ok": "确定",
        "url_filter_cancel": "取消",
        "col_media_count": "媒体",
        "media_count_fmt": "{images} 图 / {videos} 视",
        "media_count_tip": "该 URL 本地已下载的图片 / 视频数量",
        "url_duplicate": "列表中已存在相同 URL。",
        "col_delete": "",
        "row_delete": "删除",
        "no_selected_urls": "没有勾选要下载的 URL。请勾选左侧复选框。",
        "status_missing": "缺失",
        "status_ok": "就绪",
        "status_config": "cookies",
        "status_account": "状态",
        "status_idle": "空闲",
        "status_running": "下载中",
        "status_paused": "已暂停",
        "status_chip_click_tip": "点击查看配置指引",
        "open_settings": "打开配置",
        "ffmpeg_setup_title": "ffmpeg 配置指引",
        "ffmpeg_setup_html": (
            "<p><b>1. 下载 ffmpeg</b></p>"
            "<ul>"
            "<li>推荐：打开 <a href='https://www.gyan.dev/ffmpeg/builds/'>"
            "https://www.gyan.dev/ffmpeg/builds/</a>，下载 <b>essentials</b> 压缩包</li>"
            "<li>或在终端执行：<code>winget install Gyan.FFmpeg</code></li>"
            "</ul>"
            "<p><b>2. 在 X-Track 里配置</b></p>"
            "<ul>"
            "<li>打开右上角 <b>配置（⚙）</b> → <b>ffmpeg 路径</b> → 浏览并选择 "
            "<code>ffmpeg.exe</code>（或其 <code>bin</code> 目录）</li>"
            "<li>或把 <code>ffmpeg.exe</code> 放到 "
            "<code>%USERPROFILE%\\.xtrack\\bin</code>，路径留空即可自动识别</li>"
            "<li>或把 ffmpeg 加入系统 PATH 后，再点一次「检查依赖」</li>"
            "</ul>"
        ),
        "cookies_setup_title": "Cookies 配置指引",
        "cookies_setup_html": (
            "<p><b>1. 安装 Cookie 导出扩展</b></p>"
            "<ul>"
            "<li>推荐：<b>Get cookies.txt LOCALLY</b>（开源，Cookie 只保存在本机）</li>"
            "<li>Chrome 应用商店："
            "<a href='https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc'>"
            "点此安装</a></li>"
            "<li>Firefox："
            "<a href='https://addons.mozilla.org/firefox/addon/get-cookies-txt-locally/'>"
            "点此安装</a></li>"
            "<li>源码："
            "<a href='https://github.com/kairi003/Get-cookies.txt-LOCALLY'>"
            "GitHub</a></li>"
            "</ul>"
            "<p><b>2. 导出 Cookies</b></p>"
            "<ol>"
            "<li>用 Chrome/Edge 打开并登录 <b>https://x.com</b></li>"
            "<li>点击扩展图标 → 选择 <b>Netscape</b> / cookies.txt 格式</li>"
            "<li>导出/保存为 <code>.txt</code> 文件（例如 <code>x.com_cookies.txt</code>）</li>"
            "</ol>"
            "<p><b>3. 在 X-Track 里配置</b></p>"
            "<ul>"
            "<li>打开右上角 <b>配置（⚙）</b> → <b>Cookie 文件</b> → 浏览并选择该 "
            "<code>.txt</code></li>"
            "<li>配置成功后，右上角 <b>cookies</b> 会变为绿色就绪</li>"
            "</ul>"
        ),
        "media_all": "全部下载",
        "media_image": "仅图片",
        "media_video": "仅视频",
        "verbose": "详细输出:",
        "min": "最小:",
        "max": "最大:",

        # Watermark Panel
        "watermark": "水印",
        "enable_watermark": "启用水印",
        "select_image": "选择图片",
        "scale": "缩放(%):",
        "wm_mode_image": "图片",
        "wm_mode_text": "文本",
        "wm_image": "图片:",
        "wm_text": "文本:",
        "wm_image_ph": "选择水印 PNG",
        "wm_text_ph": "水印文字",
        "wm_outline": "描边:",
        "wm_outline_tip": "文字描边宽度，避免与背景同色时看不清。",
        "wm_font_ok": "字体: {path}（抖音美好体）",
        "wm_font_missing": "未找到抖音字体 — 请将 DouyinMeihao.otf 放到 resources/fonts",
        "watermark_adaptive": "自适应大小",
        "watermark_adaptive_tip": "按画面短边比例缩放，横/竖屏、1080p/4K 保持同等视觉占比。",
        "watermark_scale_tip": "水印宽度 = 画面短边的百分比（横竖屏与不同分辨率观感一致）。",
        "position": "位置:",
        "select_watermark": "选择水印图片",

        # Action Panel
        "save_config": "保存配置",
        "load_config": "加载配置",
        "check_deps": "检查依赖",
        "check_deps_tip": "搜索系统中的 gallery-dl / ffmpeg；未找到则自动安装",
        "deps_check_failed": "依赖检查失败: {error}",
        "start": "开始",
        "pause": "暂停",
        "resume": "继续",
        "stop": "停止",

        # Log Panel
        "log_output": "日志输出",

        # Status
        "pending": "等待中",
        "running": "下载中",
        "completed": "已完成",
        "failed": "失败",
        "skipped": "已跳过",
        "last_download": "上次下载",
        "url_col": "URL",
        "status_col": "状态",
        "browse": "浏览",
        "ready": "就绪",
        "pos_tl": "左上",
        "pos_tr": "右上",
        "pos_bl": "左下",
        "pos_br": "右下",
        "pos_center": "居中",
        "filter_placeholder": "例: date >= datetime(2026, 7, 5) or abort()",
        "select_file": "选择文件",
        "select_folder": "选择文件夹",
        "dest_required": "必须填写下载目录",

        # Messages
        "no_tasks": "无任务",
        "no_pending_urls": "没有勾选的 URL 可处理。",
        "all_deps_installed": "所有依赖已安装",
        "missing_deps": "缺失: {deps}",
        "auto_installing": "正在自动安装缺失的依赖...",
        "checking_deps": "正在检查依赖...",
        "starting_download": "开始下载 {count} 个 URL",
        "pausing": "已暂停 — 点击「继续」恢复",
        "resuming": "已继续下载",
        "processing": "处理中: {url}",
        "auto_filter": "自动过滤: date >= {time}",
        "download_archive": "下载归档（已下载媒体将跳过）: {path}",
        "command": "命令: {cmd}",
        "completed_msg": "已完成: {url}",
        "failed_msg": "失败 (退出码 {code}): {url}",
        "stopping": "正在停止...",
        "all_completed": "全部任务已完成",
        "watermark_applied": "已为 {count} 个文件添加水印",
        "watermark_skipped": "水印跳过: 目标文件夹不存在",

        # Dialogs
        "validation_error": "验证错误",
        "confirm_exit": "确认退出",
        "downloads_in_progress": "下载正在进行。确定要退出吗？",
        "yes": "是",
        "no": "否",

        # Install
        "installing_gallery_dl": "正在安装 gallery-dl...",
        "gallery_dl_installed": "gallery-dl 安装成功",
        "gallery_dl_failed": "gallery-dl 安装失败: {error}",
        "installing_ffmpeg": "正在安装 ffmpeg...",
        "ffmpeg_installed": "ffmpeg 安装成功",
        "ffmpeg_path": "ffmpeg 路径: {path}",
        "ffmpeg_failed": "ffmpeg 安装失败: {error}",
        "all_deps_done": "所有依赖安装完成！",
        "still_missing": "仍然缺失: {deps}",
        "auto_install_failed_title": "自动安装失败，请手动安装：",
        "manual_install_ffmpeg": (
            "ffmpeg：\n"
            "  1) 在终端执行：winget install Gyan.FFmpeg\n"
            "  2) 或从 https://www.gyan.dev/ffmpeg/builds/ 下载 essentials，\n"
            "     将 ffmpeg.exe 放到 %USERPROFILE%\\.xtrack\\bin\n"
            "  3) 或把 ffmpeg 加入系统 PATH 后，再点一次「检查依赖」"
        ),
        "manual_install_gallery_dl": (
            "gallery-dl：\n"
            "  1) 执行：pip install -U gallery-dl\n"
            "  2) 或从 https://github.com/mikf/gallery-dl/releases 下载，\n"
            "     并确保 gallery-dl.exe 在 PATH 中\n"
            "  3) 一键发行包已自带 gallery-dl.exe（与 X-Track.exe 同目录）"
        ),
        "manual_install_footer": "安装完成后，请再点一次「检查依赖」确认。",
        "ready_to_download": "准备就绪。请再次点击开始。",
        "ready_for_watermark": "水印功能就绪。请重新运行下载。",
        "watermark_accel": "水印加速: {mode}",

        # Gallery-dl not found
        "gallery_dl_not_found_title": "未找到 gallery-dl",
        "gallery_dl_not_found_msg": "gallery-dl 未安装或不在 PATH 中。\n\n是否立即安装？",

        # ffmpeg not found
        "ffmpeg_not_found_title": "未找到 ffmpeg",
        "ffmpeg_not_found_msg": "水印功能需要 ffmpeg，但未找到。\n\n是否立即安装？",

        # Batch watermark tool
        "tools": "工具",
        "wmtool_menu": "批量水印",
        "wmtool_title": "批量水印",
        "wmtool_sub": "用 ffmpeg 给文件夹里的图片和视频加水印。与下载分开，不会改下载设置。",
        "wmtool_source": "来源",
        "wmtool_io": "来源与输出",
        "wmtool_folder": "文件夹",
        "wmtool_open": "打开",
        "wmtool_subdirs": "包含子文件夹",
        "wmtool_scan": "{images} 张图片 · {videos} 个视频",
        "wmtool_scan_need": "请选择文件夹",
        "wmtool_scan_none": "没有图片或视频",
        "wmtool_mark": "水印",
        "wmtool_style": "水印与出现方式",
        "wmtool_style_collapsed": "水印与出现方式  ▸",
        "wmtool_kind_text": "文字",
        "wmtool_kind_image": "图片",
        "wmtool_color": "颜色",
        "wmtool_font_inherited": "当前 {path} · 描边 {outline}（{source}）",
        "wmtool_font": "字体文件",
        "wmtool_font_ph": "留空则使用 X-Track / 抖音字体",
        "wmtool_font_reset": "默认",
        "wmtool_font_local": "本地文件",
        "wmtool_font_default": "X-Track / 抖音",
        "wmtool_shadow": "阴影",
        "wmtool_shadow_color": "阴影颜色",
        "wmtool_color_ph": "#色号",
        "wmtool_bad_color": "请选择预置颜色，或输入 #色号（如 #808080）。",
        "wmtool_white": "白色",
        "wmtool_black": "黑色",
        "wmtool_gray": "灰色",
        "wmtool_yellow": "黄色",
        "wmtool_red": "红色",
        "wmtool_cyan": "青色",
        "wmtool_scale": "画面占比",
        "wmtool_pad": "边距",
        "wmtool_pad_tip": "水印到画面边缘的距离，按水印自身宽度的百分比计算（0 = 贴边）。",
        "wmtool_scale_tip": "水印大小 = 画面短边的百分比。文字与图片水印都按该比例作为字形高度（图片宽度跟宽高比走）。",
        "wmtool_opacity": "不透明度",
        "wmtool_fade": "渐隐时长",
        "wmtool_suffix_sec": " 秒",
        "wmtool_fade_tip": "每次换位置前淡出、换过去再淡入。0 表示硬切。仅视频；静图保持恒定不透明度。图片水印在固定、四角、随机模式下都会渐显。",
        "wmtool_hint": "大小按画面短边计算，横竖屏观感一致。渐隐和定时换位只对视频生效；图片使用不透明度，并只落在一个位置。",
        "wmtool_place": "出现方式",
        "wmtool_fixed": "固定位置",
        "wmtool_corners": "四角轮流",
        "wmtool_random": "全屏随机",
        "wmtool_refresh": "位置刷新",
        "wmtool_refresh_tip": "水印在当前位置停留多久，再换到下一角或新的随机位置。仅视频。",
        "wmtool_hint_fixed": "视频先淡入再停住。图片直接出现在所选位置。",
        "wmtool_hint_corners": "视频按左上 → 右上 → 右下 → 左下循环，每处停留 {sec} 秒。每张图片固定落在其中一个角。",
        "wmtool_hint_random": "视频每 {sec} 秒换到画面内一个新位置，水印不会超出画面。每张图片固定一个位置。",
        "wmtool_output": "输出",
        "wmtool_overwrite": "覆盖原文件",
        "wmtool_copy": "输出到新位置",
        "wmtool_out_dir": "输出目录",
        "wmtool_overwrite_safe": "覆盖会先写临时文件，成功后再替换原文件；失败则保留原文件。新位置会按原目录结构保存，文件名不变。",
        "wmtool_start": "开始处理",
        "wmtool_ffmpeg_ok": "ffmpeg 就绪",
        "wmtool_ffmpeg_ok_gpu": "ffmpeg · {mode}",
        "wmtool_ffmpeg_bad": "未找到 ffmpeg",
        "wmtool_ffmpeg_cfg": "配置 ffmpeg",
        "wmtool_accel": "加速: {mode}",
        "wmtool_need_folder": "请选择来源文件夹。",
        "wmtool_need_text": "请填写水印文字。",
        "wmtool_need_image": "请选择水印图片。",
        "wmtool_need_out": "请选择输出目录。",
        "wmtool_overlap": "输出目录不能和来源目录互相包含。",
        "wmtool_no_media": "没有可处理的图片或视频。",
        "wmtool_font_missing": "找不到可用于文字水印的字体。",
        "wmtool_failed": "水印处理失败。",
        "wmtool_running": "正在处理…",
        "wmtool_processing": "正在处理 {name}",
        "wmtool_line_ok": "完成  {name}",
        "wmtool_line_fail": "失败  {name}  {detail}",
        "wmtool_done": "处理结束。成功 {ok}，失败 {fail}。",
        "wmtool_cancelled": "已停止。成功 {ok}，失败 {fail}。",
        "wmtool_stopping": "将在当前文件结束后停止…",
        "wmtool_confirm_stop": "还在处理。要停止并关闭吗？",
        "wmtool_overwrite_title": "覆盖原文件？",
        "wmtool_overwrite_msg": "来源文件夹里的文件会被替换，且不能撤销。\n\n确定继续？",

        # Menu
        "file": "文件",
        "exit": "退出",
        "language": "语言",
    },
}


class I18n:
    def __init__(self, lang: str = "zh"):
        self.lang = lang

    def set_lang(self, lang: str):
        if lang in TRANSLATIONS:
            self.lang = lang

    def t(self, key: str, **kwargs) -> str:
        text = TRANSLATIONS.get(self.lang, TRANSLATIONS["zh"]).get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text

    def get_available_langs(self) -> list:
        return ["zh", "en"]

    def get_lang_display_name(self, lang: str) -> str:
        names = {"en": "English", "zh": "中文"}
        return names.get(lang, lang)


_i18n = I18n("zh")


def get_i18n() -> I18n:
    return _i18n


def set_language(lang: str):
    _i18n.set_lang(lang)


def t(key: str, **kwargs) -> str:
    return _i18n.t(key, **kwargs)
