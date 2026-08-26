# Шаг 6: Сайдбар без колбэков

## Briefing

- **Цель:** снять сайдбар с дашборда; `create_sidebar` — чистая функция; оба колбэка сайдбара удалить; защитить вход в профиль.
- **Ключевые файлы:**
  - `app/main.py` — `sidebar-slot` + `render_sidebar_slot`
  - `app/components/sidebar.py` — чистая функция, минус два колбэка
  - `app/components/profile_modal.py` — единственный вход открытия
  - `app/assets/sidebar.css` — один механизм скрытия колонки
- **Доп. информация:** solution-v4.md, план шаг 8 + секция «Сайдбар: Подход B». **Это самый рискованный шаг протокола** — класс регрессий C-6 работает в обе стороны.

## Sub-tasks

- [ ] `main.py`: `html.Div(id="sidebar-slot")` + `render_sidebar_slot(pathname, profile_updated)` — **два** Input'а на всегда присутствующие `url` и Store `profile-updated`; `[]` на дашборде **до** открытия сессии; одна сессия внутри с **fail-open** (`except` → профиль-заглушка + `logger.opt(exception=True)`, навигация остаётся)
- [ ] Снять статический вызов `create_sidebar()` из layout (`main.py:59`)
- [ ] `sidebar.py`: `create_sidebar(pathname, profile)` — чистая функция; литералы «Пользователь» (`:82`) и `😊` (`:65`) → из аргумента; `_build_nav_links("/dashboard")` (`:106`) → `_build_nav_links(pathname or "/dashboard")`
- [ ] **Удалить оба колбэка**: `highlight_active_sidebar` (`:152-160`) и `update_sidebar_profile` (`:163-185`); убрать ставшие ненужными импорты; `exc_info=True` (`:184`) уходит вместе с колбэком
- [ ] `profile_modal.py`: убрать `Input("sidebar-profile-container")` (`:96`) — **единственный** вход открытия `open-profile-trigger`, guard на пустой Store сохранить; `exc_info=True` (`:143,159,163`) → `logger.opt(exception=True)`
- [ ] `sidebar.css`: **один** механизм скрытия — `.sidebar-column:empty { display: none }` (правило `d-none` не вводить)
- [ ] Проверить `grep -rn "highlight_active_sidebar\|update_sidebar_profile" tests/` — если тесты есть, они удаляются вместе с колбэками, их роль берёт `test_sidebar.py` (шаг 8)

## Workflow

1. Выполни Sub-tasks последовательно
2. Проверка: `python -m py_compile app/main.py app/components/sidebar.py app/components/profile_modal.py` + `pytest tests/test_profile_modal_callbacks.py`
3. **Ручная проверка (обязательна, юнит-тестом не ловится):** запустить приложение; профиль открывается шестерёнкой на дашборде И аватаром на каждом из четырёх разделов; имя и аватар в сайдбаре корректны на всех разделах и после правки профиля; подсветка активного пункта работает; сайдбара на дашборде нет и он не оставляет пустой колонки
4. Обнови `log.md`, `context.md`
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(ui): сайдбар снят с дашборда, оба колбэка удалены [protocol-0030/06]"`
7. Push
8. Отчёт
