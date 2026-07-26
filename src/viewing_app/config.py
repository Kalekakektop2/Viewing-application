from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Project root: Viewing-application/
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
SETTINGS_PATH = DATA_DIR / "settings.json"

load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    hotkey: str = "alt+e"
    detail_mode: str = "brief"  # brief | detailed
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    )
    api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    language: str = "ru"

    @classmethod
    def load(cls) -> "Settings":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        base = cls()
        if SETTINGS_PATH.exists():
            try:
                raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                for key in ("hotkey", "detail_mode", "gemini_model", "language"):
                    if key in raw and raw[key]:
                        setattr(base, key, raw[key])
            except (json.JSONDecodeError, OSError):
                pass
        # Env always wins for secrets
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        if env_key:
            base.api_key = env_key
        env_model = os.getenv("GEMINI_MODEL", "").strip()
        if env_model:
            base.gemini_model = env_model
        return base

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "hotkey": self.hotkey,
            "detail_mode": self.detail_mode,
            "gemini_model": self.gemini_model,
            "language": self.language,
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
