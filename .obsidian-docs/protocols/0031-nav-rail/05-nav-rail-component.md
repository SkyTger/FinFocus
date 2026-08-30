# Шаг 5: Компонент полоски

## Briefing

- **Цель:** `create_nav_rail(pathname, profile_data)` — чистая функция, ноль колбэков, ноль обращений к БД.
- **Ключевые файлы:**
  - `app/components/nav_rail.py` — **НОВЫЙ**
  - `app/components/panel_cards.py` — образец: `dcc.Link` без серверного Input
  - `app/config/avatars.py` — `get_avatar_emoji`
  - `app/schema/onboarding.py` — `UserProfile`
- **Доп. информация:** `sidebar.py` пока не трогаем.

## Sub-tasks

1. `RailSection(TypedDict)`: `label`, `icon`, `href`. `RAIL_SECTIONS` — **ровно четыре** раздела: Календарь `bi-calendar3` `/calendar`, Операции `bi-list-ul` `/transactions`, Аналитика `bi-bar-chart` `/analytics`, Цели `bi-target` `/goals`. Дашборда в списке НЕТ — на него ведёт логотип.

2. `_build_logo()` — `dcc.Link(href="/dashboard")`, знак `bi-house-door` (решение владельца: домик, семантика «Домой»; **не** искать буквальное изображение электрощитка), `aria-label="На дашборд"`.

3. `_build_section_slot(section, is_active)` — `dcc.Link` несёт класс слота (зона нажатия весь слот 44×44 по WCAG 2.5.5, не знак 22px), `html.I` вложен внутрь с `aria-hidden`. `aria-label` всегда, `aria-current="page"` на активном (в Dash — через `**{"aria-current": "page"}`, проверить на построении). Язычок `.nav-rail-tip` внутри.

4. `_build_avatar(profile_data)` — `html.Div(id="nav-rail-avatar", n_clicks=0)`, эмодзи через `get_avatar_emoji`, язычок «Профиль». Серверного Input на этот узел нет и не должно появиться (инвариант 3).

5. `create_nav_rail(pathname, profile_data)` — возвращает `html.Div(id="nav-rail", className="nav-rail")` с единственным ребёнком `.nav-rail-inner`.
   **Про `id` — записать в докстринге:** это носитель React-идентичности (`createContainer` ~3972: ключ обёртки = `stringifyId(props.id)`), а **НЕ приглашение вешать Input/Output** — такой Output был бы гонкой со слот-колбэком, создающим этот же узел (0026, 0028).
   **Проп `key` не ставится нигде**: на реконсиляцию обёртки не влияет, а `dcc.Link` его вообще не принимает (`TypeError` в dash 2.17.1).
   Функция тотальна: `None` и `"/"` → `"/dashboard"`, ни один раздел не активен.

6. Докстринг модуля: наследуемые инварианты (ноль `@callback`, ноль БД, вход в профиль через Store), отсутствие «Настроек» (FR-4) и версии (FR-5), отсутствие имени пользователя (в 60px не влезает — компенсируется окном профиля, RTM #68).

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: `.venv/bin/python -m py_compile app/components/nav_rail.py`
3. `grep -n "key=" app/components/nav_rail.py` → должно быть пусто
4. Обнови `log.md`, `context.md` (Current Step 6)
5. Коммит: `feat(nav-rail): компонент полоски-меню [protocol-0031/05]`
6. Push, отчёт
