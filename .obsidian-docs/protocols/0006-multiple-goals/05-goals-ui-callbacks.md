# Шаг 5: Goals UI — модалы и callbacks

## Briefing
- **Цель:** Добавить модал настройки бюджета, реализовать callbacks для кнопок приоритетов (↑↓), интегрировать AllocationService для обновления allocated_amount.
- **Ключевые файлы:**
  - `app/components/goals.py` (изменить)
- **Additional info:**
  - Pattern-Matching callbacks с guard clauses (ADR-003)
  - При изменении приоритета пересчитывать allocation
  - При изменении бюджета пересчитывать allocation
  - Использовать dcc.Store для хранения состояния (budget, allocation_results)

## Sub-tasks

1. **Добавить модал настройки бюджета**:
   ```python
   def _build_budget_modal() -> dbc.Modal:
       """Модал для настройки месячного бюджета накоплений."""
   ```
   Содержимое:
   - Header: "Настройка бюджета накоплений"
   - Body: Input для суммы (type="number", min=0)
   - Footer: Кнопки "Отмена" и "Сохранить"
   - ID: "budget-modal"

2. **Добавить dcc.Store компоненты**:
   - `dcc.Store(id="goals-budget-store")` — текущий бюджет
   - `dcc.Store(id="goals-allocation-store")` — результаты allocation (serialized)

3. **Callback: открытие модала бюджета**:
   ```python
   @callback(
       Output("budget-modal", "is_open"),
       Output("budget-input", "value"),
       Input("open-budget-modal-btn", "n_clicks"),
       State("goals-budget-store", "data"),
       prevent_initial_call=True,
   )
   def open_budget_modal(n_clicks, current_budget):
       """Открывает модал с текущим значением бюджета."""
   ```

4. **Callback: сохранение бюджета**:
   ```python
   @callback(
       Output("budget-modal", "is_open", allow_duplicate=True),
       Output("goals-budget-store", "data"),
       Output("goals-allocation-store", "data"),
       Output("goals-list-container", "children"),
       Output("goals-summary-container", "children"),
       Input("save-budget-btn", "n_clicks"),
       State("budget-input", "value"),
       State("active-user-id", "data"),
       prevent_initial_call=True,
   )
   def save_budget(n_clicks, budget_value, user_id):
       """Сохраняет бюджет и пересчитывает allocation."""
   ```

5. **Callback: изменение приоритета (↑)**:
   ```python
   @callback(
       Output("goals-list-container", "children", allow_duplicate=True),
       Output("goals-allocation-store", "data", allow_duplicate=True),
       Input({"type": "priority-up-btn", "index": ALL}, "n_clicks"),
       State("active-user-id", "data"),
       State("goals-budget-store", "data"),
       prevent_initial_call=True,
   )
   def move_priority_up(n_clicks_list, user_id, budget):
       """Перемещает цель на один приоритет вверх."""
   ```
   Guard clauses:
   - `if ctx.triggered[0].get('value') is None: raise PreventUpdate`
   - `if not ctx.triggered_id or not ctx.triggered_id.get("index"): raise PreventUpdate`

6. **Callback: изменение приоритета (↓)**:
   Аналогично move_priority_up, но вызывает `GoalService.move_priority_down()`.

7. **Callback: обновление allocation после CRUD операций**:
   Обновить существующие callbacks (`create_goal`, `update_goal`, `delete_goal`) чтобы они пересчитывали allocation после изменений.

8. **Helper функция для пересчета и обновления UI**:
   ```python
   def _recalculate_and_render(session, user_id: int, budget: Decimal):
       """Пересчитывает allocation и возвращает обновленный UI."""
   ```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-8.

2. **Верификация:**
   ```bash
   black app/components/goals.py
   flake8 app/components/goals.py
   # Функциональная проверка:
   python run.py
   # Проверить:
   # - Открытие/закрытие модала бюджета
   # - Сохранение бюджета
   # - Кнопки ↑↓ для приоритетов
   # - Пересчет allocation при изменениях
   pytest tests/ -v
   ```

3. **Фиксация:**
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 6
   - Проверь ветку main

4. **Коммит:**
   ```bash
   git add .
   git commit -m "feat(ui): add budget modal and priority callbacks [protocol-0006/05]"
   git push
   ```

5. **Отчет пользователю.**
