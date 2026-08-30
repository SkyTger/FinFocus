# FinFocus - Архив прогресса разработки

Старые батчи, перенесённые из `feature_progress.md` по правилу Rolling Window
(в основном файле хранятся только последние 5 батчей).

---

## ✅ Epic-05-UI: Dashboard UI Redesign — COMPLETED

**Дата старта**: 2026/02/05
**Дата завершения**: 2026/02/06
**Спецификация**: `.reports/epics/epic-05-ui/dashboard_ui_spec.md`
**План**: `.reports/epics/epic-05-ui/plan.md`

### Цель:
Переделка Dashboard по новой UI/UX спецификации — дневной график кассового календаря, обновлённые KPI-карточки, формат денег ₽, split таблиц операций.

### Батчи:
- ✅ Батч 5.1: Фундамент (цвета + формат ₽ + KPI) — завершён 2026/02/06, PR #21
- ✅ Батч 5.2: Дневной график (ядро) — завершён 2026/02/06, PR #22
- ✅ Батч 5.3: Layout (операции + правая колонна + sidebar) — завершён 2026/02/06, PR #23

### Ключевые решения:
1. Тёмная тема — откладывается (Epic-06)
2. Формат денег — глобальная замена $ → ₽ (DONE)
3. Дневной график — отдельный метод (не через CalendarService)
4. AI Assistant/Exchange — скрыты (TODO Epic-08)
5. Сайдбар — обернуть в dbc.Card (без рефакторинга main.py)
6. Адаптивность — desktop-first

---

## ✅ Батч 16: Dashboard UI Foundation (2026-02-06) — MERGED

**Дата**: 2026/02/06
**Протокол**: 0021-dashboard-foundation
**PR**: https://github.com/SkyTger/FinFocus/pull/21
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Обновить цветовую схему, глобальный форматтер денег ($ → ₽), переделать KPI-карточки без градиентов, скрыть AI/Exchange — фундамент для Epic-05-UI Dashboard Redesign.

### ✅ Выполненные задачи:

1. **format_rub() в formatters.py** (Step 01)
   - Глобальный форматтер: Decimal/float/int/None → "X XXX ₽"
   - show_sign: True → "+X XXX ₽" / "−X XXX ₽"
   - MINUS_SIGN константа: U+2212 (типографский минус)
   - .00 копейки скрываются (15000 → "15 000 ₽")
   - format_amount() переопределён как alias → 28 callsites покрыты
   - 10 unit тестов

