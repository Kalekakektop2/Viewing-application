# -*- mode: python ; coding: utf-8 -*-
# Onefile GUI build without google-genai (REST via urllib)

block_cipher = None

from pathlib import Path

_ROOT = Path(SPECPATH)
_ASSETS = _ROOT / "assets"

a = Analysis(
    ["src/viewing_app/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        (str(_ASSETS / "viewing.ico"), "assets"),
        (str(_ASSETS / "viewing.png"), "assets"),
    ] if (_ASSETS / "viewing.ico").exists() else [],
    hiddenimports=[
        "viewing_app",
        "viewing_app.main",
        "viewing_app.config",
        "viewing_app.session",
        "viewing_app.hotkeys",
        "viewing_app.ai.client",
        "viewing_app.ai.prompts",
        "viewing_app.cache.store",
        "viewing_app.capture.region",
        "viewing_app.ui.overlay",
        "viewing_app.ui.settings_dialog",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "mss",
        "mss.windows",
        "PIL",
        "PIL.Image",
        "dotenv",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pytest",
        "google",
        "httpx",
        "anyio",
        "pydantic",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Viewing",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_ASSETS / "viewing.ico") if (_ASSETS / "viewing.ico").exists() else None,
)
