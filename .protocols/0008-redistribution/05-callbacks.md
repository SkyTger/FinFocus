# Шаг 5: Goals Callbacks

## Briefing
- **Цель:** Модифицировать существующий `add_contribution()` callback для детекции just-completed и добавить новые callbacks для confirm/decline перераспределения.
- **Ключевые файлы:**
  - `app/components/goals.py` (модифицировать — callbacks)
- **Additional info:**
  - "just-completed detection": проверка was_completed_before vs is_completed после взноса
  - Guard clauses согласно ADR-003 для Pattern-Matching Callbacks
  - Debounce через disabled state кнопки и dcc.Store
  - Timing logs для NFR-1 verification
  - Spinner toggle: show на входе, hide на выходе

## Sub-tasks

1. **Модифицировать `add_contribution()` callback:**
   - **Добавить Outputs:**
     - `Output("redistribution-modal", "is_open")`
     - `Output("redistribution-preview-store", "data")`
     - `Output("redistribution-btn-disabled-store", "data")`
   - **Just-completed detection:**
     ```python
     # ДО взноса
     was_completed_before = goal.is_completed

     # Добавить взнос
     goal_service.add_contribution(...)
     session.flush()

     # ПОСЛЕ взноса
     just_completed = goal.is_completed and not was_completed_before
     ```
   - **Если just_completed:**
     1. Получить all_goals, monthly_budget, savings_mode
     2. Вызвать RedistributionService.calculate_redistribution_preview()
     3. Сериализовать preview
     4. Вернуть: modal is_open=True, preview data, btn_disabled=False

2. **Создать `confirm_redistribution()` callback:**
   ```python
   @callback(
       [
           Output("redistribution-modal", "is_open", allow_duplicate=True),
           Output("goal-card-container", "children", allow_duplicate=True),
           Output("goals-allocation-store", "data", allow_duplicate=True),
           Output("confirm-redistribution-btn", "disabled"),
           Output("confirm-redistribution-spinner", "style"),
           Output("confirm-redistribution-text", "children"),
       ],
       Input("confirm-redistribution-btn", "n_clicks"),
       [
           State("redistribution-preview-store", "data"),
           State("goals-budget-store", "data"),
           State("goals-savings-mode-store", "data"),
           State("redistribution-btn-disabled-store", "data"),
       ],
       prevent_initial_call=True,
   )
   def confirm_redistribution(n_clicks, preview_data, budget, savings_mode, btn_disabled):
       # Guard clauses
       if not n_clicks:
           raise PreventUpdate
       if btn_disabled:
           raise PreventUpdate  # Debounce

       # Timing log start
       start_time = time.perf_counter()

       # Deserialize preview
       preview = deserialize_redistribution_preview(preview_data)

       # Business logic
       with get_db_session() as session:
           # Recalculate allocation
           # Log redistribution event (confirmed)
           # Render updated goals

       # Timing log end
       elapsed_ms = (time.perf_counter() - start_time) * 1000
       logger.debug(f"confirm_redistribution: {elapsed_ms:.2f}ms")

       return (
           False,  # close modal
           updated_cards,
           serialized_allocation,
           True,  # keep btn disabled
           {"display": "none"},  # hide spinner
           "Перераспределить",
       )
   ```

3. **Создать `decline_redistribution()` callback:**
   ```python
   @callback(
       Output("redistribution-modal", "is_open", allow_duplicate=True),
       Input("decline-redistribution-btn", "n_clicks"),
       State("redistribution-preview-store", "data"),
       prevent_initial_call=True,
   )
   def decline_redistribution(n_clicks, preview_data):
       # Guard clauses
       if not n_clicks:
           raise PreventUpdate

       # Log redistribution event (declined)
       preview = deserialize_redistribution_preview(preview_data)
       if preview:
           with get_db_session() as session:
               # Log event
               pass

       return False  # close modal
   ```

4. **Добавить импорты:**
   - `import time`
   - `from app.services import RedistributionService`
   - `from app.utils.serializers import serialize_redistribution_preview, deserialize_redistribution_preview`

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:**
   ```bash
   python -m py_compile app/components/goals.py
   ```

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Описание логики callbacks, особенно just-completed detection.
   - **Обнови `context.md`**: Current Step = 6, Next Action для integration тестов.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(goals): add redistribution callbacks with just-completed detection [protocol-0008/05]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**
