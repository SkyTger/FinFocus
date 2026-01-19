# Шаг 3: Goals Callbacks

## Briefing
- **Цель:** Реализовать все callbacks для CRUD операций с целями и взносами. Все callbacks используют простые ID (без Pattern-Matching).
- **Ключевые файлы:**
  - `app/components/goals.py` (модифицировать — добавить callbacks)
- **Additional info:**
  - Все callbacks с `prevent_initial_call=True`
  - Guard clauses в начале каждого callback
  - ValidationError ловится и показывается в Alert
  - dcc.Store синхронизируется при каждой CRUD операции
  - `allow_duplicate=True` для множественных Outputs на один компонент

## Sub-tasks

### 3.1 Callback загрузки данных

1. **Добавить `load_goal_data()` callback в goals.py:**

```python
# --- Callbacks (все с prevent_initial_call=True) ---


@callback(
    [
        Output("goal-card-container", "children"),
        Output("contributions-table-container", "children"),
        Output("current-goal-id", "data"),
    ],
    Input("url", "pathname"),
)
def load_goal_data(pathname: str):
    """Загружает данные активной цели и историю взносов.

    Callback срабатывает при переходе на /goals.
    Если нет активной цели, показывает empty state.

    Args:
        pathname: Текущий URL

    Returns:
        Tuple[goal_card, contributions_table, goal_id]
    """
    if pathname != "/goals":
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        # Получаем активную цель пользователя
        goals = service.get_all_by_user(user_id=DEFAULT_USER_ID, status=GoalStatus.ACTIVE)

        # Также проверяем PAUSED цели
        if not goals:
            goals = service.get_all_by_user(
                user_id=DEFAULT_USER_ID, status=GoalStatus.PAUSED
            )

        if not goals:
            # Empty state - нет активной/приостановленной цели
            return _build_empty_state(), _build_contributions_table([]), None

        goal = goals[0]  # MVP: одна цель
        goal_data = _goal_to_display_data(goal)

        # Получаем историю взносов
        contributions = service.get_contributions(goal.id, limit=10)
        contrib_data = [
            ContributionDisplayData(
                id=c.id,
                amount=c.amount,
                contribution_date=c.contribution_date,
                description=c.description,
            )
            for c in contributions
        ]

        return (
            _build_goal_card(goal_data),
            _build_contributions_table(contrib_data),
            goal.id,
        )
```

### 3.2 Callbacks для модала создания цели

2. **Добавить `toggle_create_goal_modal()` callback:**

```python
@callback(
    Output("create-goal-modal", "is_open"),
    [
        Input("create-goal-btn", "n_clicks"),
        Input("create-goal-cancel-btn", "n_clicks"),
    ],
    State("create-goal-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_create_goal_modal(create_clicks, cancel_clicks, is_open):
    """Открывает/закрывает модал создания цели.

    Simple callback без Pattern-Matching - guard clauses из ADR-003 не нужны.
    """
    triggered_id = ctx.triggered_id

    if triggered_id == "create-goal-btn":
        return True
    if triggered_id == "create-goal-cancel-btn":
        return False

    return is_open
```

3. **Добавить `create_goal()` callback:**

```python
@callback(
    [
        Output("create-goal-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("current-goal-id", "data", allow_duplicate=True),
        Output("create-goal-name-input", "value"),
        Output("create-goal-amount-input", "value"),
        Output("create-goal-date-picker", "date"),
        Output("goal-error-alert", "children"),
        Output("goal-error-alert", "is_open"),
    ],
    Input("create-goal-submit-btn", "n_clicks"),
    [
        State("create-goal-name-input", "value"),
        State("create-goal-amount-input", "value"),
        State("create-goal-date-picker", "date"),
    ],
    prevent_initial_call=True,
)
def create_goal(n_clicks, name, target_amount, target_date_str):
    """Создает новую накопительную цель."""
    if not n_clicks:
        raise PreventUpdate

    # Валидация на стороне UI
    if not name or not name.strip():
        return (
            True, no_update, no_update, no_update,
            no_update, no_update, no_update,
            "Укажите название цели", True,
        )

    if not target_amount or target_amount <= 0:
        return (
            True, no_update, no_update, no_update,
            no_update, no_update, no_update,
            "Укажите положительную сумму", True,
        )

    # Парсим дату
    target_date = parse_date_safe(target_date_str)
    if not target_date:
        return (
            True, no_update, no_update, no_update,
            no_update, no_update, no_update,
            "Укажите дату достижения цели", True,
        )

    try:
        with get_db_session() as session:
            service = GoalService(session)
            goal = service.create_goal(
                user_id=DEFAULT_USER_ID,
                name=name.strip(),
                target_amount=Decimal(str(target_amount)),
                target_date=target_date,
            )
            session.commit()

            goal_data = _goal_to_display_data(goal)
            logger.info(f"Создана цель: {goal.name} (id={goal.id})")

            # Успех: закрываем модал, очищаем форму, обновляем карточку
            min_date = (date.today() + timedelta(days=MIN_GOAL_DAYS)).isoformat()
            return (
                False,  # close modal
                _build_goal_card(goal_data),
                _build_contributions_table([]),  # нет взносов
                goal.id,
                "",  # clear name
                None,  # clear amount
                min_date,  # reset date
                "",
                False,
            )

    except ValidationError as e:
        logger.warning(f"Ошибка создания цели: {e}")
        return (
            True, no_update, no_update, no_update,
            no_update, no_update, no_update,
            str(e), True,
        )
```

