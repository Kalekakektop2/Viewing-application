# Перенос Viewing на другой ПК

## 1. С GitHub

```bat
git clone https://github.com/Kalekakektop2/Viewing-application.git
cd Viewing-application
```

## 2. Что **не** лежит в git (создать заново)

| Файл / папка | Действие |
|--------------|----------|
| `.env` | `copy .env.example .env` → вписать свой `GEMINI_API_KEY` |
| `.venv/` | создаётся при `run.bat` |
| `dist/` | exe собрать: `build_exe.bat` |
| `data/` | настройки/кэш появятся после запуска |

## 3. Запуск из исходников

1. Установить **Python 3.12** (Windows).
2. `run.bat`
3. Трей → `Alt+E` (или свой хоткей).

## 4. Сборка exe (по желанию)

```bat
build_exe.bat
```

Рядом с `dist\Viewing.exe` положить `.env`.

## 5. Репозитории проекта

| Репо | Зачем |
|------|--------|
| https://github.com/Kalekakektop2/Viewing-application | **Приложение** (этот) |
| https://github.com/Kalekakektop2/-Visual-gaming | Вижен / материалы сайта |

Дизайн-гайд (внешний): https://github.com/AkyRayy/Frontend-Design-SKILLS-for-AI  
Локально он не обязателен — принципы уже в `docs/DESIGN.md`.
