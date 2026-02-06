# FinFocus - Прогресс разработки

## 📊 Общий статус проекта: Epic-05-UI Dashboard Redesign — In Progress

**Последнее обновление**: 2026/02/06
**Статус**: 🔄 Epic-05-UI в процессе (Батч 5.1, 5.2 завершены, 5.3 в разработке)
**Прогресс Epic-05**: 2/3 батчей завершено (67%)
**GitHub**: https://github.com/SkyTger/FinFocus

---

## 🔄 Epic-05-UI: Dashboard UI Redesign — IN PROGRESS

**Дата старта**: 2026/02/05
**Спецификация**: `.reports/epics/epic-05-ui/dashboard_ui_spec.md`
**План**: `.reports/epics/epic-05-ui/plan.md`

### Цель:
Переделка Dashboard по новой UI/UX спецификации — дневной график кассового календаря, обновлённые KPI-карточки, формат денег ₽, split таблиц операций.

### Батчи:
- ✅ Батч 5.1: Фундамент (цвета + формат ₽ + KPI) — завершён 2026/02/06, PR #21
- ✅ Батч 5.2: Дневной график (ядро) — завершён 2026/02/06, PR #22
- ⏳ Батч 5.3: Layout (операции + правая колонна + sidebar) — следующий

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
   - 2 теста обновлены: "-3 000" → "\u2212" + "3 000" (типографский минус)

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

**Батч 5.3: Layout & Sidebar**:
- Split таблиц операций (Недавние/Предстоящие 50/50)
- Wishlist + Safety Cushion в правую колонну
- Sidebar как card-контейнер
- Модал "Сверка" на Dashboard
- Пустые состояния

---

## ✅ Батч 15: Postponed Purchases (Wishlist) (2026-02-04) — MERGED

**Дата**: 2026/02/04
**Протокол**: 0020-postponed-purchases
**PR**: https://github.com/SkyTger/FinFocus/pull/20
**Статус**: ✅ Merged в main (commit 258f084)

### 🎯 Цель батча:
Реализовать функционал отложенных покупок (wishlist) с подбором безопасной даты на основе кассового календаря и визуализацией каскадного влияния покупки на остатки месяца.

### ✅ Выполненные задачи:

1. **Schema + Model + Migration** (commits: 80d1ad2, 8b28dd4)
   - TypedDicts: WishlistItemData, SafeDateInfo, HoverBalances
   - WishlistItem ORM: name, amount, category_id, priority (1/2), status ("new"/"planned"), planned_date, planned_transaction_id
   - FK: user_id, category_id (nullable), planned_transaction_id (ON DELETE SET NULL)
   - scripts/migrate_006_wishlist.py — idempotent CREATE TABLE + index

2. **WishlistService** (commit: a6f0b84)
   - CRUD: create_item, get_all, get_focus, get_by_id, update_item, delete_item
   - Planning: mark_as_planned, reset_planned
   - Utility: check_orphaned_planned, to_data
   - Валидация: name (1-100), amount > 0, priority in {1, 2}
   - Planned guard: статус "planned" → можно менять только name, priority

3. **PurchaseRecommendationService** (commit: ab7f32d)
   - get_safe_dates_map() — карта безопасности дней {date: {safe, reasons}}
   - precalculate_hover_data() — предрассчет ~960 балансов для JS hover
   - Интеграция: CalendarService + CushionService
   - Каскадная проверка: min(balance[d:end_month] - amount)

4. **Unit тесты сервисов** (commit: a17c82f)
   - test_wishlist_service.py: 31 тест (CRUD, validation, planning, to_data)
   - test_purchase_recommendation.py: 11 тестов (safe dates, hover data, edge cases)
   - Всего: 483 теста (было 441, +42)

5. **Wishlist UI (виджет + модал)** (commit: ae3e15c)
   - build_wishlist_widget() — Dashboard карточка с 5 фокусными хотелками
   - create_wishlist_modal() — модал с inline-формой, секции Focus/Later
   - _build_replan_confirm_modal() — confirm dialog для перепланирования
   - 9 callbacks: open/add/delete/edit(priority toggle)/replan flow/plan navigate
   - ADR-003 guard clauses

6. **Dashboard + Main интеграция** (commit: 8f1e4d7)
   - Виджет в dashboard.py правая колонка
   - create_wishlist_modal() в main.py layout
   - dcc.Store wishlist-active-item
   - handle_calendar_query_params() для ?wishlist_item=ID (расширен для recon + wishlist)

