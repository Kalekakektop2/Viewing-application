from __future__ import annotations

from typing import Optional

INTENT_DEFAULT = "identify_craft"
INTENT_IDENTIFY = "identify"
INTENT_CRAFT = "craft"
INTENT_LOCATE = "locate"
INTENT_CUSTOM = "custom"
INTENT_IMAGE = "generate_image"


def intent_label(intent: str) -> str:
    return {
        INTENT_DEFAULT: "Что это + как скрафтить",
        INTENT_IDENTIFY: "Что это?",
        INTENT_CRAFT: "Как скрафтить?",
        INTENT_LOCATE: "Где найти?",
        INTENT_CUSTOM: "Свободный вопрос",
        INTENT_IMAGE: "Сгенерировать изображение",
    }.get(intent, intent)


def build_analysis_prompt(
    *,
    intent: str,
    user_text: str,
    detail_mode: str,
    game_name: Optional[str],
    language: str = "ru",
) -> str:
    detail_ru = (
        "Формат КРАТКО: 3–8 строк. Название предмета, 1–2 предложения сути, "
        "короткий список (ингредиенты / биом / дроп). Без воды."
        if detail_mode == "brief"
        else "Формат РАСШИРЕННО: подробный гайд — шаги, производственная цепочка, "
        "альтернативы, скрытые детали, условия. Структурируй списками и подзаголовками."
    )

    intent_instruction = {
        INTENT_DEFAULT: "Определи объект на скриншоте и объясни, как его скрафтить/получить.",
        INTENT_IDENTIFY: "Определи, что изображено (предмет, блок, моб, UI-элемент).",
        INTENT_CRAFT: "Объясни рецепт крафта / как создать объект с экрана.",
        INTENT_LOCATE: "Объясни, где найти объект: биомы, мобы, дроп, условия спавна.",
        INTENT_CUSTOM: "Ответь на вопрос игрока по скриншоту.",
    }.get(intent, "Проанализируй скриншот и помоги игроку.")

    game_line = (
        f"Контекст сессии: игрок, вероятно, в игре «{game_name}». "
        "Используй этот контекст, не переспрашивай название игры, "
        "если нет явных признаков другой игры."
        if game_name
        else "Игра неизвестна — определи её по скриншоту."
    )

    user_q = user_text.strip() if user_text.strip() else "(вопрос не задан — действуй по intent)"

    return f"""Ты — игровой ассистент-оверлей. Отвечай на языке: {language}.

{game_line}

Задача: {intent_instruction}
Вопрос игрока: {user_q}

{detail_ru}

Важно:
- Читай текст/подсказки/тултипы на скриншоте (OCR), если они есть.
- Если уверенность в игре низкая — всё равно ответь, но укажи сомнение.
- Не выдумывай точные проценты дропа, если не уверен — скажи об этом.
- В начале ответа (первой строкой JSON-блока) верни метаданные, затем текст для игрока.

Верни ответ СТРОГО в таком виде:
```meta
{{"game": "название или null", "confidence": 0.0-1.0, "item": "имя предмета", "banal": true/false}}
```
```answer
(текст для игрока)
```

banal=true только для очень распространённых базовых предметов (дерево, камень, железо ваниль и т.п.).
"""


def build_image_prompt(item_name: str, game_name: Optional[str], user_hint: str) -> str:
    game = game_name or "unknown game"
    hint = user_hint.strip() or item_name
    return (
        f"Clear game-style illustration of «{hint}» from {game}, "
        "simple background, readable icon/item presentation, no watermark."
    )
