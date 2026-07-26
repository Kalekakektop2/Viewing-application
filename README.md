# Viewing-application

**Windows-оверлей** для геймеров: `Alt+E` → выделить область → Vision-ИИ (Gemini) подсказывает, что на скрине, как скрафтить и где найти.

Спецификация: [docs/APP_SPEC.md](docs/APP_SPEC.md)  
Продуктовый вижен: [Visual-gaming](https://github.com/Kalekakektop2/-Visual-gaming)

---

## Возможности (MVP 0.1)

| Функция | Статус |
|--------|--------|
| Глобальный хоткей (по умолчанию `Alt+E`) | ✅ |
| Смена хоткея в настройках | ✅ |
| Выделение **только** области экрана | ✅ |
| Оверлей поверх всех окон | ✅ |
| Закрытие кликом вне панели | ✅ |
| Диалог (несколько вопросов) | ✅ |
| Кнопки: Что это / Крафт / Где найти | ✅ |
| Кратко / Расширенно | ✅ |
| По умолчанию: что это + крафт (пустой ввод) | ✅ |
| Gemini Vision + офлайн-заглушка без ключа | ✅ |
| Память игры в сессии + warning при низкой уверенности | ✅ |
| Кэш банальных предметов | ✅ |
| «Сгенерировать фото» + предупреждение о времени | ✅ (зависит от модели) |
| Системный трей | ✅ |

---

## Требования

- **Windows 10/11**
- **Python 3.11+** (рекомендуется 3.12)
- Ключ [Google AI Studio](https://aistudio.google.com/apikey) (бесплатный Gemini)

---

## Установка и запуск

### Готовый .exe

```bat
:: после сборки:
dist\Viewing.exe
```

Рядом с exe положите файл `.env` с `GEMINI_API_KEY=...`  
(модель по умолчанию: `gemini-flash-latest`).

Сборка exe:

```bat
build_exe.bat
:: или:  .venv\Scripts\python -m PyInstaller --noconfirm build_exe.spec
```

### Из исходников

```bat
cd Viewing-application
copy .env.example .env
:: впишите GEMINI_API_KEY в .env

run.bat
```

Или вручную:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PYTHONPATH=src
python -m viewing_app
```

После запуска приложение сидит **в трее**.  
`Alt+E` — захват области. ПКМ по иконке трея — настройки / выход.

---

## Структура

```
Viewing-application/
├── docs/APP_SPEC.md
├── src/viewing_app/
│   ├── main.py            # трей, хоткей, оркестрация
│   ├── config.py          # настройки + .env
│   ├── session.py         # контекст игры / диалог
│   ├── hotkeys.py
│   ├── ai/                # Gemini + промпты
│   ├── cache/             # файловый кэш
│   ├── capture/           # region selector + mss
│   └── ui/                # оверлей + настройки
├── data/                  # settings.json, cache (локально, в .gitignore)
├── requirements.txt
├── run.bat
└── .env.example
```

---

## Замечания

- **Exclusive fullscreen / античит** могут блокировать оверлей — используйте borderless/windowed, где возможно.
- Без `GEMINI_API_KEY` UI работает, вместо ИИ показывается офлайн-ответ с размером скрина.
- Генерация фото требует image-capable модели и может быть медленной или недоступной на free-tier.

---

## Roadmap (кратко)

- OCR-движок отдельно (Tesseract) как fallback
- Улучшение sticky game detection
- Упаковка в `.exe` (PyInstaller)
- Профиль «игра сменилась» вручную
