from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Optional
from urllib import error, request

from PIL import Image

from viewing_app.ai.prompts import (
    INTENT_IMAGE,
    build_analysis_prompt,
    build_image_prompt,
)
from viewing_app.cache.store import ItemCache
from viewing_app.config import Settings
from viewing_app.session import GameSession

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


@dataclass
class AnalysisResult:
    answer: str
    game: Optional[str] = None
    confidence: float = 0.0
    item: Optional[str] = None
    banal: bool = False
    from_cache: bool = False
    warning: Optional[str] = None
    error: Optional[str] = None
    image_bytes: Optional[bytes] = None


class VisionClient:
    def __init__(self, settings: Settings, session: GameSession, cache: ItemCache) -> None:
        self.settings = settings
        self.session = session
        self.cache = cache

    def analyze(
        self,
        image: Image.Image,
        *,
        intent: str,
        user_text: str,
        detail_mode: str,
    ) -> AnalysisResult:
        if intent == INTENT_IMAGE:
            return self.generate_image(image, user_text=user_text)

        prompt = build_analysis_prompt(
            intent=intent,
            user_text=user_text,
            detail_mode=detail_mode,
            game_name=self.session.game_name,
            language=self.settings.language,
        )

        # Production: backend proxy (no client API key). Dev: optional direct Gemini key.
        if not self.settings.api_key and not self.settings.backend_url:
            return self._offline_stub(image, intent=intent, user_text=user_text)

        try:
            raw = self._generate_content(image=image, text=prompt)
            parsed = self._parse_response(raw)
            warning = self.session.update_game(parsed.game, parsed.confidence)
            parsed.warning = warning

            if parsed.item and parsed.banal and parsed.answer:
                key = self.cache.make_key(
                    parsed.item,
                    self.session.game_name or parsed.game,
                    intent,
                    detail_mode,
                )
                self.cache.put(
                    key,
                    item_name=parsed.item,
                    game=self.session.game_name or parsed.game,
                    intent=intent,
                    detail_mode=detail_mode,
                    answer=parsed.answer,
                    banal=True,
                )
            return parsed
        except Exception as exc:
            return AnalysisResult(answer="", error=f"Ошибка Vision API: {exc}")

    def try_cache_only(
        self,
        item_name: str,
        intent: str,
        detail_mode: str,
    ) -> Optional[AnalysisResult]:
        hit = self.cache.lookup_banal(
            item_name, self.session.game_name, intent, detail_mode
        )
        if not hit:
            return None
        return AnalysisResult(
            answer=hit,
            item=item_name,
            game=self.session.game_name,
            banal=True,
            from_cache=True,
        )

    def generate_image(self, image: Image.Image, *, user_text: str) -> AnalysisResult:
        if not self.settings.api_key:
            return AnalysisResult(
                answer="",
                error="Нет GEMINI_API_KEY — генерация изображения недоступна.",
            )
        item = user_text.strip() or "game item from screenshot"
        prompt = build_image_prompt(item, self.session.game_name, user_text)
        try:
            # Image generation endpoints vary; try generateContent with IMAGE modality
            url = (
                f"{GEMINI_BASE}/models/{self.settings.gemini_model}:generateContent"
                f"?key={self.settings.api_key}"
            )
            body = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
            }
            data = self._post_json(url, body)
            image_bytes = None
            text_parts: list[str] = []
            for cand in data.get("candidates") or []:
                for part in (cand.get("content") or {}).get("parts") or []:
                    if part.get("text"):
                        text_parts.append(part["text"])
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        image_bytes = base64.b64decode(inline["data"])
            if image_bytes:
                return AnalysisResult(
                    answer="Изображение сгенерировано.",
                    image_bytes=image_bytes,
                    item=item,
                )
            return AnalysisResult(
                answer="\n".join(text_parts)
                or "Модель не вернула изображение. Попробуйте image-модель позже.",
                error=None if text_parts else "no_image",
            )
        except Exception as exc:
            return AnalysisResult(
                answer="",
                error=(
                    f"Генерация изображения не удалась: {exc}\n"
                    "Нужна image-capable модель."
                ),
            )

    def _generate_content(self, *, image: Image.Image, text: str) -> str:
        buf = BytesIO()
        image.convert("RGB").save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        # Prefer server proxy (player builds: no client key). Dev may set local GEMINI_API_KEY.
        force_direct = bool(self.settings.api_key) and not getattr(
            __import__("sys"), "frozen", False
        )
        if self.settings.backend_url and not force_direct:
            data = self._post_json(
                self.settings.backend_url,
                {
                    "image_b64": b64,
                    "prompt": text,
                    "model": self.settings.gemini_model,
                },
            )
            if data.get("error"):
                raise RuntimeError(str(data["error"]))
            out = (data.get("text") or "").strip()
            if not out:
                raise RuntimeError("Пустой ответ backend")
            return out

        if not self.settings.api_key:
            raise RuntimeError("Нет API-ключа и backend_url")

        url = (
            f"{GEMINI_BASE}/models/{self.settings.gemini_model}:generateContent"
            f"?key={self.settings.api_key}"
        )
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": "image/png", "data": b64}},
                        {"text": text},
                    ],
                }
            ]
        }
        data = self._post_json(url, body)
        texts: list[str] = []
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                if part.get("text"):
                    texts.append(part["text"])
        if not texts:
            raise RuntimeError(json.dumps(data, ensure_ascii=False)[:500])
        return "\n".join(texts).strip()

    def _post_json(self, url: str, body: dict) -> dict:
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail[:800]}") from exc

    def _parse_response(self, raw: str) -> AnalysisResult:
        game = None
        confidence = 0.0
        item = None
        banal = False
        answer = raw

        meta_match = re.search(r"```meta\s*([\s\S]*?)```", raw, re.I)
        ans_match = re.search(r"```answer\s*([\s\S]*?)```", raw, re.I)
        if meta_match:
            meta_raw = meta_match.group(1).strip()
            try:
                meta = json.loads(meta_raw)
                game = meta.get("game")
                confidence = float(meta.get("confidence") or 0)
                item = meta.get("item")
                banal = bool(meta.get("banal"))
            except Exception:
                pass
        if ans_match:
            answer = ans_match.group(1).strip()
        elif meta_match:
            answer = raw[meta_match.end() :].strip()

        return AnalysisResult(
            answer=answer,
            game=game if game not in (None, "null", "") else None,
            confidence=max(0.0, min(1.0, confidence)),
            item=item,
            banal=banal,
        )

    def _offline_stub(
        self, image: Image.Image, *, intent: str, user_text: str
    ) -> AnalysisResult:
        w, h = image.size
        return AnalysisResult(
            answer=(
                "Нет связи с AI-сервером.\n\n"
                f"Размер скрина: {w}×{h}px\n"
                f"{self.session.context_summary()}\n\n"
                "Бета ходит на backend сайта (ключ Gemini только на сервере).\n"
                "Проверьте интернет или backend_url в настройках."
            ),
            game=self.session.game_name,
            confidence=self.session.game_confidence,
            error="no_backend",
        )
