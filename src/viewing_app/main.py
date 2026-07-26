from __future__ import annotations

import faulthandler
import sys
import threading
import traceback
from datetime import datetime
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
from viewing_app.ui.theme import app_stylesheet
from viewing_app.ui.tray_window import TrayWindow

# Strong global so controller never gets GC'd
_CONTROLLER_KEEPALIVE: AppController | None = None  # type: ignore[name-defined]


def _log(msg: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / "startup.log"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg.rstrip()}\n")
    except Exception:
        pass


def _install_crash_hooks() -> None:
    """Log uncaught exceptions / hard faults instead of silent exit."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    crash_path = DATA_DIR / "crash.log"
    try:
        fh = open(crash_path, "a", encoding="utf-8")
        faulthandler.enable(file=fh, all_threads=True)
    except Exception:
        try:
            faulthandler.enable(all_threads=True)
        except Exception:
            pass

    def excepthook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        _log("UNCAUGHT:\n" + text)
        try:
            with crash_path.open("a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.now()} ---\n{text}\n")
        except Exception:
            pass
        # Do NOT call sys.__excepthook__ in a way that kills tray app silently
        try:
            if QApplication.instance() is not None:
                box = QMessageBox()
                box.setIcon(QMessageBox.Icon.Critical)
                box.setWindowTitle("Viewing — ошибка")
                box.setText("Произошла ошибка (приложение продолжает работу в трее).")
                box.setDetailedText(text[-3000:])
                box.setWindowFlags(
                    box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
                )
                box.exec()
        except Exception:
            pass

    sys.excepthook = excepthook

    if hasattr(threading, "excepthook"):

        def thread_excepthook(args):  # type: ignore[no-untyped-def]
            text = "".join(
                traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
            )
            _log("THREAD UNCAUGHT:\n" + text)

        threading.excepthook = thread_excepthook  # type: ignore[assignment]


def build_app_icon() -> QIcon:
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
        p.drawLine(int(size * 0.25), int(size * 0.28), int(size * 0.5), int(size * 0.75))
        p.drawLine(int(size * 0.75), int(size * 0.28), int(size * 0.5), int(size * 0.75))
        p.end()
        icon.addPixmap(pix)
    return icon


class Bridge(QObject):
    capture_requested = Signal()


class AppController(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__(app)  # parent = app → lives for app lifetime
        self.app = app
        self.settings = Settings.load()
        self.session = GameSession()
        self.cache = ItemCache()
        self.client = VisionClient(self.settings, self.session, self.cache)
        self.icon = build_app_icon()
        self.app.setWindowIcon(self.icon)

        self.bridge = Bridge(self)
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
        QTimer.singleShot(400, self._start_hotkeys)

        self._setup_tray()

        # Heartbeat: proves process is alive; helps diagnose silent death
        self._heartbeat = QTimer(self)
        self._heartbeat.setInterval(5 * 60 * 1000)  # 5 min
        self._heartbeat.timeout.connect(lambda: _log("heartbeat ok"))
        self._heartbeat.start()

        QTimer.singleShot(200, self.show_panel)
        QTimer.singleShot(900, self._startup_toast)
        _log(f"ready hotkey={self.settings.hotkey} tray={self.tray.isVisible()}")

        app.aboutToQuit.connect(self._on_about_to_quit)

    def _startup_toast(self) -> None:
        try:
            if self.tray.isVisible():
                self.tray.showMessage(
                    "Viewing",
                    f"В трее (под стрелкой ↑). Хоткей: {self.settings.hotkey.upper()}",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000,
                )
        except Exception as exc:
            _log(f"toast failed: {exc}")

    def _on_about_to_quit(self) -> None:
        _log("aboutToQuit")

    def _start_hotkeys(self) -> None:
        try:
            if self.hotkeys is not None:
                try:
                    self.hotkeys.stop()
                except Exception:
                    pass
            self.hotkeys = HotkeyService(
                self.settings.hotkey,
                on_activate=lambda: self.bridge.capture_requested.emit(),
                parent=self,
            )
            self.hotkeys.start()
            _log(f"hotkeys started (win32 host) raw={self.settings.hotkey}")
        except Exception as exc:
            _log(f"hotkeys failed: {exc}")
            self._top_message(
                "Viewing",
                f"Не удалось зарегистрировать хоткей ({self.settings.hotkey}).\n"
                f"{exc}\n\n"
                "Комбинация может быть занята. Смените бинд в Настройках.",
            )

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon, self.app)
        self.tray.setToolTip(f"Viewing — {self.settings.hotkey.upper()}")

        # Keep menu + actions as instance attrs (prevent GC of QMenu)
        self._tray_menu = QMenu()
        # Menu chrome comes from app_stylesheet() (theme tokens)
        self._act_show = QAction("Открыть Viewing", self)
        self._act_show.triggered.connect(self.show_panel)
        self._act_capture = QAction("Захват области", self)
        self._act_capture.triggered.connect(self.start_capture)
        self._act_settings = QAction("Настройки", self)
        self._act_settings.triggered.connect(self.open_settings)
        self._act_quit = QAction("Выход", self)
        self._act_quit.triggered.connect(self.shutdown)

        self._tray_menu.addAction(self._act_show)
        self._tray_menu.addAction(self._act_capture)
        self._tray_menu.addAction(self._act_settings)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction(self._act_quit)
        self.tray.setContextMenu(self._tray_menu)
        self.tray.activated.connect(self._on_tray_activated)

        self.tray.show()
        QTimer.singleShot(0, self.tray.show)
        QTimer.singleShot(500, self.tray.show)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            _log("WARNING: system tray not available")
        _log(f"tray shown icon_null={self.icon.isNull()} visible={self.tray.isVisible()}")

    def show_panel(self) -> None:
        try:
            self.panel.set_hotkey(self.settings.hotkey)
            self.panel.show_near_tray()
        except Exception as exc:
            _log(f"show_panel error: {exc}")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
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
        try:
            if self.overlay.isVisible():
                self.overlay.hide()
            if self.panel.isVisible():
                self.panel.hide()
            QTimer.singleShot(150, self.selector.start)
        except Exception as exc:
            _log(f"start_capture error: {exc}")

    def _on_region(self, region) -> None:
        try:
            image = grab_region(region)
        except Exception as exc:
            self._top_message("Viewing", f"Не удалось захватить экран:\n{exc}")
            return
        try:
            self.overlay.show_for_image(image)
        except Exception as exc:
            _log(f"show_for_image error: {exc}\n{traceback.format_exc()}")
            self._top_message("Viewing", f"Ошибка оверлея:\n{exc}")

    def _on_cancel_select(self) -> None:
        pass

    def open_settings(self) -> None:
        panel_was = self.panel.isVisible()
        overlay_was = self.overlay.isVisible()
        if panel_was:
            self.panel.hide()
        if overlay_was:
            self.overlay.hide()

        dlg = SettingsDialog(self.settings)
        dlg.setWindowIcon(self.icon)
        dlg.hotkey_changed.connect(self._on_hotkey_changed)
        dlg.raise_()
        dlg.activateWindow()
        dlg.exec()

        self.tray.setToolTip(f"Viewing — {self.settings.hotkey.upper()}")
        self.panel.set_hotkey(self.settings.hotkey)
        self.client.settings = self.settings

        if overlay_was:
            self.overlay.show()
            self.overlay.raise_()
        if panel_was:
            self.panel.show()
            self.panel.raise_()
            self.panel.activateWindow()

    def _top_message(self, title: str, text: str, *, error: bool = False) -> None:
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(
            QMessageBox.Icon.Critical if error else QMessageBox.Icon.Warning
        )
        box.setWindowFlags(
            box.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        box.setWindowModality(Qt.WindowModality.ApplicationModal)
        box.raise_()
        box.activateWindow()
        box.exec()

    def _on_hotkey_changed(self, hotkey: str) -> None:
        try:
            if self.hotkeys:
                self.hotkeys.rebind(hotkey)
            else:
                self._start_hotkeys()
        except Exception as exc:
            self._top_message("Viewing", f"Хоткей не применился:\n{exc}")
            return
        self.tray.showMessage(
            "Viewing",
            f"Новый хоткей: {hotkey.upper()}",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def shutdown(self) -> None:
        _log("shutdown (user)")
        global _CONTROLLER_KEEPALIVE
        if self.hotkeys:
            try:
                self.hotkeys.stop()
            except Exception:
                pass
        try:
            self._heartbeat.stop()
        except Exception:
            pass
        self.tray.hide()
        self.panel.hide()
        self.overlay.hide()
        self.app.quit()


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _install_crash_hooks()
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
        app.setStyleSheet(app_stylesheet())

        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None,
                "Viewing",
                "Системный трей недоступен.\n"
                "Проверьте, что область уведомлений Windows включена.",
            )
            return 1

        global _CONTROLLER_KEEPALIVE
        controller = AppController(app)
        _CONTROLLER_KEEPALIVE = controller
        app._viewing_controller = controller  # type: ignore[attr-defined]

        code = app.exec()
        _log(f"event loop exit code={code}")
        return code
    except Exception:
        tb = traceback.format_exc()
        _log(tb)
        try:
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
