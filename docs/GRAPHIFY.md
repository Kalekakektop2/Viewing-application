# Graphify — карта кода Viewing

Установлен пакет **[graphify](https://github.com/graphify-labs/graphify)** (PyPI: `graphifyy`).

## Что это

Инструмент строит **граф знаний** по репозиторию: классы, функции, связи.  
Удобно навигироваться по архитектуре без чтения всех файлов.

## Установка (уже в venv)

```bat
.venv\Scripts\activate
pip install graphifyy
graphify install --platform windows
graphify install --platform agents
```

## Пересобрать граф

```bat
cd Viewing-application
.venv\Scripts\graphify extract . --code-only --out .
.venv\Scripts\graphify cluster-only . --no-label
```

Результат: `graphify-out/`

| Файл | Смысл |
|------|--------|
| `graph.html` | Интерактивный граф |
| `graph.json` | Данные для запросов |
| `GRAPH_REPORT.md` | Отчёт / communities |

## Полезные команды

```bat
graphify god-nodes --top 15
graphify query "how does capture reach Gemini?"
graphify path "RegionSelector" "VisionClient"
graphify explain "OverlayPanel"
graphify hook install
```

## God nodes (текущий снимок)

1. OverlayPanel  
2. AppController  
3. VisionClient  
4. ItemCache  
5. Settings  
6. RegionSelector  
7. GameSession  

## Примечание

Полный multimodal-режим (`/graphify .`) использует LLM.  
`--code-only` — только AST, **без API-ключа**, подходит для CI.
