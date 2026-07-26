from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from PIL import Image

from viewing_app.ai.prompts import (
    INTENT_IMAGE,
    build_analysis_prompt,
    build_image_prompt,
)
from viewing_app.cache.store import ItemCache
from viewing_app.config import Settings
from viewing_app.session import GameSession


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
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.settings.api_key:
            return None
        try:
            from google import genai

            self._client = genai.Client(api_key=self.settings.api_key)
            return self._client
        except Exception:
            return None

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

        # Cache path: only if we already know item from a previous turn and text matches
        # Full vision cache by image hash is too brittle; rely on item name after first ID.
        prompt = build_analysis_prompt(
            intent=intent,
            user_text=user_text,
            detail_mode=detail_mode,
            game_name=self.session.game_name,
            language=self.settings.language,
        )

        client = self._ensure_client()
        if client is None:
            return self._offline_stub(image, intent=intent, user_text=user_text)

        try:
            from google.genai import types

            buf = BytesIO()
            rgb = image.convert("RGB")
            rgb.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                            types.Part.from_text(text=prompt),
                        ],
                    )
                ],
            )
            raw = (response.text or "").strip()
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

            # Try cache hit for known item + intent if model marked banal previously
            if parsed.item:
                cached = self.cache.lookup_banal(
                    parsed.item,
                    self.session.game_name,
                    intent,
                    detail_mode,
                )
                # already have answer from model; cache is for next time

            return parsed
        except Exception as exc:
            return AnalysisResult(
                answer="",
                error=f"Ошибка Vision API: {exc}",
            )

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
        client = self._ensure_client()
        if client is None:
            return AnalysisResult(
                answer="",
                error="Нет GEMINI_API_KEY — генерация изображения недоступна.",
            )
        # First identify quickly for better prompt if no text
        item = user_text.strip() or "game item from screenshot"
        prompt = build_image_prompt(item, self.session.game_name, user_text)
        try:
            from google.genai import types

            # Prefer image generation models when available; fall back to message.
            # gemini-2.0-flash-preview-image-generation or imagen — varies by account.
            model = self.settings.gemini_model
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )
            image_bytes = None
            text_parts: list[str] = []
            for cand in getattr(response, "candidates", None) or []:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", None) or []:
                    if getattr(part, "text", None):
                        text_parts.append(part.text)
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        image_bytes = inline.data
            if image_bytes:
                return AnalysisResult(
                    answer="Изображение сгенерировано.",
                    image_bytes=image_bytes,
                    item=item,
                )
            return AnalysisResult(
                answer="\n".join(text_parts) or "Модель не вернула изображение. "
                "Попробуйте другую модель (image-capable) или повторите позже.",
                error=None if text_parts else "no_image",
            )
        except Exception as exc:
            return AnalysisResult(
                answer="",
                error=(
                    f"Генерация изображения не удалась: {exc}\n"
                    "Убедитесь, что выбранная модель поддерживает IMAGE."
                ),
            )

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
                import json

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
                "🔧 Режим без API-ключа.\n\n"
                f"Размер скрина: {w}×{h}px\n"
                f"Intent: {intent}\n"
                f"Вопрос: {user_text or '(пусто → что это + крафт)'}\n"
                f"{self.session.context_summary()}\n\n"
                "Добавьте GEMINI_API_KEY в файл `.env` (см. `.env.example`) "
                "и перезапустите приложение.\n"
                "Ключ: https://aistudio.google.com/apikey"
            ),
            game=self.session.game_name,
            confidence=self.session.game_confidence,
            error="no_api_key",
        )
