from __future__ import annotations

from typing import Callable, Optional

from pynput import keyboard


def parse_hotkey(hotkey: str) -> str:
    """Normalize user hotkey to pynput format: <alt>+e"""
    parts = [p.strip().lower() for p in hotkey.replace(" ", "").split("+") if p.strip()]
    if not parts:
        return "<alt>+e"
    mods = []
    key = None
    for p in parts:
        if p in ("alt", "ctrl", "control", "shift", "win", "cmd", "cmd_l", "cmd_r"):
            name = "ctrl" if p == "control" else p
            if name == "win":
                name = "cmd"
            mods.append(f"<{name}>")
        else:
            key = p
    if not key:
        key = "e"
    if not mods:
        mods = ["<alt>"]
    return "+".join(mods + [key])


class HotkeyService:
    def __init__(self, hotkey: str, on_activate: Callable[[], None]) -> None:
        self._on_activate = on_activate
        self._hotkey = parse_hotkey(hotkey)
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    @property
    def hotkey(self) -> str:
        return self._hotkey

    def start(self) -> None:
        self.stop()
        mapping = {self._hotkey: self._safe_activate}
        self._listener = keyboard.GlobalHotKeys(mapping)
        self._listener.start()

    def rebind(self, hotkey: str) -> None:
        self._hotkey = parse_hotkey(hotkey)
        self.start()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _safe_activate(self) -> None:
        try:
            self._on_activate()
        except Exception:
            pass
