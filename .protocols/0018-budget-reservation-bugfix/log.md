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

### Step 1 — Helper методы (commit: pending)
- Добавлены 4 helper метода в BudgetReservationService:
  - `_find_any_reserve_template()` — поиск любого шаблона (включая остановленный)
  - `_get_template_day()` — извлечение дня из шаблона (EOM → 31)
  - `_get_reserve_date_for_month()` — дата резерва с учётом коротких месяцев
  - `_delete_exception_for_date()` — удаление exception для даты
- py_compile: OK
