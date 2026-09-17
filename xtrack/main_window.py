import os
import sys
import threading
import time
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QDate, QEvent
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QCheckBox,
    QSpinBox,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QMessageBox,
    QRadioButton,
    QButtonGroup,
    QProgressBar,
    QStatusBar,
    QScrollArea,
    QSizePolicy,
    QFrame,
    QComboBox,
    QSplitter,
    QDialog,
    QDialogButtonBox,
    QToolButton,
)

from .config_store import ConfigStore, UrlItem
from .command_builder import CommandBuilder, CommandExecutor, check_gallery_dl_installed
from .watermark import WatermarkProcessor
from .watermark_pipeline import DestMediaWatcher, InlineWatermarkPipeline
from .installer import DependencyInstaller, check_all_dependencies
from .cookies import cookies_status
from .download_paths import download_archive_path
from .manifest import update_manifest
from .optional_date import OptionalDateBox
from .url_utils import count_media_for_url
from .i18n import get_i18n, set_language, t
from .paths import resource_dir


class SignalBridge(QObject):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(int, str)
    progress_signal = pyqtSignal(int, int, str)
    counts_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    deps_done_signal = pyqtSignal(str, bool)  # message, success


class MainWindow(QMainWindow):
    COL_CHECK = 0
    COL_NUM = 1
    COL_URL = 2
    COL_COUNTS = 3
    COL_FILTER = 4
    COL_LAST_DOWNLOAD = 5
    COL_STATUS = 6
    COL_DELETE = 7

    DEFAULT_URL_COLUMN_WIDTHS = [40, 32, 320, 100, 168, 110, 72, 56]

    def __init__(self):
        super().__init__()
        self.config_store = ConfigStore()
        self.command_builder = CommandBuilder()
        self.executor = CommandExecutor()
        self.watermark_processor = WatermarkProcessor()
        self.wm_pipeline = InlineWatermarkPipeline()
        self._wm_stop = threading.Event()
        self._wm_watcher: Optional[DestMediaWatcher] = None
        self.signals = SignalBridge()
        self.is_running = False
        self.is_paused = False
        self._pause_gate = threading.Event()
        self._pause_gate.set()  # not paused → open
        self.current_index = 0
        self._updating_url_table = False

        set_language(self.config_store.config.language or "zh")
        self.i18n = get_i18n()

        self._setup_signals()
        self._init_ui()
        self._load_config_to_ui()

    def _setup_signals(self):
        self.signals.log_signal.connect(self._append_log)
        self.signals.status_signal.connect(self._update_url_status)
        self.signals.progress_signal.connect(self._update_watermark_progress)
        self.signals.counts_signal.connect(self._on_url_counts_refresh)
        self.signals.finished_signal.connect(self._on_all_finished)
        self.signals.deps_done_signal.connect(self._on_deps_check_finished)

    def _init_ui(self):
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(960, 640)
        self.resize(1100, 760)

        self._create_menu_bar()
        self._create_account_status_bar()

        # Build settings form once (shown in dialog)
        self.settings_form = self._create_settings_form()
        self.settings_dialog = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 8, 10, 8)

        self.url_group = self._create_url_panel()
        self.url_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.url_group, 5)

        main_layout.addWidget(self._create_log_panel(), 3)
        main_layout.addWidget(self._create_action_panel(), 0)

        self._create_status_bar()

    def _create_menu_bar(self):
        self.i18n = get_i18n()
        menubar = self.menuBar()
        menubar.clear()

        file_menu = menubar.addMenu(t("file"))
        exit_action = QAction(t("exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        lang_menu = menubar.addMenu(t("language"))
        self.lang_action_group = []
        for lang in self.i18n.get_available_langs():
            lang_display = self.i18n.get_lang_display_name(lang)
            action = QAction(lang_display, self)
            action.setCheckable(True)
            action.setData(lang)
            if lang == self.i18n.lang:
                action.setChecked(True)
            action.triggered.connect(lambda checked, l=lang: self._change_language(l))
            lang_menu.addAction(action)
            self.lang_action_group.append(action)

    def _create_account_status_bar(self):
        """Status chips + settings gear in the menu bar top-right."""
        bar = QWidget()
        bar.setObjectName("accountStatusBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 8, 0)
        layout.setSpacing(8)

        self.status_gdl = QLabel()
        self.status_ffmpeg = QLabel()
        self.status_config = QLabel()
        self.status_run = QLabel()
        self._ff_ok = False
        self._cookies_ok = False
        for lbl in (self.status_gdl, self.status_ffmpeg, self.status_config, self.status_run):
            lbl.setObjectName("statusChip")
            layout.addWidget(lbl)
        self.status_ffmpeg.installEventFilter(self)
        self.status_config.installEventFilter(self)

        self.settings_btn = QToolButton()
        self.settings_btn.setObjectName("settingsGearBtn")
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip(t("configuration"))
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        layout.addWidget(self.settings_btn)

        self.menuBar().setCornerWidget(bar, Qt.Corner.TopRightCorner)
        self._refresh_account_status()

        if not hasattr(self, "_status_timer") or self._status_timer is None:
            self._status_timer = QTimer(self)
            self._status_timer.timeout.connect(self._refresh_account_status)
            self._status_timer.start(5000)

    def _status_chip(self, name: str, ok: bool, detail: str = "") -> str:
        color = "#22C55E" if ok else "#F87171"
        tip = detail or ("OK" if ok else "N/A")
        return f'<span style="color:{color}">●</span> {name} <span style="color:#64748B">{tip}</span>'

    def _refresh_account_status(self):
        from .installer import check_all_dependencies
        import os

        if hasattr(self, "ffmpeg_path_input"):
            self._apply_ffmpeg_path_from_config()

        status, _ = check_all_dependencies()
        gdl_ok = status["gallery-dl"]["installed"]
        ff_ok = status["ffmpeg"]["installed"]
        gdl_ver = status["gallery-dl"]["version"] if gdl_ok else t("status_missing")
        ff_ver = "OK" if ff_ok else t("status_missing")
        if ff_ok and status["ffmpeg"]["version"]:
            ff_ver = status["ffmpeg"]["version"][:24]

        cfg_path = self.config_store.config.cookies_file
        cfg_ok, _ = cookies_status(cfg_path)

        if self.is_running and self.is_paused:
            run_text = t("status_paused")
            run_ok = True
        elif self.is_running:
            run_text = t("status_running")
            run_ok = True
        else:
            run_text = t("status_idle")
            run_ok = True

        if hasattr(self, "status_gdl"):
            self.status_gdl.setText(self._status_chip("gallery-dl", gdl_ok, gdl_ver if gdl_ok else ""))
            self.status_gdl.setToolTip(str(gdl_ver))
            self._ff_ok = bool(ff_ok)
            self.status_ffmpeg.setText(self._status_chip("ffmpeg", ff_ok, "" if ff_ok else t("status_missing")))
            self.status_ffmpeg.setToolTip(
                str(ff_ver) if ff_ok else t("status_chip_click_tip")
            )
            self.status_ffmpeg.setCursor(
                Qt.CursorShape.PointingHandCursor if not ff_ok else Qt.CursorShape.ArrowCursor
            )
            self.status_ffmpeg.setProperty("clickable", "true" if not ff_ok else "false")
            self.status_ffmpeg.style().unpolish(self.status_ffmpeg)
            self.status_ffmpeg.style().polish(self.status_ffmpeg)

            self._cookies_ok = bool(cfg_ok)
            self.status_config.setText(
                self._status_chip("cookies", cfg_ok, t("status_ok") if cfg_ok else t("status_missing"))
            )
            self.status_config.setToolTip(
                cfg_path if cfg_ok else t("status_chip_click_tip")
            )
            self.status_config.setCursor(
                Qt.CursorShape.PointingHandCursor if not cfg_ok else Qt.CursorShape.ArrowCursor
            )
            self.status_config.setProperty("clickable", "true" if not cfg_ok else "false")
            self.status_config.style().unpolish(self.status_config)
            self.status_config.style().polish(self.status_config)

            self.status_run.setText(self._status_chip(t("status_account"), True, run_text))

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if obj is getattr(self, "status_ffmpeg", None) and not self._ff_ok:
                self._show_ffmpeg_setup_guide()
                return True
            if obj is getattr(self, "status_config", None) and not self._cookies_ok:
                self._show_cookies_setup_guide()
                return True
        return super().eventFilter(obj, event)

    def _show_setup_guide_dialog(self, title: str, html: str):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(520)
        root = QVBoxLayout(dlg)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)
        body = QLabel(html)
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setOpenExternalLinks(True)
        body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        body.setStyleSheet("QLabel { color: #E2E8F0; line-height: 1.45; }")
        root.addWidget(body)
        buttons = QDialogButtonBox()
        open_cfg = buttons.addButton(t("open_settings"), QDialogButtonBox.ButtonRole.ActionRole)
        close_btn = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        open_cfg.clicked.connect(lambda: (dlg.accept(), self._open_settings_dialog()))
        close_btn.clicked.connect(dlg.reject)
        root.addWidget(buttons)
        dlg.exec()

    def _show_ffmpeg_setup_guide(self):
        self._show_setup_guide_dialog(t("ffmpeg_setup_title"), t("ffmpeg_setup_html"))

    def _show_cookies_setup_guide(self):
        self._show_setup_guide_dialog(t("cookies_setup_title"), t("cookies_setup_html"))

    def _change_language(self, lang: str):
        set_language(lang)
        self.i18n = get_i18n()
        self.config_store.config.language = lang
        self.config_store.save()
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle(t("app_title"))
        self.url_group.setTitle(t("url_list"))
        self.log_group.setTitle(t("log_output"))
        self.start_btn.setText(t("start"))
        if hasattr(self, "check_deps_btn"):
            self.check_deps_btn.setText(t("check_deps"))
            self.check_deps_btn.setToolTip(t("check_deps_tip"))
        if hasattr(self, "pause_btn"):
            self.pause_btn.setText(t("resume") if self.is_paused else t("pause"))
        if hasattr(self, "stop_btn"):
            self.stop_btn.setText(t("stop"))
        self._refresh_pause_button_text()
        self.stop_btn.setText(t("stop"))
        if hasattr(self, "settings_btn"):
            self.settings_btn.setToolTip(t("configuration"))
        self.watermark_enabled.setText(t("enable_watermark"))
        self.select_watermark_btn.setText(t("select_image"))
        self.watermark_adaptive.setText(t("watermark_adaptive"))
        self.watermark_adaptive.setToolTip(t("watermark_adaptive_tip"))
        self.watermark_scale.setToolTip(t("watermark_scale_tip"))
        if hasattr(self, "wm_mode_image"):
            self.wm_mode_image.setText(t("wm_mode_image"))
            self.wm_mode_text.setText(t("wm_mode_text"))
            self.watermark_path_input.setPlaceholderText(t("wm_image_ph"))
            self.watermark_text_input.setPlaceholderText(t("wm_text_ph"))
            self.wm_outline_label.setText(t("wm_outline"))
            self.watermark_outline.setToolTip(t("wm_outline_tip"))
            self._refresh_wm_font_label()
        self.position_tl.setText(t("pos_tl"))
        self.position_tr.setText(t("pos_tr"))
        self.position_bl.setText(t("pos_bl"))
        self.position_br.setText(t("pos_br"))
        self.position_center.setText(t("pos_center"))
        if hasattr(self, "watermark_section_label"):
            self.watermark_section_label.setText(t("watermark"))
        if hasattr(self, "watermark_pos_label"):
            self.watermark_pos_label.setText(t("position"))
        if hasattr(self, "watermark_scale_label"):
            self.watermark_scale_label.setText(t("scale"))
        self.dest_folder_btn.setText(t("browse"))
        self.cookies_file_btn.setText(t("browse"))
        if hasattr(self, "ffmpeg_path_btn"):
            self.ffmpeg_path_btn.setText(t("browse"))
            self.ffmpeg_path_btn.setToolTip(t("ffmpeg_path_tip"))
        if hasattr(self, "ffmpeg_path_input"):
            self.ffmpeg_path_input.setPlaceholderText(t("ffmpeg_path_placeholder"))
            self.ffmpeg_path_input.setToolTip(t("ffmpeg_path_tip"))
        self.write_metadata_check.setText(t("write_metadata"))
        self.write_info_json_check.setText(t("write_info_json"))
        self.cookies_file_input.setPlaceholderText(t("cookies_placeholder"))
        self.url_input.setPlaceholderText(t("enter_url"))
        self.verbose_checkbox.setText(t("verbose"))
        self.status_label.setText(t("ready"))
        self.url_table.setHorizontalHeaderLabels(self._url_headers())
        self._refresh_filter_buttons()
        self._update_url_table()
        self._create_menu_bar()
        self._create_account_status_bar()
        if hasattr(self, "check_deps_btn"):
            self.check_deps_btn.setText(t("check_deps"))
            self.check_deps_btn.setToolTip(t("check_deps_tip"))
        if hasattr(self, "settings_check_deps_btn"):
            self.settings_check_deps_btn.setText(t("check_deps"))
            self.settings_check_deps_btn.setToolTip(t("check_deps_tip"))
        if self.settings_dialog is not None:
            self.settings_dialog.setWindowTitle(t("configuration"))


    def _url_headers(self) -> List[str]:
        return [
            t("col_select"),
            "#",
            t("url_col"),
            t("col_media_count"),
            t("col_filter"),
            t("last_download"),
            t("status_col"),
            t("col_delete"),
        ]

    def _create_url_panel(self) -> QWidget:
        group = QGroupBox(t("url_list"))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(t("enter_url"))
        self.url_input.returnPressed.connect(self._add_url)
        input_layout.addWidget(self.url_input, 1)

        add_btn = QPushButton(t("add"))
        add_btn.setFixedWidth(64)
        add_btn.clicked.connect(self._add_url)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)

        self.url_table = QTableWidget()
        self.url_table.setColumnCount(8)
        self.url_table.setHorizontalHeaderLabels(self._url_headers())
        header = self.url_table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        # All columns user-resizable; widths persist to config
        for col in range(8):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        self._applying_column_widths = False
        self._apply_saved_column_widths()
        header.sectionResized.connect(self._on_column_resized)

        self.url_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.url_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.url_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.url_table.verticalHeader().setVisible(False)
        self.url_table.setMinimumHeight(200)
        self.url_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.url_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.url_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.url_table.setWordWrap(False)
        self.url_table.setShowGrid(True)
        self.url_table.setAlternatingRowColors(True)
        layout.addWidget(self.url_table, 1)

        return group

    def _apply_saved_column_widths(self):
        widths = list(getattr(self.config_store.config, "url_column_widths", None) or [])
        if len(widths) != self.url_table.columnCount():
            widths = list(self.DEFAULT_URL_COLUMN_WIDTHS)
        self._applying_column_widths = True
        for i, w in enumerate(widths):
            if 0 <= i < self.url_table.columnCount() and w > 20:
                self.url_table.setColumnWidth(i, int(w))
        self._applying_column_widths = False

    def _on_column_resized(self, index: int, old: int, new: int):
        if getattr(self, "_applying_column_widths", False):
            return
        widths = [self.url_table.columnWidth(i) for i in range(self.url_table.columnCount())]
        self.config_store.config.url_column_widths = widths
        # Debounce disk write
        if not hasattr(self, "_col_save_timer") or self._col_save_timer is None:
            self._col_save_timer = QTimer(self)
            self._col_save_timer.setSingleShot(True)
            self._col_save_timer.timeout.connect(lambda: self.config_store.save())
        self._col_save_timer.start(400)

    def _create_settings_form(self) -> QWidget:
        form_host = QWidget()
        layout = QFormLayout(form_host)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.dest_folder_input = QLineEdit()
        self.dest_folder_input.textChanged.connect(self._update_start_button)
        dest_folder_layout = QHBoxLayout()
        dest_folder_layout.setSpacing(6)
        dest_folder_layout.addWidget(self.dest_folder_input, 1)
        self.dest_folder_btn = QPushButton(t("browse"))
        self.dest_folder_btn.setFixedWidth(64)
        self.dest_folder_btn.clicked.connect(lambda: self._browse_folder(self.dest_folder_input))
        dest_folder_layout.addWidget(self.dest_folder_btn)
        layout.addRow(t("dest_folder"), dest_folder_layout)

        cookies_row = QHBoxLayout()
        cookies_row.setSpacing(6)
        self.cookies_file_input = QLineEdit()
        self.cookies_file_input.setPlaceholderText(t("cookies_placeholder"))
        self.cookies_file_input.textChanged.connect(self._refresh_account_status)
        cookies_row.addWidget(self.cookies_file_input, 1)
        self.cookies_file_btn = QPushButton(t("browse"))
        self.cookies_file_btn.setFixedWidth(64)
        self.cookies_file_btn.clicked.connect(self._browse_cookies_file)
        cookies_row.addWidget(self.cookies_file_btn)
        layout.addRow(t("cookies"), cookies_row)

        ffmpeg_row = QHBoxLayout()
        ffmpeg_row.setSpacing(6)
        self.ffmpeg_path_input = QLineEdit()
        self.ffmpeg_path_input.setPlaceholderText(t("ffmpeg_path_placeholder"))
        self.ffmpeg_path_input.setToolTip(t("ffmpeg_path_tip"))
        self.ffmpeg_path_input.textChanged.connect(self._refresh_account_status)
        ffmpeg_row.addWidget(self.ffmpeg_path_input, 1)
        self.ffmpeg_path_btn = QPushButton(t("browse"))
        self.ffmpeg_path_btn.setFixedWidth(64)
        self.ffmpeg_path_btn.setToolTip(t("ffmpeg_path_tip"))
        self.ffmpeg_path_btn.clicked.connect(self._browse_ffmpeg_path)
        ffmpeg_row.addWidget(self.ffmpeg_path_btn)
        layout.addRow(t("ffmpeg_path"), ffmpeg_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        self.write_metadata_check = QCheckBox(t("write_metadata"))
        self.write_metadata_check.setChecked(True)
        self.write_metadata_check.setToolTip(t("write_metadata_tip"))
        self.write_info_json_check = QCheckBox(t("write_info_json"))
        self.write_info_json_check.setChecked(True)
        self.write_info_json_check.setToolTip(t("write_info_json_tip"))
        meta_row.addWidget(self.write_metadata_check)
        meta_row.addWidget(self.write_info_json_check)
        meta_row.addStretch()
        layout.addRow(t("media_info"), meta_row)

        sleep_layout = QHBoxLayout()
        sleep_layout.setSpacing(6)
        self.sleep_min = QSpinBox()
        self.sleep_min.setRange(0, 3600)
        self.sleep_min.setValue(3)
        self.sleep_min.setFixedWidth(64)
        sleep_layout.addWidget(QLabel(t("min")))
        sleep_layout.addWidget(self.sleep_min)
        self.sleep_max = QSpinBox()
        self.sleep_max.setRange(0, 3600)
        self.sleep_max.setValue(7)
        self.sleep_max.setFixedWidth(64)
        sleep_layout.addWidget(QLabel(t("max")))
        sleep_layout.addWidget(self.sleep_max)
        sleep_layout.addStretch()
        layout.addRow(t("sleep_range"), sleep_layout)

        sleep_req_layout = QHBoxLayout()
        sleep_req_layout.setSpacing(6)
        self.sleep_req_min = QSpinBox()
        self.sleep_req_min.setRange(0, 3600)
        self.sleep_req_min.setValue(5)
        self.sleep_req_min.setFixedWidth(64)
        sleep_req_layout.addWidget(QLabel(t("min")))
        sleep_req_layout.addWidget(self.sleep_req_min)
        self.sleep_req_max = QSpinBox()
        self.sleep_req_max.setRange(0, 3600)
        self.sleep_req_max.setValue(8)
        self.sleep_req_max.setFixedWidth(64)
        sleep_req_layout.addWidget(QLabel(t("max")))
        sleep_req_layout.addWidget(self.sleep_req_max)
        sleep_req_layout.addStretch()
        layout.addRow(t("sleep_request"), sleep_req_layout)

        self.sleep_429 = QSpinBox()
        self.sleep_429.setRange(0, 3600)
        self.sleep_429.setValue(120)
        self.sleep_429.setFixedWidth(72)
        layout.addRow(t("sleep_429"), self.sleep_429)

        self.verbose_checkbox = QCheckBox(t("verbose"))
        layout.addRow("", self.verbose_checkbox)

        self.watermark_section_label = QLabel(t("watermark"))
        self.watermark_section_label.setStyleSheet("color: #94A3B8; font-weight: 600; padding-top: 4px;")
        layout.addRow(self.watermark_section_label)

        wm_en = QHBoxLayout()
        wm_en.setSpacing(6)
        self.watermark_enabled = QCheckBox(t("enable_watermark"))
        self.watermark_enabled.stateChanged.connect(self._on_watermark_toggled)
        wm_en.addWidget(self.watermark_enabled)
        self.wm_mode_group = QButtonGroup(self)
        self.wm_mode_image = QRadioButton(t("wm_mode_image"))
        self.wm_mode_text = QRadioButton(t("wm_mode_text"))
        self.wm_mode_image.setObjectName("chipRadio")
        self.wm_mode_text.setObjectName("chipRadio")
        self.wm_mode_image.setChecked(True)
        self.wm_mode_group.addButton(self.wm_mode_image, 0)
        self.wm_mode_group.addButton(self.wm_mode_text, 1)
        wm_en.addWidget(self.wm_mode_image)
        wm_en.addWidget(self.wm_mode_text)
        self.wm_mode_image.toggled.connect(self._on_watermark_mode_changed)
        wm_en.addStretch()
        layout.addRow("", wm_en)

        # Image watermark row
        self.wm_image_row = QWidget()
        wm_row = QHBoxLayout(self.wm_image_row)
        wm_row.setContentsMargins(0, 0, 0, 0)
        wm_row.setSpacing(6)
        self.watermark_path_input = QLineEdit()
        self.watermark_path_input.setReadOnly(True)
        self.watermark_path_input.setPlaceholderText(t("wm_image_ph"))
        wm_row.addWidget(self.watermark_path_input, 1)
        self.select_watermark_btn = QPushButton(t("select_image"))
        self.select_watermark_btn.setFixedWidth(72)
        self.select_watermark_btn.clicked.connect(self._select_watermark)
        wm_row.addWidget(self.select_watermark_btn)
        layout.addRow(t("wm_image"), self.wm_image_row)

        # Text watermark row
        self.wm_text_row = QWidget()
        text_row = QHBoxLayout(self.wm_text_row)
        text_row.setContentsMargins(0, 0, 0, 0)
        text_row.setSpacing(6)
        self.watermark_text_input = QLineEdit()
        self.watermark_text_input.setPlaceholderText(t("wm_text_ph"))
        text_row.addWidget(self.watermark_text_input, 1)
        layout.addRow(t("wm_text"), self.wm_text_row)

        self.wm_font_label = QLabel()
        self.wm_font_label.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addRow("", self.wm_font_label)

        wm_opts = QHBoxLayout()
        wm_opts.setSpacing(6)
        self.watermark_adaptive = QCheckBox(t("watermark_adaptive"))
        self.watermark_adaptive.setChecked(True)
        self.watermark_adaptive.setToolTip(t("watermark_adaptive_tip"))
        wm_opts.addWidget(self.watermark_adaptive)
        self.watermark_scale_label = QLabel(t("scale"))
        wm_opts.addWidget(self.watermark_scale_label)
        self.watermark_scale = QSpinBox()
        self.watermark_scale.setRange(1, 50)
        self.watermark_scale.setValue(15)
        self.watermark_scale.setSuffix(" %")
        self.watermark_scale.setFixedWidth(72)
        self.watermark_scale.setToolTip(t("watermark_scale_tip"))
        wm_opts.addWidget(self.watermark_scale)
        self.wm_outline_label = QLabel(t("wm_outline"))
        wm_opts.addWidget(self.wm_outline_label)
        self.watermark_outline = QSpinBox()
        self.watermark_outline.setRange(0, 12)
        self.watermark_outline.setValue(3)
        self.watermark_outline.setFixedWidth(56)
        self.watermark_outline.setToolTip(t("wm_outline_tip"))
        wm_opts.addWidget(self.watermark_outline)
        wm_opts.addStretch()
        layout.addRow("", wm_opts)

        wm_pos = QHBoxLayout()
        wm_pos.setSpacing(6)
        self.watermark_pos_label = QLabel(t("position"))
        wm_pos.addWidget(self.watermark_pos_label)
        position_group = QButtonGroup(self)
        self.position_tl = QRadioButton(t("pos_tl"))
        self.position_tr = QRadioButton(t("pos_tr"))
        self.position_bl = QRadioButton(t("pos_bl"))
        self.position_br = QRadioButton(t("pos_br"))
        self.position_center = QRadioButton(t("pos_center"))
        self.position_br.setChecked(True)
        for i, btn in enumerate(
            (self.position_tl, self.position_tr, self.position_bl, self.position_br, self.position_center)
        ):
            btn.setObjectName("chipRadio")
            position_group.addButton(btn, i)
            wm_pos.addWidget(btn)
        wm_pos.addStretch()
        layout.addRow("", wm_pos)

        self._on_watermark_mode_changed()
        return form_host

    def _open_settings_dialog(self):
        if self.settings_dialog is None:
            dlg = QDialog(self)
            dlg.setWindowTitle(t("configuration"))
            dlg.setMinimumWidth(560)
            dlg.setMinimumHeight(480)
            root = QVBoxLayout(dlg)
            root.setContentsMargins(10, 10, 10, 10)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(self.settings_form)
            root.addWidget(scroll, 1)
            deps_row = QHBoxLayout()
            self.settings_check_deps_btn = QPushButton(t("check_deps"))
            self.settings_check_deps_btn.setToolTip(t("check_deps_tip"))
            self.settings_check_deps_btn.clicked.connect(self._check_dependencies)
            deps_row.addWidget(self.settings_check_deps_btn)
            deps_row.addStretch()
            root.addLayout(deps_row)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dlg.reject)
            buttons.accepted.connect(dlg.accept)
            close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
            if close_btn:
                close_btn.clicked.connect(dlg.accept)
            root.addWidget(buttons)
            dlg.finished.connect(self._on_settings_dialog_finished)
            self.settings_dialog = dlg

        self.settings_dialog.setWindowTitle(t("configuration"))
        self.settings_dialog.exec()

    def _on_settings_dialog_finished(self, _result: int = 0):
        self._collect_config_from_ui()
        if not self._date_filter_valid():
            QMessageBox.warning(self, t("validation_error"), t("date_range_invalid"))
            return
        self.config_store.save()
        self._update_start_button()
        self._refresh_account_status()

    def _create_action_panel(self) -> QWidget:
        widget = QWidget()
        widget.setMinimumHeight(44)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self.watermark_progress = QProgressBar()
        self.watermark_progress.setVisible(False)
        self.watermark_progress.setMaximumWidth(200)
        self.watermark_progress.setFixedHeight(12)
        layout.addWidget(self.watermark_progress)
        layout.addStretch()

        self.check_deps_btn = QPushButton(t("check_deps"))
        self.check_deps_btn.setMinimumSize(100, 34)
        self.check_deps_btn.setToolTip(t("check_deps_tip"))
        self.check_deps_btn.clicked.connect(self._check_dependencies)
        layout.addWidget(self.check_deps_btn)

        self.start_btn = QPushButton(t("start"))
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setMinimumSize(100, 34)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton(t("pause"))
        self.pause_btn.setObjectName("warningBtn")
        self.pause_btn.setMinimumSize(100, 34)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton(t("stop"))
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setMinimumSize(100, 34)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_btn)

        return widget

    def _create_log_panel(self) -> QWidget:
        group = QGroupBox(t("log_output"))
        self.log_group = group
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(4)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_output.setMinimumHeight(120)
        layout.addWidget(self.log_output, 1)

        return group

    def _create_status_bar(self) -> QStatusBar:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel(t("ready"))
        self.status_bar.addPermanentWidget(self.status_label, 1)
        return self.status_bar

    def _load_config_to_ui(self):
        cfg = self.config_store.config

        if cfg.language:
            set_language(cfg.language)
            self.i18n = get_i18n()

        self.dest_folder_input.setText(cfg.dest_folder)
        self.cookies_file_input.setText(getattr(cfg, "cookies_file", "") or "")
        if hasattr(self, "ffmpeg_path_input"):
            self.ffmpeg_path_input.setText(getattr(cfg, "ffmpeg_path", "") or "")
        self._apply_ffmpeg_path_from_config()
        self.write_metadata_check.setChecked(bool(getattr(cfg, "write_metadata", True)))
        self.write_info_json_check.setChecked(bool(getattr(cfg, "write_info_json", True)))
        self.sleep_min.setValue(cfg.sleep_min)
        self.sleep_max.setValue(cfg.sleep_max)
        self.sleep_req_min.setValue(cfg.sleep_request_min)
        self.sleep_req_max.setValue(cfg.sleep_request_max)
        self.sleep_429.setValue(cfg.sleep_429)
        self.verbose_checkbox.setChecked(cfg.verbose)

        self.watermark_enabled.setChecked(cfg.watermark.enabled)
        mode = getattr(cfg.watermark, "mode", "image") or "image"
        if mode == "text":
            self.wm_mode_text.setChecked(True)
        else:
            self.wm_mode_image.setChecked(True)
        img_path = (cfg.watermark.image_path or "").strip()
        if not img_path:
            try:
                from .watermark import ensure_default_watermark_png

                img_path = ensure_default_watermark_png()
            except Exception:
                from .watermark import default_watermark_path

                candidate = default_watermark_path()
                img_path = candidate if os.path.isfile(candidate) else ""
        self.watermark_path_input.setText(img_path)
        text_val = getattr(cfg.watermark, "text", "") or ""
        self.watermark_text_input.setText(text_val or "X-Track水印")
        self.watermark_scale.setValue(cfg.watermark.scale_ratio)
        self.watermark_adaptive.setChecked(getattr(cfg.watermark, "adaptive", True))
        self.watermark_outline.setValue(int(getattr(cfg.watermark, "outline_width", 3) or 3))
        self._on_watermark_toggled(cfg.watermark.enabled)
        self._on_watermark_mode_changed()
        self._refresh_wm_font_label()

        position_map = {
            "top-left": self.position_tl,
            "top-right": self.position_tr,
            "bottom-left": self.position_bl,
            "bottom-right": self.position_br,
            "center": self.position_center,
        }
        pos_btn = position_map.get(cfg.watermark.position, self.position_br)
        pos_btn.setChecked(True)

        self._update_url_table()
        self._refresh_media_counts(save=True)
        self._apply_saved_column_widths()
        self._update_start_button()

    def _sync_url_table_to_config(self):
        """Persist checkbox widgets back into UrlItem list."""
        if self._updating_url_table:
            return
        urls = self.config_store.config.urls
        rows = min(self.url_table.rowCount(), len(urls))
        for i in range(rows):
            item = urls[i]
            check = self._row_checkbox(i)
            if check is not None:
                item.selected = check.isChecked()

    def _refresh_filter_buttons(self):
        for i in range(self.url_table.rowCount()):
            btn = self.url_table.cellWidget(i, self.COL_FILTER)
            if isinstance(btn, QPushButton) and i < len(self.config_store.config.urls):
                btn.setText(self._filter_summary(self.config_store.config.urls[i]))

    def _filter_summary(self, item) -> str:
        start = (getattr(item, "filter_date_start", "") or "").strip()
        end = (getattr(item, "filter_date_end", "") or "").strip()
        mt = getattr(item, "media_type", "all") or "all"
        media_label = {
            "all": t("media_all"),
            "image": t("media_image"),
            "video": t("media_video"),
        }.get(mt, t("media_all"))
        if not start and not end and mt == "all":
            return t("url_filter_summary_empty")
        start_s = start or t("url_filter_any")
        end_s = end or t("url_filter_any")
        # Compact dates: 2026-09-01 → 09-01 when year same
        def short(d: str) -> str:
            if len(d) == 10 and d[4] == "-" and d[7] == "-":
                return d[5:]
            return d

        if start and end and start[:4] == end[:4]:
            start_s, end_s = short(start), short(end)
        elif start:
            start_s = short(start) if len(start) == 10 else start
        elif end:
            end_s = short(end) if len(end) == 10 else end
        return t("url_filter_summary", start=start_s, end=end_s, media=media_label)

    def _open_url_filter_dialog(self, row: int):
        if not (0 <= row < len(self.config_store.config.urls)):
            return
        self._sync_url_table_to_config()
        item = self.config_store.config.urls[row]

        dlg = QDialog(self)
        dlg.setWindowTitle(t("url_filter_title"))
        dlg.setMinimumWidth(360)
        form = QFormLayout(dlg)
        form.setContentsMargins(14, 14, 14, 10)
        form.setSpacing(10)

        start_box = OptionalDateBox(t("filter_date_from_ph"))
        start_box.set_date_string(getattr(item, "filter_date_start", "") or "")
        end_box = OptionalDateBox(t("filter_date_to_ph"))
        end_box.set_date_string(getattr(item, "filter_date_end", "") or "")
        media = QComboBox()
        media.addItem(t("media_all"), "all")
        media.addItem(t("media_image"), "image")
        media.addItem(t("media_video"), "video")
        mt = getattr(item, "media_type", "all") or "all"
        idx = media.findData(mt)
        media.setCurrentIndex(idx if idx >= 0 else 0)

        form.addRow(t("filter_date_from"), start_box)
        form.addRow(t("filter_date_to"), end_box)
        form.addRow(t("media_type"), media)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("url_filter_ok"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("url_filter_cancel"))
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        start = start_box.date()
        end = end_box.date()
        if start and end and start.isValid() and end.isValid() and start > end:
            QMessageBox.warning(self, t("validation_error"), t("date_range_invalid"))
            return

        item.filter_date_start = start_box.date_string()
        item.filter_date_end = end_box.date_string()
        item.media_type = media.currentData() or "all"
        self.config_store.save()
        btn = self.url_table.cellWidget(row, self.COL_FILTER)
        if isinstance(btn, QPushButton):
            btn.setText(self._filter_summary(item))
            tip_parts = [
                f"{t('filter_date_from')}: {item.filter_date_start or t('url_filter_any')}",
                f"{t('filter_date_to')}: {item.filter_date_end or t('url_filter_any')}",
                f"{t('media_type')}: {media.currentText()}",
            ]
            btn.setToolTip("\n".join(tip_parts))

    def _update_url_table(self):
        urls = self.config_store.config.urls
        self._updating_url_table = True
        self.url_table.setRowCount(len(urls))
        for i, item in enumerate(urls):
            self.url_table.setRowHeight(i, 42)

            check = QCheckBox()
            check.setChecked(bool(getattr(item, "selected", True)))
            check.stateChanged.connect(lambda *_: self._sync_url_table_to_config())
            check_wrap = QWidget()
            check_layout = QHBoxLayout(check_wrap)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_layout.addWidget(check)
            check_wrap._check = check  # type: ignore[attr-defined]
            self.url_table.setCellWidget(i, self.COL_CHECK, check_wrap)

            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.url_table.setItem(i, self.COL_NUM, num_item)
            self.url_table.setItem(i, self.COL_URL, QTableWidgetItem(item.url))

            counts_item = QTableWidgetItem(self._format_media_counts(item))
            counts_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            counts_item.setToolTip(t("media_count_tip"))
            self.url_table.setItem(i, self.COL_COUNTS, counts_item)

            filter_btn = QPushButton(self._filter_summary(item))
            filter_btn.setObjectName("rowFilterBtn")
            filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            filter_btn.setFixedHeight(28)
            tip_parts = [
                f"{t('filter_date_from')}: {getattr(item, 'filter_date_start', '') or t('url_filter_any')}",
                f"{t('filter_date_to')}: {getattr(item, 'filter_date_end', '') or t('url_filter_any')}",
                f"{t('media_type')}: "
                + {
                    "all": t("media_all"),
                    "image": t("media_image"),
                    "video": t("media_video"),
                }.get(getattr(item, "media_type", "all") or "all", t("media_all")),
            ]
            filter_btn.setToolTip("\n".join(tip_parts))
            filter_btn.clicked.connect(lambda _=False, row=i: self._open_url_filter_dialog(row))
            self.url_table.setCellWidget(i, self.COL_FILTER, filter_btn)

            last_download = item.last_download_time
            if last_download:
                try:
                    dt = datetime.fromisoformat(last_download)
                    last_download = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
            self.url_table.setItem(i, self.COL_LAST_DOWNLOAD, QTableWidgetItem(last_download))

            status_text = t(item.status) if item.status else item.status
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(self._get_status_color(item.status))
            self.url_table.setItem(i, self.COL_STATUS, status_item)

            del_btn = QPushButton(t("row_delete"))
            del_btn.setObjectName("rowDeleteBtn")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _=False, row=i: self._delete_url_at(row))
            self.url_table.setCellWidget(i, self.COL_DELETE, del_btn)

        self._updating_url_table = False

    def _row_checkbox(self, row: int) -> Optional[QCheckBox]:
        wrap = self.url_table.cellWidget(row, self.COL_CHECK)
        if wrap is None:
            return None
        if isinstance(wrap, QCheckBox):
            return wrap
        inner = getattr(wrap, "_check", None)
        if isinstance(inner, QCheckBox):
            return inner
        for child in wrap.findChildren(QCheckBox):
            return child
        return None

    def _get_status_color(self, status: str) -> QColor:
        colors = {
            "pending": QColor("#94A3B8"),
            "running": QColor("#22D3EE"),
            "completed": QColor("#22C55E"),
            "failed": QColor("#EF4444"),
            "skipped": QColor("#F59E0B"),
        }
        return colors.get(status, QColor("#94A3B8"))

    def _format_media_counts(self, item) -> str:
        images = int(getattr(item, "image_count", 0) or 0)
        videos = int(getattr(item, "video_count", 0) or 0)
        return t("media_count_fmt", images=images, videos=videos)

    def _refresh_media_counts(self, index: Optional[int] = None, *, save: bool = False):
        dest = self.config_store.config.dest_folder
        urls = self.config_store.config.urls
        indices = range(len(urls)) if index is None else [index]
        for i in indices:
            if not (0 <= i < len(urls)):
                continue
            images, videos = count_media_for_url(dest, urls[i].url)
            self.config_store.set_url_media_counts(i, images, videos)
            if i < self.url_table.rowCount():
                counts_item = QTableWidgetItem(self._format_media_counts(urls[i]))
                counts_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                counts_item.setToolTip(t("media_count_tip"))
                self.url_table.setItem(i, self.COL_COUNTS, counts_item)
        if save:
            self.config_store.save()

    def _add_url(self):
        self._sync_url_table_to_config()
        url = self.url_input.text().strip()
        if not url:
            self._update_start_button()
            return
        idx = self.config_store.add_url(url)
        if idx < 0:
            QMessageBox.information(self, t("url_list"), t("url_duplicate"))
            self.status_bar.showMessage(t("url_duplicate"), 4000)
            return
        self._refresh_media_counts(idx)
        self._update_url_table()
        self.url_input.clear()
        self.config_store.save()
        self._update_start_button()

    def _delete_url_at(self, row: int):
        self._sync_url_table_to_config()
        if 0 <= row < len(self.config_store.config.urls):
            self.config_store.remove_urls([row])
            self._update_url_table()
            self.config_store.save()
            self._update_start_button()

    def _date_filter_valid(self) -> bool:
        self._sync_url_table_to_config()
        for item in self.config_store.config.urls:
            start_s = item.filter_date_start or ""
            end_s = item.filter_date_end or ""
            if not start_s or not end_s:
                continue
            start = QDate.fromString(start_s, "yyyy-MM-dd")
            end = QDate.fromString(end_s, "yyyy-MM-dd")
            if start.isValid() and end.isValid() and start > end:
                return False
        return True

    def _browse_cookies_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("select_cookies"),
            "",
            "Cookie Files (*.txt);;All Files (*)",
        )
        if path:
            self.cookies_file_input.setText(path)
            self._refresh_account_status()

    def _browse_ffmpeg_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("select_ffmpeg"),
            "",
            "ffmpeg (ffmpeg.exe);;Executable (*.exe);;All Files (*)"
            if sys.platform.startswith("win")
            else "ffmpeg (*);;All Files (*)",
        )
        if path:
            self.ffmpeg_path_input.setText(path)
            self._apply_ffmpeg_path_from_config()
            self._refresh_account_status()

    def _apply_ffmpeg_path_from_config(self):
        from .installer import DependencyInstaller

        path = getattr(self.config_store.config, "ffmpeg_path", "") or ""
        if hasattr(self, "ffmpeg_path_input"):
            path = self.ffmpeg_path_input.text().strip() or path
        DependencyInstaller.set_configured_ffmpeg_path(path)
        try:
            self.watermark_processor.ffmpeg_cmd = self.watermark_processor._find_ffmpeg()
            self.watermark_processor._installed = None
            self.watermark_processor._accel = None
        except Exception:
            pass

    def _browse_file(self, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, t("select_file"))
        if path:
            line_edit.setText(path)

    def _browse_folder(self, line_edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, t("select_folder"))
        if path:
            line_edit.setText(path)
            self._update_start_button()

    def _refresh_wm_font_label(self):
        from .watermark import find_douyin_font

        path = find_douyin_font(getattr(self.config_store.config.watermark, "font_path", "") or "")
        if path:
            self.wm_font_label.setText(t("wm_font_ok", path=os.path.basename(path)))
        else:
            self.wm_font_label.setText(t("wm_font_missing"))

    def _on_watermark_mode_changed(self, *_args):
        is_text = self.wm_mode_text.isChecked()
        self.wm_image_row.setVisible(not is_text)
        self.wm_text_row.setVisible(is_text)
        self.wm_font_label.setVisible(is_text)
        self.wm_outline_label.setVisible(is_text)
        self.watermark_outline.setVisible(is_text)
        # adaptive only meaningful for image overlay
        self.watermark_adaptive.setVisible(not is_text)
        self._refresh_wm_font_label()
        self._on_watermark_toggled(self.watermark_enabled.isChecked())

    def _on_watermark_toggled(self, state):
        if isinstance(state, bool):
            enabled = state
        else:
            enabled = state == Qt.CheckState.Checked.value
        is_text = self.wm_mode_text.isChecked()
        self.wm_mode_image.setEnabled(enabled)
        self.wm_mode_text.setEnabled(enabled)
        self.watermark_path_input.setEnabled(enabled and not is_text)
        self.select_watermark_btn.setEnabled(enabled and not is_text)
        self.watermark_text_input.setEnabled(enabled and is_text)
        self.watermark_scale.setEnabled(enabled)
        self.watermark_adaptive.setEnabled(enabled and not is_text)
        self.watermark_outline.setEnabled(enabled and is_text)
        for btn in [self.position_tl, self.position_tr, self.position_bl, self.position_br, self.position_center]:
            btn.setEnabled(enabled)

    def _select_watermark(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("select_watermark"),
            "",
            "PNG Files (*.png);;All Files (*)",
        )
        if path:
            self.watermark_path_input.setText(path)

    def _collect_config_from_ui(self):
        self._sync_url_table_to_config()
        cfg = self.config_store.config
        cfg.dest_folder = self.dest_folder_input.text().strip()
        cfg.cookies_file = self.cookies_file_input.text().strip()
        if hasattr(self, "ffmpeg_path_input"):
            cfg.ffmpeg_path = self.ffmpeg_path_input.text().strip()
        self._apply_ffmpeg_path_from_config()
        cfg.write_metadata = self.write_metadata_check.isChecked()
        cfg.write_info_json = self.write_info_json_check.isChecked()
        cfg.sleep_min = self.sleep_min.value()
        cfg.sleep_max = self.sleep_max.value()
        cfg.sleep_request_min = self.sleep_req_min.value()
        cfg.sleep_request_max = self.sleep_req_max.value()
        cfg.sleep_429 = self.sleep_429.value()
        cfg.verbose = self.verbose_checkbox.isChecked()

        cfg.watermark.enabled = self.watermark_enabled.isChecked()
        cfg.watermark.mode = "text" if self.wm_mode_text.isChecked() else "image"
        cfg.watermark.image_path = self.watermark_path_input.text().strip()
        cfg.watermark.text = self.watermark_text_input.text().strip()
        cfg.watermark.outline_width = self.watermark_outline.value()
        cfg.watermark.scale_ratio = self.watermark_scale.value()
        cfg.watermark.adaptive = self.watermark_adaptive.isChecked()
        # keep colors / font defaults unless user customized in config file
        if not getattr(cfg.watermark, "text_color", ""):
            cfg.watermark.text_color = "white"
        if not getattr(cfg.watermark, "outline_color", ""):
            cfg.watermark.outline_color = "black"

        if self.position_tl.isChecked():
            cfg.watermark.position = "top-left"
        elif self.position_tr.isChecked():
            cfg.watermark.position = "top-right"
        elif self.position_bl.isChecked():
            cfg.watermark.position = "bottom-left"
        elif self.position_br.isChecked():
            cfg.watermark.position = "bottom-right"
        elif self.position_center.isChecked():
            cfg.watermark.position = "center"

    def _save_config(self):
        self._collect_config_from_ui()
        if not self._date_filter_valid():
            QMessageBox.warning(self, t("validation_error"), t("date_range_invalid"))
            return
        if self.config_store.save():
            self._append_log(f"[{self._timestamp()}] Config saved successfully")
        else:
            self._append_log(f"[{self._timestamp()}] Failed to save config")

    def _load_config(self):
        if self.config_store.load():
            self._load_config_to_ui()
            self._append_log(f"[{self._timestamp()}] Config loaded successfully")
        else:
            self._append_log(f"[{self._timestamp()}] Failed to load config")

    def _check_dependencies(self):
        if hasattr(self, "check_deps_btn"):
            self.check_deps_btn.setEnabled(False)
        if hasattr(self, "settings_check_deps_btn"):
            self.settings_check_deps_btn.setEnabled(False)
        self._append_log(f"[{self._timestamp()}] {t('checking_deps')}")
        self.status_bar.showMessage(t("checking_deps"), 0)
        threading.Thread(target=self._check_dependencies_thread, daemon=True).start()

    def _check_dependencies_thread(self):
        summary_lines: List[str] = []
        try:
            status, missing = check_all_dependencies()

            for name, info in status.items():
                if info["installed"]:
                    line = f"{name}: {info['version']}"
                    self.signals.log_signal.emit(f"[{self._timestamp()}] {line}")
                    summary_lines.append(f"✓ {line}")
                else:
                    line = f"{name}: NOT FOUND"
                    self.signals.log_signal.emit(f"[{self._timestamp()}] {line}")
                    summary_lines.append(f"✗ {line}")

            if not missing:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('all_deps_installed')}")
                self.signals.deps_done_signal.emit(
                    t("all_deps_installed") + "\n\n" + "\n".join(summary_lines),
                    True,
                )
                return

            still_missing = ", ".join(missing.keys())
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('missing_deps', deps=still_missing)}")
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('auto_installing')}")

            self._install_dependencies_thread(missing)

            status2, still = check_all_dependencies()
            summary_lines = []
            for name, info in status2.items():
                if info["installed"]:
                    summary_lines.append(f"✓ {name}: {info['version']}")
                else:
                    summary_lines.append(f"✗ {name}: NOT FOUND")

            if not still:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('all_deps_done')}")
                msg = t("all_deps_done") + "\n\n" + "\n".join(summary_lines)
                self.signals.deps_done_signal.emit(msg, True)
            else:
                missing_list = ", ".join(still.keys())
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('still_missing', deps=missing_list)}")
                tips: List[str] = [t("auto_install_failed_title"), "", *summary_lines, ""]
                if "ffmpeg" in still:
                    tips.append(t("manual_install_ffmpeg"))
                    tips.append("")
                if "gallery-dl" in still:
                    tips.append(t("manual_install_gallery_dl"))
                    tips.append("")
                tips.append(t("manual_install_footer"))
                msg = "\n".join(tips)
                for line in msg.splitlines():
                    if line.strip():
                        self.signals.log_signal.emit(f"[{self._timestamp()}] {line}")
                self.signals.deps_done_signal.emit(msg, False)
        except Exception as e:
            self.signals.log_signal.emit(f"[{self._timestamp()}] deps check error: {e}")
            self.signals.deps_done_signal.emit(t("deps_check_failed", error=str(e)), False)

    def _on_deps_check_finished(self, message: str, success: bool = True):
        if hasattr(self, "check_deps_btn"):
            self.check_deps_btn.setEnabled(True)
        if hasattr(self, "settings_check_deps_btn"):
            self.settings_check_deps_btn.setEnabled(True)
        self._refresh_account_status()
        try:
            self.watermark_processor.ffmpeg_cmd = self.watermark_processor._find_ffmpeg()
            self.watermark_processor._installed = None
        except Exception:
            pass
        self.status_bar.showMessage(
            t("ready") if success else t("auto_install_failed_title"),
            5000,
        )
        if success:
            QMessageBox.information(self, t("check_deps"), message)
        else:
            QMessageBox.warning(self, t("check_deps"), message)

    def _install_dependencies(self, missing: dict):
        self._append_log(f"[{self._timestamp()}] Starting dependency installation...")
        threading.Thread(target=self._install_dependencies_thread, args=(missing,), daemon=True).start()

    def _install_dependencies_thread(self, missing: dict):
        installer = DependencyInstaller()

        def on_progress(msg):
            self.signals.log_signal.emit(f"[{self._timestamp()}] {msg}")

        if "gallery-dl" in missing:
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('installing_gallery_dl')}")
            ok, msg = installer.install_gallery_dl(on_progress)
            if ok:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('gallery_dl_installed')}")
            else:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('gallery_dl_failed', error=msg)}")

        if "ffmpeg" in missing:
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('installing_ffmpeg')}")
            ok, msg = installer.install_ffmpeg(on_progress)
            if ok:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('ffmpeg_installed')}")
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('ffmpeg_path', path=msg)}")
            else:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('ffmpeg_failed', error=msg)}")

    def _install_gallery_dl_and_continue(self):
        installer = DependencyInstaller()

        def on_progress(msg):
            self.signals.log_signal.emit(f"[{self._timestamp()}] {msg}")

        self.signals.log_signal.emit(f"[{self._timestamp()}] {t('installing_gallery_dl')}")
        ok, msg = installer.install_gallery_dl(on_progress)
        if ok:
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('gallery_dl_installed')}")
            installed, _ = check_gallery_dl_installed()
            if installed:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('ready_to_download')}")
        else:
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('gallery_dl_failed', error=msg)}")
            tip = "\n".join(
                [
                    t("auto_install_failed_title"),
                    "",
                    t("manual_install_gallery_dl"),
                    "",
                    t("manual_install_footer"),
                ]
            )
            self.signals.deps_done_signal.emit(tip, False)

    def _install_ffmpeg_and_continue(self):
        installer = DependencyInstaller()

        def on_progress(msg):
            self.signals.log_signal.emit(f"[{self._timestamp()}] {msg}")

        self.signals.log_signal.emit(f"[{self._timestamp()}] {t('installing_ffmpeg')}")
        ok, msg = installer.install_ffmpeg(on_progress)
        if ok:
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('ffmpeg_installed')}")
            self.watermark_processor._installed = None
            self.watermark_processor._accel = None
            self.watermark_processor.ffmpeg_cmd = self.watermark_processor._find_ffmpeg()
            installed, _ = self.watermark_processor.is_installed()
            if installed:
                self.signals.log_signal.emit(f"[{self._timestamp()}] {t('ready_for_watermark')}")
        else:
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('ffmpeg_failed', error=msg)}")
            tip = "\n".join(
                [
                    t("auto_install_failed_title"),
                    "",
                    t("manual_install_ffmpeg"),
                    "",
                    t("manual_install_footer"),
                ]
            )
            self.signals.deps_done_signal.emit(tip, False)

    def _update_start_button(self):
        has_urls = len(self.config_store.config.urls) > 0
        has_dest = bool(self.dest_folder_input.text().strip())
        self.start_btn.setEnabled(has_urls and has_dest and not self.is_running)
        if hasattr(self, "pause_btn"):
            self.pause_btn.setEnabled(self.is_running)
            self._refresh_pause_button_text()

    def _refresh_pause_button_text(self):
        if not hasattr(self, "pause_btn"):
            return
        self.pause_btn.setText(t("resume") if self.is_paused else t("pause"))

    def _wait_while_paused(self):
        """Block worker threads until resumed or stopped."""
        while self.is_running and self.is_paused:
            self._pause_gate.wait(timeout=0.4)

    def _safe_resume_downloads(self):
        """Resume gallery-dl only if user has not paused."""
        if self.is_running and not self.is_paused:
            self.executor.resume_all()

    def _timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _append_log(self, message: str):
        self.log_output.append(message)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_url_counts_refresh(self, index: int):
        self._refresh_media_counts(index, save=True)

    def _update_url_status(self, index: int, status: str):
        self.config_store.set_url_status(index, status)
        if 0 <= index < self.url_table.rowCount():
            status_text = t(status) if status else status
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(self._get_status_color(status))
            self.url_table.setItem(index, self.COL_STATUS, status_item)

    def _update_watermark_progress(self, current: int, total: int, message: str):
        self.watermark_progress.setMaximum(total)
        self.watermark_progress.setValue(current)
        self._append_log(f"[{self._timestamp()}] {message}")

    def _on_all_finished(self):
        self.is_running = False
        self.is_paused = False
        self._pause_gate.set()
        self._refresh_account_status()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self._refresh_pause_button_text()
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage(t("all_completed"), 5000)
        self._update_start_button()
        done = self.wm_pipeline.done_files
        if done:
            self._append_log(
                f"[{self._timestamp()}] {t('watermark_applied', count=len(done))}"
            )

    def _configure_wm_pipeline(self):
        wm = self.config_store.config.watermark
        settings = {
            "mode": getattr(wm, "mode", "image") or "image",
            "watermark_path": wm.image_path,
            "text": getattr(wm, "text", "") or "X-Track水印",
            "font_path": getattr(wm, "font_path", "") or "",
            "text_color": getattr(wm, "text_color", "white") or "white",
            "outline_color": getattr(wm, "outline_color", "black") or "black",
            "outline_width": int(getattr(wm, "outline_width", 3) or 3),
            "position": wm.position,
            "scale_ratio": wm.scale_ratio,
            "adaptive": getattr(wm, "adaptive", True),
        }
        if settings["mode"] != "text":
            wp = settings.get("watermark_path") or ""
            if wp and not os.path.isabs(wp):
                for base in (resource_dir(), os.path.dirname(os.path.abspath(__file__))):
                    cand = os.path.join(base, wp)
                    if os.path.isfile(cand):
                        settings["watermark_path"] = cand
                        break
            if not settings.get("watermark_path") or not os.path.isfile(settings["watermark_path"]):
                try:
                    from .watermark import ensure_default_watermark_png

                    settings["watermark_path"] = ensure_default_watermark_png()
                except Exception:
                    pass

        self.wm_pipeline.reset()
        self.wm_pipeline.configure(
            enabled=bool(wm.enabled),
            settings=settings,
            on_log=lambda m: self.signals.log_signal.emit(f"[{self._timestamp()}] {m}"),
            suspend=self.executor.suspend_all,
            resume=self._safe_resume_downloads,
            wait_if_paused=self._wait_while_paused,
        )
        self._wm_stop.set()
        if self._wm_watcher:
            self._wm_watcher.join(timeout=1.0)
        self._wm_stop = threading.Event()
        self._wm_watcher = None
        if wm.enabled:
            dest = self.config_store.config.dest_folder
            max_files = int(getattr(self.config_store.config, "max_items", 0) or 0)
            # soft cap for watcher across all URLs
            watcher_max = max_files * max(1, int(getattr(self.config_store.config, "max_parallel", 3) or 3)) if max_files else 0
            watcher_max = min(watcher_max, 100) if watcher_max else 0

            def on_limit():
                self.signals.log_signal.emit(
                    f"[{self._timestamp()}] Watermark file limit reached — stopping downloads"
                )
                self.is_running = False
                self.executor.cancel()

            self._wm_watcher = DestMediaWatcher(
                dest,
                self.wm_pipeline,
                self._wm_stop,
                max_files=watcher_max,
                on_limit=on_limit,
            )
            seeded = self._wm_watcher.seed_existing()
            self._wm_watcher.start()
            self.signals.log_signal.emit(
                f"[{self._timestamp()}] Inline watermark ON ({settings['mode']}), "
                f"worker thread + queue max=1, folder watcher (seeded {seeded})"
            )

    def _on_start_clicked(self):
        self._collect_config_from_ui()
        self.config_store.save()

        if not self._date_filter_valid():
            QMessageBox.warning(self, t("validation_error"), t("date_range_invalid"))
            return

        valid, msg = self.command_builder.validate(self.config_store.config)
        if not valid:
            QMessageBox.warning(self, t("validation_error"), t(msg))
            return

        installed, path = check_gallery_dl_installed()
        if not installed:
            reply = QMessageBox.question(
                self,
                t("gallery_dl_not_found_title"),
                t("gallery_dl_not_found_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                threading.Thread(
                    target=self._install_gallery_dl_and_continue,
                    daemon=True
                ).start()
                return
            else:
                return

        self.is_running = True
        self.is_paused = False
        self._pause_gate.set()
        self._refresh_account_status()
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self._refresh_pause_button_text()
        self.stop_btn.setEnabled(True)
        self.status_bar.showMessage(t("status_running"))

        urls = self.config_store.config.urls
        pending_urls = [
            (i, u.url)
            for i, u in enumerate(urls)
            if getattr(u, "selected", True)
            and u.status in ("pending", "failed", "skipped", "completed")
        ]

        if not pending_urls:
            QMessageBox.information(self, t("no_tasks"), t("no_selected_urls"))
            self.is_running = False
            self._refresh_account_status()
            self._update_start_button()
            return

        for i, _ in pending_urls:
            if urls[i].status in ("completed", "skipped", "failed"):
                self.config_store.set_url_status(i, "pending")
        self._update_url_table()

        self.current_index = 0
        self._append_log(f"[{self._timestamp()}] {t('starting_download', count=len(pending_urls))}")
        self._configure_wm_pipeline()
        threading.Thread(target=self._run_downloads, args=(pending_urls,), daemon=True).start()

    def _run_downloads(self, pending_urls: List[tuple]):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from datetime import datetime

        max_workers = max(1, int(getattr(self.config_store.config, "max_parallel", 3) or 3))
        max_workers = min(max_workers, len(pending_urls))
        self.signals.log_signal.emit(
            f"[{self._timestamp()}] Parallel workers: {max_workers}"
        )

        def run_one(idx: int, url: str):
            self._wait_while_paused()
            if not self.is_running:
                return

            self.signals.status_signal.emit(idx, "running")
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('processing', url=url)}")

            url_item = self.config_store.config.urls[idx]
            last_download_time = url_item.last_download_time

            if last_download_time:
                self.signals.log_signal.emit(
                    f"[{self._timestamp()}] {t('auto_filter', time=last_download_time)}"
                )

            cmd = self.command_builder.build(
                url,
                self.config_store.config,
                last_download_time,
                url_item=url_item,
            )
            dest = self.config_store.config.dest_folder
            if dest:
                self.signals.log_signal.emit(
                    f"[{self._timestamp()}] {t('download_archive', path=download_archive_path(dest))}"
                )
            self.signals.log_signal.emit(f"[{self._timestamp()}] {t('command', cmd=' '.join(cmd))}")

            def on_output(line):
                self._wait_while_paused()
                if not self.is_running:
                    return
                self.signals.log_signal.emit(line)
                try:
                    self.wm_pipeline.handle_output_line(line)
                except Exception as e:
                    self.signals.log_signal.emit(f"[{self._timestamp()}] watermark hook: {e}")

            def on_complete(code, _idx=idx, _url=url):
                dest = self.config_store.config.dest_folder
                if code == 0:
                    self.signals.status_signal.emit(_idx, "completed")
                    now = datetime.now().isoformat()
                    self.config_store.set_url_last_download_time(_idx, now)
                    self.signals.log_signal.emit(
                        f"[{self._timestamp()}] {t('completed_msg', url=_url)} @ {now}"
                    )
                    try:
                        path = update_manifest(
                            dest,
                            source_url=_url,
                            status="completed",
                            last_download_time=now,
                        )
                        if path:
                            self.signals.log_signal.emit(
                                f"[{self._timestamp()}] {t('manifest_updated', path=path)}"
                            )
                    except Exception as e:
                        self.signals.log_signal.emit(
                            f"[{self._timestamp()}] manifest error: {e}"
                        )
                else:
                    status = "skipped" if not self.is_running else "failed"
                    self.signals.status_signal.emit(_idx, status)
                    self.signals.log_signal.emit(
                        f"[{self._timestamp()}] {t('failed_msg', code=code, url=_url)}"
                    )
                    try:
                        update_manifest(dest, source_url=_url, status=status)
                    except Exception:
                        pass
                self.signals.counts_signal.emit(_idx)

            self.executor.run(cmd, on_output, on_complete)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(run_one, idx, url) for idx, url in pending_urls]
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as e:
                    self.signals.log_signal.emit(f"[{self._timestamp()}] worker error: {e}")
                if not self.is_running:
                    self.executor.cancel()
                    for pending in futures:
                        pending.cancel()
                    break

        self._wm_stop.set()
        if self._wm_watcher:
            self._wm_watcher.join(timeout=2.0)
            # Catch files finished while the last watermark jobs were running.
            # Two passes so size-stability (>=0.3s) can elapse for brand-new files.
            try:
                self._wm_watcher.flush_once()
                time.sleep(0.4)
                self._wm_watcher.flush_once()
            except Exception:
                pass
            self._wm_watcher = None
        if self.wm_pipeline.enabled:
            pending = self.wm_pipeline.pending_count
            if pending:
                self.signals.log_signal.emit(
                    f"[{self._timestamp()}] Waiting for {pending} watermark job(s) to finish..."
                )
            if not self.wm_pipeline.drain(timeout=3600):
                self.signals.log_signal.emit(
                    f"[{self._timestamp()}] Watermark drain timed out "
                    f"(remaining={self.wm_pipeline.pending_count})"
                )
        self.signals.finished_signal.emit()

    def _on_pause_clicked(self):
        if not self.is_running:
            return
        if not self.is_paused:
            self.is_paused = True
            self._pause_gate.clear()
            self.executor.suspend_all()
            self._refresh_pause_button_text()
            self._refresh_account_status()
            self._append_log(f"[{self._timestamp()}] {t('pausing')}")
            self.status_bar.showMessage(t("status_paused"))
        else:
            self.is_paused = False
            self._pause_gate.set()
            self.executor.resume_all()
            self._refresh_pause_button_text()
            self._refresh_account_status()
            self._append_log(f"[{self._timestamp()}] {t('resuming')}")
            self.status_bar.showMessage(t("status_running"))

    def _on_stop_clicked(self):
        self.is_running = False
        self.is_paused = False
        self._pause_gate.set()
        self._wm_stop.set()
        self.wm_pipeline.shutdown(timeout=2.0)
        self._refresh_account_status()
        self.executor.cancel()
        self._append_log(f"[{self._timestamp()}] {t('stopping')}")
        self.status_bar.showMessage(t("stopping"))

        for i, u in enumerate(self.config_store.config.urls):
            if u.status == "running":
                self.signals.status_signal.emit(i, "skipped")

        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self._refresh_pause_button_text()
        self.stop_btn.setEnabled(False)
        self._update_start_button()

    def _apply_watermark_to_all(self):
        dest_folder = self.config_store.config.dest_folder
        if not dest_folder or not os.path.isdir(dest_folder):
            self._append_log(f"[{self._timestamp()}] {t('watermark_skipped')}")
            return

        installed, _ = self.watermark_processor.is_installed()
        if not installed:
            reply = QMessageBox.question(
                self,
                t("ffmpeg_not_found_title"),
                t("ffmpeg_not_found_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                threading.Thread(
                    target=self._install_ffmpeg_and_continue,
                    daemon=True
                ).start()
            return

        self._append_log(f"[{self._timestamp()}] Applying watermark...")
        accel = self.watermark_processor.get_acceleration_info()
        self._append_log(
            f"[{self._timestamp()}] {t('watermark_accel', mode=accel['label'])}"
        )
        self.watermark_progress.setVisible(True)

        def on_progress(current, total, msg):
            self.signals.progress_signal.emit(current, total, msg)

        wm = self.config_store.config.watermark
        success, msg = self.watermark_processor.apply_watermark(
            dest_folder,
            position=wm.position,
            scale_ratio=wm.scale_ratio,
            adaptive=getattr(wm, "adaptive", True),
            mode=getattr(wm, "mode", "image") or "image",
            watermark_path=wm.image_path,
            text=getattr(wm, "text", "") or "",
            font_path=getattr(wm, "font_path", "") or "",
            text_color=getattr(wm, "text_color", "white") or "white",
            outline_color=getattr(wm, "outline_color", "black") or "black",
            outline_width=int(getattr(wm, "outline_width", 3) or 3),
            on_progress=on_progress,
        )

        self.watermark_progress.setVisible(False)
        self._append_log(f"[{self._timestamp()}] Watermark: {msg}")

    def closeEvent(self, event):
        if self.is_running:
            reply = QMessageBox.question(
                self,
                t("confirm_exit"),
                t("downloads_in_progress"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            self.executor.cancel()

        self._collect_config_from_ui()
        self.config_store.save()
        event.accept()
