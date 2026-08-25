# Шаг 2: Тесты визуального слоя щитка

## Briefing

- **Цель:** Закрыть тестовый долг протокола 0028: визуальный слой щитка
  (шапка, график полос, легенда, тултипы, расчёт подписей оси, пустые
  состояния) получает unit-тесты, чтобы кусок 2 Epic-11 менял дашборд
  под их защитой.
- **Ключевые файлы:**
  - `app/components/dashboard.py` — тестируемые чистые функции:
    - `build_free_header` (:193) + хелперы `_build_header_who` (:129),
      `_build_header_empty_state` (:162), `_build_recon_button` (:91),
      `_build_settings_cog` (:110)
    - `build_layers_chart` (:462), `_axis_tickvals` (:275),
      `_build_layer_legend` (:392), `_build_payments_tooltip` (:315),
      `_build_reserve_tooltip` (:355), `_build_chart_empty_state` (:439)
  - `tests/test_dashboard_panel_ui.py` — НОВЫЙ файл тестов
  - `app/schema/money_layers.py` — контракт `MoneyLayersData` для сборки
    фикстур (и константы `WINDOW_DAYS`, `MAX_X_TICKS`, `LAYER_COLORS`)
  - `tests/conftest.py` — хелперы относительных дат
- **Доп. информация:**
  - Функции чистые: принимают `MoneyLayersData`/`UserProfile`, возвращают
    Dash-компоненты. БД не нужна — фикстуры-словари, собранные хелпером
    в тест-файле. Проверять СТРУКТУРУ и ДАННЫЕ (тексты, суммы через
    format_rub, наличие/отсутствие элементов, id, классы), а не пиксели.
  - Три критерия приёмки 0028, проверенные тогда только вручную, —
    формализовать в тестах (найти их в
    `.obsidian-docs/protocols/0028-money-layers-panel/plan.md` /
    `.obsidian-docs/design/epic-11-panel-batch-1/spec.md`).
  - Обязательные инварианты для покрытия (из решений владельца, spec 0028):
    - в шапке НЕТ вердикта/светофора; единственное исключение —
      отрицательное «Свободно» красным (факт знака)
    - в шапке НЕТ приветствия
    - шапка — не дверь: без dcc.Link / n_clicks / cursor:pointer
    - `is_empty=True` → dcc.Graph ОТСУТСТВУЕТ в дереве (Plotly не вызывается)
    - `window_is_flat=True` → график рисуется (не подменяется пустым состоянием)
    - `degraded=True` → сноска «показано без бюджета целей» в шапке;
      тултип резерва не утверждает состав
    - `_axis_tickvals`: MAX_X_TICKS — потолок, не цель (k = ceil(len/MAX));
      первая/последняя даты окна
    - график: 3 traces в стопке (free/payments/reserve), линия «сегодня»,
      маркер минимума free, вехи целей ≤ MAX_MILESTONES_IN_WINDOW
    - легенда HTML (не Plotly), тултип резерва говорит факт дня
      (`reserve` vs `reserve_configured` — «остаётся X из Y»)
  - Обход дерева Dash-компонентов — маленьким локальным хелпером
    (рекурсия по .children), без сторонних библиотек.
  - Колбэки НЕ трогать — они уже покрыты `tests/test_dashboard_callbacks.py`
    и `tests/test_profile_modal_callbacks.py`.
  - Выборочная mutation-проверка: временно испортить 2-3 инварианта
    (например, вернуть приветствие в шапку, подменить график пустым
    состоянием при window_is_flat) → соответствующие тесты обязаны упасть.

## Sub-tasks

1. Найти и выписать (в log.md, кратко) три ручных критерия приёмки 0028
   из plan/spec родительского протокола — они станут именованными тестами.
2. Создать `tests/test_dashboard_panel_ui.py`: фикстуры-строители
   `MoneyLayersData` (нормальное окно / is_empty / window_is_flat /
   degraded / отрицательное free) на относительных датах + хелпер обхода
   дерева компонентов.
3. Тесты шапки: цифры из TodaySlice, разбор «баланс − платежи − резерв»,
   инварианты владельца (нет вердикта/приветствия/двери), красное
   отрицательное «Свободно», сноска degraded, empty state шапки.
4. Тесты графика: 3 traces и их порядок/цвета из LAYER_COLORS, линия
   «сегодня», маркер минимума, вехи целей (и beyond_window), пустые
   состояния (is_empty / window_is_flat), `_axis_tickvals` (потолок,
   границы, шаг k).
5. Тесты легенды и тултипов: состав легенды, тултип платежей (список
   UpcomingPayment), тултип резерва — факт дня vs настройка, вариант
   degraded.
6. Mutation-проверка 2-3 инвариантов (см. Доп. информация) — зафиксировать
   в log.md что ломали и какие тесты поймали.

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `/home/skytiger/Projects/FinFocus/.venv/bin/python -m py_compile tests/test_dashboard_panel_ui.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "test(dashboard): покрытие визуального слоя щитка [protocol-0029/2]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
