from __future__ import annotations

from io import BytesIO
from typing import Callable, Optional

from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
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
    QScrollArea,
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
            self.failed.emit(str(exc))


class OverlayPanel(QWidget):
    """Always-on-top assistant panel. Closes when clicking the outside dimmer."""

    closed = Signal()

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

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Root: full-screen dimmer + floating card
        self._dimmer = QWidget(self)
        self._dimmer.setStyleSheet("background: rgba(0,0,0,100);")
        self._dimmer.mousePressEvent = self._on_dimmer_click  # type: ignore[method-assign]

        self._card = QFrame(self)
        self._card.setObjectName("card")
        self._card.setStyleSheet(
            """
            QFrame#card {
                background: #0f0e1a;
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 14px;
            }
            QLabel, QRadioButton, QTextEdit, QLineEdit {
                color: #e8e8f0;
                font-family: Segoe UI, sans-serif;
            }
            QLineEdit, QTextEdit {
                background: #07060d;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #00f0ff, stop:1 #b026ff);
                color: #07060d;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 700;
            }
            QPushButton:disabled { opacity: 0.5; }
            QPushButton#secondary {
                background: rgba(255,255,255,0.08);
                color: #e8e8f0;
                border: 1px solid rgba(255,255,255,0.12);
            }
            QPushButton#danger {
                background: rgba(255,60,80,0.15);
                color: #ff8a9a;
                border: 1px solid rgba(255,60,80,0.35);
            }
            """
        )

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Viewing")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #00f0ff;")
        self.game_label = QLabel("Игра: —")
        self.game_label.setStyleSheet("color: #9aa0b5; font-size: 12px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.game_label)
        layout.addLayout(header)

        self.preview = QLabel()
        self.preview.setFixedHeight(90)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            "background:#07060d; border-radius:8px; border:1px solid rgba(255,255,255,0.08);"
        )
        layout.addWidget(self.preview)

        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color:#ffcc66; font-size:12px;")
        self.warning_label.hide()
        layout.addWidget(self.warning_label)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Свой вопрос… или отправьте пустым (что это + крафт)")
        self.input.returnPressed.connect(self._on_send_custom)
        layout.addWidget(self.input)

        btns = QHBoxLayout()
        self.btn_id = QPushButton("Что это?")
        self.btn_craft = QPushButton("Как скрафтить?")
        self.btn_where = QPushButton("Где найти?")
        self.btn_id.clicked.connect(lambda: self._ask(INTENT_IDENTIFY))
        self.btn_craft.clicked.connect(lambda: self._ask(INTENT_CRAFT))
        self.btn_where.clicked.connect(lambda: self._ask(INTENT_LOCATE))
        btns.addWidget(self.btn_id)
        btns.addWidget(self.btn_craft)
        btns.addWidget(self.btn_where)
        layout.addLayout(btns)

        modes = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.radio_brief = QRadioButton("Кратко")
        self.radio_detail = QRadioButton("Расширенно")
        self.mode_group.addButton(self.radio_brief)
        self.mode_group.addButton(self.radio_detail)
        if settings.detail_mode == "detailed":
            self.radio_detail.setChecked(True)
        else:
            self.radio_brief.setChecked(True)
        modes.addWidget(self.radio_brief)
        modes.addWidget(self.radio_detail)
        modes.addStretch()
        layout.addLayout(modes)

        actions = QHBoxLayout()
        self.btn_send = QPushButton("Спросить")
        self.btn_send.clicked.connect(self._on_send_custom)
        self.btn_photo = QPushButton("Сгенерировать фото")
        self.btn_photo.setObjectName("secondary")
        self.btn_photo.clicked.connect(self._on_generate_photo)
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("secondary")
        self.btn_settings.setFixedWidth(40)
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("danger")
        self.btn_close.setFixedWidth(40)
        self.btn_close.clicked.connect(self.hide_panel)
        actions.addWidget(self.btn_send)
        actions.addWidget(self.btn_photo)
        actions.addWidget(self.btn_settings)
        actions.addWidget(self.btn_close)
        layout.addLayout(actions)

        self.status = QLabel("")
        self.status.setStyleSheet("color:#7fdfff; font-size:12px;")
        layout.addWidget(self.status)

        self.answer = QTextEdit()
        self.answer.setReadOnly(True)
        self.answer.setMinimumHeight(180)
        self.answer.setPlaceholderText("Ответ ИИ появится здесь. Можно задать ещё вопрос.")
        layout.addWidget(self.answer)

        self.image_out = QLabel()
        self.image_out.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_out.hide()
        layout.addWidget(self.image_out)

        self.hide()

    def _open_settings(self) -> None:
        if self.on_open_settings:
            self.on_open_settings()

    def _on_dimmer_click(self, event) -> None:
        # Close only if click is outside the card
        if not self._card.geometry().contains(event.position().toPoint()):
            self.hide_panel()

    def hide_panel(self) -> None:
        self.hide()
        self.closed.emit()

    def show_for_image(self, image: Image.Image) -> None:
        self._image = image
        self._set_preview(image)
        self.answer.clear()
        self.image_out.hide()
        self.warning_label.hide()
        self.status.setText("Скрин готов. Задайте вопрос или нажмите кнопку.")
        self._refresh_game_label()
        self._layout_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()
        # Auto default intent if empty — user can still type; we don't auto-send
        # Spec: default when no context = identify+craft — offer via empty send

    def _layout_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.setGeometry(geo)
        self._dimmer.setGeometry(self.rect())
        card_w, card_h = 480, 620
        x = geo.x() + (geo.width() - card_w) // 2
        y = geo.y() + (geo.height() - card_h) // 2
        self._card.setGeometry(x - geo.x(), y - geo.y(), card_w, card_h)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._dimmer.setGeometry(self.rect())

    def _set_preview(self, image: Image.Image) -> None:
        thumb = image.copy()
        thumb.thumbnail((420, 80))
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
        ):
            w.setEnabled(not busy)

    def _on_send_custom(self) -> None:
        text = self.input.text().strip()
        if text:
            self._ask(INTENT_CUSTOM, text)
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

        # Cache fast-path for known banal items on craft/locate after first ID
        if self._last_item and intent in (INTENT_CRAFT, INTENT_LOCATE, INTENT_IDENTIFY):
            cached = self.client.try_cache_only(
                self._last_item, intent, self._detail_mode()
            )
            if cached:
                self._apply_result(cached, user_echo=text or intent)
                return

        self._set_busy(True)
        self.status.setText("ИИ анализирует…")
        self.client.session.add_user(text or intent)
        self._worker = Worker(
            self.client, self._image, intent, text or "", self._detail_mode()
        )
        self._worker.finished_ok.connect(self._on_result)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_result(self, result: object) -> None:
        self._set_busy(False)
        assert isinstance(result, AnalysisResult)
        self._apply_result(result, user_echo=None)

    def _apply_result(self, result: AnalysisResult, user_echo: Optional[str]) -> None:
        self._refresh_game_label()
        if result.warning:
            self.warning_label.setText(result.warning)
            self.warning_label.show()
        if result.error == "no_api_key":
            self.status.setText("Нет API-ключа — показан офлайн-режим")
        elif result.from_cache:
            self.status.setText("Ответ из кэша (быстрее)")
        elif result.error:
            self.status.setText("Ошибка")
        else:
            self.status.setText("Готово · можно уточнить вопрос")

        parts = []
        if result.answer:
            parts.append(result.answer)
        if result.error and result.error not in ("no_api_key", "no_image"):
            parts.append(f"\n[{result.error}]")
        text = "\n".join(parts).strip()
        if text:
            prev = self.answer.toPlainText().strip()
            block = text if not prev else prev + "\n\n———\n\n" + text
            self.answer.setPlainText(block)
            self.client.session.add_assistant(text)

        if result.item:
            self._last_item = result.item

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
        self.answer.append(f"\nОшибка: {message}")
