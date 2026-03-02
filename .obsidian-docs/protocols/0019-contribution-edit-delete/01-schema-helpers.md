# Шаг 1: Schema и GoalService helpers

## Briefing

- **Цель:** Создать TypedDicts (ContributionUpdateResult, ContributionInfo), добавить _get_budget_service() helper и get_contribution_by_id() в GoalService
- **Ключевые файлы:**
  - `app/schema/goals.py` — новые TypedDicts
  - `app/schema/__init__.py` — экспорт
  - `app/services/goal_service.py` — helper методы + рефакторинг lazy import
- **Доп. информация:** См. `.design/solution-v4.md` секции "Ключевые интерфейсы" и "Изменение 3"

## Sub-tasks

1. **Создать `app/schema/goals.py`** (если не существует):
   ```python
   from typing import Literal, TypedDict
   from datetime import date
   from decimal import Decimal
   from app.models.database import Goal

   class ContributionInfo(TypedDict):
       """Информация о взносе для confirmation modal."""
       contribution_id: int
       amount: Decimal
       contribution_date: date
       goal_name: str

   class ContributionUpdateResult(TypedDict):
       """Результат операции обновления/удаления взноса."""
       success: bool
       goal: Goal | None
       status_changed: bool
       new_status: Literal["active", "completed"] | None
       error: str | None
       contribution_info: ContributionInfo | None
   ```

2. **Обновить `app/schema/__init__.py`** — добавить экспорт ContributionUpdateResult, ContributionInfo

3. **Добавить `_get_budget_service()` в GoalService:**
   ```python
   def _get_budget_service(self):
       """Возвращает BudgetReservationService с текущей сессией.
       Lazy import для избежания circular dependency."""
       from app.services.budget_reservation_service import BudgetReservationService
       return BudgetReservationService(self.session)
   ```

4. **Рефакторинг lazy import** — заменить все вхождения inline lazy import на `self._get_budget_service()`:
   - `add_contribution()` (~строка 154)
   - `update_savings_budget()` (~строка 486)
   - `delete_contribution()` (~строка 569)

5. **Добавить `get_contribution_by_id()`:**
   ```python
   def get_contribution_by_id(self, contribution_id: int) -> GoalContribution | None:
       """Получает взнос по ID для предзаполнения формы редактирования."""
       return self.session.get(GoalContribution, contribution_id)
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/schema/goals.py app/services/goal_service.py`
3. Запусти существующие тесты: `pytest tests/ -x -q` — убедись что рефакторинг не сломал ничего
4. Обнови `log.md` — что сделано, неочевидные решения
5. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
6. Коммит: `git add . && git commit -m "feat(goals): add ContributionUpdateResult schema and GoalService helpers [protocol-0019/01]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
