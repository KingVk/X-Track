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
        "watermark_adaptive_tip": "Scale watermark by the shorter side of each image (works for landscape/portrait, 1080p/4K).",
        "watermark_scale_tip": "Percent of image shorter side. Image: watermark width. Text: mapped to a smaller font so it matches logo weight.",
        "position": "Position:",
        "select_watermark": "Select Watermark Image",

        # Action Panel
        "save_config": "Save Config",
        "load_config": "Load Config",
        "check_deps": "Check Dependencies",
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
        "ready_to_download": "Ready to download. Click START again.",
        "ready_for_watermark": "Ready for watermark. Run download again.",
        "watermark_accel": "Watermark acceleration: {mode}",

        # Gallery-dl not found
        "gallery_dl_not_found_title": "gallery-dl Not Found",
        "gallery_dl_not_found_msg": "gallery-dl is not installed or not in PATH.\n\nWould you like to install it now?",

        # ffmpeg not found
        "ffmpeg_not_found_title": "ffmpeg Not Found",
        "ffmpeg_not_found_msg": "ffmpeg is required for watermark feature but was not found.\n\nWould you like to install it now?",

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
        "watermark_adaptive_tip": "按每张图片短边比例缩放水印，横/竖图、1080p/4K 都能保持合适大小。",
        "watermark_scale_tip": "相对图片短边的百分比。图片模式：水印宽度；文字模式会按比例缩小字号，避免过大。",
        "position": "位置:",
        "select_watermark": "选择水印图片",

        # Action Panel
        "save_config": "保存配置",
        "load_config": "加载配置",
        "check_deps": "检查依赖",
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
        "ready_to_download": "准备就绪。请再次点击开始。",
        "ready_for_watermark": "水印功能就绪。请重新运行下载。",
        "watermark_accel": "水印加速: {mode}",

        # Gallery-dl not found
        "gallery_dl_not_found_title": "未找到 gallery-dl",
        "gallery_dl_not_found_msg": "gallery-dl 未安装或不在 PATH 中。\n\n是否立即安装？",

        # ffmpeg not found
        "ffmpeg_not_found_title": "未找到 ffmpeg",
        "ffmpeg_not_found_msg": "水印功能需要 ffmpeg，但未找到。\n\n是否立即安装？",

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
