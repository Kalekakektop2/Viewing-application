from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _project_root() -> Path:
    """Dev: repo root. Frozen .exe: folder next to the executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    """Path to bundled resource (PyInstaller _MEIPASS) or project assets."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / Path(*parts)  # type: ignore[attr-defined]
    return _project_root() / Path(*parts)


# Project root: Viewing-application/ (or dist/ when packaged)
ROOT = _project_root()
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
SETTINGS_PATH = DATA_DIR / "settings.json"

load_dotenv(ROOT / ".env")
# Also try cwd (handy when launching from another folder)
load_dotenv(Path.cwd() / ".env", override=False)


# Public backend (API key only on server — never in the .exe).
DEFAULT_BACKEND_URL = "https://game-vision-site.vercel.app/api/analyze"


def _normalize_backend_url(url: str) -> str:
    """Force working Vercel proxy; reject dead Netlify function URLs."""
    u = (url or "").strip().rstrip("/")
    if not u:
        return DEFAULT_BACKEND_URL
    # Old broken Netlify path → auto-migrate
    if "netlify.app" in u or "netlify.com" in u or "/.netlify/functions/" in u:
        return DEFAULT_BACKEND_URL
    if not u.endswith("/api/analyze") and "vercel.app" in u and "/api/" not in u:
        return u.rstrip("/") + "/api/analyze"
    return u


@dataclass
class Settings:
    hotkey: str = "alt+e"
    detail_mode: str = "brief"  # brief | detailed
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    )
    # Optional local/dev key. Player builds use backend only.
    api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    backend_url: str = field(default_factory=lambda: DEFAULT_BACKEND_URL)
    language: str = "ru"

    @classmethod
    def load(cls) -> "Settings":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        base = cls()
        if SETTINGS_PATH.exists():
            try:
                raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                for key in (
                    "hotkey",
                    "detail_mode",
                    "gemini_model",
                    "language",
                    "backend_url",
                ):
                    if key in raw and raw[key]:
                        setattr(base, key, raw[key])
            except (json.JSONDecodeError, OSError):
                pass
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        if env_key:
            base.api_key = env_key
        env_model = os.getenv("GEMINI_MODEL", "").strip()
        if env_model:
            base.gemini_model = env_model
        env_backend = os.getenv("VIEWING_BACKEND_URL", "").strip()
        if env_backend:
            base.backend_url = env_backend
        base.backend_url = _normalize_backend_url(base.backend_url)
        # Persist migration away from Netlify so next launch is clean
        try:
            base.save()
        except Exception:
            pass
        return base

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "hotkey": self.hotkey,
            "detail_mode": self.detail_mode,
            "gemini_model": self.gemini_model,
            "language": self.language,
            "backend_url": self.backend_url,
        }
        SETTINGS_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def to_public_dict(self) -> dict:
        d = asdict(self)
        if d.get("api_key"):
            d["api_key"] = "***"
        return d
