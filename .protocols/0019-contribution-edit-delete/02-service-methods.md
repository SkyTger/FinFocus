# Шаг 2: update_contribution() и fix delete_contribution()

## Briefing

- **Цель:** Реализовать GoalService.update_contribution() с каскадной синхронизацией и переписать delete_contribution() по Варианту A (прямое удаление без delete_contribution_transaction())
- **Ключевые файлы:**
  - `app/services/goal_service.py` — update_contribution(), delete_contribution()
- **Доп. информация:** См. `.design/solution-v4.md` секции "Обновленный update_contribution()" и "Изменение 1: delete_contribution()"

## Sub-tasks

1. **Реализовать `update_contribution()`** — полный код из solution-v4:
   - Guard #1: amount > 0
   - Guard #2a: дата не в прошлом месяце
   - Guard #2b: дата не далее текущий месяц + 1
   - Guard #3: contribution not found
   - Обновление полей GoalContribution
   - Delta calculation + Goal.current_amount += delta
   - Guard: `if goal.current_amount < Decimal("0"): goal.current_amount = Decimal("0")`
   - Sync Transaction (amount, date, description)
   - Description семантика: None = не менять, "" = очистить (default), непустая = установить
   - Пересчет Exception: `if contribution_date is not None and contribution_date != old_date`
   - Status change detection: COMPLETED <-> ACTIVE
   - flush() + return ContributionUpdateResult

2. **Переписать `delete_contribution()`** по Варианту A:
   - **НЕ вызывать** `budget_service.delete_contribution_transaction()`
   - Удалять Transaction и GoalContribution через `session.delete()` напрямую
   - `goal_name = goal.name` сохранять ДО flush() (detached state protection)
   - Единственное место обновления current_amount
   - Единственное место отката статуса COMPLETED -> ACTIVE
   - return ContributionUpdateResult с contribution_info

3. **Проверить вызовы delete_contribution_transaction():**
   - Выполнить `grep -rn "delete_contribution_transaction" app/` для проверки что метод не вызывается из других мест, которые зависят от побочных эффектов

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/goal_service.py`
3. Запусти существующие тесты: `pytest tests/ -x -q`
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
6. Коммит: `git add . && git commit -m "feat(goals): add update_contribution and fix delete_contribution [protocol-0019/02]"`
7. Push
8. Отчёт
