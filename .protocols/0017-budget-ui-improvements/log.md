# Work Log: 0017-budget-ui-improvements — Улучшение UI бюджета накоплений + механика fixed_date

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

Restore context: protocol-0017#ctx-1

---

## Step Log

### Step 0 — Setup (commit: 7cadb23)
- Создан worktree 0017-budget-ui-improvements
- Созданы артефакты протокола: plan.md, context.md, log.md, 00-06 step files
- Спецификация: `.reports/epics/epic-04-advanced/spec-budget-ui-improvements.md`

### Step 1 — UI Description (commit: c4ae7ad)
- Изменена константа RESERVE_DESCRIPTION: "Резерв на цели" → "Резервирование бюджета"
- Обновлён docstring модуля для консистентности
- "(авто)" суффикс подтверждён в calendar.py:481 — без изменений

### Step 2 — Remove Budget Card (commit: pending)
- Удалена функция `_build_budget_progress_card()` (~70 строк)
- Удалён container `budget-progress-card-container` из layout
- Удалён Store `budget-progress-refresh-trigger`
- Удалён callback `load_budget_progress_card()` (~55 строк)
- Удалён неиспользуемый импорт `BudgetProgress`
- Итого удалено: ~130 строк кода
