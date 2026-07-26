from __future__ import annotations

from PySide6.QtCore import Signal
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


class SettingsDialog(QDialog):
    hotkey_changed = Signal(str)

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Viewing — настройки")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.hotkey_edit = QLineEdit(settings.hotkey)
        self.hotkey_edit.setPlaceholderText("например: alt+e  или  ctrl+shift+q")
        form.addRow("Горячая клавиша", self.hotkey_edit)

        self.model_edit = QLineEdit(settings.gemini_model)
        form.addRow("Модель Gemini", self.model_edit)

        key_state = "задан (.env)" if settings.api_key else "не задан"
        form.addRow("API-ключ", QLabel(key_state))

        hint = QLabel(
            "Формат хоткея: модификаторы через + (alt, ctrl, shift, win) и клавиша.\n"
            "Ключ GEMINI_API_KEY задаётся в файле .env в корне проекта."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#888;")

        layout.addLayout(form)
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        save = QPushButton("Сохранить")
        cancel = QPushButton("Отмена")
        save.clicked.connect(self._save)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

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
