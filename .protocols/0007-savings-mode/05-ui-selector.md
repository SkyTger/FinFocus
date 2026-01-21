# Шаг 5: UI - selector и callback

## Briefing
- **Цель:** Создать RadioItems selector для выбора режима накоплений, callback для сохранения режима, обновить все существующие callbacks что вызывают `_recalculate_and_render()`.
- **Ключевые файлы:**
  - `app/components/goals.py` (модифицировать)
  - `app/assets/goals.css` (модифицировать — добавить стили)
- **Additional info:**
  - RadioItems размещается в summary section рядом с кнопкой "Настроить бюджет"
  - Callback `save_savings_mode()` обновляет БД и пересчитывает allocation
  - ВСЕ callbacks, вызывающие `_recalculate_and_render()`, должны передавать `savings_mode`

## Sub-tasks

1. **Создать функцию _build_mode_selector():**
   ```python
   def _build_mode_selector(current_mode: str) -> dbc.Card:
       """Создает RadioItems для выбора режима накоплений."""
       options = [
           {
               "label": html.Div([
                   html.Span(MODE_OPTIONS[mode]["label"], className="mode-label"),
                   html.Br(),
                   html.Small(MODE_OPTIONS[mode]["description"], className="mode-description"),
               ]),
               "value": mode,
           }
           for mode in ["free", "medium", "strict"]
       ]

       return dbc.Card([
           dbc.CardHeader("Режим накоплений"),
           dbc.CardBody([
               dbc.RadioItems(
                   id="savings-mode-selector",
                   options=options,
                   value=current_mode,
                   className="savings-mode-radio",
               ),
           ]),
       ], className="mode-selector-card")
   ```

2. **Интегрировать selector в summary section:**
   - Найти функцию `_build_summary_section()` или эквивалент
   - Добавить вызов `_build_mode_selector(savings_mode)` рядом с budget button
   - Расположить в Row/Col для адаптивности

3. **Создать callback save_savings_mode():**
   ```python
   @callback(
       Output("goal-card-container", "children", allow_duplicate=True),
       Output("goals-allocation-store", "data", allow_duplicate=True),
       Output("goals-savings-mode-store", "data", allow_duplicate=True),
       Input("savings-mode-selector", "value"),
       State("goals-budget-store", "data"),
       prevent_initial_call=True,
   )
   def save_savings_mode(new_mode, budget):
       """Сохраняет выбранный режим и пересчитывает allocation."""
       if new_mode is None:
           raise PreventUpdate

       with get_db_session() as session:
           user_id = 1
           service.update_savings_mode(session, user_id, new_mode)
           session.commit()

           budget_decimal = Decimal(str(budget)) if budget else Decimal("0")
           goal_cards, allocation_data = _recalculate_and_render(
               session, user_id, budget_decimal, savings_mode=new_mode
           )

           return goal_cards, allocation_data, new_mode
   ```

4. **Обновить ВСЕ callbacks, вызывающие _recalculate_and_render():**
   - `create_goal()` — добавить State для savings_mode_store, передать в helper
   - `save_budget()` — добавить State для savings_mode_store, передать в helper
   - `add_contribution()` — добавить State для savings_mode_store, передать в helper
   - `toggle_goal_status()` — добавить State для savings_mode_store, передать в helper
   - `change_priority()` — добавить State для savings_mode_store, передать в helper
   - `delete_goal()` — добавить State для savings_mode_store, передать в helper

   Для каждого callback:
   - Добавить `State("goals-savings-mode-store", "data")` в декоратор
   - Добавить параметр `savings_mode` в функцию
   - Передать `savings_mode=savings_mode or "free"` в `_recalculate_and_render()`

5. **Добавить CSS стили:**
   - В `app/assets/goals.css` добавить стили для mode selector

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:**
   - `python -m py_compile app/components/goals.py`

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Опиши selector, callback и список обновленных callbacks.
   - **Обнови `context.md`**: `Current Step` на 6, подготовь `Next Action` для финализации.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(ui): add savings mode selector and update callbacks [protocol-0007/05]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**

## Детали реализации

### CSS стили для goals.css (~20 строк)
```css
/* Savings Mode Selector */
.mode-selector-card {
    margin-bottom: 1rem;
}

.mode-selector-card .card-header {
    font-weight: 600;
    background-color: var(--bs-light);
}

.savings-mode-radio .form-check {
    margin-bottom: 0.75rem;
    padding: 0.5rem;
    border-radius: 0.375rem;
    transition: background-color 0.2s;
}

.savings-mode-radio .form-check:hover {
    background-color: rgba(0, 128, 0, 0.05);
}

.savings-mode-radio .form-check-input:checked + .form-check-label {
    color: var(--primary-green);
}

.mode-label {
    font-weight: 500;
}

.mode-description {
    color: var(--bs-secondary);
    font-size: 0.85rem;
}
```

### Паттерн обновления callback (пример для create_goal)
```python
@callback(
    Output("goal-card-container", "children", allow_duplicate=True),
    Output("goals-allocation-store", "data", allow_duplicate=True),
    Output("create-goal-modal", "is_open", allow_duplicate=True),
    Input("create-goal-submit", "n_clicks"),
    State("create-goal-name", "value"),
    # ... другие State ...
    State("goals-budget-store", "data"),
    State("goals-savings-mode-store", "data"),  # ADD THIS
    prevent_initial_call=True,
)
def create_goal(n_clicks, name, ..., budget, savings_mode):  # ADD PARAM
    # ... валидация и создание цели ...

    goal_cards, allocation_data = _recalculate_and_render(
        session,
        user_id,
        budget_decimal,
        savings_mode=savings_mode or "free",  # PASS MODE
    )

    return goal_cards, allocation_data, False
```

### Список callbacks для обновления
1. `create_goal()` — создание цели
2. `save_budget()` — сохранение бюджета
3. `add_contribution()` — добавление взноса
4. `toggle_goal_status()` — смена статуса цели
5. `change_priority()` — изменение приоритета
6. `delete_goal()` — удаление цели

Для каждого добавить:
- `State("goals-savings-mode-store", "data")` в декоратор
- параметр `savings_mode` в функцию
- передачу `savings_mode=savings_mode or "free"` в helper
