import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, fields

from .paths import config_path


@dataclass
class WatermarkSettings:
    enabled: bool = False
    mode: str = "image"  # image | text
    image_path: str = ""
    text: str = "X-Track水印"
    font_path: str = ""  # empty = auto Douyin font in app folder
    text_color: str = "white"
    outline_color: str = "black"
    outline_width: int = 3
    position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right, center
    scale_ratio: int = 15  # % of shorter side — image width (or banner height); text block width
    adaptive: bool = True  # image mode: scale relative to target shorter side


@dataclass
class UrlItem:
    url: str
    selected: bool = True
    status: str = "pending"  # pending, running, completed, failed, skipped
    last_download_time: str = ""  # ISO format timestamp
    filter_date_start: str = ""  # YYYY-MM-DD, empty = no start bound
    filter_date_end: str = ""  # YYYY-MM-DD, empty = no end bound
    media_type: str = "all"  # all | image | video
    image_count: int = 0
    video_count: int = 0

    @property
    def filter_date_start_enabled(self) -> bool:
        return bool(self.filter_date_start)

    @property
    def filter_date_end_enabled(self) -> bool:
        return bool(self.filter_date_end)


@dataclass
class AppConfig:
    language: str = "zh"
    dest_folder: str = ""
    cookies_file: str = ""
    write_metadata: bool = True
    write_info_json: bool = True
    sleep_min: int = 3
    sleep_max: int = 7
    sleep_request_min: int = 5
    sleep_request_max: int = 8
    sleep_429: int = 120
    verbose: bool = False
    max_parallel: int = 3  # concurrent URL downloads
    max_items: int = 0  # gallery-dl --range 1-N per URL (0 = unlimited)
    url_column_widths: List[int] = None
    watermark: WatermarkSettings = None
    urls: List[UrlItem] = None

    def __post_init__(self):
        if self.watermark is None:
            self.watermark = WatermarkSettings()
        if self.urls is None:
            self.urls = []
        if self.url_column_widths is None:
            self.url_column_widths = []


def _parse_url_item(raw: Dict[str, Any], legacy: Dict[str, Any]) -> UrlItem:
    allowed = {f.name for f in fields(UrlItem)}
    data = {k: v for k, v in raw.items() if k in allowed}

    if "filter_date_start" not in raw:
        if legacy.get("filter_date_start_enabled") or legacy.get("filter_date_mode") in (
            "after",
            "range",
        ) or legacy.get("filter_date_enabled"):
            data["filter_date_start"] = legacy.get("filter_date_start", "") or ""
        else:
            data.setdefault("filter_date_start", "")
    if "filter_date_end" not in raw:
        if legacy.get("filter_date_end_enabled") or legacy.get("filter_date_mode") in (
            "before",
            "range",
        ) or legacy.get("filter_date_enabled"):
            data["filter_date_end"] = legacy.get("filter_date_end", "") or ""
        else:
            data.setdefault("filter_date_end", "")
    if "media_type" not in raw:
        data["media_type"] = legacy.get("media_type", "all") or "all"
    data.setdefault("selected", True)
    data.setdefault("image_count", 0)
    data.setdefault("video_count", 0)

    url = data.pop("url", "") or raw.get("url", "")
    return UrlItem(url=url, **{k: v for k, v in data.items() if k != "url"})


class ConfigStore:
    def __init__(self, config_path_arg: Optional[str] = None):
        self.config_path = config_path_arg or config_path()
        self.config: AppConfig = AppConfig()
        self.load()

    def load(self) -> bool:
        if not os.path.exists(self.config_path):
            return False

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            watermark_data = data.pop("watermark", {})
            if isinstance(watermark_data, dict):
                allowed = {f.name for f in fields(WatermarkSettings)}
                watermark_data = {k: v for k, v in watermark_data.items() if k in allowed}
                self.config.watermark = WatermarkSettings(**watermark_data)
            else:
                self.config.watermark = WatermarkSettings()

            urls_data = data.pop("urls", [])
            legacy = {
                "filter_date_start": data.get("filter_date_start", ""),
                "filter_date_end": data.get("filter_date_end", ""),
                "filter_date_start_enabled": data.get("filter_date_start_enabled", False),
                "filter_date_end_enabled": data.get("filter_date_end_enabled", False),
                "filter_date_mode": data.get("filter_date_mode"),
                "filter_date_enabled": data.get("filter_date_enabled", False),
                "media_type": data.get("media_type", "all"),
            }
            self.config.urls = [_parse_url_item(u, legacy) for u in urls_data]

            # Drop legacy / unused fields
            for key in (
                "config_file",
                "cookies_browser",
                "cookies_from_browser",
                "filter_date_start",
                "filter_date_end",
                "filter_date_start_enabled",
                "filter_date_end_enabled",
                "filter_date_mode",
                "filter_date_enabled",
                "media_type",
            ):
                data.pop(key, None)

            for key, value in data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

            return True
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Config load error: {e}, resetting to defaults")
            self.config = AppConfig()
            return False

    def save(self) -> bool:
        try:
            data = {
                "language": self.config.language,
                "dest_folder": self.config.dest_folder,
                "cookies_file": self.config.cookies_file,
                "write_metadata": self.config.write_metadata,
                "write_info_json": self.config.write_info_json,
                "sleep_min": self.config.sleep_min,
                "sleep_max": self.config.sleep_max,
                "sleep_request_min": self.config.sleep_request_min,
                "sleep_request_max": self.config.sleep_request_max,
                "sleep_429": self.config.sleep_429,
                "verbose": self.config.verbose,
                "max_parallel": int(getattr(self.config, "max_parallel", 3) or 3),
                "max_items": int(getattr(self.config, "max_items", 0) or 0),
                "url_column_widths": list(self.config.url_column_widths or []),
                "watermark": asdict(self.config.watermark),
                "urls": [asdict(u) for u in self.config.urls],
            }

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Config save error: {e}")
            return False

    def get_url_status(self, index: int) -> str:
        if 0 <= index < len(self.config.urls):
            return self.config.urls[index].status
        return ""

    def set_url_status(self, index: int, status: str):
        if 0 <= index < len(self.config.urls):
            self.config.urls[index].status = status

    def set_url_last_download_time(self, index: int, timestamp: str):
        if 0 <= index < len(self.config.urls):
            self.config.urls[index].last_download_time = timestamp

    def set_url_media_counts(self, index: int, image_count: int, video_count: int):
        if 0 <= index < len(self.config.urls):
            self.config.urls[index].image_count = max(0, int(image_count))
            self.config.urls[index].video_count = max(0, int(video_count))

    def find_url_index(self, url: str) -> int:
        from .url_utils import urls_equal

        for i, item in enumerate(self.config.urls):
            if urls_equal(item.url, url):
                return i
        return -1

    def add_url(self, url: str) -> int:
        """Add URL. Returns index, or -1 if duplicate/empty."""
        url = (url or "").strip()
        if not url:
            return -1
        if self.find_url_index(url) >= 0:
            return -1
        self.config.urls.append(UrlItem(url=url, selected=True, status="pending"))
        return len(self.config.urls) - 1

    def remove_urls(self, indices: List[int]):
        indices = sorted(indices, reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.config.urls):
                del self.config.urls[idx]

    def clear_urls(self):
        self.config.urls = []
