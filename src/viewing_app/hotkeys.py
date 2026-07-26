from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QWidget

user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

user32.RegisterHotKey.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    wintypes.UINT,
    wintypes.UINT,
]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL


class MSG(ctypes.Structure):
    _fields_ = [
        ("hWnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


VK_MAP = {
    **{chr(c).lower(): c for c in range(ord("A"), ord("Z") + 1)},
    **{str(i): 0x30 + i for i in range(10)},
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "space": 0x20,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
}


def parse_hotkey_win(hotkey: str) -> tuple[int, int]:
    parts = [p.strip().lower() for p in hotkey.replace(" ", "").split("+") if p.strip()]
    if not parts:
        parts = ["alt", "e"]
    mods = 0
    key = None
    for p in parts:
        if p == "alt":
            mods |= MOD_ALT
        elif p in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif p == "shift":
            mods |= MOD_SHIFT
        elif p in ("win", "cmd", "super"):
            mods |= MOD_WIN
        else:
            key = p
    if key is None:
        key = "e"
    if mods == 0:
        mods = MOD_ALT
    vk = VK_MAP.get(key)
    if vk is None and len(key) == 1:
        vk = ord(key.upper())
    if vk is None:
        vk = ord("E")
    return mods, vk


class _HotkeyHost(QWidget):
    """
    Tiny native window that owns RegisterHotKey HWND.
    Handles WM_HOTKEY only on THIS window (safe — no app-wide native filter).
    """

    hotkey_pressed = Signal()

    def __init__(self, hotkey_id: int) -> None:
        # No QObject parent — QWidget parent must be QWidget; we keep ref on HotkeyService
        super().__init__(None)
        self._hotkey_id = hotkey_id
        self.setObjectName("ViewingHotkeyHost")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Keep a real HWND alive; off-screen 1x1
        self.setGeometry(-32000, -32000, 1, 1)
        self.show()

    @property
    def hwnd(self) -> int:
        return int(self.winId())

    def nativeEvent(self, eventType, message):  # noqa: N802
        try:
            et = bytes(eventType).decode("utf-8", errors="ignore")
        except Exception:
            et = str(eventType)
        if "windows" not in et.lower():
            return False, 0
        try:
            # PySide6: message is a voidptr-like object
            addr = int(message)
            if addr == 0:
                return False, 0
            msg = MSG.from_address(addr)
            if msg.message == WM_HOTKEY and int(msg.wParam) == self._hotkey_id:
                self.hotkey_pressed.emit()
                return True, 0
        except Exception:
            # Never let nativeEvent crash the process
            return False, 0
        return False, 0


class HotkeyService(QObject):
    """Global hotkey via Win32 RegisterHotKey on a dedicated host window."""

    activated = Signal()
    HOTKEY_ID = 0x56494557

    def __init__(
        self,
        hotkey: str,
        on_activate: Callable[[], None],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._raw = hotkey
        self._mods, self._vk = parse_hotkey_win(hotkey)
        self._on_activate = on_activate
        self._host: Optional[_HotkeyHost] = None
        self._hwnd = 0
        self.activated.connect(self._emit_user)

    @property
    def hotkey(self) -> str:
        return self._raw

    def start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Хоткеи только на Windows")
        self.stop()

        self._host = _HotkeyHost(self.HOTKEY_ID)
        self._host.hotkey_pressed.connect(self.activated)
        # Ensure native window exists
        self._host.show()
        QApplication.processEvents()
        self._hwnd = self._host.hwnd
        if not self._hwnd:
            raise OSError("Не удалось создать HWND для хоткея")

        registered = False
        for mods in (self._mods | MOD_NOREPEAT, self._mods):
            if user32.RegisterHotKey(self._hwnd, self.HOTKEY_ID, mods, self._vk):
                registered = True
                break
        if not registered:
            err = ctypes.get_last_error()
            self.stop()
            raise OSError(
                f"RegisterHotKey failed (WinError {err}). "
                f"Комбинация «{self._raw}» занята — смените в настройках."
            )

    def rebind(self, hotkey: str) -> None:
        self._raw = hotkey
        self._mods, self._vk = parse_hotkey_win(hotkey)
        self.start()

    def stop(self) -> None:
        if self._hwnd:
            try:
                user32.UnregisterHotKey(self._hwnd, self.HOTKEY_ID)
            except Exception:
                pass
        self._hwnd = 0
        if self._host is not None:
            try:
                self._host.hotkey_pressed.disconnect()
            except Exception:
                pass
            self._host.hide()
            self._host.deleteLater()
            self._host = None

    def _emit_user(self) -> None:
        try:
            self._on_activate()
        except Exception:
            pass
