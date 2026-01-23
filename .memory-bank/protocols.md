# Протоколы разработки

## Суть
История выполненных протоколов — детализированных технических задач с пошаговой реализацией.

## Формат протокола
Каждый протокол — изолированная задача в worktree с детальным планом (6 шагов), логом работы и commit-trail.

## Завершенные протоколы

### Протокол 0011: Chips + Bulk + Export UI (2026-01-24)
**Статус**: ✅ MERGED (commit ac25b5d, PR #11)
**Батч**: Epic-03-Analytics (Batch 3.2)
**Worktree**: `/worktrees/0011-chips-bulk-export`

**Контекст**:
- Батч 3.2 был завершен ранее, но UI компоненты потеряны при merge
- Backend методы готовы: `bulk_update_category`, `export_to_csv`, `get_frequent_for_type`
- Требовалось восстановить Chips UI, Bulk actions, CSV export

**Реализация** (6 шагов):
1. **Layout + Helpers** (commit 1b2e3f5)
   - dcc.Store: selected-transactions, frequent-categories
   - dcc.Download: export-download
   - Helper: `_pluralize_operations()` — склонение "операция/операции/операций"
   - Helper: `_build_bulk_panel()` — sticky panel с dropdown

2. **Table + Chips** (commit ef16193)
   - Helper: `_build_chips_cell()` с guard для TRANSFER/ADJUSTMENT
   - Chips из frequent_categories[:5] + overflow dropdown
   - Checkboxes в таблице (select-all + individual)

3. **Chips Callbacks** (commit 1931a48)
   - `load_frequent_categories()` — кеширование через CategoryService
   - `chip_assign_category()` — Pattern-Matching с 3-уровневыми guard clauses (ADR-003)
   - `chip_dropdown_assign_category()` — аналогично для overflow dropdown

4. **Bulk Callbacks** (commit b89c954)
   - `update_selection_state()` — обработка Select All и checkboxes
   - `clear_selection_on_filter_change()` — WYSIWYG поведение
   - `toggle_bulk_panel()` — показ/скрытие с prevent_initial_call=True
   - `bulk_assign_category()` — ValidationError handling, emit trigger

5. **Export + Tests** (commit 240ca5e)
   - `export_transactions()` — filename pattern, UTF-8 BOM
   - tests/test_transactions_callbacks.py: 13 тестов для _pluralize_operations

6. **Финализация** (commit ea62f55)
   - Black: 65 файлов OK
   - Flake8: 0 ошибок
   - Pytest: 259 passed

**Результат**:
- +636 строк в transactions.py
- +81 строка в tests
- 13 новых unit тестов (все PASS)
- Полное восстановление UX функциональности Батча 3.2

**Критичные детали**:
- Pattern-Matching guard clauses (ADR-003) обязательны для chips и bulk callbacks
- TRANSFER/ADJUSTMENT не могут иметь категорию (guard в `_build_chips_cell`)
- Max 100 транзакций для bulk операций (лимит в TransactionService)
- UTF-8 BOM критичен для Excel совместимости экспорта

**Референсы**:
- План: `.protocols/0011-chips-bulk-export/plan.md`
- Лог: `.protocols/0011-chips-bulk-export/log.md`
- Design doc: `.design/solution-v2.md`

---

### Протокол 0010: Analytics & UX Improvements (2026-01-23)
**Статус**: ✅ MERGED (commit ed0fc44, PR #10)
**Батч**: Epic-03-Analytics (Batch 3.2)

**Реализация**:
- AnalyticsService (~290 строк)
- TransactionService: bulk_update_category, export_to_csv
- CategoryService: get_frequent_for_type
- Страница /analytics с donut/bar charts
- UI компоненты (потеряны при merge, восстановлены в протоколе 0011)

**Результат**:
- 246 unit тестов (было 213)
- Memory Bank обновлен

---

### Протокол 0009: Categories + Reconciliation (2026-01-23)
**Статус**: ✅ MERGED (commit merge PR #9)
**Батч**: Epic-03-Analytics (Batch 3.1)

**Реализация**:
- Category модель, TransactionType.ADJUSTMENT
- CategoryService, ReconciliationService
- Сверка баланса через модал
- 16 предустановленных категорий (seed idempotent)

**Результат**:
- 213 unit и integration тестов

---

### Протокол 0008: Redistribution (2026-01-22)
**Статус**: ✅ MERGED (PR #8)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- RedistributionService с Temporary Status Pattern
- TypedDicts и Serializers для preview/event
- Redistribution Modal UI с анимациями

**Результат**: 23 новых теста

---

### Протокол 0007: Savings Modes (2026-01-22)
**Статус**: ✅ MERGED (PR #7)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- User.savings_mode (free/medium/strict)
- Множители к monthly_contribution (1.0 / 1.15 / 1.5)
- UI селектор режимов

---

### Протокол 0006: Multiple Goals (2026-01-21)
**Статус**: ✅ MERGED (PR #6)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- User.monthly_savings_budget
- AllocationService с жадным алгоритмом
- TypedDicts модуль (app/types/)
- Goals UI рефакторинг (~600 строк)

**Результат**: 98 unit и integration тестов

---

### Протокол 0005: Recurring Transactions (2026-01-20)
**Статус**: ✅ MERGED (PR #5)
**Батч**: Epic-02-EnhancedPlanning (Batch 2)

**Реализация**:
- RecurringService (~550 строк)
- Anchored-алгоритм генерации дат
- Wizard UI "экземпляр vs серия"

**Результат**: 75 unit тестов, ADR-004 создан

---

### Протокол 0004: Goals UI (2026-01-19)
**Статус**: ✅ MERGED (PR #4)
**Батч**: Epic-01-CoreMVP (Фаза 5)

**Реализация**:
- Utils модуль (app/utils/formatters.py)
- Goals UI (~1040 строк)
- 10 callbacks для CRUD

**Результат**: 37 unit тестов

---

### Протокол 0003: Dashboard Integration (2026-01-19)
**Статус**: ✅ MERGED (PR #3)
**Батч**: Epic-01-CoreMVP (Фаза 4)

**Реализация**:
- DashboardService (~290 строк)
- CalendarService расширен (get_balance_on_date, get_year_summary)
- Dashboard UI переписан (~685 строк)

**Результат**: 16 новых unit тестов (33 всего)

---

### Протокол 0002: Cash Calendar (2026-01-19)
**Статус**: ✅ MERGED (PR #2)
**Батч**: Epic-01-CoreMVP (Фаза 3)

**Реализация**:
- CalendarService (~310 строк)
- Calendar UI (~700 строк)
- 3 callbacks с guard clauses (ADR-003)

**Результат**: 15 unit тестов

---

## Паттерны протоколов

### Структура протокола
```
.protocols/NNNN-название/
├── plan.md          # High-level план (6 шагов)
├── log.md           # Журнал работы (append-only)
├── context.md       # Restore context записи
├── NN-название.md   # Детальный план каждого шага
└── ...
```

### Commit Convention
```
type(scope): description [protocol-NNNN/NN]

Примеры:
feat(transactions): add chips callbacks [protocol-0011/03]
chore(review): complete review steps 1-3 [protocol-0011/3-m]
docs(protocol): finalize 0011-chips-bulk-export [protocol-0011/06]
```

### Workflow
1. Создание worktree и ветки
2. Пошаговая реализация (6 шагов)
3. Code quality checks (black, flake8, pytest)
4. Finalize документации
5. PR создание и review
6. Merge в main

---

Детали: см. `CLAUDE.md` (Protocol Workflow section), `.protocols/_core/workflow.md`