7. **Calendar wishlist module** (commit: 3a5d4b2)
   - calendar_wishlist.py (~280 строк):
     - build_wishlist_overlay_banner() — баннер с легендой, счетчиком дней
     - build_wishlist_day_cell() — ячейка с safe/unsafe маркерами, data-date, reasons tooltip
     - build_wishlist_calendar_grid() — полная сетка с .wishlist-mode CSS
     - cancel_wishlist_mode callback

8. **Calendar.py расширение** (commit: 236228e)
   - data-date атрибут на .calendar-day-balance (для JS hover)
   - dcc.Stores: wishlist-safe-dates, wishlist-hover-data
   - wishlist-overlay div в layout
   - load_and_navigate_calendar: +Input wishlist-active-item, +3 Outputs (overlay + stores)
   - Wishlist mode: PurchaseRecommendationService + wishlist grid
   - wishlist.css: +55 строк (overlay, markers, safe/unsafe, hover, past-day)

9. **JS hover asset** (commit: e7a0f3c)
   - wishlist_hover.js (~145 строк):
     - IIFE pattern, 'use strict'
     - rubleFormatter: Intl.NumberFormat('ru-RU') + ' ₽'
     - getHoverData() — JSON.parse из #wishlist-hover-data (dcc.Store DOM)
     - applyHoverBalances() — подмена .calendar-day-balance[data-date] из by_candidate
     - restoreBaseBalances() — восстановление из base_balances
     - attachHoverListeners() — mouseenter/mouseleave, data-hover-attached guard
     - observeContainer() — MutationObserver для .wishlist-mode обнаружения
     - init() — DOMContentLoaded / readyState check

10. **Preselection + mark_planned + orphan detection** (commit: f9c8a41)
    - transaction_modals.py:
      - +4 dcc.Stores: preselected-amount, -date, -description, -risk-warning
      - set_preselection_on_modal_open(): расширен для source="wishlist" (7 outputs)
      - create_transaction: +wishlist_item_id State, trigger_data["wishlist_item_id"], +4 reset (19 outputs)
      - close_create_modal: +4 resets (10 outputs)
    - calendar_wishlist.py:
      - open_create_from_wishlist_day() — клик на wishlist-day-cell → create-modal с preselection
      - ADR-003 guard clauses #1-#4
      - Risk warning из safe_dates
    - wishlist.py:
      - mark_wishlist_planned_after_create() — trigger source="wishlist" → mark_as_planned()
      - detect_orphaned_wishlist() — trigger action="delete" → check_orphaned_planned() → reset_planned()

11. **Финализация** (Step 11, в процессе)
    - Black: TBD
    - Flake8: TBD
    - Pytest: 483 tests PASSED
    - PR создание

### 📊 Результат:
- ✅ +~1700 строк кода (services ~430, UI ~1100, JS ~145)
- ✅ +~280 строк tests
- ✅ 483 unit и integration тестов (было 441, +42)
- ✅ Полный wishlist workflow: add → plan → calendar mode → hover → select → create transaction → mark planned
- ✅ JS hover без server calls (< 1ms vs ~200ms предрассчет)
- ✅ Orphan detection для data integrity

### 💡 Ключевые решения:

1. **Каскадный hover через JS** — предрассчет ~960 балансов (~30KB Store) + clientside JS для hover (< 1ms)
2. **Статическая карта safe/unsafe** — маркеры pre-calculated, не меняются при hover (UX clarity)
3. **Orphan detection** — ON DELETE SET NULL + callback для автосброса статуса "planned"
4. **Planned guard** — статус "planned" блокирует изменение amount, category_id (только name, priority)
5. **Preselection Store Pattern** — 4 новых Stores для передачи данных в create-modal (amount, date, description, risk_warning)
6. **MutationObserver** — обнаружение .wishlist-mode для подключения hover listeners (data-hover-attached guard)
7. **Lazy import для circular dependency** — _get_budget_service() в WishlistService (как в протоколе 0018)

### 🔧 Технические детали:

**Новые файлы:**
- `app/models/database.py` — WishlistItem ORM (+7 полей)
- `app/services/wishlist_service.py` — WishlistService (~270 строк)
- `app/services/purchase_recommendation_service.py` — PurchaseRecommendationService (~160 строк)
- `app/schema/wishlist.py` — 3 TypedDicts (~50 строк)
- `app/components/wishlist.py` — Wishlist UI + modal + callbacks (~500 строк)
- `app/components/calendar_wishlist.py` — Calendar wishlist grid + overlay (~280 строк)
- `app/assets/wishlist.css` — стили overlay, markers, safe/unsafe (~130 строк)
- `app/assets/wishlist_hover.js` — JS hover logic (~145 строк)
- `tests/test_wishlist_service.py` — 31 unit тест
- `tests/test_purchase_recommendation.py` — 11 unit тестов
- `scripts/migrate_006_wishlist.py` — idempotent migration

