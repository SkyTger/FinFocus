# Work Log: 0018-budget-reservation-bugfix — Исправление переиспользования шаблонов резервирования

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0018#ctx-N -->

### Restore context: protocol-0018#ctx-1
- Дата: 2026-02-02
- Состояние: Чистое (только context.md изменён)
- Текущий шаг: 1 (Helper методы)
- Последний коммит: Step 0 (план)

---

## Step Log

### Step 0 — Setup (commit: 4b8c998)
- Создан протокол с 10 шагами
- Основа: solution-v3.md (5/5 в critique)
- Ключевые изменения: lazy import, reference_date переименование, логирование, integration тесты

### Step 1 — Helper методы (commit: 644bef6)
- Добавлены 4 helper метода в BudgetReservationService:
  - `_find_any_reserve_template()` — поиск любого шаблона (включая остановленный)
  - `_get_template_day()` — извлечение дня из шаблона (EOM → 31)
  - `_get_reserve_date_for_month()` — дата резерва с учётом коротких месяцев
  - `_delete_exception_for_date()` — удаление exception для даты
- py_compile: OK

### Step 2 — recalculate метод (commit: b5a1204)
- Добавлен `recalculate_current_month_exception(user_id, reference_date)`
- Расширен `_get_contributions_sum_for_month` параметром `before_date`
- Логика: нет взносов → удалить exception, есть → создать/обновить с уменьшенной суммой
- Lazy import для RecurringService (как в adjust_reserve_for_contribution)
- py_compile: OK

### Step 3 — cleanup + logging (commit: 408308a)
- Добавлен `_cleanup_orphan_exceptions(template_id)` — удаляет все exceptions остановленного шаблона
- logger.info() при удалении, logger.debug() если нечего удалять
- py_compile: OK

### Step 4 — set_mode модификация (commit: 88f044b)
- Рефакторинг set_mode() для переиспользования шаблонов:
  - Тот же день → реактивируем (exceptions сохраняются!)
  - Другой день → stop + cleanup + create new
  - from_balance → stop (exceptions НЕ чистим — пригодятся при возврате)
- Обновлен docstring с описанием логики
- py_compile: OK

### Step 5 — get_budget_progress (commit: b68e2d0)
- Унифицирован расчёт used_budget — взносы для обоих режимов
- mode_text = "Внесено" для обоих режимов
- Сохранена существующая логика статусов (success/warning/orange/danger)
- py_compile: OK

### Step 6 — GoalService (commit: 5f4cf36)
- Добавлен delete_contribution() в GoalService
- Lazy import BudgetReservationService (избежание circular dependency)
- Удаление транзакции если есть → пересчёт exception
- py_compile: OK

### Step 7 — Callbacks интеграция (commit: 16975a5)
- goals.py: save_budget — добавлен recalculate_current_month_exception после set_mode
- budget_reservation_service.py: update_contribution_transaction — добавлен recalculate
- Комментарии про порядок вызовов
- py_compile: OK

### Step 8 — Unit тесты (commit: afbe1dc)
- Добавлено 13 новых тестов для protocol-0018:
  - TestFindAnyReserveTemplate: 4 теста
  - TestGetTemplateDay: 2 теста
  - TestCleanupOrphanExceptions: 2 теста
  - TestRecalculateCurrentMonthException: 4 теста
  - TestUpdateContributionRecalc: 1 тест
- Исправлен test_progress_fixed_date_mode (mode_text → "Внесено")
- pytest: 45 passed

### Step 9 — Integration тесты (commit: 4a572a7)
- Создан test_budget_calendar_integration.py с 3 E2E тестами:
  - test_contribution_before_reserve_reduces_reserve_in_calendar
  - test_contribution_after_mode_switch_updates_reserve
  - test_delete_contribution_restores_reserve
- pytest.skip() для дат >= reserve_day
- Decimal конверсия для сравнения amount
- pytest: 3 passed

### Step 10 — Финализация (commit: 18d6a1c)
- black: 2 files reformatted
- flake8: E501 fix в docstring
- pytest: 418 passed
- Статус: Completed
