# Шаг 6: Dashboard интеграция

## Briefing
- **Цель:** Обновить DashboardService для агрегации savings по всем активным целям, а не только по первой.
- **Ключевые файлы:**
  - `app/services/dashboard_service.py` (изменить)
  - `app/components/dashboard.py` (возможно изменить)
  - `tests/test_dashboard_service.py` (добавить тесты)
- **Additional info:**
  - Текущая реализация показывает только первую активную цель
  - Нужно: сумма по всем активным целям
  - Формула: savings_progress = (sum(current) / sum(target)) * 100
  - Если целей > 1, показывать "{N} целей" вместо имени цели

## Sub-tasks

1. **Изучить текущую реализацию** в `DashboardService.get_overview_metrics()`:
   - Найти где берется savings информация
   - Понять структуру OverviewMetrics

2. **Обновить `get_overview_metrics()`**:
   ```python
   # Текущий код (примерно):
   active_goal = goal_service.get_active_goal(session, user_id)
   savings_current = active_goal.current_amount if active_goal else 0
   savings_target = active_goal.target_amount if active_goal else 0

   # Новый код:
   active_goals = goal_service.get_all_by_user(session, user_id, status=GoalStatus.ACTIVE)
   savings_current = sum(g.current_amount for g in active_goals)
   savings_target = sum(g.target_amount for g in active_goals)
   savings_progress = (savings_current / savings_target * 100) if savings_target > 0 else 0
   savings_name = f"{len(active_goals)} целей" if len(active_goals) > 1 else (active_goals[0].name if active_goals else "Нет целей")
   ```

3. **Обновить OverviewMetrics TypedDict** (если нужно):
   - Добавить `savings_count: int` — количество активных целей
   - Или использовать существующие поля

4. **Обновить Dashboard UI** (если нужно):
   - Проверить как отображается savings карточка
   - Убедиться что показывается корректное название

5. **Написать тесты** в `tests/test_dashboard_service.py`:
   ```python
   def test_overview_metrics_multiple_goals():
       """Метрики агрегируют savings по нескольким активным целям."""
       # Создать 3 активных цели
       # Проверить что savings_current = sum(all current)
       # Проверить что savings_target = sum(all target)
       # Проверить что savings_name содержит "3 целей"

   def test_overview_metrics_single_goal():
       """Метрики для одной цели показывают её имя."""

   def test_overview_metrics_no_goals():
       """Метрики без целей показывают "Нет целей"."""
   ```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-5.

2. **Верификация:**
   ```bash
   black app/services/dashboard_service.py app/components/dashboard.py
   flake8 app/services/dashboard_service.py app/components/dashboard.py
   pytest tests/test_dashboard_service.py -v
   pytest tests/ -v
   # Визуальная проверка: открыть Dashboard и проверить savings карточку
   python run.py
   ```

3. **Фиксация:**
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 7
   - Проверь ветку main

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(dashboard): aggregate savings across all active goals [protocol-0006/06]"
   git push
   ```

5. **Отчет пользователю.**