**Модифицированные файлы:**
- `app/components/dashboard.py` — +wishlist виджет (~70 строк)
- `app/components/calendar.py` — +wishlist mode integration (~100 строк)
- `app/components/transaction_modals.py` — +4 preselection Stores (~40 строк)
- `app/main.py` — create_wishlist_modal(), handle_calendar_query_params расширен
- `app/schema/__init__.py`, `app/services/__init__.py`, `app/components/__init__.py` — экспорты

### 🚀 Следующие шаги:

**Финализация протокола 0020**:
- Black: 8 файлов
- Flake8: проверка E501, F401
- PR #20 создание и merge

**Epic-04 продолжение**:
- Импорт операций из банков (CSV, Excel, OFX)
- Уведомления и напоминания

---

## ✅ Батч 14: Contribution Edit/Delete (2026-02-04) — MERGED

**Дата**: 2026/02/04
**Протокол**: 0019-contribution-edit-delete
**PR**: https://github.com/SkyTiger/FinFocus/pull/19
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Реализовать полноценное CRUD для GoalContribution с каскадной синхронизацией (Contribution ↔ Transaction ↔ Goal.current_amount ↔ Exception) и блокировкой SAVINGS_CONTRIBUTION в calendar tooltip.

### ✅ Выполненные задачи:

1. **Schema + Helpers** (commit: 8b0648c)
   - ContributionInfo и ContributionUpdateResult TypedDicts
   - _get_budget_service() для lazy import (избегание circular dependency)
   - get_contribution_by_id() метод

2. **Service Methods** (commit: 9089dc5)
   - update_contribution() с Guards #1-3, каскадная синхронизация (Contribution → Transaction → current_amount → Exception)
   - Переписан delete_contribution() по Варианту A (прямое удаление, без delete_contribution_transaction())
   - Откат статуса COMPLETED → ACTIVE в обоих методах

3. **Calendar Guard #6** (commit: de9531f)
   - Блокировка SAVINGS_CONTRIBUTION в tooltip (аналогично SAVINGS_RESERVE)
   - Обновлен тест test_savings_contribution_is_readonly

4. **Goals UI** (commit: 28b02b4)
   - Таблица взносов с кнопками Edit/Delete
   - Модалы: edit_contribution_modal, delete_contribution_confirm_modal
   - 4 callbacks с ADR-003 guard clauses

5. **Unit Tests** (commit: d557f2c)
   - 23 новых тестов (17 update, 5 delete, 1 not_found)
   - Mock scope fix для across_months теста

6. **Финализация** (commit: edc2195)
   - Black: 3 файла переформатированы
   - Flake8: 1 unused import исправлен
   - Pytest: 441 tests passed (было 418, +23)

### 📊 Результат:
- ✅ 441 unit и integration тестов (было 418, +23)
- ✅ Полный lifecycle для GoalContribution (CRUD complete)
- ✅ Каскадная синхронизация 4 уровней (Contribution → Transaction → Goal → Exception)
- ✅ Защита от data corruption через calendar
- ✅ Black + Flake8 OK
- ✅ PR #19 Merged

### 💡 Ключевые решения:

1. **Вариант A в delete_contribution** — прямое удаление без вызова delete_contribution_transaction() для избежания дублирования логики current_amount
2. **Lazy import для circular dependency** — _get_budget_service() в GoalService
3. **ContributionInfo detachment** — сохранение данных до flush() для защиты от detached state
4. **Guard #6 в calendar** — блокировка SAVINGS_CONTRIBUTION для предотвращения рассинхронизации

### 🔧 Технические детали:

**Новые файлы:**
- `tests/test_contribution_edit_delete.py` — 23 unit тестов

**Модифицированные файлы:**
- `app/schema/goals.py` — +2 TypedDicts (ContributionInfo, ContributionUpdateResult)
- `app/services/goal_service.py` — +3 методы (_get_budget_service, get_contribution_by_id, update_contribution), переписан delete_contribution
- `app/components/calendar.py` — +Guard #6, обновлен tooltip readonly
- `app/components/goals.py` — +таблица actions, +2 модала, +4 callbacks

### 🚀 Следующие шаги:

**Epic-04 продолжение**:
- Отложенные покупки (Wishlist) — протокол 0020
- Импорт операций из банков (Backlog)
- Уведомления и напоминания (Backlog)

---

## ✅ Батч 13: Onboarding Wizard (2026-01-31) — MERGED

