# Шаг 7: Переключение callback'ов, снятие вытесненного, чистка

## Briefing

- **Цель:** Перевести дашборд на новую модель, снять переключатель периода и приветствие, удалить мёртвый код и осиротевший CSS, поправить тесты callback'ов.
- **Ключевые файлы:**
  - `app/components/dashboard.py` — layout, `_load_dashboard_components`, `load_dashboard_data`, `refresh_dashboard_after_crud`, `open_create_from_chart`, удаление мёртвого кода
  - `app/assets/custom.css` — чистка
  - `tests/test_dashboard_callbacks.py` — четыре позиции правок
- **Источник правды:** solution-v4.md — таблица «Состав Output'ов после правки», раздел «Судьба `dashboard-greeting` и `_build_greeting_text`», шаги 11–13 плана.
- **Соответствует шагам 11, 12, 13 плана решения** (оценка 7 ч).

## Это шаг с наибольшим blast radius

Снимается сразу несколько элементов, у каждого есть потребители. Порядок важен: сначала переключить callback'и, потом удалять — иначе приложение не поднимется между правками.

## Sub-tasks

1. **`_load_dashboard_components(period_state)`** — сигнатура **теряет `period`**:
   - Причина: `update_period_state` — единственный писатель Store `dashboard-period`, он снимается вместе с `period-switcher`; аргумент навсегда получал бы дефолт из layout. Мёртвый параметр не заводим
   - Внутри: **один** `OnboardingService.get_profile()` (для шапки) + **один** `MoneyLayersService.get_money_layers()`
   - Возврат — 5 значений: `(free_header, layers_chart, recent, upcoming, cushion)`
   - Store `dashboard-period` **остаётся** в layout с дефолтом (его читает `open_create_from_chart` как guard)

2. **`load_dashboard_data`** — новый контракт:
   - Outputs (5): `dashboard-free-header`, `dashboard-layers-chart`, `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `dashboard-cushion-card`
   - **Снять** Output `dashboard-greeting` (:1348) и Input `period-switcher.value` (:1352)
   - Inputs: `url.pathname`, `profile-updated.data`; State: `dashboard-period.data`
   - Сигнатура: `(pathname, profile_updated, period_state)`
   - Ветка ошибки: `(error_alert,) * 5`, лог через `logger.opt(exception=True).error(...)` вместо `logger.error(f"...{e}")` (:1389)

3. **`refresh_dashboard_after_crud`** — те же 5 Output'ов с `allow_duplicate=True`; `logger.opt(exception=True)` (:1451).

4. **`update_period_state`** — **удалить** callback целиком (:1397-1408) вместе с элементом `period-switcher` (:118-128).

5. **`open_create_from_chart`** — перепривязать:
   - Input → `dashboard-layers-chart-graph.clickData`
   - Дата из `point["x"]` (ISO-строка) вместо `int(point["x"])`
   - Guard по `period_state` сохранить

6. **Снять из layout:** `dashboard-greeting` (:108-112), `dashboard-overview-cards` (:129-133), `dashboard-statistics-card` (:170), `period-switcher` (:118-128). **Сохранить** вызов `build_wishlist_widget()` (:167) и карточку подушки — C-1.

7. **Удалить мёртвый код** в `dashboard.py`:
   - `_build_greeting_text()` (:82-91) — оба вызывающих сняты (:111 layout, :1386 Output), grep подтверждает отсутствие третьего. Вместе с ним уходит «пустой» для loguru `exc_info=True` (:90)
   - `build_overview_cards`, `_build_kpi_card`, `build_statistics_card`
   - `build_cashflow_chart`, `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`
   - `create_ai_assistant_card`, `create_exchange_card`, `build_recent_transactions_card`
   - **Проверить импорты:** `OnboardingService` остаётся нужен `toggle_balance_toast` (:1522), `get_db_session` — четырём местам. Мёртвых импортов не оставлять

8. **`app/assets/custom.css`** — удалить: `#dashboard-overview-cards .row`, `.db-period-switcher` (все правила), `.kpi-card` / `.kpi-card-icon` / `.kpi-trend*` / `.kpi-number` / `.kpi-title` / `.kpi-subtitle` (:195-268). Grep уже проведён на этапе проектирования: вне `dashboard.py` и `custom.css` не используются; `.an-period-switcher` в analytics — **отдельный** класс, не трогать. Поправить `.db-page` / `.db-left-col` под новую сетку.

9. **`tests/test_dashboard_callbacks.py`** — четыре позиции:
   - **(1)** Удалить класс `TestBuildGreetingText` (:73-102, 2 теста) и импорт `_build_greeting_text` (:20) — тесты удалённой функции не оставляем
   - **(2)** `test_load_dashboard_data_decorator_declares_greeting_output` (:62-70) → переориентировать на `Output("dashboard-free-header", "children")`, переименовать
   - **(3)** `test_returns_seven_values_with_greeting_last` (:188-210) → 5 значений; ассерт приветствия снять, вместо него — ассерт имени профиля в содержимом шапки; переименовать
   - **(4)** `test_wrong_pathname_prevents_update` (:212-222) → снять `period_value=` из вызова
   - Докстринг модуля (:1-12): «7-й Output» → «приветствие снято решением владельца п. 3г; имя и аватар обновляются первым Output'ом шапки»
   - **Не трогать:** `test_load_dashboard_data_decorator_declares_profile_updated_input` (:50), `test_toggle_balance_toast_decorator_declares_profile_updated_input` (:57) — защита протокола 0026

## Проверки шага

Grep-проверки (все должны быть пусты):
- `grep -rn "period_value" app tests`
- `grep -rn "_build_greeting_text\|dashboard-greeting" app tests`
- `grep -rn "TARGET_X_TICKS" app tests`
- `grep -rn "VERDICT_\|dip_threshold\|DIP_RATIO\|DIP_FLOOR\|VerdictLevel" app tests`
- `grep -rn "build_overview_cards\|_build_kpi_card\|_build_daily_cashflow_chart\|_build_yearly_cashflow_chart\|build_cashflow_chart\|build_statistics_card\|dashboard-overview-cards\|dashboard-statistics-card\|period-switcher\|update_period_state\|kpi-" app tests` — по дашборду пусто (остаётся `an-period-switcher` в analytics)
- `grep -rn "exc_info" app/components/dashboard.py`
- `grep -rn "_get_reserve_sum_for_month\|get_budget_progress" app/services/money_layers_service.py`

Функциональные:
- `/` и `/dashboard` открываются; в консоли Dash **нет** ошибок про nonexistent object
- Wishlist-виджет, таблицы недавних/предстоящих операций, карточка подушки — на месте и живые (C-1)
- Клик по столбцу графика открывает модал создания с подставленной датой
- `.venv/bin/pytest -q` — **565 − 2 + новые**; в `test_dashboard_service.py`, `test_calendar_service.py`, `test_budget_reservation_service.py`, `test_goal_service.py` **ни одной правки**
- `.venv/bin/black` + `.venv/bin/flake8 --select=F` — чисто

## Workflow

1. Выполни Sub-tasks последовательно (порядок: сначала переключение, потом удаление)
2. Базовая проверка: `python -m py_compile {FILES}`
3. Обнови `log.md` — записать фактическое число тестов после прогона
4. Обнови `context.md` — Current Step: 8, Next Action: Шаг 8
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "refactor(dashboard): перевод на модель слоёв, снятие KPI-ряда и старого графика [protocol-0028/07]"`
7. Push
8. Отчёт
