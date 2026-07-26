from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import mss
from PIL import Image
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int

    def as_mss(self) -> dict:
        return {
            "left": self.left,
            "top": self.top,
            "width": max(1, self.width),
            "height": max(1, self.height),
        }


def grab_region(region: Region) -> Image.Image:
    with mss.mss() as sct:
        shot = sct.grab(region.as_mss())
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


class RegionSelector(QWidget):
    """Fullscreen dim overlay; drag to select a rectangle."""

    selected = Signal(object)  # Region | None
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self._cover_virtual_desktop()

    def _cover_virtual_desktop(self) -> None:
        # Union of all screens
        geo = QRect()
        for screen in QGuiApplication.screens():
            geo = geo.united(screen.geometry())
        self.setGeometry(geo)

    def start(self) -> None:
        self._origin = None
        self._current = None
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        if self._origin and self._current:
            rect = QRect(self._origin, self._current).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor(0, 240, 255), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                rect.left(),
                max(16, rect.top() - 6),
                f"{rect.width()}×{rect.height()}  (Esc — отмена)",
            )
        else:
            painter.setPen(QColor(230, 230, 240))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Выделите область мышью · Esc — отмена",
            )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or not self._origin:
            return
        self._current = event.position().toPoint()
        rect = QRect(self._origin, self._current).normalized()
        self.hide()
        if rect.width() < 4 or rect.height() < 4:
            self.cancelled.emit()
            return
        # Map widget coords → global screen coords
        top_left = self.mapToGlobal(rect.topLeft())
        region = Region(
            left=top_left.x(),
            top=top_left.y(),
            width=rect.width(),
            height=rect.height(),
        )
        self.selected.emit(region)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.cancelled.emit()