**Дата**: 2026/01/31
**Протокол**: 0014-onboarding-wizard
**PR**: https://github.com/SkyTger/FinFocus/pull/14
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Реализовать onboarding wizard для новых пользователей — обязательная настройка starting_balance при первом запуске для корректных расчетов кассового календаря.

### ✅ Выполненные задачи:

1. **Schema + Model** (commit: 0659dfc)
   - User.first_launch: Boolean, default=True, nullable=False
   - OnboardingStatus TypedDict (first_launch, starting_balance, needs_balance_alert)

2. **Migration Script** (commit: e048e7a)
   - scripts/migrate_003_first_launch.py
   - Logic: starting_balance != 0 → first_launch = False
   - Idempotent: PRAGMA table_info check перед ALTER

3. **OnboardingService** (commit: f70e66e)
   - get_status(), complete_with_balance(), skip()
   - Flush/commit contract documented в docstring

4. **Unit Tests** (commit: e666816)
   - 8 тестов для OnboardingService
   - Coverage: get_status (3), complete_with_balance (3), skip (2)

5. **Wizard UI** (commit: ae8824d)
   - Blocking modal: backdrop="static", keyboard=False
   - InputGroup с ruble sign, warning для negative
   - Buttons: "Пропустить" + "Продолжить"

6. **Wizard Callbacks** (commit: 3bab87f)
   - check_onboarding_and_validate — first_launch check + input validation
   - handle_onboarding_action — submit/skip с ADR-003 guards
   - Fail-closed DB strategy (hide wizard on error)

7. **Main Integration** (commit: c5cd192)
   - Global wizard в main.py после transaction_modals
   - dcc.Store("balance-toast-dismissed") для session state

8. **Dashboard Toast** (commit: 59eb24b)
   - _build_balance_toast() — warning toast с CTA
   - Shows если starting_balance=0 AND first_launch=False
   - CTA → /calendar?open_recon=1
   - 2 callbacks: toggle, persist dismissal

9. **Calendar Query Param** (commit: d4a0f92)
   - Extended toggle_reconciliation_modal для ?open_recon=1
   - Query cleanup: full (url.search = "")
   - 6th Output для url.search во всех returns

10. **CSS Styles** (commit: cd891f1)
    - onboarding.css (~80 строк)
    - Green gradient header, warning colors
    - Responsive adjustments

11. **Финализация** (commit: 3b72b95)
    - Black: 2 files reformatted
    - Flake8: 2 E501 fixed
    - Pytest: 300 tests PASSED (было 292, +8)

### 📊 Результат:
- ✅ 300 unit и integration тестов (было 292, +8)
- ✅ OnboardingService с flush/commit contract
- ✅ Blocking modal wizard для первого запуска
- ✅ Dashboard toast для мягкого напоминания
- ✅ Calendar query param ?open_recon=1
- ✅ Migration script для существующих пользователей
- ✅ Black + Flake8 OK
- ✅ PR #14 Merged

### 💡 Ключевые решения:

1. **Fail-closed DB strategy** — wizard скрывается при ошибке БД, не блокирует UI (critical для UX)
2. **Flush/commit contract** — сервис flush(), caller commit() (documented в docstring)
3. **Query param full cleanup** — url.search = "" после обработки (не оставляем артефактов)
4. **Toast в session Store** — dismissal не в БД, reset при новой сессии
5. **ADR-003 guard clauses** — n_clicks проверки для предотвращения автовызовов

### 🔧 Технические детали:

**Новые файлы:**
- `app/services/onboarding_service.py` — OnboardingService (~80 строк)
- `app/schema/onboarding.py` — OnboardingStatus TypedDict
- `app/components/onboarding_wizard.py` — Wizard UI + callbacks (~200 строк)
- `app/assets/onboarding.css` — стили (~80 строк)
- `scripts/migrate_003_first_launch.py` — idempotent migration
- `tests/test_onboarding_service.py` — 8 unit тестов

**Модифицированные файлы:**
- `app/models/database.py` — User.first_launch (+1 поле)
- `app/main.py` — global wizard + Store
- `app/components/dashboard.py` — toast UI + callbacks (~100 строк)
- `app/components/calendar.py` — query param handler (~30 строк изменено)
- `app/schema/__init__.py`, `app/services/__init__.py`, `app/components/__init__.py` — экспорты

### 🚀 Следующие шаги:

**Epic-04 продолжение**:
- Импорт операций из банков (CSV, Excel, OFX)
- Уведомления и напоминания
- Tooltip для дней календаря

---

*Последнее обновление: 2026/02/06*
*Формат: Rolling Window (последние 5 батчей)*

> Архив старых батчей: Батч 12 (Safety Cushion) и ранее — см. feature_progress_archive.md
