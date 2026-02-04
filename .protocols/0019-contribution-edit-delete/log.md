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

### Step 06 — Финализация (commit: edc2195)
- Black: 3 файла переформатированы
- Flake8: 1 unused import исправлен (TransactionType)
- Pytest: 441 tests passed
- PR #19 marked as Ready for Review

### Step 05 — Unit тесты (commit: d557f2c)
- 23 новых тестов в tests/test_contribution_edit_delete.py
- update_contribution: 17 тестов (amount, date, description, status, error)
- delete_contribution: 5 тестов (transaction_id, no_transaction, info, recalculate, no_double_decrement)
- delete not found: 1 тест
- Исправлен mock scope для across_months теста (patch.object вместо @patch)
- 441 тестов проходят (418 + 23)

### Step 04 — Goals UI (commit: 28b02b4)
- Расширена _build_contributions_table(): колонка "Действия" с Edit/Delete кнопками
- Создан _build_edit_contribution_modal(): inline alert, amount/date/description поля
- Создан _build_delete_contribution_confirm_modal(): confirmation с суммой/датой
- 4 callbacks: open_edit, submit_edit, open_delete, confirm_delete
- ADR-003 guard clauses во всех callbacks
- Detached state protection: скалярные данные до commit()
- 418 тестов проходят

### Step 03 — Calendar Guard #6 (commit: de9531f)
- Добавлен Guard #6 в open_edit_from_tooltip(): блокирует SAVINGS_CONTRIBUTION
- SAVINGS_CONTRIBUTION помечен как readonly в tooltip UI (аналогично SAVINGS_RESERVE)
- Обновлен тест test_savings_contribution_is_not_readonly → test_savings_contribution_is_readonly
- 418 тестов проходят
