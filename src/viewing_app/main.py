from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Allow `python -m viewing_app` from src/
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from viewing_app.ai.client import VisionClient
from viewing_app.cache.store import ItemCache
from viewing_app.capture.region import RegionSelector, grab_region
from viewing_app.config import DATA_DIR, ROOT, Settings, resource_path
from viewing_app.hotkeys import HotkeyService
from viewing_app.session import GameSession
from viewing_app.ui.overlay import OverlayPanel
from viewing_app.ui.settings_dialog import SettingsDialog
from viewing_app.ui.tray_window import TrayWindow


def _log(msg: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / "startup.log"
        with path.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def build_app_icon() -> QIcon:
    """Load packaged icon or paint a fallback 'V' icon (multiple sizes for tray)."""
    candidates = [
        resource_path("assets", "viewing.ico"),
        resource_path("assets", "viewing.png"),
        ROOT / "assets" / "viewing.ico",
        ROOT / "assets" / "viewing.png",
    ]
    icon = QIcon()
    for p in candidates:
        if p and p.exists():
            icon.addFile(str(p))
            if not icon.isNull():
                return icon

    # Fallback: paint multi-size pixmaps
    for size in (16, 24, 32, 48, 64):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#0f0e1a"))
        p.setPen(QColor("#00f0ff"))
        margin = max(1, size // 12)
        p.drawRoundedRect(
            margin,
            margin,
            size - 2 * margin,
            size - 2 * margin,
            size // 5,
            size // 5,
        )
        pen = p.pen()
        pen.setWidth(max(2, size // 10))
        pen.setColor(QColor("#00f0ff"))
        p.setPen(pen)
        # V
        p.drawLine(int(size * 0.25), int(size * 0.28), int(size * 0.5), int(size * 0.75))
        p.drawLine(int(size * 0.75), int(size * 0.28), int(size * 0.5), int(size * 0.75))
        p.end()
        icon.addPixmap(pix)
    return icon


class Bridge(QObject):
    """Thread-safe bridge from pynput hotkey thread into Qt main thread."""

    capture_requested = Signal()


class AppController(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = Settings.load()
        self.session = GameSession()
        self.cache = ItemCache()
        self.client = VisionClient(self.settings, self.session, self.cache)
        self.icon = build_app_icon()
        self.app.setWindowIcon(self.icon)

        self.bridge = Bridge()
        self.bridge.capture_requested.connect(self.start_capture)

        self.selector = RegionSelector()
        self.selector.selected.connect(self._on_region)
        self.selector.cancelled.connect(self._on_cancel_select)

        self.overlay = OverlayPanel(
            self.settings, self.client, on_open_settings=self.open_settings
        )

        self.panel = TrayWindow(
            hotkey=self.settings.hotkey,
            on_capture=self.start_capture,
            on_settings=self.open_settings,
            on_quit=self.shutdown,
        )
        self.panel.setWindowIcon(self.icon)

        self.hotkeys: HotkeyService | None = None
        self._start_hotkeys()

        self._setup_tray()

        # Show control panel once so user knows app started (Discord-like UX)
        QTimer.singleShot(200, self.show_panel)
        QTimer.singleShot(
            600,
            lambda: self.tray.showMessage(
                "Viewing",
                f"В трее (под стрелкой ↑). Хоткей: {self.settings.hotkey.upper()}",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            ),
        )
        _log(f"ready hotkey={self.settings.hotkey} tray={self.tray.isVisible()}")

    def _start_hotkeys(self) -> None:
        try:
            self.hotkeys = HotkeyService(
                self.settings.hotkey,
                on_activate=lambda: self.bridge.capture_requested.emit(),
            )
            self.hotkeys.start()
            _log("hotkeys started")
        except Exception as exc:
            _log(f"hotkeys failed: {exc}")
            QMessageBox.warning(
                None,
                "Viewing",
                f"Не удалось зарегистрировать хоткей ({self.settings.hotkey}).\n"
                f"{exc}\n\nИспользуйте кнопку «Захват» в окне или меню трея.",
            )

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon, self.app)
        self.tray.setToolTip(f"Viewing — {self.settings.hotkey.upper()}")

        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background:#141222; color:#e8e8f0; border:1px solid #00f0ff; }"
            "QMenu::item:selected { background:#00f0ff; color:#07060d; }"
        )
        act_show = QAction("Открыть Viewing", self.app)
        act_show.triggered.connect(self.show_panel)
        act_capture = QAction("Захват области", self.app)
        act_capture.triggered.connect(self.start_capture)
        act_settings = QAction("Настройки", self.app)
        act_settings.triggered.connect(self.open_settings)
        act_quit = QAction("Выход", self.app)
        act_quit.triggered.connect(self.shutdown)

        menu.addAction(act_show)
        menu.addAction(act_capture)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)

        self.tray.show()
        # Some Windows builds need a second show after event loop starts
        QTimer.singleShot(0, self.tray.show)
        QTimer.singleShot(500, self.tray.show)

        if not self.tray.isSystemTrayAvailable():
            _log("WARNING: system tray not available")
        _log(f"tray shown icon_null={self.icon.isNull()} visible={self.tray.isVisible()}")

    def show_panel(self) -> None:
        self.panel.set_hotkey(self.settings.hotkey)
        self.panel.show_near_tray()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # Left click / double click / context → open panel (Discord-like)
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.MiddleClick,
        ):
            if self.panel.isVisible():
                self.panel.hide()
            else:
                self.show_panel()

    @Slot()
    def start_capture(self) -> None:
        if self.overlay.isVisible():
            self.overlay.hide()
        if self.panel.isVisible():
            self.panel.hide()
        QTimer.singleShot(150, self.selector.start)

    def _on_region(self, region) -> None:
        try:
            image = grab_region(region)
        except Exception as exc:
            QMessageBox.warning(None, "Viewing", f"Не удалось захватить экран:\n{exc}")
            return
        self.overlay.show_for_image(image)

    def _on_cancel_select(self) -> None:
        pass

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.settings)
        dlg.hotkey_changed.connect(self._on_hotkey_changed)
        dlg.exec()
        self.tray.setToolTip(f"Viewing — {self.settings.hotkey.upper()}")
        self.panel.set_hotkey(self.settings.hotkey)
        self.client.settings = self.settings

    def _on_hotkey_changed(self, hotkey: str) -> None:
        try:
            if self.hotkeys:
                self.hotkeys.rebind(hotkey)
            else:
                self._start_hotkeys()
        except Exception as exc:
            QMessageBox.warning(None, "Viewing", f"Хоткей не применился:\n{exc}")
            return
        self.tray.showMessage(
            "Viewing",
            f"Новый хоткей: {hotkey.upper()}",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def shutdown(self) -> None:
        _log("shutdown")
        if self.hotkeys:
            try:
                self.hotkeys.stop()
            except Exception:
                pass
        self.tray.hide()
        self.panel.hide()
        self.overlay.hide()
        self.app.quit()


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _log("--- start ---")
    _log(f"frozen={getattr(sys, 'frozen', False)} exe={sys.executable}")
    _log(f"root={ROOT}")

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        app.setApplicationName("Viewing")
        app.setOrganizationName("Kalekakektop2")
        app.setWindowIcon(build_app_icon())

        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None,
                "Viewing",
                "Системный трей недоступен.\n"
                "Проверьте, что область уведомлений Windows включена.",
            )
            return 1

        controller = AppController(app)
        app._viewing_controller = controller  # type: ignore[attr-defined]
        return app.exec()
    except Exception:
        tb = traceback.format_exc()
        _log(tb)
        try:
            # Ensure message box works even mid-failure
            if QApplication.instance() is None:
                QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Viewing — ошибка запуска",
                f"Приложение не смогло запуститься:\n\n{tb[-1500:]}",
            )
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
