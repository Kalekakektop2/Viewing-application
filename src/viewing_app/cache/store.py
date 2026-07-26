from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Optional

from viewing_app.config import CACHE_DIR


class ItemCache:
    """Simple file cache for banal/common item answers."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or CACHE_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._index: dict = {}
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            try:
                self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._index = {}

    def _save(self) -> None:
        self.index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _normalize_item(name: str) -> str:
        return re.sub(r"\s+", " ", name.strip().lower())

    def make_key(
        self,
        item_name: str,
        game: str | None,
        intent: str,
        detail_mode: str,
    ) -> str:
        raw = f"{game or 'unknown'}|{self._normalize_item(item_name)}|{intent}|{detail_mode}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def get(self, key: str) -> Optional[str]:
        entry = self._index.get(key)
        if not entry:
            return None
        return entry.get("answer")

    def put(
        self,
        key: str,
        *,
        item_name: str,
        game: str | None,
        intent: str,
        detail_mode: str,
        answer: str,
        banal: bool = False,
    ) -> None:
        # Only cache short/banal answers by default flag, or always store if banal
        self._index[key] = {
            "item_name": item_name,
            "game": game,
            "intent": intent,
            "detail_mode": detail_mode,
            "answer": answer,
            "banal": banal,
            "ts": time.time(),
        }
        self._save()

    def lookup_banal(
        self,
        item_name: str,
        game: str | None,
        intent: str,
        detail_mode: str,
    ) -> Optional[str]:
        key = self.make_key(item_name, game, intent, detail_mode)
        entry = self._index.get(key)
        if entry and entry.get("banal"):
            return entry.get("answer")
        # Also try without detail mode for ultra-common items
        key2 = self.make_key(item_name, game, intent, "brief")
        entry2 = self._index.get(key2)
        if entry2 and entry2.get("banal"):
            return entry2.get("answer")
        return None
