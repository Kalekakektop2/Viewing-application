"""
Design tokens + Qt stylesheets for Viewing.

Aesthetic (Frontend-Design-SKILLS-for-AI):
  Technical / Mono + Refined Minimal (Linear/Vercel-like product chrome)
  — one accent, deep neutrals, hairlines, 6–8px radius, no gradient soup.
"""

from __future__ import annotations

# --- Tokens (Deep / Ink + single accent) — color.md ---
SURFACE = "#0E0E0E"
SURFACE_ELEVATED = "#161616"
SURFACE_SUNKEN = "#050505"
INK = "#F5F5F5"
INK_MUTED = "#A3A3A3"
INK_SUBTLE = "#6B6B6B"
HAIRLINE = "#262626"
HAIRLINE_STRONG = "#3D3D3D"
ACCENT = "#5CE1E6"  # single brand accent — used sparingly
ACCENT_SOFT = "rgba(92, 225, 230, 0.12)"
ACCENT_INK = "#0A0A0A"
WARNING = "#E8B84A"
ERROR = "#E85D6C"
RADIUS_SM = "6px"
RADIUS_MD = "8px"
FONT = '"Segoe UI", "Inter", system-ui, sans-serif'
FONT_MONO = '"Cascadia Mono", "Consolas", "JetBrains Mono", monospace'

# Transition timing (motion.md: short, purposeful)
TRANSITION_MS = "120ms"


def app_stylesheet() -> str:
    """Global app chrome (dialogs, menus)."""
    return f"""
    QWidget {{
        font-family: {FONT};
        font-size: 13px;
        color: {INK};
    }}
    QMenu {{
        background: {SURFACE_ELEVATED};
        color: {INK};
        border: 1px solid {HAIRLINE_STRONG};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 8px 14px;
        border-radius: {RADIUS_SM};
    }}
    QMenu::item:selected {{
        background: {ACCENT_SOFT};
        color: {ACCENT};
    }}
    QMenu::separator {{
        height: 1px;
        background: {HAIRLINE};
        margin: 4px 8px;
    }}
    QToolTip {{
        background: {SURFACE_ELEVATED};
        color: {INK};
        border: 1px solid {HAIRLINE};
        padding: 4px 8px;
    }}
    """


def overlay_stylesheet() -> str:
    """Wide HUD panel — product chrome, not marketing glassmorphism."""
    return f"""
    QFrame#card {{
        background: {SURFACE_ELEVATED};
        border: 1px solid {HAIRLINE_STRONG};
        border-radius: 10px;
    }}
    QLabel, QRadioButton, QTextEdit, QLineEdit {{
        color: {INK};
        font-family: {FONT};
    }}
    QLabel#title {{
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.04em;
        color: {INK};
    }}
    QLabel#kicker {{
        font-family: {FONT_MONO};
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 0.12em;
        color: {INK_SUBTLE};
        text-transform: uppercase;
    }}
    QLabel#muted {{
        color: {INK_MUTED};
        font-size: 11px;
    }}
    QLabel#status {{
        color: {ACCENT};
        font-size: 11px;
        font-family: {FONT_MONO};
    }}
    QLabel#warning {{
        color: {WARNING};
        font-size: 11px;
    }}
    QLineEdit, QTextEdit {{
        background: {SURFACE_SUNKEN};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_SM};
        padding: 8px 10px;
        selection-background-color: {ACCENT};
        selection-color: {ACCENT_INK};
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border: 1px solid {ACCENT};
    }}
    QTextEdit {{
        font-size: 13px;
        line-height: 1.45;
    }}
    QPushButton {{
        background: {ACCENT};
        color: {ACCENT_INK};
        border: 1px solid transparent;
        border-radius: {RADIUS_SM};
        padding: 0 12px;
        min-height: 32px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: #7AECF0;
    }}
    QPushButton:pressed {{
        background: #4BC8CD;
    }}
    QPushButton:disabled {{
        background: {HAIRLINE};
        color: {INK_SUBTLE};
    }}
    QPushButton#secondary {{
        background: transparent;
        color: {INK};
        border: 1px solid {HAIRLINE_STRONG};
        font-weight: 500;
    }}
    QPushButton#secondary:hover {{
        border-color: {ACCENT};
        color: {ACCENT};
        background: {ACCENT_SOFT};
    }}
    QPushButton#ghost {{
        background: transparent;
        color: {INK_MUTED};
        border: 1px solid transparent;
        font-weight: 500;
        min-height: 28px;
        padding: 0 8px;
    }}
    QPushButton#ghost:hover {{
        color: {INK};
        background: {ACCENT_SOFT};
    }}
    QPushButton#danger {{
        background: transparent;
        color: {ERROR};
        border: 1px solid rgba(232, 93, 108, 0.45);
        font-weight: 500;
    }}
    QPushButton#danger:hover {{
        background: rgba(232, 93, 108, 0.12);
    }}
    QRadioButton {{
        color: {INK_MUTED};
        spacing: 6px;
        font-size: 12px;
    }}
    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 7px;
        border: 1px solid {HAIRLINE_STRONG};
        background: {SURFACE_SUNKEN};
    }}
    QRadioButton::indicator:checked {{
        border: 4px solid {ACCENT};
        background: {SURFACE};
    }}
    QRadioButton:checked {{
        color: {INK};
        font-weight: 600;
    }}
    QLabel#preview {{
        background: {SURFACE_SUNKEN};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_SM};
    }}
    QFrame#divider {{
        background: {HAIRLINE};
        max-width: 1px;
        min-width: 1px;
    }}
    """


