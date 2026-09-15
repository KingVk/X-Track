DARK_STYLE = """
QWidget {
    background-color: #0B1220;
    color: #E2E8F0;
    font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0B1220;
}

QGroupBox {
    background-color: #111827;
    border: 1px solid #1E293B;
    border-radius: 10px;
    margin-top: 14px;
    padding: 18px 12px 12px 12px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 0px;
    padding: 2px 8px;
    color: #94A3B8;
    font-size: 12px;
    font-weight: 600;
    background-color: #111827;
}

QLabel {
    color: #94A3B8;
    background: transparent;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 7px 10px;
    color: #E2E8F0;
    selection-background-color: #0E7490;
    selection-color: #F8FAFC;
    min-height: 20px;
}

QDateEdit {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 4px 32px 4px 10px;
    color: #E2E8F0;
    selection-background-color: #0E7490;
    selection-color: #F8FAFC;
    min-width: 160px;
    min-height: 28px;
}

QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border: 1px solid #22D3EE;
}

QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled, QComboBox:disabled {
    background-color: #0B1220;
    color: #475569;
    border-color: #1E293B;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    border: none;
    border-left: 1px solid #1E293B;
    width: 22px;
}

QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #94A3B8;
    margin-right: 2px;
}

QComboBox QAbstractItemView {
    background-color: #111827;
    border: 1px solid #1E293B;
    selection-background-color: #164E63;
    color: #E2E8F0;
    outline: none;
    padding: 4px;
    min-height: 72px;
}

QDateEdit::drop-down {
    subcontrol-origin: border;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}

QDateEdit::down-arrow {
    width: 12px;
    height: 12px;
}

QCalendarWidget {
    background-color: #111827;
}

QCalendarWidget QToolButton {
    color: #E2E8F0;
    background: transparent;
    border-radius: 4px;
    padding: 4px;
}

QCalendarWidget QToolButton:hover {
    background-color: #1E293B;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #E2E8F0;
    selection-background-color: #0E7490;
    selection-color: #F8FAFC;
}

QPushButton {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 14px;
    min-width: 72px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0F172A;
}

QPushButton:disabled {
    background-color: #111827;
    color: #475569;
    border-color: #1E293B;
}

QPushButton#primaryBtn {
    background-color: #0891B2;
    border: 1px solid #06B6D4;
    color: #F0FDFF;
    font-weight: 700;
}

QPushButton#primaryBtn:hover {
    background-color: #06B6D4;
}

QPushButton#primaryBtn:disabled {
    background-color: #164E63;
    border-color: #155E75;
    color: #64748B;
}

QPushButton#dangerBtn {
    background-color: #7F1D1D;
    border: 1px solid #EF4444;
    color: #FEE2E2;
    font-weight: 700;
}

QPushButton#dangerBtn:hover {
    background-color: #991B1B;
}

QPushButton#dangerBtn:disabled {
    background-color: #1E293B;
    border-color: #334155;
    color: #64748B;
}

QPushButton#warningBtn {
    background-color: #78350F;
    border: 1px solid #F59E0B;
    color: #FFFBEB;
    font-weight: 700;
}

QPushButton#warningBtn:hover {
    background-color: #92400E;
}

QPushButton#warningBtn:disabled {
    background-color: #1E293B;
    border-color: #334155;
    color: #64748B;
}

/* Clean checkbox 鈥?thin border, cyan fill, no crude default look */
QCheckBox {
    color: #CBD5E1;
    spacing: 8px;
    background: transparent;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #0F172A;
}

QCheckBox::indicator:hover {
    border-color: #22D3EE;
}

QCheckBox::indicator:checked {
    background-color: #0891B2;
    border: 1.5px solid #22D3EE;
    /* simple tech check: filled cyan square */
}

QCheckBox::indicator:disabled {
    border-color: #334155;
    background-color: #0B1220;
}

/* Radio 鈥?ring + inner cyan dot */
QRadioButton {
    color: #CBD5E1;
    spacing: 8px;
    background: transparent;
    padding: 4px 2px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #475569;
    border-radius: 9px;
    background-color: #0F172A;
}

QRadioButton::indicator:hover {
    border-color: #22D3EE;
}

QRadioButton::indicator:checked {
    border: 1.5px solid #22D3EE;
    background-color: qradialgradient(
        cx: 0.5, cy: 0.5, radius: 0.55,
        fx: 0.5, fy: 0.5,
        stop: 0 #22D3EE,
        stop: 0.38 #22D3EE,
        stop: 0.42 transparent,
        stop: 1 transparent
    );
}

QRadioButton::indicator:disabled {
    border-color: #334155;
}

/* Segmented chip radios for media type / date mode */
QRadioButton#chipRadio {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 6px 12px;
    color: #94A3B8;
    spacing: 0px;
}

QRadioButton#chipRadio::indicator {
    width: 0;
    height: 0;
    border: none;
}

QRadioButton#chipRadio:hover {
    border-color: #334155;
    color: #E2E8F0;
}

QRadioButton#chipRadio:checked {
    background-color: #083344;
    border: 1px solid #22D3EE;
    color: #67E8F9;
    font-weight: 600;
}

QTableWidget {
    background-color: #0F172A;
    alternate-background-color: #111827;
    border: 1px solid #1E293B;
    border-radius: 8px;
    gridline-color: #1E293B;
    color: #E2E8F0;
    outline: none;
}

QHeaderView::section {
    background-color: #111827;
    color: #64748B;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #1E293B;
    font-weight: 600;
    font-size: 12px;
}

QTableWidget::item {
    padding: 6px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #164E63;
    color: #F0FDFF;
}

QTextEdit {
    background-color: #070B14;
    border: 1px solid #1E293B;
    border-radius: 8px;
    color: #94A3B8;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 6px;
}

QProgressBar {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 4px;
    text-align: center;
    color: #94A3B8;
    max-height: 14px;
}

QProgressBar::chunk {
    background-color: #0891B2;
    border-radius: 3px;
}

QMenuBar {
    background-color: #0B1220;
    color: #94A3B8;
    border-bottom: 1px solid #1E293B;
    padding: 2px;
}

QMenuBar::item {
    padding: 6px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #1E293B;
    color: #E2E8F0;
}

QMenu {
    background-color: #111827;
    color: #E2E8F0;
    border: 1px solid #1E293B;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #164E63;
}

QToolButton#settingsGearBtn {
    background-color: transparent;
    border: 1px solid #1E293B;
    border-radius: 6px;
    color: #94A3B8;
    font-size: 15px;
    padding: 0;
}

QToolButton#settingsGearBtn:hover {
    background-color: #164E63;
    border-color: #22D3EE;
    color: #E2E8F0;
}


QPushButton#rowDeleteBtn:hover {
    background-color: #7F1D1D;
    color: #FEE2E2;
}

QPushButton#rowFilterBtn {
    padding: 2px 8px;
    font-size: 12px;
}

QPushButton#rowFilterBtn:hover {
    background-color: #164E63;
    border-color: #22D3EE;
    color: #E2E8F0;
}


QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    height: 0;
    background: none;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background-color: #334155;
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #475569;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    width: 0;
    background: none;
}

QAbstractItemView {
    background-color: #0F172A;
    color: #E2E8F0;
    outline: none;
}

QToolTip {
    background-color: #111827;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 6px 8px;
}

QLineEdit#optionalDateEdit {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-top-left-radius: 6px;
    border-bottom-left-radius: 6px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    padding: 6px 10px;
    color: #E2E8F0;
    min-height: 20px;
}

QLineEdit#optionalDateEdit:hover {
    border-color: #22D3EE;
}

QToolButton#dateClearBtn {
    background-color: #1E293B;
    border: 1px solid #1E293B;
    border-left: none;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    color: #94A3B8;
    min-width: 28px;
    padding: 0;
}

QToolButton#dateClearBtn:hover {
    background-color: #334155;
    color: #F87171;
}

QFrame#datePopup {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 8px;
}

QWidget#accountStatusBar {
    background: transparent;
}

QLabel#statusChip {
    color: #CBD5E1;
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}
"""
