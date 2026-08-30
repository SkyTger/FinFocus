# Шаг 9: Свернуть прежний сайдбар

## Briefing

- **Цель:** Убрать мёртвый код. **Только теперь** — после зелёного `test_nav_rail.py` (шаг 7) и пройденной живой AC-5 (шаг 8). Это единственная необратимая операция протокола.
- **Ключевые файлы:**
  - `app/components/sidebar.py` — **УСЫХАЕТ до надгробия, НЕ удаляется**
  - `app/assets/sidebar.css` — удаляется целиком
  - `tests/test_sidebar.py` — удаляется
- **Доп. информация:** Решение владельца Р2 — константа `ADDITIONAL_NAV_ITEMS` остаётся.

## Sub-tasks

1. **Перед удалением:** `grep -rn "sidebar" app/ tests/` — разобрать каждое попадание по критерию «исполняемое / докстринг». Не должно остаться **исполняемых** упоминаний: импортов `app.components.sidebar`, id `sidebar-slot`/`sidebar-profile-container`, классов `.sidebar-*` в CSS или в `className`. Отдельно `grep -n "sidebar" app/assets/custom.css`.
   Ожидаемые и **допустимые** попадания: файл-надгробие и докстринги вида «прежний сайдбар».

2. `app/components/sidebar.py` усыхает до `ADDITIONAL_NAV_ITEMS` + докстринг-надгробие: «остаток удалённого сайдбара; константа сохранена решением владельца 2026-08-27, вернуть иконку при появлении `/settings` или `/help`». Уходят: `MAIN_NAV_ITEMS`, `_build_nav_links`, `create_sidebar`, зашитая `html.Span("v1.0.0")` (строка 166), импорты `dbc`/`html`/`get_avatar_emoji`/`UserProfile`.
   **Файл НЕ удаляется** — решение владельца Р2: прецедент «решение владельца можно обойти удачной трактовкой» дороже одного почти пустого файла.

3. `app/assets/sidebar.css` — удаляется целиком (весь про 288px-карточку; CSS-файл под решение владельца не подпадает).

4. `tests/test_sidebar.py` — удаляется, его роль полностью перенял `test_nav_rail.py`.

5. Активировать отложенный тест из шага 2: `grep` по `app/` не находит `v1.0.0` — теперь должен быть зелёным.

6. Тест: `ADDITIONAL_NAV_ITEMS` никем не импортируется.

## Workflow

1. Выполни Sub-tasks
2. `.venv/bin/python -m pytest` — весь прогон
3. `.venv/bin/python -m flake8 app/` — новых замечаний быть не должно (известные pre-existing E501: goals.py:3085, dashboard_service.py:375/420, transaction_service.py:54)
4. Обнови `log.md`, `context.md` (Current Step 10)
5. Коммит: `refactor(sidebar): свернуть прежний сайдбар до надгробия [protocol-0031/09]`
6. Push, отчёт
