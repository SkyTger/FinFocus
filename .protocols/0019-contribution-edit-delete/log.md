# Work Log: 0019-contribution-edit-delete — Редактирование и удаление взносов

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0019#ctx-N -->
Restore context: protocol-0019#ctx-1

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 01 — Schema и GoalService helpers (commit: pending)
- Добавлены ContributionInfo и ContributionUpdateResult TypedDicts в app/schema/goals.py
- Обновлен app/schema/__init__.py с новыми экспортами
- Добавлен _get_budget_service() helper в GoalService
- Рефакторинг: заменены 3 inline lazy imports на self._get_budget_service()
- Добавлен get_contribution_by_id() метод
- 418 тестов проходят без регрессий
