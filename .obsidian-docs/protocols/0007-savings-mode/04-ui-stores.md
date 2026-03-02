# Шаг 4: UI - stores и helper

## Briefing
- **Цель:** Подготовить UI инфраструктуру для savings_mode: добавить dcc.Store, расширить helper функцию `_recalculate_and_render()`, обновить callback загрузки данных.
- **Ключевые файлы:**
  - `app/components/goals.py` (модифицировать)
- **Additional info:**
  - Добавить `dcc.Store(id="goals-savings-mode-store", data=None)` в layout
  - Расширить `_recalculate_and_render()` параметром `savings_mode`
  - Обновить `load_goal_data()` для чтения и передачи savings_mode
  - На этом шаге НЕ создаем UI selector — только инфраструктуру

## Sub-tasks

1. **Добавить константу MODE_OPTIONS:**
   - В начале `goals.py` после импортов:
     ```python
     MODE_OPTIONS = {
         "free": {
             "label": "Свободный (100%)",
             "description": "Минимальные взносы точно по графику",
         },
         "medium": {
             "label": "Средний (115%)",
             "description": "+15% буфер для непредвиденных расходов",
         },
         "strict": {
             "label": "Строгий (150%)",
             "description": "Максимизация накоплений для раннего достижения",
         },
     }
     ```

2. **Добавить dcc.Store для savings_mode:**
   - В функции `create_goals_layout()` найти существующие stores
   - Добавить новый store:
     ```python
     dcc.Store(id="goals-savings-mode-store", data=None),
     ```

3. **Расширить _recalculate_and_render():**
   - Добавить параметр `savings_mode: str = "free"`
   - Передать в `AllocationService.calculate_allocation()`:
     ```python
     allocation_summary = allocation_service.calculate_allocation(
         goals=all_goals,
         monthly_budget=budget,
         savings_mode=savings_mode,
     )
     ```

4. **Обновить load_goal_data() callback:**
   - Добавить Output для `goals-savings-mode-store`
   - Читать режим из БД: `savings_mode = service.get_savings_mode(session, user_id)`
   - Передать в `_recalculate_and_render()`
   - Вернуть `savings_mode` для инициализации store

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:**
   - `python -m py_compile app/components/goals.py`

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Опиши добавленные stores и изменения в helper.
   - **Обнови `context.md`**: `Current Step` на 5, подготовь `Next Action` для Шага 5.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(ui): add savings_mode store and extend helper [protocol-0007/04]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**

## Детали реализации

### Изменения в _recalculate_and_render()
```python
def _recalculate_and_render(
    session,
    user_id: int,
    budget: Decimal,
    savings_mode: str = "free",  # NEW PARAM
):
    """Пересчитывает allocation и возвращает обновленный UI.

    Args:
        session: SQLAlchemy session.
        user_id: ID пользователя.
        budget: Месячный бюджет на накопления.
        savings_mode: Режим накоплений ("free", "medium", "strict").

    Returns:
        tuple: (goal_cards, allocation_store_data)
    """
    # ... получение целей ...

    allocation_summary = allocation_service.calculate_allocation(
        goals=all_goals,
        monthly_budget=budget,
        savings_mode=savings_mode,  # Передаем режим
    )

    # ... построение UI ...
```

### Изменения в load_goal_data() callback
```python
@callback(
    Output("goal-card-container", "children"),
    Output("goals-budget-store", "data"),
    Output("goals-allocation-store", "data"),
    Output("goals-savings-mode-store", "data"),  # NEW OUTPUT
    Input("url", "pathname"),
    prevent_initial_call=False,
)
def load_goal_data(pathname):
    """Загружает данные целей при открытии страницы."""
    if pathname != "/goals":
        raise PreventUpdate

    with get_db_session() as session:
        user_id = 1  # MVP: один пользователь

        # Получаем budget и savings_mode
        budget = service.get_savings_budget(session, user_id)
        savings_mode = service.get_savings_mode(session, user_id)  # NEW

        # Пересчитываем с учетом режима
        goal_cards, allocation_data = _recalculate_and_render(
            session, user_id, budget, savings_mode=savings_mode  # PASS MODE
        )

        return (
            goal_cards,
            float(budget),
            allocation_data,
            savings_mode,  # NEW RETURN
        )
```

### Важно: Проверить что _recalculate_and_render возвращает кортеж
Функция должна возвращать `(goal_cards, allocation_data)`, убедись что это соответствует текущей реализации.
