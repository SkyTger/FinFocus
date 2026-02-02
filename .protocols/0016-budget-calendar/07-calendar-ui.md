# Шаг 7: Calendar UI

## Briefing

- **Цель:** Визуализация SAVINGS_RESERVE/CONTRIBUTION в календаре, edit/delete callbacks
- **Ключевые файлы:**
  - `app/components/calendar.py` — UI и callbacks
  - `app/utils/formatters.py` — иконки для новых типов
- **Доп. информация:** SAVINGS_RESERVE read-only, SAVINGS_CONTRIBUTION editable

## Sub-tasks

1. **ICON_TO_EMOJI** в `formatters.py` — добавить:
   ```python
   "savings_reserve": "💼",
   "savings_contribution": "🎯",
   ```

2. **Tooltip для SAVINGS_RESERVE**:
   - Иконка 💼, название "Резерв на цели"
   - Read-only (без клика на edit)
   - Пометка "(системная)" или визуальный индикатор

3. **Tooltip для SAVINGS_CONTRIBUTION**:
   - Иконка 🎯, название "Взнос: {goal_name}"
   - Кликабельно → открывает edit modal
   - Редактирование суммы синхронизирует GoalContribution

4. **Callback: edit SAVINGS_CONTRIBUTION**:
   - При сохранении вызывать BudgetReservationService.update_contribution_transaction()
   - Обновлять calendar и goals refresh triggers

5. **Callback: delete SAVINGS_CONTRIBUTION**:
   - Подтверждение удаления
   - Вызывать BudgetReservationService.delete_contribution_transaction()
   - Каскадное удаление GoalContribution

6. **Guard clauses** (ADR-003):
   - Проверка n_clicks в callbacks
   - prevent_initial_call=True для модалов

7. **Unit тесты** — проверить отображение новых типов в TransactionInfo

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/components/calendar.py`
3. Визуальное тестирование: создать SAVINGS_RESERVE через fixed_date режим, проверить отображение
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 8
6. Коммит: `git add . && git commit -m "feat(calendar): add SAVINGS_RESERVE/CONTRIBUTION visualization [protocol-0016/07]"`
7. Push
