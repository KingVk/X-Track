"""Optional date box: empty by default, click opens calendar popup."""

from typing import Optional

from PyQt6.QtCore import Qt, QDate, pyqtSignal, QEvent
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QCalendarWidget,
    QVBoxLayout,
    QFrame,
)


class _ClickableLineEdit(QLineEdit):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class OptionalDateBox(QWidget):
    changed = pyqtSignal()

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self._date: Optional[QDate] = None

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.edit = _ClickableLineEdit()
        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit.setObjectName("optionalDateEdit")
        self.edit.setFixedHeight(32)
        self.edit.setMinimumWidth(140)
        self.edit.clicked.connect(self._open_calendar)

        self.clear_btn = QToolButton()
        self.clear_btn.setText("×")
        self.clear_btn.setObjectName("dateClearBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFixedSize(28, 32)
        self.clear_btn.setToolTip("Clear")
        self.clear_btn.clicked.connect(self.clear)
        self.clear_btn.setVisible(False)

        row.addWidget(self.edit, 1)
        row.addWidget(self.clear_btn)

        self._popup = QFrame(None, Qt.WindowType.Popup)
        self._popup.setObjectName("datePopup")
        pop_layout = QVBoxLayout(self._popup)
        pop_layout.setContentsMargins(6, 6, 6, 6)
        self._cal = QCalendarWidget()
        self._cal.setGridVisible(True)
        self._cal.clicked.connect(self._on_picked)
        pop_layout.addWidget(self._cal)

    def setPlaceholder(self, text: str):
        self.edit.setPlaceholderText(text)

    def has_date(self) -> bool:
        return self._date is not None and self._date.isValid()

    def date(self) -> Optional[QDate]:
        return self._date

    def date_string(self) -> str:
        if self.has_date():
            return self._date.toString("yyyy-MM-dd")
        return ""

    def set_date(self, qd: QDate):
        if not qd or not qd.isValid():
            self.clear()
            return
        self._date = qd
        self.edit.setText(qd.toString("yyyy-MM-dd"))
        self.clear_btn.setVisible(True)
        self._cal.setSelectedDate(qd)
        self.changed.emit()

    def set_date_string(self, s: str):
        s = (s or "").strip()
        if not s:
            self.clear()
            return
        qd = QDate.fromString(s, "yyyy-MM-dd")
        if qd.isValid():
            self.set_date(qd)
        else:
            self.clear()

    def clear(self):
        was_set = self._date is not None
        self._date = None
        self.edit.clear()
        self.clear_btn.setVisible(False)
        if was_set:
            self.changed.emit()

    def _open_calendar(self):
        if self.has_date():
            self._cal.setSelectedDate(self._date)
        else:
            self._cal.setSelectedDate(QDate.currentDate())
        pos = self.edit.mapToGlobal(self.edit.rect().bottomLeft())
        self._popup.adjustSize()
        self._popup.move(pos)
        self._popup.show()
        self._popup.raise_()
        self._popup.activateWindow()

    def _on_picked(self, qd: QDate):
        self.set_date(qd)
        self._popup.hide()
