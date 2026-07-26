from __future__ import annotations

from typing import Callable, Optional

from PIL import Image
from PySide6.QtCore import QTimer, Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from viewing_app.ai.client import AnalysisResult, VisionClient
from viewing_app.ai.prompts import (
    INTENT_CRAFT,
    INTENT_CUSTOM,
    INTENT_DEFAULT,
    INTENT_IDENTIFY,
    INTENT_IMAGE,
    INTENT_LOCATE,
)
from viewing_app.config import Settings
from viewing_app.ui.theme import overlay_stylesheet


class Worker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        client: VisionClient,
        image: Image.Image,
        intent: str,
        user_text: str,
        detail_mode: str,
    ) -> None:
        super().__init__()
        self.client = client
        self.image = image
        self.intent = intent
        self.user_text = user_text
        self.detail_mode = detail_mode

    def run(self) -> None:
        try:
            result = self.client.analyze(
                self.image,
                intent=self.intent,
                user_text=self.user_text,
                detail_mode=self.detail_mode,
            )
            self.finished_ok.emit(result)
        except Exception as exc:
            # Never let worker exception kill the process
            self.failed.emit(str(exc))


class OverlayPanel(QWidget):
    """Wide horizontal HUD overlay. Click outside to close."""

    closed = Signal()

    # Landscape HUD size
    CARD_W = 980
    CARD_H = 340

    def __init__(
        self,
        settings: Settings,
        client: VisionClient,
        on_open_settings: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.client = client
        self.on_open_settings = on_open_settings
        self._image: Optional[Image.Image] = None
        self._worker: Optional[Worker] = None
        self._last_item: Optional[str] = None
        self._auto_timer: Optional[QTimer] = None
        self._last_intent: str = INTENT_DEFAULT
        self._last_user_text: str = ""
        self._has_answer: bool = False
        self._current_detail: str = settings.detail_mode

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._dimmer = QWidget(self)
        # Soft scrim — not heavy glassmorphism
        self._dimmer.setStyleSheet("background: rgba(0,0,0,110);")
        self._dimmer.mousePressEvent = self._on_dimmer_click  # type: ignore[method-assign]

        self._card = QFrame(self)
        self._card.setObjectName("card")
        self._card.setStyleSheet(overlay_stylesheet())

        root = QHBoxLayout(self._card)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(0)

        # ---- LEFT column: preview + controls ----
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 16, 0)
        left.setSpacing(10)

        kicker = QLabel("OVERLAY")
        kicker.setObjectName("kicker")
        left.addWidget(kicker)

        header = QHBoxLayout()
        title = QLabel("Viewing")
        title.setObjectName("title")
        self.game_label = QLabel("Игра: —")
        self.game_label.setObjectName("muted")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.game_label)
        left.addLayout(header)

        self.preview = QLabel()
        self.preview.setObjectName("preview")
        self.preview.setFixedSize(280, 96)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.preview)

        self.warning_label = QLabel("")
        self.warning_label.setObjectName("warning")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        left.addWidget(self.warning_label)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Уточняющий вопрос… (Enter)")
        self.input.returnPressed.connect(self._on_send_custom)
        left.addWidget(self.input)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.btn_id = QPushButton("Что это?")
        self.btn_id.setObjectName("secondary")
        self.btn_craft = QPushButton("Как скрафтить?")
        self.btn_craft.setObjectName("secondary")
        self.btn_where = QPushButton("Где найти?")
        self.btn_where.setObjectName("secondary")
        self.btn_id.clicked.connect(lambda: self._ask(INTENT_IDENTIFY))
        self.btn_craft.clicked.connect(lambda: self._ask(INTENT_CRAFT))
        self.btn_where.clicked.connect(lambda: self._ask(INTENT_LOCATE))
        btns.addWidget(self.btn_id)
        btns.addWidget(self.btn_craft)
        btns.addWidget(self.btn_where)
        left.addLayout(btns)

        modes = QHBoxLayout()
        modes.setSpacing(12)
        self.mode_group = QButtonGroup(self)
        self.radio_brief = QRadioButton("Кратко")
        self.radio_detail = QRadioButton("Расширенно")
        self.mode_group.addButton(self.radio_brief)
        self.mode_group.addButton(self.radio_detail)
        if settings.detail_mode == "detailed":
            self.radio_detail.setChecked(True)
        else:
            self.radio_brief.setChecked(True)
        self.radio_brief.toggled.connect(self._on_detail_mode_toggled)
        self.radio_detail.toggled.connect(self._on_detail_mode_toggled)
        modes.addWidget(self.radio_brief)
        modes.addWidget(self.radio_detail)
        modes.addStretch()
        left.addLayout(modes)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.btn_send = QPushButton("Спросить")
        self.btn_send.clicked.connect(self._on_send_custom)
        self.btn_photo = QPushButton("Фото")
        self.btn_photo.setObjectName("secondary")
        self.btn_photo.clicked.connect(self._on_generate_photo)
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("ghost")
        self.btn_settings.setFixedWidth(36)
        self.btn_settings.setToolTip("Настройки")
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("danger")
        self.btn_close.setFixedWidth(36)
        self.btn_close.setToolTip("Закрыть")
        self.btn_close.clicked.connect(self.hide_panel)
        actions.addWidget(self.btn_send)
        actions.addWidget(self.btn_photo)
        actions.addWidget(self.btn_settings)
        actions.addWidget(self.btn_close)
        left.addLayout(actions)

        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        left.addWidget(self.status)
        left.addStretch(1)

        left_wrap = QWidget()
        left_wrap.setFixedWidth(300)
        left_wrap.setLayout(left)
        root.addWidget(left_wrap)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(divider)

        # ---- RIGHT column: answer ----
        right = QVBoxLayout()
        right.setContentsMargins(16, 0, 0, 0)
        right.setSpacing(8)
        ans_kicker = QLabel("ANSWER")
        ans_kicker.setObjectName("kicker")
        right.addWidget(ans_kicker)

        self.answer = QTextEdit()
        self.answer.setReadOnly(True)
        self.answer.setPlaceholderText(
            "После скрина — автоответ: что это + как скрафтить. "
            "Кнопки и поле — для уточнений."
        )
        self.answer.textChanged.connect(self._scroll_answer_to_bottom)
        right.addWidget(self.answer, 1)

        self.image_out = QLabel()
        self.image_out.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_out.setMaximumHeight(120)
        self.image_out.hide()
        right.addWidget(self.image_out)

        root.addLayout(right, 1)
        self.hide()

    def _open_settings(self) -> None:
        if self.on_open_settings:
            self.on_open_settings()

    def _on_dimmer_click(self, event) -> None:
        if not self._card.geometry().contains(event.position().toPoint()):
            self.hide_panel()

    def hide_panel(self) -> None:
        if self._auto_timer is not None:
            self._auto_timer.stop()
            self._auto_timer = None
        self.hide()
        self.closed.emit()

    def show_for_image(self, image: Image.Image) -> None:
        """Show HUD and immediately run default analysis (what + craft)."""
        self._image = image
        self._set_preview(image)
        self.answer.clear()
        self.image_out.hide()
        self.warning_label.hide()
        self._has_answer = False
        self._last_intent = INTENT_DEFAULT
        self._last_user_text = ""
        self._last_item = None
        self._current_detail = self._detail_mode()
        self.status.setText("Анализ… (что это + как скрафтить)")
        self._refresh_game_label()
        self._layout_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

        # Auto-answer per TZ: default intent right after capture
        if self._auto_timer is not None:
            self._auto_timer.stop()
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._auto_default_ask)
        self._auto_timer.start(80)

    def _auto_default_ask(self) -> None:
        self._ask(INTENT_DEFAULT, "")

    def _on_detail_mode_toggled(self, checked: bool) -> None:
        """When player flips Кратко/Расширенно after an answer — re-query AI."""
        if not checked:
            return  # only the newly selected radio
        new_mode = self._detail_mode()
        if new_mode == self._current_detail:
            return
        if self._image is None or not self._has_answer:
            self._current_detail = new_mode
            return
        if self._worker and self._worker.isRunning():
            # revert radio until free
            self._block_mode_signals(True)
            if self._current_detail == "detailed":
                self.radio_detail.setChecked(True)
            else:
                self.radio_brief.setChecked(True)
            self._block_mode_signals(False)
            self.status.setText("Подождите, идёт запрос…")
            return

        self._current_detail = new_mode
        label = "расширенно" if new_mode == "detailed" else "кратко"
        self.status.setText(f"Переключаю формат: {label}…")
        # Same question/intent, new detail format
        self._ask(self._last_intent, self._last_user_text)

    def _block_mode_signals(self, block: bool) -> None:
        self.radio_brief.blockSignals(block)
        self.radio_detail.blockSignals(block)

    def _layout_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.setGeometry(geo)
        self._dimmer.setGeometry(self.rect())
        card_w, card_h = self.CARD_W, self.CARD_H
        # Prefer lower-center HUD (less blocking, wide)
        x = geo.x() + (geo.width() - card_w) // 2
        y = geo.y() + geo.height() - card_h - 48
        if y < geo.y() + 20:
            y = geo.y() + (geo.height() - card_h) // 2
        self._card.setGeometry(x - geo.x(), y - geo.y(), card_w, card_h)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._dimmer.setGeometry(self.rect())

    def _set_preview(self, image: Image.Image) -> None:
        thumb = image.copy()
        thumb.thumbnail((270, 90))
        data = thumb.convert("RGBA").tobytes("raw", "RGBA")
        qimg = QImage(
            data,
            thumb.width,
            thumb.height,
            thumb.width * 4,
            QImage.Format.Format_RGBA8888,
        )
        self.preview.setPixmap(QPixmap.fromImage(qimg.copy()))

    def _detail_mode(self) -> str:
        return "detailed" if self.radio_detail.isChecked() else "brief"

    def _refresh_game_label(self) -> None:
        s = self.client.session
        if s.game_name:
            self.game_label.setText(f"Игра: {s.game_name}")
        else:
            self.game_label.setText("Игра: —")

    def _set_busy(self, busy: bool) -> None:
        for w in (
            self.btn_id,
            self.btn_craft,
            self.btn_where,
            self.btn_send,
            self.btn_photo,
            self.input,
            self.radio_brief,
            self.radio_detail,
        ):
            w.setEnabled(not busy)

    def _scroll_answer_to_bottom(self) -> None:
        cursor = self.answer.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.answer.setTextCursor(cursor)
        self.answer.ensureCursorVisible()
        sb = self.answer.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_send_custom(self) -> None:
        text = self.input.text().strip()
        if text:
            self._ask(INTENT_CUSTOM, text)
            self.input.clear()
        else:
            self._ask(INTENT_DEFAULT, "")

    def _on_generate_photo(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Генерация фото")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(
            "Генерация изображения может занять заметное время "
            "и зависит от лимитов бесплатной модели.\n\nПродолжить?"
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        self._ask(INTENT_IMAGE, self.input.text().strip())

    def _ask(self, intent: str, user_text: Optional[str] = None) -> None:
        if self._image is None:
            return
        if self._worker and self._worker.isRunning():
            return
        text = self.input.text() if user_text is None else user_text
        if intent != INTENT_CUSTOM and user_text is None:
            text = self.input.text()
        text = text or ""

        self._last_intent = intent
        self._last_user_text = text
        self._current_detail = self._detail_mode()

        if self._last_item and intent in (INTENT_CRAFT, INTENT_LOCATE, INTENT_IDENTIFY):
            cached = self.client.try_cache_only(
                self._last_item, intent, self._detail_mode()
            )
            if cached:
                self._apply_result(cached)
                return

        self._set_busy(True)
        mode_label = "расширенно" if self._detail_mode() == "detailed" else "кратко"
        self.status.setText(f"ИИ анализирует… ({mode_label})")
        self.client.session.add_user(text or intent)
        self._worker = Worker(
            self.client, self._image, intent, text, self._detail_mode()
        )
        self._worker.finished_ok.connect(self._on_result)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_result(self, result: object) -> None:
        self._set_busy(False)
        assert isinstance(result, AnalysisResult)
        self._apply_result(result)

    def _apply_result(self, result: AnalysisResult) -> None:
        self._refresh_game_label()
        if result.warning:
            self.warning_label.setText(result.warning)
            self.warning_label.show()
        if result.error == "no_api_key":
            self.status.setText("Нет API-ключа — офлайн-режим")
        elif result.from_cache:
            self.status.setText("Из кэша · можно уточнить")
        elif result.error:
            self.status.setText("Ошибка")
        else:
            self.status.setText(
                "Готово · Кратко/Расширенно — переключить формат · кнопки — уточнить"
            )

        parts = []
        if result.answer:
            parts.append(result.answer)
        if result.error and result.error not in ("no_api_key", "no_image"):
            parts.append(f"\n[{result.error}]")
        text = "\n".join(parts).strip()
        if text:
            prev = self.answer.toPlainText().strip()
            mode_tag = (
                "Расширенно" if self._detail_mode() == "detailed" else "Кратко"
            )
            header = f"——— {mode_tag} ———"
            block = text if not prev else prev + "\n\n" + header + "\n\n" + text
            self.answer.setPlainText(block)
            self.client.session.add_assistant(text)
            self._has_answer = True
            # Force scroll after layout
            QTimer.singleShot(0, self._scroll_answer_to_bottom)
            QTimer.singleShot(50, self._scroll_answer_to_bottom)

        if result.item:
            self._last_item = result.item
        self._current_detail = self._detail_mode()

        if result.image_bytes:
            qimg = QImage.fromData(result.image_bytes)
            if not qimg.isNull():
                pix = QPixmap.fromImage(qimg).scaledToWidth(
                    420, Qt.TransformationMode.SmoothTransformation
                )
                self.image_out.setPixmap(pix)
                self.image_out.show()

        self.settings.detail_mode = self._detail_mode()
        self.settings.save()

    def _on_fail(self, message: str) -> None:
        self._set_busy(False)
        self.status.setText("Ошибка")
        prev = self.answer.toPlainText().strip()
        block = f"Ошибка: {message}"
        self.answer.setPlainText(block if not prev else prev + "\n\n" + block)
        QTimer.singleShot(0, self._scroll_answer_to_bottom)
