# Шаг 3: Обновление exports

## Briefing
- **Цель:** Обновить `app/services/__init__.py` для экспорта всех новых компонентов (DashboardService, TypedDicts).
- **Ключевые файлы:**
  - `app/services/__init__.py` (изменить)
- **Additional info:**
  - Экспортировать: DashboardService, OverviewMetrics, CashflowDataPoint, RecentTransaction, PeriodType
  - YearSummary уже добавлен в Шаге 1

## Sub-tasks

1. **Прочитать текущее содержимое** `app/services/__init__.py`

2. **Добавить импорт DashboardService и TypedDicts**:
   ```python
   from .dashboard_service import (
       DashboardService,
       OverviewMetrics,
       CashflowDataPoint,
       RecentTransaction,
       PeriodType,
   )
   ```

3. **Обновить `__all__`** списком экспортируемых имен:
   ```python
   __all__ = [
       # Existing
       "TransactionService",
       "GoalService",
       "CalendarService",
       "MonthSummary",
       "TransactionInfo",
       "YearSummary",
       # New
       "DashboardService",
       "OverviewMetrics",
       "CashflowDataPoint",
       "RecentTransaction",
       "PeriodType",
   ]
   ```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.
2. **Верификация:** После завершения запусти проверки:
   ```bash
   cd /home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration
   black app/services/__init__.py
   flake8 app/services/__init__.py
   python -c "from app.services import DashboardService, OverviewMetrics; print('OK')"
   ```
3. **Фиксация:** После успешной верификации:
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 4
   - Проверь ветку main
4. **Коммит**: `git add . && git commit -m "chore(services): export DashboardService and TypedDicts [protocol-0003/03]"`. Push.
5. **Отчет пользователю** в установленном формате.
