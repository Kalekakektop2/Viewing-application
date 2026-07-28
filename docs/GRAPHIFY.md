# Graphify — только для команды (этот репозиторий)

**Не** часть приложения для игроков.  
**Не** часть сайта Netlify/Vercel.  
**Да** — карта кода **Viewing-application** для нас (разработка / Grok / Cursor).

Пакет: [graphify-labs/graphify](https://github.com/graphify-labs/graphify) (PyPI: `graphifyy`).

---

## Зачем

Быстро понимать связи в проекте: `OverlayPanel` → `VisionClient` → backend, без перечитывания всех файлов.

Выход: папка `graphify-out/` в корне **этого** репо.

| Файл | Для чего |
|------|----------|
| `graphify-out/graph.html` | Открыть в браузере — интерактивный граф |
| `graphify-out/graph.json` | Запросы CLI |
| `graphify-out/GRAPH_REPORT.md` | Текстовый отчёт |

---

## Установка (на dev-машине)

```bat
cd Viewing-application
.venv\Scripts\activate
pip install -r requirements-dev.txt
graphify install --platform windows
graphify install --platform agents
```

Runtime для exe: только `requirements.txt` (**без** graphify).

---

## Пересобрать граф по этому проекту

```bat
cd C:\Users\Admin\Viewing-application
.venv\Scripts\graphify extract . --code-only --out .
.venv\Scripts\graphify cluster-only . --no-label
```

## Запросы

```bat
graphify god-nodes --top 15
graphify query "how does capture reach the backend?"
graphify path "RegionSelector" "VisionClient"
graphify explain "AppController"
```

Hook (опционально): `graphify hook install` — обновление графа после commit.

---

## God nodes (снимок)

1. OverlayPanel  
2. AppController  
3. VisionClient  
4. ItemCache / Settings / RegionSelector / GameSession  

---

## Границы

| | |
|--|--|
| Репо | `Viewing-application` only |
| Игроки / `.exe` | graphify **не** входит |
| Сайт | graphify **не** входит |
| Команда / ИИ-агенты | да — `graphify-out/` + `/graphify .` |
