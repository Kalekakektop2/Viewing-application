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
        self.setMinimumWidth(480)
        self.setMinimumHeight(220)
        self.resize(520, 240)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet(settings_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        kicker = QLabel("SETTINGS")
        kicker.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10px; "
            "letter-spacing: 0.12em; color: #6B6B6B;"
        )
        layout.addWidget(kicker)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self.hotkey_edit = QLineEdit(settings.hotkey)
        self.hotkey_edit.setPlaceholderText("alt+e  ·  ctrl+shift+q")
        self.hotkey_edit.setMinimumHeight(40)
        form.addRow("Горячая клавиша", self.hotkey_edit)
        layout.addLayout(form)

        hint = QLabel(
            "От этой комбинации зависит открытие HUD.\n"
            "Модификаторы: alt, ctrl, shift, win + клавиша."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8A8A8A; font-size:12px;")
        layout.addWidget(hint)

        layout.addStretch(1)

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
        old = self.settings.hotkey
        self.settings.hotkey = hotkey
        self.settings.save()
        if hotkey != old:
            self.hotkey_changed.emit(hotkey)
        self.accept()
