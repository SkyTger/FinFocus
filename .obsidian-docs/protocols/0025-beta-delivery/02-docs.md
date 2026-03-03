# Шаг 2: Документация

## Briefing

- **Цель:** Создать BETA_README.md и docs/RELEASE_GUIDE.md
- **Ключевые файлы:**
  - `BETA_README.md` — CREATE: инструкция на русском для бета-тестеров
  - `docs/RELEASE_GUIDE.md` — CREATE: процесс GitHub Release
- **Доп. информация:** Черновики из `.obsidian-docs/design/epic-09-phase-3/solution-v2.md`

## Sub-tasks

1. **BETA_README.md** — создать по черновику из solution-v2:
   - "Что это?" — краткое описание
   - "Установка за 3 шага": Python → распаковка → запуск
   - Ссылки на python.org для каждой ОС
   - "Частые вопросы (FAQ)" — 5+ вопросов:
     - Python не найден
     - Порт 8050 занят
     - Браузер не открылся
     - Как остановить
     - Как обновить
   - "Нашли ошибку?" — GitHub issue + описание + скриншот
   - **Без технического жаргона**

2. **docs/RELEASE_GUIDE.md** — создать:
   - Tag format: `v0.9.0-beta.N`
   - Пошаговый процесс создания Release
   - Шаблон Release Notes
   - Что включать в ZIP (start.sh, start.bat, BETA_README.md, requirements.txt, run.py, app/)
   - Что НЕ включать (.venv/, data/*.db, __pycache__/, .git/, tests/)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/main.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 3, Next Action: Финализация
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "docs(delivery): add BETA_README and RELEASE_GUIDE [protocol-0025/02]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