### 3.3 Callbacks для модала взноса

4. **Добавить `toggle_contribution_modal()` callback:**

```python
@callback(
    Output("contribution-modal", "is_open"),
    [
        Input("add-contribution-btn", "n_clicks"),
        Input("contribution-cancel-btn", "n_clicks"),
    ],
    State("contribution-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_contribution_modal(add_clicks, cancel_clicks, is_open):
    """Открывает/закрывает модал добавления взноса."""
    triggered_id = ctx.triggered_id

    if triggered_id == "add-contribution-btn":
        return True
    if triggered_id == "contribution-cancel-btn":
        return False

    return is_open
```

5. **Добавить `add_contribution()` callback:**

```python
@callback(
    [
        Output("contribution-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("contribution-amount-input", "value"),
        Output("contribution-date-picker", "date"),
        Output("contribution-description-input", "value"),
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("contribution-submit-btn", "n_clicks"),
    [
        State("current-goal-id", "data"),
        State("contribution-amount-input", "value"),
        State("contribution-date-picker", "date"),
        State("contribution-description-input", "value"),
    ],
    prevent_initial_call=True,
)
def add_contribution(n_clicks, goal_id, amount, date_str, description):
    """Добавляет взнос в цель."""
    if not n_clicks or not goal_id:
        raise PreventUpdate

    if not amount or amount <= 0:
        return (
            True, no_update, no_update,
            no_update, no_update, no_update,
            "Укажите положительную сумму", True,
        )

    contribution_date = parse_date_safe(date_str)

    try:
        with get_db_session() as session:
            service = GoalService(session)
            goal = service.add_contribution(
                goal_id=goal_id,
                amount=Decimal(str(amount)),
                contribution_date=contribution_date,
                description=description.strip() if description else None,
            )
            session.commit()

            goal_data = _goal_to_display_data(goal)

            # Получаем обновленную историю взносов
            contributions = service.get_contributions(goal.id, limit=10)
            contrib_data = [
                ContributionDisplayData(
                    id=c.id,
                    amount=c.amount,
                    contribution_date=c.contribution_date,
                    description=c.description,
                )
                for c in contributions
            ]

            logger.info(f"Добавлен взнос {amount} в цель {goal_id}")

            return (
                False,  # close modal
                _build_goal_card(goal_data),
                _build_contributions_table(contrib_data),
                None,  # clear amount
                date.today().isoformat(),  # reset date
                "",  # clear description
                "",
                False,
            )

    except ValidationError as e:
        logger.warning(f"Ошибка добавления взноса: {e}")
        return (
            True, no_update, no_update,
            no_update, no_update, no_update,
            str(e), True,
        )
```

### 3.4 Callbacks для редактирования цели

6. **Добавить `toggle_edit_modal()` callback:**

```python
@callback(
    [
        Output("edit-goal-modal", "is_open"),
        Output("edit-goal-name-input", "value"),
        Output("edit-goal-amount-input", "value"),
        Output("edit-goal-date-picker", "date"),
    ],
    [
        Input("edit-goal-btn", "n_clicks"),
        Input("edit-goal-cancel-btn", "n_clicks"),
    ],
    State("current-goal-id", "data"),
    State("edit-goal-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_edit_modal(edit_clicks, cancel_clicks, goal_id, is_open):
    """Открывает/закрывает модал редактирования с загрузкой данных.

    Simple callback - goal_id берем из dcc.Store, не нужен Pattern-Matching.
    При открытии загружаем актуальные данные цели из БД.
    """
    triggered_id = ctx.triggered_id

    if triggered_id == "edit-goal-cancel-btn":
        return False, no_update, no_update, no_update

    if triggered_id == "edit-goal-btn":
        if not goal_id:
            raise PreventUpdate

        with get_db_session() as session:
            service = GoalService(session)
            goal = service.get_by_id(goal_id)

            if not goal:
                raise PreventUpdate

            return (
                True,
                goal.name,
                float(goal.target_amount),
                goal.target_date.isoformat(),
            )

    raise PreventUpdate
```

7. **Добавить `update_goal()` callback:**

