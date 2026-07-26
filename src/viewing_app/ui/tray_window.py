from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from viewing_app.ui.theme import tray_stylesheet


class TrayWindow(QWidget):
    """
    Control panel (tray companion). Closing does not quit the app.
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
        self.setFixedSize(380, 240)
        self.setStyleSheet(tray_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        kicker = QLabel("VIEWING · TRAY")
        kicker.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10px; "
            "letter-spacing: 0.12em; color: #6B6B6B;"
        )
        root.addWidget(kicker)

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
        cl.setContentsMargins(12, 10, 12, 10)
        hint = QLabel(
            "Работает в трее (иконка «V» под стрелкой у часов).\n"
            "Закрытие этого окна не завершает программу."
        )
        hint.setObjectName("sub")
        hint.setWordWrap(True)
        cl.addWidget(hint)
        root.addWidget(card)

        row = QHBoxLayout()
        row.setSpacing(8)
        btn_cap = QPushButton("Захват")
        btn_cap.clicked.connect(on_capture)
        btn_set = QPushButton("Настройки")
        btn_set.setObjectName("secondary")
        btn_set.clicked.connect(on_settings)
        btn_quit = QPushButton("Выход")
        btn_quit.setObjectName("danger")
        btn_quit.clicked.connect(on_quit)
        row.addWidget(btn_cap, 2)
        row.addWidget(btn_set, 2)
        row.addWidget(btn_quit, 1)
        root.addLayout(row)

    def set_hotkey(self, hotkey: str) -> None:
        self.status.setText(
            f"Фон · хоткей {hotkey.upper()}\n"
            f"ПКМ по иконке в трее — меню"
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()

    def show_near_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
