from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from viewing_app.config import Settings
from viewing_app.ui.theme import settings_stylesheet


class SettingsDialog(QDialog):
    hotkey_changed = Signal(str)

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Viewing — настройки")
        self.setMinimumWidth(420)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet(settings_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        kicker = QLabel("SETTINGS")
        kicker.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10px; "
            "letter-spacing: 0.12em; color: #6B6B6B;"
        )
        layout.addWidget(kicker)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.hotkey_edit = QLineEdit(settings.hotkey)
        self.hotkey_edit.setPlaceholderText("alt+e  ·  ctrl+shift+q")
        form.addRow("Горячая клавиша", self.hotkey_edit)

        self.model_edit = QLineEdit(settings.gemini_model)
        form.addRow("Модель Gemini", self.model_edit)

        key_state = "задан (.env)" if settings.api_key else "не задан"
        form.addRow("API-ключ", QLabel(key_state))
        layout.addLayout(form)

        hint = QLabel(
            "Модификаторы: alt, ctrl, shift, win + клавиша.\n"
            "GEMINI_API_KEY — в файле .env рядом с программой."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#A3A3A3; font-size:12px;")
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        save = QPushButton("Сохранить")
        cancel = QPushButton("Отмена")
        cancel.setObjectName("secondary")
        save.clicked.connect(self._save)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def _save(self) -> None:
        hotkey = self.hotkey_edit.text().strip().lower().replace(" ", "")
        if not hotkey:
            hotkey = "alt+e"
        model = self.model_edit.text().strip() or self.settings.gemini_model
        old = self.settings.hotkey
        self.settings.hotkey = hotkey
        self.settings.gemini_model = model
        self.settings.save()
        if hotkey != old:
            self.hotkey_changed.emit(hotkey)
        self.accept()