def tray_stylesheet() -> str:
    return f"""
    QWidget {{
        background: {SURFACE_ELEVATED};
        color: {INK};
        font-family: {FONT};
    }}
    QLabel#title {{
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.02em;
        color: {INK};
    }}
    QLabel#sub {{
        color: {INK_MUTED};
        font-size: 12px;
    }}
    QFrame#card {{
        background: {SURFACE};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_MD};
    }}
    QPushButton {{
        background: {ACCENT};
        color: {ACCENT_INK};
        border: none;
        border-radius: {RADIUS_SM};
        padding: 10px 14px;
        font-weight: 600;
        font-size: 12px;
        min-height: 36px;
    }}
    QPushButton:hover {{ background: #7AECF0; }}
    QPushButton#secondary {{
        background: transparent;
        color: {INK};
        border: 1px solid {HAIRLINE_STRONG};
        font-weight: 500;
    }}
    QPushButton#secondary:hover {{
        border-color: {ACCENT};
        color: {ACCENT};
        background: {ACCENT_SOFT};
    }}
    QPushButton#danger {{
        background: transparent;
        color: {ERROR};
        border: 1px solid rgba(232, 93, 108, 0.4);
        font-weight: 500;
    }}
    QPushButton#danger:hover {{
        background: rgba(232, 93, 108, 0.12);
    }}
    """


def settings_stylesheet() -> str:
    return f"""
    QDialog {{
        background: {SURFACE_ELEVATED};
        color: {INK};
        font-family: {FONT};
    }}
    QLabel {{ color: {INK}; font-size: 14px; }}
    QLineEdit {{
        background: {SURFACE_SUNKEN};
        color: {INK};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_SM};
        padding: 10px 14px;
        min-height: 28px;
        font-size: 15px;
    }}
    QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
    QPushButton {{
        background: {ACCENT};
        color: {ACCENT_INK};
        border: none;
        border-radius: {RADIUS_SM};
        padding: 10px 18px;
        font-weight: 600;
        min-height: 36px;
        font-size: 13px;
    }}
    QPushButton:hover {{ background: #7AECF0; }}
    QPushButton#secondary {{
        background: transparent;
        color: {INK};
        border: 1px solid {HAIRLINE_STRONG};
        font-weight: 500;
    }}
    QPushButton#secondary:hover {{
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    """
