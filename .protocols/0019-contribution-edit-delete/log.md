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

### Step 01 — Schema и GoalService helpers (commit: 8b0648c)
- Добавлены ContributionInfo и ContributionUpdateResult TypedDicts в app/schema/goals.py
- Обновлен app/schema/__init__.py с новыми экспортами
- Добавлен _get_budget_service() helper в GoalService
- Рефакторинг: заменены 3 inline lazy imports на self._get_budget_service()
- Добавлен get_contribution_by_id() метод
- 418 тестов проходят без регрессий

### Step 02 — update_contribution() и fix delete_contribution() (commit: 9089dc5)
- Реализован update_contribution() с Guards #1, #2a, #2b, #3
- Каскадная синхронизация: GoalContribution → Transaction → Goal.current_amount → Exception
- Переписан delete_contribution() по Варианту A (прямое удаление без delete_contribution_transaction())
- Добавлен откат статуса COMPLETED -> ACTIVE в обоих методах
- ContributionInfo сохраняется до flush() для detached state protection
- Добавлены imports: Literal, Transaction, ContributionInfo, ContributionUpdateResult
- 418 тестов проходят

### Step 03 — Calendar Guard #6 (commit: pending)
- Добавлен Guard #6 в open_edit_from_tooltip(): блокирует SAVINGS_CONTRIBUTION
- SAVINGS_CONTRIBUTION помечен как readonly в tooltip UI (аналогично SAVINGS_RESERVE)
- Обновлен тест test_savings_contribution_is_not_readonly → test_savings_contribution_is_readonly
- 418 тестов проходят
