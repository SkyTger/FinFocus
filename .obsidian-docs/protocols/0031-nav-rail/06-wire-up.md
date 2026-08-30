# Шаг 6: Подключение компонента

## Briefing

- **Цель:** Полоска встаёт в layout вместо сайдбара. Старый `sidebar.py` остаётся жив и просто перестаёт вызываться — мёртвый код на три шага, это осознанно.
- **Ключевые файлы:**
  - `app/main.py:27` (импорт), `:75` (слот), `:129-179` (слот-колбэк), `:188-193` (clientside-триггер)
  - `app/assets/clientside_triggers.js` — `timestamp_trigger` переиспользуется без изменений
- **Доп. информация:** Контракт двух Input'ов слот-колбэка НЕ меняется.

## Sub-tasks

1. Импорт `create_nav_rail` вместо `create_sidebar`.

2. Слот в layout: `html.Div(id="nav-rail-slot", className="nav-rail-column")` (было `sidebar-slot`/`sidebar-column`). Переименование не косметика: старый `.sidebar-column` несёт `width: 288px`.

3. `render_sidebar_slot` → `render_nav_rail_slot`. Тело и оба Input'а (`url.pathname`, `profile-updated.data` — всегда присутствующие узлы) без изменений, кроме имени и вызова компонента.
   **Возврат — РОВНО ОДИН компонент, не список**: это часть механизма FR-2 (стабильная позиция единственного ребёнка в дополнение к стабильному `id`).
   На дашбордных путях `[]` **до открытия сессии**. Fail-open чтения профиля сохраняется (except → заглушка + лог; находимость разделов важнее аватара).

4. Clientside-триггер: `Input("nav-rail-avatar", "n_clicks")` → `Output("open-profile-trigger", "data")` через существующую `ClientsideFunction("triggers", "timestamp_trigger")`. Новой JS-функции не нужно.

5. **Правка докстринга `timestamp_trigger`** в `clientside_triggers.js` (факт установлен чтением файла): сейчас там «Используется для: recon buttons (Calendar, Dashboard KPI)» — закрытый перечень, устаревший ещё с протокола 0030 (аватар сайдбара пользуется той же функцией и не упомянут). Дописать аватар полоски и снять видимость исчерпывающего списка.

6. **Убедиться, что `_OWNED_SEARCH_PATHS` и `handle_panel_query_params` не задеты вовсе** (инвариант 4, C-4/AC-10).

7. Проверить второй вход в профиль: шестерёнка `pnl-cog` на дашборде пишет в тот же Store с `allow_duplicate=True` — переименование первого входа не должно её сломать.

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `.venv/bin/python -m py_compile app/main.py`
3. `.venv/bin/python -m pytest tests/test_panel_query_params.py -v` — регрессионный барьер AC-10, должен быть зелёным без правок
4. Обнови `log.md`, `context.md` (Current Step 7)
5. Коммит: `feat(nav-rail): подключение полоски в layout [protocol-0031/06]`
6. Push, отчёт
