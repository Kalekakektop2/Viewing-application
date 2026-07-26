from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TrayWindow(QWidget):
    """
    Small control panel (Discord-style: app lives in tray, window opens on click).
    Closing this window does NOT quit the app — only hides it.
    """

    def __init__(
        self,
        *,
        hotkey: str,
        on_capture: Callable[[], None],
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Viewing")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setFixedSize(360, 220)
        self.setStyleSheet(
            """
            QWidget { background: #0f0e1a; color: #e8e8f0; font-family: Segoe UI; }
            QLabel#title { font-size: 18px; font-weight: 800; color: #00f0ff; }
            QLabel#sub { color: #9aa0b5; font-size: 12px; }
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #00f0ff, stop:1 #b026ff);
                color: #07060d; border: none; border-radius: 10px;
                padding: 10px 14px; font-weight: 700;
            }
            QPushButton#secondary {
                background: rgba(255,255,255,0.08); color: #e8e8f0;
                border: 1px solid rgba(255,255,255,0.12);
            }
            QPushButton#danger {
                background: rgba(255,60,80,0.15); color: #ff8a9a;
                border: 1px solid rgba(255,60,80,0.35);
            }
            QFrame#card {
                background: #141222; border: 1px solid rgba(0,240,255,0.25);
                border-radius: 12px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Viewing")
        title.setObjectName("title")
        root.addWidget(title)

        self.status = QLabel()
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        self.set_hotkey(hotkey)
        root.addWidget(self.status)

        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        hint = QLabel(
            "Приложение работает в трее (иконка «V» под стрелкой ↑ у часов).\n"
            "Закрытие этого окна не завершает программу."
        )
        hint.setObjectName("sub")
        hint.setWordWrap(True)
        cl.addWidget(hint)
        root.addWidget(card)

        row = QHBoxLayout()
        btn_cap = QPushButton("Захват (область)")
        btn_cap.clicked.connect(on_capture)
        btn_set = QPushButton("Настройки")
        btn_set.setObjectName("secondary")
        btn_set.clicked.connect(on_settings)
        btn_quit = QPushButton("Выход")
        btn_quit.setObjectName("danger")
        btn_quit.clicked.connect(on_quit)
        row.addWidget(btn_cap)
        row.addWidget(btn_set)
        row.addWidget(btn_quit)
        root.addLayout(row)

    def set_hotkey(self, hotkey: str) -> None:
        self.status.setText(
            f"Статус: работает в фоне\n"
            f"Хоткей: {hotkey.upper()}\n"
            f"ПКМ по иконке в трее — меню"
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        # Hide instead of destroy — keep tray app alive
        event.ignore()
        self.hide()

    def show_near_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
