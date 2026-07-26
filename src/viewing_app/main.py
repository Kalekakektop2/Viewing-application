from __future__ import annotations

import sys
from pathlib import Path

# Allow `python -m viewing_app` from src/
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from viewing_app.ai.client import VisionClient
from viewing_app.cache.store import ItemCache
from viewing_app.capture.region import RegionSelector, grab_region
from viewing_app.config import Settings
from viewing_app.hotkeys import HotkeyService
from viewing_app.session import GameSession
from viewing_app.ui.overlay import OverlayPanel
from viewing_app.ui.settings_dialog import SettingsDialog


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

        self.bridge = Bridge()
        self.bridge.capture_requested.connect(self.start_capture)

        self.selector = RegionSelector()
        self.selector.selected.connect(self._on_region)
        self.selector.cancelled.connect(self._on_cancel_select)

        self.overlay = OverlayPanel(
            self.settings, self.client, on_open_settings=self.open_settings
        )

        self.hotkeys = HotkeyService(
            self.settings.hotkey,
            on_activate=lambda: self.bridge.capture_requested.emit(),
        )
        self.hotkeys.start()

        self._setup_tray()

        # Startup toast via tray
        if self.tray.isVisible():
            self.tray.showMessage(
                "Viewing",
                f"Работает в трее. Хоткей: {self.settings.hotkey.upper()}",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.app)
        # Built-in null icon fallback — solid color pixmap
        from PySide6.QtGui import QColor, QPixmap

        pix = QPixmap(32, 32)
        pix.fill(QColor("#00f0ff"))
        self.tray.setIcon(QIcon(pix))
        self.tray.setToolTip(f"Viewing — {self.settings.hotkey.upper()}")

        menu = QMenu()
        act_capture = QAction("Захват области", self.app)
        act_capture.triggered.connect(self.start_capture)
        act_settings = QAction("Настройки", self.app)
        act_settings.triggered.connect(self.open_settings)
        act_quit = QAction("Выход", self.app)
        act_quit.triggered.connect(self.shutdown)

        menu.addAction(act_capture)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.start_capture()

    @Slot()
    def start_capture(self) -> None:
        # Hide overlay while selecting
        if self.overlay.isVisible():
            self.overlay.hide()
        # Small delay so tray/menu doesn't appear in screenshot selection
        QTimer.singleShot(120, self.selector.start)

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
        # Refresh client model / key from env+settings
        self.client.settings = self.settings
        self.client._client = None  # noqa: SLF001 — force re-init

    def _on_hotkey_changed(self, hotkey: str) -> None:
        self.hotkeys.rebind(hotkey)
        self.tray.showMessage(
            "Viewing",
            f"Новый хоткей: {hotkey.upper()}",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def shutdown(self) -> None:
        self.hotkeys.stop()
        self.tray.hide()
        self.app.quit()


def main() -> int:
    # High-DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Viewing")
    app.setOrganizationName("Kalekakektop2")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Viewing", "Системный трей недоступен.")
        return 1

    controller = AppController(app)
    # Keep reference
    app._viewing_controller = controller  # type: ignore[attr-defined]
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