```python
@callback(
    [
        Output("edit-goal-modal", "is_open", allow_duplicate=True),
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("goal-error-alert", "children", allow_duplicate=True),
        Output("goal-error-alert", "is_open", allow_duplicate=True),
    ],
    Input("edit-goal-submit-btn", "n_clicks"),
    [
        State("current-goal-id", "data"),
        State("edit-goal-name-input", "value"),
        State("edit-goal-amount-input", "value"),
        State("edit-goal-date-picker", "date"),
    ],
    prevent_initial_call=True,
)
def update_goal(n_clicks, goal_id, name, target_amount, target_date_str):
    """Обновляет параметры цели."""
    if not n_clicks or not goal_id:
        raise PreventUpdate

    target_date = parse_date_safe(target_date_str)

    try:
        with get_db_session() as session:
            service = GoalService(session)
            goal = service.update_goal(
                goal_id=goal_id,
                name=name.strip() if name else None,
                target_amount=Decimal(str(target_amount)) if target_amount else None,
                target_date=target_date,
            )
            session.commit()

            goal_data = _goal_to_display_data(goal)
            logger.info(f"Обновлена цель {goal_id}")

            return False, _build_goal_card(goal_data), "", False

    except ValidationError as e:
        logger.warning(f"Ошибка обновления цели: {e}")
        return True, no_update, str(e), True
```

### 3.5 Callbacks для удаления цели

8. **Добавить `request_delete_goal()` callback:**

```python
@callback(
    Output("confirm-delete-goal", "displayed"),
    Input("delete-goal-btn", "n_clicks"),
    State("current-goal-id", "data"),
    prevent_initial_call=True,
)
def request_delete_goal(n_clicks, goal_id):
    """Открывает диалог подтверждения удаления.

    Использует dcc.ConfirmDialog - нативный браузерный диалог.
    """
    if not n_clicks or not goal_id:
        raise PreventUpdate

    return True
```

9. **Добавить `confirm_delete_goal()` callback:**

```python
@callback(
    [
        Output("goal-card-container", "children", allow_duplicate=True),
        Output("contributions-table-container", "children", allow_duplicate=True),
        Output("current-goal-id", "data", allow_duplicate=True),
    ],
    Input("confirm-delete-goal", "submit_n_clicks"),
    State("current-goal-id", "data"),
    prevent_initial_call=True,
)
def confirm_delete_goal(submit_clicks, goal_id):
    """Удаляет цель после подтверждения.

    Callback срабатывает при клике "OK" в ConfirmDialog.
    """
    if not submit_clicks or not goal_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        deleted = service.delete_goal(goal_id)
        session.commit()

        if not deleted:
            raise PreventUpdate

        logger.info(f"Удалена цель {goal_id}")

        # Показываем empty state
        return _build_empty_state(), _build_contributions_table([]), None
```

### 3.6 Callback для смены статуса

10. **Добавить `toggle_goal_status()` callback:**

```python
@callback(
    Output("goal-card-container", "children", allow_duplicate=True),
    Input("toggle-status-btn", "n_clicks"),
    State("current-goal-id", "data"),
    prevent_initial_call=True,
)
def toggle_goal_status(n_clicks, goal_id):
    """Переключает статус цели ACTIVE <-> PAUSED.

    Бизнес-правила:
    - ACTIVE -> PAUSED: всегда разрешено
    - PAUSED -> ACTIVE: разрешено (в MVP нет других активных целей)
    - COMPLETED -> любой: запрещено (возврат из COMPLETED не поддерживается)
    """
    if not n_clicks or not goal_id:
        raise PreventUpdate

    with get_db_session() as session:
        service = GoalService(session)
        goal = service.get_by_id(goal_id)

        if not goal:
            raise PreventUpdate

        # Бизнес-правила переключения статуса
        if goal.status == GoalStatus.COMPLETED:
            # Нельзя менять статус завершенной цели
            raise PreventUpdate

        # Определяем новый статус
        new_status = (
            GoalStatus.PAUSED
            if goal.status == GoalStatus.ACTIVE
            else GoalStatus.ACTIVE
        )

        updated_goal = service.update_goal(goal_id, status=new_status)
        session.commit()

        goal_data = _goal_to_display_data(updated_goal)
        logger.info(f"Статус цели {goal_id} изменен на {new_status.value}")

        return _build_goal_card(goal_data)
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно добавляй callbacks в goals.py после build-функций.
2.  **Верификация:**
    - `black app/components/goals.py`
    - `flake8 app/components/goals.py`
    - Проверка импорта: `python -c "from app.components.goals import create_goals_layout; print('OK')"`
3.  **Фиксация:**
    - **Добавь запись в `log.md`**
    - **Обнови `context.md`**: `Current Step` = 4
4.  **Сделай коммит:** `git commit -m "feat(goals): add all callbacks for goals CRUD [protocol-0004/03]"`. Push.
5.  **Отчет пользователю.**
