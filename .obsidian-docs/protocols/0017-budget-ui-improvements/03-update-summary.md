# Шаг 3: Update Summary Section

## Briefing

- **Цель:** Обновить "Сводку по целям" — показать прогресс бюджета в формате "X / Y ₽"
- **Ключевые файлы:**
  - `app/components/goals.py`
- **Доп. информация:** Нужно добавить параметр budget_progress в функцию и обновить вызывающий код

## Sub-tasks

1. Изменить сигнатуру `_build_summary_section()`:
   ```python
   def _build_summary_section(
       goals_summary: GoalsSummary,
       allocation_summary: AllocationSummary,
       budget_progress: BudgetProgress,  # NEW
   ) -> dbc.Card:
   ```

2. Добавить импорт BudgetProgress если отсутствует:
   ```python
   from app.schema import BudgetProgress
   ```

3. Изменить секцию "Бюджет накоплений" (примерно строки 539-556):
   ```python
   dbc.Col(
       [
           html.P(
               "Бюджет накоплений",
               className="text-muted mb-0 small",
           ),
           html.Small(
               "В текущем месяце",
               className="text-muted",
           ),
           html.H5(
               [
                   format_amount(budget_progress["used_budget"]),
                   html.Span(" / ", className="text-muted"),
                   html.Span(
                       format_amount(budget_progress["total_budget"]),
                       className="text-muted",
                   ),
               ],
               className="mb-0",
           ),
       ],
       md=6,
   ),
   ```

4. Найти callback который вызывает `_build_summary_section()` и обновить:
   - Добавить вызов `BudgetReservationService.get_budget_progress()`
   - Передать `budget_progress` в функцию

5. Добавить импорт BudgetReservationService если отсутствует:
   ```python
   from app.services import BudgetReservationService
   ```

6. Добавить refresh trigger после внесения взноса (если ещё нет):
   - Найти callback который обрабатывает внесение
   - Добавить Output для обновления сводки

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/goals.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Коммит: `git add . && git commit -m "feat(goals): update summary section with budget progress [protocol-0017/03]"`
6. Push
7. Отчёт
