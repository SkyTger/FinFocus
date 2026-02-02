# Work Log: 0016-budget-calendar — Интеграция бюджета целей с кассовым календарём

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0016#ctx-N -->
- Restore context: protocol-0016#ctx-1 (2026-02-02)

---

## Step Log

### Step 0 — Setup (commit: 6446fff)
- Создан worktree 0016-budget-calendar
- Созданы артефакты протокола: plan.md, context.md, log.md, 00-setup.md, 01-07 step files, 08-finalize.md
- Brief: `.design/brief.md`
- Solution: `.design/solution-v2.md`

### Step 1 — Database Schema (commit: 66a0a6f)
- TransactionType: +SAVINGS_RESERVE, +SAVINGS_CONTRIBUTION
- User: +reservation_mode (default "from_balance"), +reservation_day (nullable)
- GoalContribution: +transaction_id FK (SET NULL), +ix_contribution_date index
- Migration: scripts/migrate_005_reservation.py (idempotent)
- Unit tests: 15 passed (8 новых тестов)

### Step 2 — BudgetReservationService Core (commit: 20fe4c3)
- TypedDicts: ReservationMode, BudgetReservationSettings, BudgetProgress, ContributionRecord
- BudgetReservationService: get_settings(), set_mode(), get_budget_progress()
- Private helpers: _get_reserve_template(), _create_reserve_template(), _stop_reserve_template()
- Экспорт в schema/__init__.py и services/__init__.py
- Unit tests: 17 passed

### Step 3 — BudgetReservationService CRUD (commit: 19c1bef)
- create_contribution_transaction() — создаёт SAVINGS_CONTRIBUTION в режиме from_balance
- update_contribution_transaction() — синхронизирует Transaction ↔ GoalContribution ↔ Goal
- delete_contribution_transaction() — каскадное удаление с обновлением цели
- sync_template_amount() — синхронизация суммы шаблона с бюджетом
- Unit tests: 26 passed (+9 новых)

### Step 4 — CalendarService Integration (commit: ade680f)
- _calculate_balance_before_date() — добавлены SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
- _get_daily_changes() — добавлены новые типы (уменьшают баланс как EXPENSE)
- _get_recurring_daily_changes() — обработка savings_reserve, savings_contribution
- _get_recurring_totals_for_period() — аналогично
- Unit tests: 34 passed (+4 новых)

### Step 5 — GoalService Integration (commit: d17dab7)
- add_contribution() — создаёт SAVINGS_CONTRIBUTION транзакцию (from_balance режим)
- add_contribution() — guard clause для COMPLETED целей
- add_contribution() — warning logging при budget=0
- update_savings_budget() — sync_template_amount для fixed_date
- Unit tests: 8 passed (+4 новых)

### Step 6 — Goals UI (commit: pending)
- _build_budget_progress_card() — карточка прогресса бюджета (цвета по статусу)
- budget-progress-card-container — контейнер в layout
- load_budget_progress_card callback — загрузка при переходе на /goals
- CSS стили .budget-progress-card с gradient header
