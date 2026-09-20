"""Standalone batch-watermark window."""

from __future__ import annotations

import json
import os
import threading

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QCheckBox,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .batch_watermark import BatchJob, BatchResult, BatchWatermarker, _is_video, list_media, paths_overlap
from .config_store import ConfigStore
from .i18n import t
from .installer import DependencyInstaller
from .paths import data_dir
from .watermark import find_douyin_font

_PREFS = "wmtool.json"
_COLORS = (
    ("wmtool_white", "white"),
    ("wmtool_black", "black"),
    ("wmtool_yellow", "yellow"),
    ("wmtool_red", "red"),
    ("wmtool_cyan", "cyan"),
)
_POSITIONS = (
    ("top-left", "pos_tl"),
    ("top-right", "pos_tr"),
    ("bottom-left", "pos_bl"),
    ("bottom-right", "pos_br"),
    ("center", "pos_center"),
)


def _prefs_path() -> str:
    return os.path.join(data_dir(), _PREFS)


class _ScanThread(QThread):
    counted = pyqtSignal(int, int, int)

    def __init__(self, generation: int, folder: str, recursive: bool):
        super().__init__()
        self.generation = generation
        self.folder = folder
        self.recursive = recursive

    def run(self) -> None:
        files = list_media(self.folder, self.recursive) if self.folder else []
        images = sum(1 for path in files if not _is_video(path))
        self.counted.emit(self.generation, images, len(files) - images)


class _RunThread(QThread):
    tick = pyqtSignal(int, int, str, str, str)
    finished_with = pyqtSignal(object)

    def __init__(self, job: BatchJob):
        super().__init__()
        self.job = job
        self.cancel = threading.Event()

    def run(self) -> None:
        prev = DependencyInstaller._configured_path
        if self.job.ffmpeg_path:
            DependencyInstaller.set_configured_ffmpeg_path(self.job.ffmpeg_path)
        try:
            result = BatchWatermarker().run(
                self.job,
                self.cancel,
                lambda *args: self.tick.emit(*args),
            )
        except Exception as exc:
            result = BatchResult(error_key="wmtool_failed")
            result.files = [str(exc)]
        finally:
            DependencyInstaller._configured_path = prev
        self.finished_with.emit(result)


class WatermarkToolWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(820, 620)
        self.resize(900, 700)
        self._scan_gen = 0
        self._scan_thread: _ScanThread | None = None
        self._runner: _RunThread | None = None
        self._images = 0
        self._videos = 0
        self._ffmpeg_ok = False
        self._ffmpeg_path = ""
        self._config_store = ConfigStore()
        self._build()
        self._load_prefs()
        self.apply_i18n()
        self._sync_modes()
        self._refresh_ffmpeg()
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.timeout.connect(self._start_scan)
        self._schedule_scan()

    def _build(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 14, 16, 12)
        outer.setSpacing(10)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title_label = QLabel()
        self.title_label.setStyleSheet(
            "color: #F8FAFC; font-size: 20px; font-weight: 700; background: transparent;"
        )
        self.sub_label = QLabel()
        self.sub_label.setWordWrap(True)
        self.sub_label.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        titles.addWidget(self.title_label)
        titles.addWidget(self.sub_label)
        header.addLayout(titles, 1)

        ff_wrap = QHBoxLayout()
        ff_wrap.setSpacing(8)
        self.ffmpeg_state = QLabel()
        self.ffmpeg_state.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.ffmpeg_cfg_btn = QPushButton()
        self.ffmpeg_cfg_btn.setObjectName("warningBtn")
        self.ffmpeg_cfg_btn.setMinimumHeight(30)
        self.ffmpeg_cfg_btn.clicked.connect(self._browse_ffmpeg)
        self.ffmpeg_cfg_btn.setVisible(False)
        ff_wrap.addWidget(self.ffmpeg_state)
        ff_wrap.addWidget(self.ffmpeg_cfg_btn)
        header.addLayout(ff_wrap)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        form = QVBoxLayout(host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)

        # —— Source + output ——
        self.io_box = QGroupBox()
        io = QVBoxLayout(self.io_box)
        io.setSpacing(8)

        folder_row = QHBoxLayout()
        self.folder_label = QLabel()
        self.folder_edit = QLineEdit()
        self.folder_edit.textChanged.connect(self._schedule_scan)
        self.folder_btn = QPushButton()
        self.folder_btn.setFixedWidth(72)
        self.folder_btn.clicked.connect(self._browse_folder)
        self.folder_open = QPushButton()
        self.folder_open.setFixedWidth(72)
        self.folder_open.clicked.connect(lambda: self._open_path(self.folder_edit.text()))
        folder_row.addWidget(self.folder_label)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(self.folder_btn)
        folder_row.addWidget(self.folder_open)
        io.addLayout(folder_row)

        scan_row = QHBoxLayout()
        self.subdirs = QCheckBox()
        self.subdirs.setChecked(True)
        self.subdirs.toggled.connect(self._schedule_scan)
        self.scan_label = QLabel()
        self.scan_label.setStyleSheet("color: #22D3EE; font-weight: 600; background: transparent;")
        scan_row.addWidget(self.subdirs)
        scan_row.addStretch()
        scan_row.addWidget(self.scan_label)
        io.addLayout(scan_row)

        out_row = QHBoxLayout()
        self.out_group = QButtonGroup(self)
        self.out_overwrite = QRadioButton()
        self.out_copy = QRadioButton()
        self.out_overwrite.setObjectName("chipRadio")
        self.out_copy.setObjectName("chipRadio")
        self.out_copy.setChecked(True)
        self.out_group.addButton(self.out_overwrite, 0)
        self.out_group.addButton(self.out_copy, 1)
        self.out_group.idClicked.connect(lambda _i: self._sync_modes())
        out_row.addWidget(self.out_overwrite)
        out_row.addWidget(self.out_copy)
        out_row.addStretch()
        io.addLayout(out_row)

        dest_row = QHBoxLayout()
        self.dest_label = QLabel()
        self.dest_edit = QLineEdit()
        self.dest_btn = QPushButton()
        self.dest_btn.setFixedWidth(72)
        self.dest_btn.clicked.connect(self._browse_dest)
        self.dest_open = QPushButton()
        self.dest_open.setFixedWidth(72)
        self.dest_open.clicked.connect(lambda: self._open_path(self.dest_edit.text()))
        dest_row.addWidget(self.dest_label)
        dest_row.addWidget(self.dest_edit, 1)
        dest_row.addWidget(self.dest_btn)
        dest_row.addWidget(self.dest_open)
        io.addLayout(dest_row)
        self.out_hint = QLabel()
        self.out_hint.setWordWrap(True)
        self.out_hint.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        io.addWidget(self.out_hint)
        form.addWidget(self.io_box)

        # —— Watermark + placement (collapsed by default) ——
        self.style_box = QGroupBox()
        self.style_box.setCheckable(True)
        self.style_box.setChecked(False)
        self.style_box.setFlat(False)
        style_outer = QVBoxLayout(self.style_box)
        style_outer.setContentsMargins(10, 8, 10, 10)
        style_outer.setSpacing(0)

        self.style_body = QWidget()
        self.style_body.setVisible(False)
        mark = QVBoxLayout(self.style_body)
        mark.setContentsMargins(0, 6, 0, 0)
        mark.setSpacing(8)
        style_outer.addWidget(self.style_body)
        self.style_box.toggled.connect(self._on_style_toggled)

        kind_row = QHBoxLayout()
        self.kind_group = QButtonGroup(self)
        self.kind_text = QRadioButton()
        self.kind_image = QRadioButton()
        self.kind_text.setObjectName("chipRadio")
        self.kind_image.setObjectName("chipRadio")
        self.kind_text.setChecked(True)
        self.kind_group.addButton(self.kind_text, 0)
        self.kind_group.addButton(self.kind_image, 1)
        self.kind_group.idClicked.connect(lambda _i: self._sync_modes())
        kind_row.addWidget(self.kind_text)
        kind_row.addWidget(self.kind_image)
        kind_row.addStretch()
        mark.addLayout(kind_row)

        self.text_row = QWidget()
        text_layout = QHBoxLayout(self.text_row)
        text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_label = QLabel()
        self.text_edit = QLineEdit()
        self.text_edit.setMaxLength(80)
        self.color_label = QLabel()
        self.color_combo = QComboBox()
        self.color_combo.setFixedWidth(120)
        for key, value in _COLORS:
            self.color_combo.addItem(key, value)
        text_layout.addWidget(self.text_label)
        text_layout.addWidget(self.text_edit, 1)
        text_layout.addWidget(self.color_label)
        text_layout.addWidget(self.color_combo)
        mark.addWidget(self.text_row)

        self.font_label = QLabel()
        self.font_label.setWordWrap(True)
        self.font_label.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        mark.addWidget(self.font_label)

        self.image_row = QWidget()
        image_layout = QHBoxLayout(self.image_row)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel()
        self.image_edit = QLineEdit()
        self.image_btn = QPushButton()
        self.image_btn.setFixedWidth(72)
        self.image_btn.clicked.connect(self._browse_image)
        image_layout.addWidget(self.image_label)
        image_layout.addWidget(self.image_edit, 1)
        image_layout.addWidget(self.image_btn)
        mark.addWidget(self.image_row)

        opt = QGridLayout()
        opt.setHorizontalSpacing(10)
        opt.setVerticalSpacing(8)
        self.scale_label = QLabel()
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(3, 30)
        self.scale_spin.setValue(8)
        self.scale_spin.setSuffix(" %")
        self.opacity_label = QLabel()
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(10, 100)
        self.opacity_spin.setValue(85)
        self.opacity_spin.setSuffix(" %")
        self.fade_label = QLabel()
        self.fade_spin = QDoubleSpinBox()
        self.fade_spin.setRange(0.0, 3.0)
        self.fade_spin.setSingleStep(0.1)
        self.fade_spin.setDecimals(1)
        self.fade_spin.setValue(0.4)
        for col, (label, widget) in enumerate(
            (
                (self.scale_label, self.scale_spin),
                (self.opacity_label, self.opacity_spin),
                (self.fade_label, self.fade_spin),
            )
        ):
            opt.addWidget(label, 0, col * 2)
            opt.addWidget(widget, 0, col * 2 + 1)
        mark.addLayout(opt)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        mark.addWidget(self.hint_label)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #1E293B; background: #1E293B; max-height: 1px;")
        mark.addWidget(divider)

        place_row = QHBoxLayout()
        self.place_group = QButtonGroup(self)
        self.place_fixed = QRadioButton()
        self.place_corners = QRadioButton()
        self.place_random = QRadioButton()
        for btn in (self.place_fixed, self.place_corners, self.place_random):
            btn.setObjectName("chipRadio")
            place_row.addWidget(btn)
        self.place_fixed.setChecked(True)
        self.place_group.addButton(self.place_fixed, 0)
        self.place_group.addButton(self.place_corners, 1)
        self.place_group.addButton(self.place_random, 2)
        self.place_group.idClicked.connect(lambda _i: self._sync_modes())
        place_row.addStretch()
        mark.addLayout(place_row)

        pos_row = QHBoxLayout()
        self.pos_label = QLabel()
        pos_row.addWidget(self.pos_label)
        self.pos_group = QButtonGroup(self)
        self.pos_buttons = {}
        for index, (value, _key) in enumerate(_POSITIONS):
            btn = QRadioButton()
            btn.setObjectName("chipRadio")
            self.pos_group.addButton(btn, index)
            self.pos_buttons[value] = btn
            pos_row.addWidget(btn)
        self.pos_buttons["bottom-right"].setChecked(True)
        pos_row.addStretch()
        mark.addLayout(pos_row)

        refresh_row = QHBoxLayout()
        self.refresh_label = QLabel()
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(1, 120)
        self.refresh_spin.setValue(4)
        self.refresh_spin.valueChanged.connect(lambda _v: self._sync_modes())
        refresh_row.addWidget(self.refresh_label)
        refresh_row.addWidget(self.refresh_spin)
        refresh_row.addStretch()
        mark.addLayout(refresh_row)
        self.place_hint = QLabel()
        self.place_hint.setWordWrap(True)
        self.place_hint.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        mark.addWidget(self.place_hint)
        form.addWidget(self.style_box)

        self.current_label = QLabel()
        self.current_label.setStyleSheet("color: #94A3B8; background: transparent;")
        outer.addWidget(self.current_label)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        outer.addWidget(self.progress)

        actions = QHBoxLayout()
        self.start_btn = QPushButton()
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setMinimumSize(120, 36)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton()
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setMinimumSize(100, 36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        actions.addWidget(self.start_btn)
        actions.addWidget(self.stop_btn)
        actions.addStretch()
        outer.addLayout(actions)

        self.log_box = QGroupBox()
        log_layout = QVBoxLayout(self.log_box)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setAcceptRichText(False)
        self.log.setMinimumHeight(100)
        self.log.setMaximumHeight(150)
        self.log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.log.document().setMaximumBlockCount(400)
        log_layout.addWidget(self.log)
        outer.addWidget(self.log_box)

    def _on_style_toggled(self, checked: bool) -> None:
        self.style_body.setVisible(checked)
        self._update_style_title()

    def _update_style_title(self) -> None:
        if not hasattr(self, "style_box"):
            return
        if self.style_box.isChecked():
            self.style_box.setTitle(t("wmtool_style"))
        else:
            self.style_box.setTitle(t("wmtool_style_collapsed"))

    def apply_i18n(self) -> None:
        self.setWindowTitle(t("wmtool_title"))
        self.title_label.setText(t("wmtool_title"))
        self.sub_label.setText(t("wmtool_sub"))
        self.ffmpeg_cfg_btn.setText(t("wmtool_ffmpeg_cfg"))
        self.io_box.setTitle(t("wmtool_io"))
        self.folder_label.setText(t("wmtool_folder"))
        self.folder_btn.setText(t("browse"))
        self.folder_open.setText(t("wmtool_open"))
        self.subdirs.setText(t("wmtool_subdirs"))
        self._update_style_title()
        self.kind_text.setText(t("wmtool_kind_text"))
        self.kind_image.setText(t("wmtool_kind_image"))
        self.text_label.setText(t("wm_text"))
        self.text_edit.setPlaceholderText(t("wm_text_ph"))
        self.color_label.setText(t("wmtool_color"))
        for index, (key, _value) in enumerate(_COLORS):
            self.color_combo.setItemText(index, t(key))
        self._refresh_font_label()
        self.image_label.setText(t("wm_image"))
        self.image_edit.setPlaceholderText(t("wm_image_ph"))
        self.image_btn.setText(t("browse"))
        self.scale_label.setText(t("wmtool_scale"))
        self.scale_spin.setToolTip(t("wmtool_scale_tip"))
        self.opacity_label.setText(t("wmtool_opacity"))
        self.fade_label.setText(t("wmtool_fade"))
        self.fade_spin.setSuffix(t("wmtool_suffix_sec"))
        self.fade_spin.setToolTip(t("wmtool_fade_tip"))
        self.hint_label.setText(t("wmtool_hint"))
        self.place_fixed.setText(t("wmtool_fixed"))
        self.place_corners.setText(t("wmtool_corners"))
        self.place_random.setText(t("wmtool_random"))
        self.pos_label.setText(t("position"))
        for value, key in _POSITIONS:
            self.pos_buttons[value].setText(t(key))
        self.refresh_label.setText(t("wmtool_refresh"))
        self.refresh_spin.setSuffix(t("wmtool_suffix_sec"))
        self.refresh_spin.setToolTip(t("wmtool_refresh_tip"))
        self.out_overwrite.setText(t("wmtool_overwrite"))
        self.out_copy.setText(t("wmtool_copy"))
        self.dest_label.setText(t("wmtool_out_dir"))
        self.dest_btn.setText(t("browse"))
        self.dest_open.setText(t("wmtool_open"))
        self.out_hint.setText(t("wmtool_overwrite_safe"))
        self.start_btn.setText(t("wmtool_start"))
        self.stop_btn.setText(t("stop"))
        self.log_box.setTitle(t("log_output"))
        self._paint_scan()
        self._sync_modes()
        self._refresh_ffmpeg()

    def _sync_modes(self) -> None:
        text_mode = self.kind_text.isChecked()
        self.text_row.setVisible(text_mode)
        self.font_label.setVisible(text_mode)
        self.image_row.setVisible(not text_mode)
        fixed = self.place_fixed.isChecked()
        for btn in self.pos_buttons.values():
            btn.setEnabled(fixed)
        self.pos_label.setEnabled(fixed)
        self.refresh_spin.setEnabled(not fixed)
        self.refresh_label.setEnabled(not fixed)
        copying = self.out_copy.isChecked()
        self.dest_edit.setEnabled(copying)
        self.dest_btn.setEnabled(copying)
        self.dest_open.setEnabled(copying)
        self.dest_label.setEnabled(copying)
        sec = self.refresh_spin.value()
        if fixed:
            hint = t("wmtool_hint_fixed")
        elif self.place_corners.isChecked():
            hint = t("wmtool_hint_corners", sec=sec)
        else:
            hint = t("wmtool_hint_random", sec=sec)
        self.place_hint.setText(hint)

    def _wm_style(self):
        """Live style from main X-Track watermark settings (font + outline)."""
        try:
            self._config_store.load()
        except Exception:
            pass
        return self._config_store.config.watermark

    def _refresh_font_label(self) -> None:
        if not hasattr(self, "font_label"):
            return
        wm = self._wm_style()
        path = find_douyin_font(getattr(wm, "font_path", "") or "")
        outline = int(getattr(wm, "outline_width", 3) or 0)
        if path:
            self.font_label.setText(
                t("wmtool_font_inherited", path=os.path.basename(path), outline=outline)
            )
        else:
            self.font_label.setText(t("wm_font_missing"))

    def _job(self) -> BatchJob:
        if self.place_fixed.isChecked():
            placement = "fixed"
        elif self.place_corners.isChecked():
            placement = "corners"
        else:
            placement = "random"
        position = "bottom-right"
        for value, btn in self.pos_buttons.items():
            if btn.isChecked():
                position = value
                break
        wm = self._wm_style()
        return BatchJob(
            source_dir=self.folder_edit.text().strip(),
            include_subdirs=self.subdirs.isChecked(),
            kind="text" if self.kind_text.isChecked() else "image",
            text=self.text_edit.text().strip(),
            text_color=str(self.color_combo.currentData() or getattr(wm, "text_color", "white") or "white"),
            font_path=getattr(wm, "font_path", "") or "",
            outline_color=getattr(wm, "outline_color", "black") or "black",
            outline_width=int(getattr(wm, "outline_width", 3) or 0),
            image_path=self.image_edit.text().strip(),
            scale_percent=self.scale_spin.value(),
            opacity=self.opacity_spin.value() / 100.0,
            fade_sec=float(self.fade_spin.value()),
            placement=placement,
            fixed_position=position,
            refresh_sec=float(self.refresh_spin.value()),
            output_mode="overwrite" if self.out_overwrite.isChecked() else "copy",
            output_dir=self.dest_edit.text().strip(),
            ffmpeg_path=self._ffmpeg_path or "",
        )

    def _schedule_scan(self) -> None:
        if hasattr(self, "_scan_timer"):
            self._scan_timer.start(200)

    def _start_scan(self) -> None:
        self._scan_gen += 1
        gen = self._scan_gen
        folder = self.folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            self._images = 0
            self._videos = 0
            self._paint_scan()
            return
        thread = _ScanThread(gen, folder, self.subdirs.isChecked())
        thread.counted.connect(self._on_scanned)
        thread.finished.connect(thread.deleteLater)
        self._scan_thread = thread
        thread.start()

    def _on_scanned(self, generation: int, images: int, videos: int) -> None:
        if generation != self._scan_gen:
            return
        self._images = images
        self._videos = videos
        self._paint_scan()

    def _paint_scan(self) -> None:
        folder = self.folder_edit.text().strip() if hasattr(self, "folder_edit") else ""
        if not folder or not os.path.isdir(folder):
            self.scan_label.setText(t("wmtool_scan_need"))
            self.scan_label.setStyleSheet("color: #64748B; font-weight: 600; background: transparent;")
            return
        if self._images + self._videos <= 0:
            self.scan_label.setText(t("wmtool_scan_none"))
            self.scan_label.setStyleSheet("color: #F59E0B; font-weight: 600; background: transparent;")
            return
        self.scan_label.setText(t("wmtool_scan", images=self._images, videos=self._videos))
        self.scan_label.setStyleSheet("color: #22D3EE; font-weight: 600; background: transparent;")

    def _refresh_ffmpeg(self) -> None:
        if not hasattr(self, "ffmpeg_state"):
            return
        prev = DependencyInstaller._configured_path
        if self._ffmpeg_path:
            DependencyInstaller.set_configured_ffmpeg_path(self._ffmpeg_path)
        found = DependencyInstaller.find_ffmpeg_path()
        DependencyInstaller._configured_path = prev
        self._ffmpeg_ok = bool(found)
        if found:
            self.ffmpeg_state.setText(t("wmtool_ffmpeg_ok"))
            self.ffmpeg_state.setStyleSheet("color: #34D399; font-weight: 600; background: transparent;")
            self.ffmpeg_state.setToolTip(found)
            self.ffmpeg_cfg_btn.setVisible(False)
        else:
            self.ffmpeg_state.setText(t("wmtool_ffmpeg_bad"))
            self.ffmpeg_state.setStyleSheet("color: #F87171; font-weight: 600; background: transparent;")
            self.ffmpeg_state.setToolTip("")
            self.ffmpeg_cfg_btn.setVisible(True)

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, t("wmtool_folder"), self.folder_edit.text().strip())
        if path:
            self.folder_edit.setText(path)

    def _browse_dest(self) -> None:
        path = QFileDialog.getExistingDirectory(self, t("wmtool_out_dir"), self.dest_edit.text().strip())
        if path:
            self.dest_edit.setText(path)

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("select_watermark"),
            self.image_edit.text().strip(),
            "Images (*.png *.webp *.jpg *.jpeg)",
        )
        if path:
            self.image_edit.setText(path)

    def _browse_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("select_ffmpeg"),
            self._ffmpeg_path or "",
            "ffmpeg (ffmpeg.exe);;Executable (*.exe);;All Files (*)",
        )
        if path:
            self._ffmpeg_path = path
            DependencyInstaller.set_configured_ffmpeg_path(path)
            self._refresh_ffmpeg()
            self._save_prefs()

    def _open_path(self, path: str) -> None:
        path = (path or "").strip()
        if not path or not os.path.isdir(path):
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError:
            pass

    def _append(self, text: str) -> None:
        self.log.append(text)

    def _set_busy(self, busy: bool) -> None:
        self.start_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        self.io_box.setEnabled(not busy)
        self.style_box.setEnabled(not busy)
        self.ffmpeg_cfg_btn.setEnabled(not busy)

    def _precheck(self, job: BatchJob) -> str:
        if not self._ffmpeg_ok:
            return "wmtool_ffmpeg_bad"
        if not job.source_dir or not os.path.isdir(job.source_dir):
            return "wmtool_need_folder"
        if job.kind == "text" and not job.text:
            return "wmtool_need_text"
        if job.kind == "image" and (not job.image_path or not os.path.isfile(job.image_path)):
            return "wmtool_need_image"
        if job.output_mode == "copy":
            if not job.output_dir:
                return "wmtool_need_out"
            if paths_overlap(job.source_dir, job.output_dir):
                return "wmtool_overlap"
        return ""

    def _start(self) -> None:
        if self._runner and self._runner.isRunning():
            return
        self._refresh_font_label()
        job = self._job()
        key = self._precheck(job)
        if key:
            QMessageBox.warning(self, t("wmtool_title"), t(key))
            return
        if job.output_mode == "overwrite":
            answer = QMessageBox.question(
                self,
                t("wmtool_overwrite_title"),
                t("wmtool_overwrite_msg"),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._save_prefs()
        self.progress.setValue(0)
        self.current_label.setText(t("wmtool_running"))
        self._append("— " + t("wmtool_start"))
        self._set_busy(True)
        self._runner = _RunThread(job)
        self._runner.tick.connect(self._on_tick)
        self._runner.finished_with.connect(self._on_finished)
        self._runner.start()

    def _stop(self) -> None:
        if self._runner and self._runner.isRunning():
            self._runner.cancel.set()
            self.stop_btn.setEnabled(False)
            self._append(t("wmtool_stopping"))

    def _on_tick(self, index: int, total: int, name: str, state: str, detail: str) -> None:
        if total > 0 and state in ("ok", "fail"):
            self.progress.setMaximum(total)
            self.progress.setValue(index)
        if state == "start":
            self.current_label.setText(t("wmtool_processing", name=name))
        elif state == "ok":
            self._append(t("wmtool_line_ok", name=name))
        elif state == "fail":
            self._append(t("wmtool_line_fail", name=name, detail=detail or t("failed")))
        elif state == "ready" and detail:
            self._append(t("wmtool_accel", mode=detail) if detail else detail)

    def _on_finished(self, result: BatchResult) -> None:
        self._set_busy(False)
        self._refresh_ffmpeg()
        if result.error_key:
            extra = result.files[0] if result.files else ""
            text = t(result.error_key)
            if extra and result.error_key == "wmtool_failed":
                text = f"{text}\n{extra}"
            QMessageBox.warning(self, t("wmtool_title"), text)
            self._append(text)
            self.current_label.setText(text)
            return
        if result.cancelled:
            msg = t("wmtool_cancelled", ok=result.ok, fail=result.failed)
        else:
            msg = t("wmtool_done", ok=result.ok, fail=result.failed)
        self.current_label.setText(msg)
        self._append(msg)

    def _load_prefs(self) -> None:
        data = {}
        try:
            with open(_prefs_path(), "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        cfg = self._config_store.config
        wm = cfg.watermark
        self.folder_edit.setText(str(data.get("source_dir") or ""))
        self.subdirs.setChecked(bool(data.get("include_subdirs", True)))
        if data.get("kind") == "image":
            self.kind_image.setChecked(True)
        else:
            self.kind_text.setChecked(True)
        default_text = (getattr(wm, "text", "") or "").strip() or "X-Track水印"
        self.text_edit.setText(str(data.get("text") or default_text))
        color = str(data.get("text_color") or getattr(wm, "text_color", "") or "white")
        idx = self.color_combo.findData(color)
        if idx >= 0:
            self.color_combo.setCurrentIndex(idx)
        default_image = (getattr(wm, "image_path", "") or "").strip()
        self.image_edit.setText(str(data.get("image_path") or default_image))
        self.scale_spin.setValue(int(data.get("scale_percent") or 8))
        self.opacity_spin.setValue(int(data.get("opacity") or 85))
        self.fade_spin.setValue(float(data.get("fade_sec") if data.get("fade_sec") is not None else 0.4))
        placement = str(data.get("placement") or "fixed")
        if placement == "corners":
            self.place_corners.setChecked(True)
        elif placement == "random":
            self.place_random.setChecked(True)
        else:
            self.place_fixed.setChecked(True)
        pos = str(data.get("fixed_position") or getattr(wm, "position", "") or "bottom-right")
        if pos in self.pos_buttons:
            self.pos_buttons[pos].setChecked(True)
        self.refresh_spin.setValue(int(data.get("refresh_sec") or 4))
        if data.get("output_mode") == "overwrite":
            self.out_overwrite.setChecked(True)
        else:
            self.out_copy.setChecked(True)
        self.dest_edit.setText(str(data.get("output_dir") or ""))
        ffmpeg = str(data.get("ffmpeg_path") or getattr(cfg, "ffmpeg_path", "") or "")
        if not ffmpeg:
            ffmpeg = DependencyInstaller._configured_path or ""
        self._ffmpeg_path = ffmpeg
        # Always start collapsed for a clean first view
        self.style_box.setChecked(False)
        self.style_body.setVisible(False)
        self._refresh_font_label()

    def _save_prefs(self) -> None:
        job = self._job()
        payload = {
            "source_dir": job.source_dir,
            "include_subdirs": job.include_subdirs,
            "kind": job.kind,
            "text": job.text,
            "text_color": job.text_color,
            "image_path": job.image_path,
            "scale_percent": job.scale_percent,
            "opacity": int(round(job.opacity * 100)),
            "fade_sec": job.fade_sec,
            "placement": job.placement,
            "fixed_position": job.fixed_position,
            "refresh_sec": int(job.refresh_sec),
            "output_mode": job.output_mode,
            "output_dir": job.output_dir,
            "ffmpeg_path": job.ffmpeg_path,
        }
        try:
            with open(_prefs_path(), "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def closeEvent(self, event) -> None:
        if self._runner and self._runner.isRunning():
            answer = QMessageBox.question(self, t("wmtool_title"), t("wmtool_confirm_stop"))
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._runner.cancel.set()
            self._runner.wait(5000)
        self._save_prefs()
        super().closeEvent(event)