2. **CSS-переменные + типографика** (Step 02)
   - 15 новых CSS-переменных (палитра #2ecc71, текст, фон, границы)
   - Deprecated aliases --primary-green, --light-green для обратной совместимости
   - 9 типографических классов (kpi-number/title/subtitle, table-amount, link-show-all)
   - custom.css: 7 замен hardcoded цветов
   - calendar.css: 6 замен (#28a745 → var(--color-primary/-dark))
   - transactions.css: 2 замены
   - onboarding.css: 3 замены

3. **Dashboard.py переработка** (Step 03)
   - create_metric_card() → _build_kpi_card() (белый фон, border, kpi-* классы)
   - 12 inline замен на format_rub() (KPI values, cashflow text, transaction amounts)
   - Кнопка "Сверка" на Total Balance → /calendar?open_recon=1
   - Русские label: Overview→Обзор, Income→Доходы, Expense→Расходы
   - AI Assistant и Exchange скрыты (TODO Epic-08)
   - table-amount.positive/.negative классы для транзакций

4. **Calendar.py обновления** (Step 04)
   - format_balance() рефакторинг: внутри format_rub(), возвращает с символом ₽
   - 4 callsite обновлены (убран ручной "₽")
   - Stats cards: income show_sign=True, expense → format_rub(-amount)
   - Tooltip balance + 5 amount строк → format_rub()
   - Reconciliation: 2 expected, 1 diff, 2 adjustment → format_rub()
   - 2 теста обновлены: "-3 000" → "−" + "3 000" (типографский минус)

5. **Analytics.py обновления** (Step 05)
   - 2 inline замены: donut center annotation + total H4 → format_rub()

6. **Финализация** (Step 06)
   - Black: 0 changes (all clean)
   - Flake8: 0 errors
   - Pytest: 492 passed (было 483, +10 новых, +1 updated)
   - 1 pre-existing failure: test_budget_change_updates_allocation (precision)

### 📊 Результат:
- ✅ 492 unit и integration тестов (было 483, +10 новых для format_rub)
- ✅ Глобальный формат денег X XXX ₽ (28 callsites format_amount + 12 dashboard + 11 calendar + 2 analytics)
- ✅ 15 CSS-переменных палитры #2ecc71
- ✅ 9 типографических классов
- ✅ KPI-карточки без градиентов (белый фон, border)
- ✅ AI/Exchange скрыты (TODO Epic-08)
- ✅ Black + Flake8 OK
- ✅ PR #21 Merged

### 💡 Ключевые решения:

1. **format_amount() как alias** — 28 существующих callsites покрыты без изменений (обратная совместимость)
2. **MINUS_SIGN константа** — U+2212 (типографский минус) вместо ASCII "-" (0x2D)
3. **Deprecated CSS aliases** — --primary-green, --light-green для legacy code (warnings)
4. **format_balance() внутри format_rub()** — календарь теперь единообразный (4 callsites обновлены)
5. **AI/Exchange скрыты, не удалены** — код сохранён для Epic-08

### 🔧 Технические детали:

**Модифицированные файлы:**
- `app/utils/formatters.py` — format_rub() + MINUS_SIGN
- `app/assets/custom.css` — 15 CSS-переменных + 9 типографических классов
- `app/assets/calendar.css` — 6 замен цветов
- `app/assets/transactions.css` — 2 замены
- `app/assets/onboarding.css` — 3 замены
- `app/components/dashboard.py` — _build_kpi_card(), 12 format_rub(), AI/Exchange скрыты
- `app/components/calendar.py` — format_balance() рефакторинг, 11 format_rub()
- `app/components/analytics.py` — 2 inline замены
- `tests/test_formatters.py` — 10 unit тестов
- `tests/test_calendar_service.py` — 2 теста обновлены (типографский минус)

### 🚀 Следующие шаги:

**Батч 5.2: Дневной график (ядро)**:
- DashboardService.get_daily_cashflow() — дневные данные
- Plotly: grouped bars + линия баланса + маркер минимума
- Hover tooltip, клик → модал, переключатель Month/Year

---

## ✅ Батч 17: Daily & Yearly Cashflow Chart (2026-02-06) — MERGED

**Дата**: 2026/02/06
**Протокол**: 0022-daily-cashflow-chart
**PR**: https://github.com/SkyTger/FinFocus/pull/22
**Статус**: ✅ Merged в main (commit 0ca4227)

### 🎯 Цель батча:
Реализовать дневной и годовой график кассового календаря на Dashboard с grouped bars (доход/расход), линией баланса, маркером минимума, интерактивными hover tooltip и клик-to-create для операций.

### ✅ Выполненные задачи:

1. **Schema + CalendarService** (commit e9ce06d)
   - 8 TypedDicts: BalanceStatus, DailyCashflow, DailyBalancePoint, MonthlyCashflowData, MonthlyCashflow, YearlyCashflowData
   - 4 константы: BALANCE_RISK/ATTENTION_THRESHOLD (0, 5000), STATUS_COLORS (ok/attention/risk)
   - CalendarService.get_recurring_income_expense_by_day() — публичный API для recurring интеграции
   - Экспорты в schema/__init__.py и services/__init__.py

2. **DashboardService расширение** (commit 2c75a77)
   - get_daily_cashflow() — merge regular + recurring, running balance, min marker → MonthlyCashflowData
   - get_yearly_cashflow() — оптимизация: один calculate_daily_balances(Jan 1, Dec 31) вместо 12x
   - _classify_balance_status() helper — ok/attention/risk по порогам
   - _get_daily_income_expense() — SQL CASE для INCOME/EXPENSE/SAVINGS/ADJUSTMENT, GROUP BY date
   - _get_monthly_income_expense() — переиспользует _get_daily_income_expense()
   - ADJUSTMENT handling: amount > 0 → income, amount < 0 → expense

3. **Unit тесты** (commit 69a7d51)
   - 16 новых тестов (12 daily + 4 yearly)
   - Покрытие: basic, no_txn, risk/attention/ok, min_position, cumulative, ADJUSTMENT +/-, TRANSFER, SAVINGS types
   - Всего: 508 тестов (было 492, +16)

4. **Charts + Callbacks** (commit 2c75a77)
   - _build_daily_cashflow_chart() — grouped bars (income/expense) + balance line (yaxis2) + diamond marker + today dashed line
   - _build_yearly_cashflow_chart() — end-of-month balances + current month highlight rect
   - _load_dashboard_components() helper — единая точка загрузки для обоих режимов (устраняет дублирование)
   - open_create_from_chart callback — клик на bar → create-modal с preselected-date (month mode only)
   - Dual Y-axis pattern для bars vs balance line (разные масштабы)
   - hovermode="x unified" с format_rub() в customdata
   - transaction_modals.py: source="chart" → set preselected-date

5. **Финализация** (commit ba0e448)
   - Black: 3 файла переформатированы
   - Flake8: 2 ошибки исправлены (F841, F401)
   - Pytest: 508 passed (1 deselected pre-existing precision issue)
   - Code review: PASS (no blockers, 16 unit tests, all planned items implemented)
   - Knowledge Bank update: 5 файлов обновлены, 2 новых (plotly-charts, callbacks patterns)

### 📊 Результат:
- ✅ 508 unit и integration тестов (было 492, +16 для daily/yearly cashflow)
- ✅ Дневной график с grouped bars + balance line + diamond min marker + today line
- ✅ Годовой график с end-of-month balances + current month highlight
- ✅ Клик на bar → create-modal с preselected date (Month mode)
- ✅ Dual Y-axis pattern для разных масштабов
- ✅ Unified hover tooltip с format_rub()
- ✅ _load_dashboard_components() helper (устраняет 80% дублирования)
- ✅ CalendarService.get_recurring_income_expense_by_day() публичный API
- ✅ Black + Flake8 OK
- ✅ PR #22 Merged

### 💡 Ключевые решения:

1. **Дневной vs годовой режим** — единый Chart ID, переключение через store {period, year, month}
2. **Year mode оптимизация** — один calculate_daily_balances() для всех 365 дней вместо 12x месячных
3. **Recurring через публичный API** — CalendarService.get_recurring_income_expense_by_day() вместо прямого вызова protected метода
4. **Dual Y-axis** — bars на первой оси, balance line на второй (разные масштабы)
5. **ADJUSTMENT классификация** — positive → income, negative → expense(abs) (осознанное решение)
6. **Protect method access** — _get_recurring_totals_for_period в Year mode (допустимо, тот же слой сервисов)

### 🔧 Технические детали:

**Новые файлы:**
- `app/schema/dashboard.py` — 8 TypedDicts (~104 строк)
- `tests/test_dashboard_service.py` — 16 unit тестов (~347 строк)

**Модифицированные файлы:**
- `app/components/dashboard.py` — +520 строк (chart builders, callbacks, helper)
- `app/services/dashboard_service.py` — +320 строк (get_daily/yearly_cashflow, helpers)
- `app/services/calendar_service.py` — +42 строк (get_recurring_income_expense_by_day)
- `app/components/transaction_modals.py` — +12 строк (source="chart" preselection)
- `app/schema/__init__.py`, `app/services/__init__.py` — экспорты

### 🚀 Следующие шаги:

**Epic-06: Dark Theme**:
- Тёмная тема по спецификации dashboard_ui_spec.md секция 2

**Epic-07: Mobile Responsive**:
- Полная адаптивность < 576px

---

## ✅ Батч 18: Dashboard Layout Redesign (2026-02-06) — MERGED

**Дата**: 2026/02/06
**Протокол**: 0023-dashboard-layout
**PR**: https://github.com/SkyTger/FinFocus/pull/23
**Статус**: ✅ Merged в main (commit a0ece8c + b4e6000)

### 🎯 Цель батча:
Финальная перестройка Dashboard layout: split таблиц операций 50/50, правая колонна с Wishlist + Cushion, sidebar в card, глобализация reconciliation modal, пустые состояния.

### ✅ Выполненные задачи:

1. **Formatters + DashboardService** (Step 01)
   - format_date_human() — "5 февраля" для операций
   - MONTH_NAMES_RU_GENITIVE константа
   - is_recurring_instance: bool в RecentTransaction TypedDict
   - get_recent_transactions() рефакторинг: reference_date параметр, month range filter (1-го числа..reference_date)
   - get_upcoming_transactions() NEW: операции после reference_date, ASC sort
   - _map_transactions() helper для устранения дублирования
   - 12 unit тестов: 3 formatter + 3 recent refactor + 6 upcoming
   - 57 тестов DashboardService (13 старых + 44 новых)

2. **Reconciliation глобализация** (Step 02)
   - calendar.py: удалён calendar-refresh-trigger, удалён create_reconciliation_modal() из layout
   - calendar.py: apply_reconciliation() Output global-transaction-trigger (allow_duplicate), return data с source/action
   - main.py: create_reconciliation_modal() перенесён в app.layout после wishlist modal
   - dashboard.py: KPI recon_button dcc.Link→dbc.Button(id="open-recon-from-dashboard-btn")
   - dashboard.py: Banner button с ID="open-recon-from-dashboard-banner-btn"
   - dashboard.py: open_recon_from_dashboard() callback — 2 Inputs → Output open-recon-trigger

3. **Dashboard UI rebuild** (Step 03)
   - _build_empty_state() — icon, message, button_id для CTA
   - _build_transactions_split_table() — format_date_human, 🔁 для recurring, ссылка "Все операции"
   - _build_cushion_card_readonly() — CushionService.get_settings(), readonly прогресс-бар, link→/goals
   - create_dashboard_layout() перестроен: 8/4 split, recent/upcoming 50/50, cushion + wishlist правая колонна
   - _load_dashboard_components() расширен: +get_upcoming_transactions(), +cushion, 6 outputs
   - open_create_from_empty() callback — 2 Inputs (empty buttons) → create-modal
   - Import CushionService + format_date_human

4. **Sidebar + Transactions** (Step 04)
   - sidebar.py: dbc.Card(className="sidebar-card h-100"), MAIN_NAV_ITEMS + ADDITIONAL_NAV_ITEMS константы
   - sidebar.py: _build_nav_links() helper, highlight_active_sidebar() callback — url.pathname → sidebar-nav.children
   - sidebar.css: НОВЫЙ файл — .sidebar-card, .sidebar-nav-item-active (border-left 4px green)
   - transactions.py: apply_url_date_filter() callback — url.search → filter-date-range dates (parse_qs + date.fromisoformat)

5. **Финализация** (Step 05)
   - CSS: .empty-state, .dashboard-split-table в custom.css
   - Black: 3 файла переформатированы (calendar, dashboard, dashboard_service)
   - Flake8: 2 F841 исправлены (start_param, end_param unused)
   - Pytest: 520 passed, 1 failed (pre-existing precision issue)
   - PR создан как draft

### 📊 Результат:
- ✅ 520 unit и integration тестов (было 508, +12 новых: 3 formatters + 9 dashboard_service)
- ✅ format_date_human() — человекочитаемые даты в операциях
- ✅ get_upcoming_transactions() — предстоящие операции (от reference_date до конца месяца)
- ✅ Reconciliation modal глобализация — доступ с Dashboard и Calendar
- ✅ Dashboard layout 8/4 — split tables 50/50, cushion + wishlist в правой колонне
- ✅ Sidebar card с active highlight callback
- ✅ Transactions URL query params — ?start=&end=
- ✅ Empty states с CTA кнопками
- ✅ Black + Flake8 OK (2 F841 исправлены, остальные E501 pre-existing)

### 💡 Ключевые решения:

1. **Reconciliation globalization через global-transaction-trigger** — календарь теряет calendar-refresh-trigger, замена на global trigger
2. **Split tables на reference_date** — get_recent (ДО today), get_upcoming (ОТ today)
3. **format_date_human()** — "5 февраля" вместо "05.02.2026" для лучшей читабельности
4. **_map_transactions() helper** — устранение дублирования маппинга между recent и upcoming
5. **Sidebar card без main.py рефакторинга** — обёртка в Card, callback для active highlight (не затрагивает routing)
6. **Readonly cushion на Dashboard** — CushionService.get_settings(), link→/goals (без дублирования ID)
7. **Empty states с CTA** — кнопки "Добавить" открывают create-modal
8. **Layout 8/4 не 9/3** — оптимально для wishlist widget width

### 🔧 Технические детали:

**Новые функции:**
- `format_date_human()` в formatters.py (~20 строк)
- `get_upcoming_transactions()` в dashboard_service.py (~40 строк)
- `_map_transactions()` helper в dashboard_service.py (~15 строк)
- `_build_empty_state()` в dashboard.py (~10 строк)
- `_build_transactions_split_table()` в dashboard.py (~80 строк)
- `_build_cushion_card_readonly()` в dashboard.py (~50 строк)
- `highlight_active_sidebar()` callback в sidebar.py (~30 строк)
- `apply_url_date_filter()` callback в transactions.py (~20 строк)

**Модифицированные файлы:**
- `app/utils/formatters.py` — +format_date_human() (~100 строк total)
- `app/services/dashboard_service.py` — +get_upcoming_transactions(), рефакторинг get_recent_transactions (~700 строк total)
- `app/components/dashboard.py` — layout rebuild, +3 build functions, +2 callbacks (~1100 строк total)
- `app/components/calendar.py` — reconciliation globalization (~820 строк total)
- `app/components/sidebar.py` — card wrap, +callback (~130 строк total)
- `app/components/transactions.py` — +URL query params callback
- `app/main.py` — reconciliation modal перенесён
- `app/assets/custom.css` — +.empty-state, +.dashboard-split-table
- `app/assets/sidebar.css` — НОВЫЙ файл (~50 строк)
- `tests/test_formatters.py` — +3 теста (format_date_human)
- `tests/test_dashboard_service.py` — +9 тестов (3 recent refactor + 6 upcoming)

### 🚀 Следующие шаги:

**Epic-06: Dark Theme**:
- Тёмная тема по спецификации dashboard_ui_spec.md секция 2

**Epic-07: Mobile Responsive**:
- Полная адаптивность < 576px

---

> Более старые батчи (Батч 15 Wishlist и ранее) — см. историю git
> `.obsidian-docs/reports/notes/feature_progress.md` до этой архивации,
> либо ссылку в текущем feature_progress.md на момент их переноса.

---

## ✅ Батч 19: User Profile (2026-03-03) — MERGED

**Дата**: 2026/03/03
**Протокол**: 0024-user-profile
**PR**: https://github.com/SkyTger/FinFocus/pull/24
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Персонализация приложения: расширить onboarding wizard (имя + аватарка + баланс), сделать sidebar динамическим, добавить profile modal для редактирования, приветствие на dashboard.

### ✅ Выполненные задачи:

1. **Data Layer** — app/config/avatars.py (10 emoji аватарок, DEFAULT_AVATAR_ID, get_avatar_emoji())
2. **Migration + Bootstrap** — миграция 007_avatar_id, bootstrap с avatar_id="emoji-default"
3. **Service Layer** — OnboardingService: complete(), update_profile(), get_profile(), _validate_profile_fields(), deprecated wrapper complete_with_balance()
4. **Schema** — UserProfile TypedDict, name/avatar_id в OnboardingStatus
5. **Onboarding UI** — перестроен wizard: имя + RadioItems аватарка + баланс, два callback'а
6. **Sidebar + Profile Modal** — динамический профиль (Store-based), profile_modal.py (edit name/avatar)
7. **Main + Dashboard** — Store("profile-updated"), dashboard greeting "Добро пожаловать, {name}!"
8. **Tests** — test_avatars.py (5), test_migration_007.py (3), test_onboarding_service.py расширен до 15

### 📊 Результат:
- ✅ 546 unit и integration тестов (было 531, +15 новых)
- ✅ 10 emoji аватарок с конфигом
- ✅ Store("profile-updated") как event bus для sidebar
- ✅ Inline DB read для dashboard greeting
- ✅ Code review: Security 5/5, Quality 4/5
- ✅ Critical fix: profile_modal.py — keep modal open on save error

---

## ✅ Батч 20: Beta Delivery & Setup (2026-03-03) — MERGED

**Дата**: 2026/03/03
**Протокол**: 0025-beta-delivery
**PR**: https://github.com/SkyTger/FinFocus/pull/25
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Обеспечить 1-click запуск FinFocus для нетехнических бета-тестеров: платформенные скрипты с авто-настройкой venv и зависимостей, инструкция для тестеров, процесс создания релизов.

### ✅ Выполненные задачи:

1. **Requirements split** — requirements.txt (runtime only) + requirements-dev.txt (pytest, black, flake8)
2. **start.sh** (168 строк) — Python 3.10+ check, venv creation, deps marker (.deps_installed), port check (ss/lsof/netstat), trap handler, colored output, auto browser open
3. **start.bat** (148 строк) — py -3/python fallback, version parsing, venv, deps marker (xcopy /D /L), netstat port check, pause on error
4. **BETA_README.md** (86 строк) — 3 шага установки, 6 FAQ, ссылка на GitHub issues для bug reports
5. **docs/RELEASE_GUIDE.md** (82 строк) — tag format v0.9.0-beta.N, git archive команда, Release Notes шаблон, checklist

### 📊 Результат:
- ✅ 546 тестов (без изменений — новый код не содержит Python)
- ✅ start.sh + start.bat — 1-click запуск на 3 платформах
- ✅ Идемпотентная установка зависимостей через маркер-файл
- ✅ Проверка Python >= 3.10 и порта перед запуском

### 💡 Ключевые решения:
1. **Setup-скрипты, не Docker/PyInstaller** — minimal barrier для тестеров с Python
2. **Deps marker** — .venv/.deps_installed, обновляется при изменении requirements.txt
3. **Port check fallback chain** — ss → lsof → netstat (кроссплатформенность)
4. **xcopy /D /L трюк** — Windows timestamp comparison без PowerShell

---

## 🔧 Возврат проекта из архива (2026-08-19) — MERGED

**Ветка**: `bugfix/test-date-rot`
**Тип**: ад-хок работа без протокола (подготовка к возобновлению разработки)

Проект достали из архива, окружение пересоздано (venv отсутствовал —
он машинно-локальный и с папкой проекта не переезжает). Локальная
версия Python — 3.10.12; на 3.13 SQLAlchemy 2.0.23 падает при импорте
(нет cp313-wheel), поддерживаемый диапазон — 3.10–3.12.

**Починка протухания тестов** (5 файлов в `tests/`, код `app/` не менялся):
- 8 падений при возврате из архива были вызваны захардкоженными датами,
  а НЕ дефектом продукта: сервисы считают от `date.today()`, а тесты
  подставляли февраль-март 2026. Проверено заморозкой времени — на
  2026-02-02 проходили все 48
- Опровергнут прежний диагноз: `test_budget_change_updates_allocation`
  числился «давним падением из-за точности Decimal» — неверно
- В `tests/conftest.py` добавлены 6 хелперов относительных дат
- Попутно исправлены 2 скрытых дефекта: падение на 29 февраля
  (`today.replace(year=+1)`) и протухание целей на датах после 2027
- Убрано самоотключение 3 тестов после 25-го числа месяца — покрытие
  молча падало в конце каждого месяца
- Осмысленность тестов подтверждена порчей логики (mutation testing)
- Итог: 553 теста, 0 пропусков (было 552 + 1 пропуск, а после 25-го
  числа — 550 + 3 пропуска)

**Прогон тестов в CI** (`.github/workflows/tests.yml`):
- Тесты в CI не запускались ВООБЩЕ — единственный workflow собирал
  PyInstaller-бандлы по тегу. Это и есть причина, почему протухание
  жило 5 месяцев: в протоколе 0025 (март 2026) 7 падений были списаны
  как «pre-existing, регрессий нет»
- Матрица Python 3.10 + 3.12, триггеры: push в main, pull_request, вручную
- Линтеры намеренно не включены (6 pre-existing E501 в `app/`)

**Актуализация Knowledge Bank** (по результатам `/kb-audit` + `/doc-audit`):
- `testing.md` — переписан: было «Coverage: 0%, тесты не написаны»
  (состояние до начала разработки), стало 553 теста + задокументирована
  стратегия относительных дат
- `tech-stack.md` — убрано ложное обоснование «Python 3.12 нужен для
  match-case» (его в коде нет); таблица трёх рантаймов + верхняя
  граница 3.13; Alembic помечен как неиспользуемый
- `deployment.md` — PyInstaller зафиксирован как факт, описан
  `app/core/paths.py`; статус двух способов доставки — открытый вопрос

**Заведена секция «Открытые вопросы»** в `ROADMAP.md` — 6 пунктов
(способ доставки, DELEGATION_GUIDE из чужого проекта, остаток
актуализации KB, хвосты в рабочей копии, линтеры в CI, паттерн
самоотключения тестов).

Файлы: `tests/conftest.py`, `tests/test_budget_*.py`,
`tests/test_goals_integration.py`, `tests/test_contribution_edit_delete.py`,
`.github/workflows/tests.yml`, `knowledge-bank/{testing,tech-stack,deployment}.md`

---

## 🔍 Двойной аудит: UX + код (2026-08-20) — анализ, без правок кода

**Тип**: ад-хок сессия без протокола; код `app/` не менялся, только документация.

**Контекст**: фидбек бета-тестеров — «всё круто, но очень сложно, нужна
огромная инструкция». Решено: аудит → починка ясности → потом агентный
слой (MCP) как ускоритель ввода, не раньше.

**UX-аудит** (живой прогон приложения, чистая + рабочая база, 14 скриншотов):
- Отчёт-артефакт: https://claude.ai/code/artifact/0fc1f14f-c46f-4a8c-9bce-1226e5a0fe28
- Главный вывод: порог входа концептуальный — продукт не объясняет свои
  понятия (сверка, резервирование, режимы накоплений), цифры соседних
  карточек противоречат друг другу на глаз
- Итоги (4 критичных / 5 важных / 4 мелких) заведены в `ROADMAP.md`,
  секция «UX-аудит 2026-08-20 — итоги»

**Аудит кода** (`/project-analysis` full, прогон по бизнес-процессу):
- Отчёт: `knowledge-bank/analyses/2026-08-20-full.md`
- 🔴 2 (онбординг не подписан на Store profile-updated; тихий fail-open
  в рекомендациях покупок) / 🟡 7 / 🟢 4
- Архитектура признана здоровой: слои соблюдаются, Decimal-дисциплина,
  сессии БД образцовые — «перелопачивать» не нужно
- Находки UX-аудита классифицированы: 5 багов, 2 заглушки (настройки,
  версия), 1 осознанное решение с недокументированным UX-эффектом
  (окна данных карточек дашборда)

**Концепт нового главного графика** («деньги с именами»):
- Интерактивное демо: https://claude.ai/code/artifact/f9edd8b1-c600-4026-8315-dabc548b2e90
- Остаток по дням, разложенный на слои: свободные / обещанные / резерв;
  красная зона дефицита; «Свободно сегодня» как главная цифра дашборда
- Припарковано как открытый вопрос №7 в ROADMAP (закрыт 2026-08-23
  обсуждением «дашборд как меню»)

**Следующий шаг на момент сессии**: владелец отсматривает отчёт анализа,
заполняет секцию «Решения по итогам отсмотра» → `/protocol-new`
(«быстрые победы»: онбординг, логирование, пустой график, мёртвый блок
в аналитике). Выполнено протоколами 0026-0027 (см. Батч 21-22 выше).

---

## ✅ Батч 21: Онбординг — мгновенное применение профиля (2026-08-21)

**Дата**: 2026/08/21
**Протокол**: 0026-onboarding-refresh
**PR**: #26 — смержен
**Статус**: ✅ Смержено (2026/08/21, b209721)

### 🎯 Цель батча:
Багфикс находки 🔴 №1 двойного аудита 2026-08-20: дашборд не обновлялся без ручной перезагрузки страницы после онбординга/сверки профиля (приветствие «Пользователь», баланс 0 ₽, баннер сверки оставались).

### ✅ Выполненные задачи:
- Дашборд подписан на event bus `profile-updated` (протокол 0024): `Input("profile-updated", "data")` добавлен в `load_dashboard_data` и `toggle_balance_toast`
- Приветствие — 7-й Output `load_dashboard_data` (хелпер `_build_greeting_text()`); отдельный callback отвергнут на ревью 3-m: воспроизводил альтернативу, отклонённую в 0024 (риск ReferenceError на других страницах)
- +10 колбэчных тестов (`tests/test_dashboard_callbacks.py`), контракт подписок зафиксирован через `inspect.getsource`; 563 passed
- Попутно на ревью (4-m): починено расхождение доков и кода по `needs_balance_alert` — KB описывал доп. условие `first_launch=False`, которого в коде нет (3 места в modules/)

Файлы: `app/components/dashboard.py`, `tests/test_dashboard_callbacks.py`

→ ROADMAP.md, P1 «Онбординг не применяется без ручной перезагрузки» — закрыт

---

## ✅ Батч 22: Быстрые победы аудита кода — fail-open логирование + мёртвый блок (2026-08-21)

**Дата**: 2026/08/21
**Протокол**: 0027-audit-quick-wins
**PR**: #27 — смержен
**Статус**: ✅ Смержено (2026/08/21, c6c5529)

### 🎯 Цель батча:
Пп. 2-3 приоритизированного плана двойного аудита 2026-08-20
(`knowledge-bank/analyses/2026-08-20-full.md`): тихий fail-open в
рекомендациях покупок и мёртвый блок кода в аналитике.

### ✅ Выполненные задачи:
- `purchase_recommendation_service.get_safe_dates_map`: сбой чтения настроек
  подушки теперь логируется `logger.opt(exception=True).warning(...)`
  с трейсбеком; fail-open поведение (threshold=0 → критерий подушки
  отключён) сохранено и задокументировано в докстринге
- Попутная находка: `exc_info=True` — идиома `logging`, а не `loguru`;
  loguru молча игнорирует этот параметр (трейсбек не пишется). Идиома
  loguru — `opt(exception=True)` или `logger.exception(...)`. Существующие
  `exc_info=True` в кодовой базе (dashboard.py и др.) остаются «пустыми» —
  относятся к отложенному п.10 аудита (унификация логирования)
- `analytics_service.py`: удалён мёртвый двойного вычисления блок
  `end_of_month` (hardcoded fallback 28, сразу перезаписывался
  `calendar.monthrange`-вариантом); `import calendar` поднят на уровень
  модуля
- +2 теста: fail-open подушки (mock сбоя настроек → проверка расчёта,
  отсутствия критерия cushion, наличия warning с трейсбеком в логе) и
  граница декабрь/январь в аналитике (регрессионная защита от
  fallback-28 бага); 565 passed

Файлы: `app/services/purchase_recommendation_service.py`,
`app/services/analytics_service.py`,
`tests/test_purchase_recommendation.py`, `tests/test_analytics_service.py`

→ Отчёт аудита `knowledge-bank/analyses/2026-08-20-full.md`, пп. 2-3

---

## 🎨 Концепт-сессия: редизайн дашборда «щиток» (2026-08-23) — обсуждение закрыто, кода нет

**Тип**: дизайн-обсуждение (`.obsidian-docs/discussions/`), без протокола и без правок `app/`.

**Итог**: обсуждение «дашборд как меню» закрыто, концепция принята владельцем.
Дашборд становится навигацией по метафоре электрощитка: шапка-вердикт
«Свободно сегодня: N ₽», центральный график полос «Свободно / Платежи /
Резерв целей и подушки» с вехами целей (полная замена текущего графика
доходы/расходы + баланс), карточки-двери на все разделы меню (конституция
щитка — каждый пункт меню обязан иметь карточку), компактная полоска-меню
на остальных экранах вместо текущего сайдбара. Всего 20 решений.

Визуальный эскиз собран через `/visual` (2 раунда, вердикт SHIP) и принят
владельцем как основа реализации.

**Секвенирование** (решение владельца): редизайн делается ДО бета-цикла;
фаза 4 Epic-09 (сбор фидбека беты) — после редизайна, чтобы не тратить
фидбек на экран, который всё равно выбрасывается.

Закрыты открытые вопросы ROADMAP: №7 (переосмысление главного графика) —
полностью; №9 (доработка инструмента vs заплатки) — дашборд-часть; пп. 5/7
аудита (жизненный цикл целей) остаются открытыми отдельно.

Файлы:
- `.obsidian-docs/discussions/_archive/dashboard-as-menu-2026-08-23/design.md` — источник правды, 20 решений
- `.visual/finfocus-panel-dashboard/` — эскиз (v3.html финал, v3.png рендер, brief.md, critique-v2/v3.md)
- Артефакт эскиза: https://claude.ai/code/artifact/019f9b22-b13b-48f6-a362-f9f0b8735f62

---




<!-- Перенесено из feature_progress.md 2026-08-30 (rolling window) -->

## ✅ Батч 22: Быстрые победы аудита кода — fail-open логирование + мёртвый блок (2026-08-21)

Багфикс fail-open в `purchase_recommendation_service.get_safe_dates_map`
(теперь логируется `logger.opt(exception=True).warning(...)` с
трейсбеком; loguru игнорирует `exc_info=True`) + удалён мёртвый
двойного вычисления блок `end_of_month` в `analytics_service.py`.
565 тестов (+2).
Файлы: `app/services/purchase_recommendation_service.py`, `app/services/analytics_service.py`
→ Протокол 0027, PR #27, смержено 2026-08-21 (c6c5529)

---

## ✅ Батч 21: Онбординг — мгновенное применение профиля (2026-08-21)

Дашборд подписан на event bus `profile-updated`: приветствие/баланс/
баннер сверки обновляются без ручного F5 после онбординга. 563 теста (+10).
Файлы: `app/components/dashboard.py`, `tests/test_dashboard_callbacks.py`
→ Протокол 0026, PR #26, смержено 2026-08-21 (b209721); ROADMAP.md P1 закрыт

---

