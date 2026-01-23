# Шаг 10: UI Calendar

## Briefing
- **Цель:** Добавить кнопку "Сверка" и модал сверки на страницу календаря.
- **Ключевые файлы:**
  - `app/components/calendar.py` (модифицировать)
  - `app/assets/calendar.css` (модифицировать при необходимости)
- **Additional info:**
  - Кнопка "Сверка" в header календаря рядом с навигацией
  - Модал показывает: выбор даты, расчетный баланс, поле ввода фактического баланса
  - При подтверждении — создается ADJUSTMENT и обновляется календарь
  - Использовать ReconciliationService для preview и создания корректировки

## Sub-tasks

### 10.1. Добавить кнопку "Сверка" в header

В layout календаря добавить кнопку:

```python
# В header рядом с кнопками навигации
dbc.Button(
    [html.I(className="bi-calculator me-1"), "Сверка"],
    id="open-reconciliation-btn",
    color="outline-secondary",
    size="sm",
    className="ms-auto"
),
```

### 10.2. Создать модал сверки

```python
def create_reconciliation_modal():
    """Создать модал сверки баланса."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Сверка баланса")),
        dbc.ModalBody([
            # Выбор даты
            dbc.FormGroup([
                dbc.Label("Дата сверки"),
                dcc.DatePickerSingle(
                    id="reconciliation-date",
                    date=date.today().isoformat(),
                    display_format="DD.MM.YYYY",
                    first_day_of_week=1
                )
            ], className="mb-3"),

            # Расчетный баланс (readonly)
            dbc.FormGroup([
                dbc.Label("Расчетный баланс"),
                dbc.Input(
                    id="reconciliation-expected",
                    type="text",
                    disabled=True,
                    className="text-end"
                )
            ], className="mb-3"),

            # Фактический баланс (ввод)
            dbc.FormGroup([
                dbc.Label("Фактический баланс"),
                dbc.Input(
                    id="reconciliation-actual",
                    type="number",
                    step="0.01",
                    placeholder="Введите фактический баланс"
                )
            ], className="mb-3"),

            # Preview разницы
            html.Div(id="reconciliation-preview", className="mt-3"),

            # Сообщение об ошибке/успехе
            html.Div(id="reconciliation-message", className="mt-2")
        ]),
        dbc.ModalFooter([
            dbc.Button("Отмена", id="cancel-reconciliation-btn", color="secondary"),
            dbc.Button("Применить", id="apply-reconciliation-btn", color="primary")
        ])
    ],
    id="reconciliation-modal",
    is_open=False,
    centered=True
    )
```

### 10.3. Callback для открытия модала

```python
@callback(
    Output("reconciliation-modal", "is_open"),
    Output("reconciliation-expected", "value"),
    Input("open-reconciliation-btn", "n_clicks"),
    Input("cancel-reconciliation-btn", "n_clicks"),
    State("reconciliation-date", "date"),
    State("reconciliation-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_reconciliation_modal(
    open_clicks: int | None,
    cancel_clicks: int | None,
    selected_date: str | None,
    is_open: bool
):
    """Открыть/закрыть модал сверки."""
    if ctx.triggered[0].get('value') is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    if triggered_id == "cancel-reconciliation-btn":
        return False, ""

    if triggered_id == "open-reconciliation-btn":
        # Получить расчетный баланс на выбранную дату
        target_date = date.fromisoformat(selected_date) if selected_date else date.today()

        with get_db_session() as session:
            service = ReconciliationService(session)
            expected = service.get_expected_balance(user_id=1, target_date=target_date)

        return True, f"{expected:,.2f} ₽"

    return is_open, ""
```

### 10.4. Callback для обновления preview при вводе

```python
@callback(
    Output("reconciliation-preview", "children"),
    Input("reconciliation-actual", "value"),
    State("reconciliation-date", "date"),
    prevent_initial_call=True
)
def update_reconciliation_preview(
    actual_value: float | None,
    selected_date: str | None
):
    """Обновить preview разницы при вводе фактического баланса."""
    if actual_value is None or selected_date is None:
        return ""

    target_date = date.fromisoformat(selected_date)
    actual_balance = Decimal(str(actual_value))

    with get_db_session() as session:
        service = ReconciliationService(session)
        preview = service.calculate_preview(
            user_id=1,
            target_date=target_date,
            actual_balance=actual_balance
        )

    # Стилизация в зависимости от разницы
    diff = Decimal(preview["difference"])
    if diff == Decimal("0"):
        color = "text-success"
        icon = "bi-check-circle"
    elif diff > Decimal("0"):
        color = "text-primary"
        icon = "bi-plus-circle"
    else:
        color = "text-danger"
        icon = "bi-dash-circle"

    return dbc.Alert([
        html.I(className=f"{icon} me-2"),
        html.Strong(f"Разница: {diff:+,.2f} ₽"),
        html.Br(),
        html.Small(preview["explanation"])
    ], color="light", className=f"{color}")
```

### 10.5. Callback для применения сверки

```python
@callback(
    Output("reconciliation-message", "children"),
    Output("reconciliation-modal", "is_open", allow_duplicate=True),
    Output("calendar-refresh-trigger", "data"),  # Триггер обновления календаря
    Input("apply-reconciliation-btn", "n_clicks"),
    State("reconciliation-date", "date"),
    State("reconciliation-actual", "value"),
    prevent_initial_call=True
)
def apply_reconciliation(
    n_clicks: int | None,
    selected_date: str | None,
    actual_value: float | None
):
    """Применить сверку и создать корректировку."""
    if ctx.triggered[0].get('value') is None:
        raise PreventUpdate

    if actual_value is None:
        return dbc.Alert("Введите фактический баланс", color="warning"), True, no_update

    target_date = date.fromisoformat(selected_date)
    actual_balance = Decimal(str(actual_value))

    try:
        with get_db_session() as session:
            service = ReconciliationService(session)
            adjustment = service.create_adjustment(
                user_id=1,
                target_date=target_date,
                actual_balance=actual_balance
            )
            session.commit()

            if adjustment is None:
                return dbc.Alert("Баланс совпадает, корректировка не нужна", color="info"), False, no_update

            return (
                dbc.Alert(f"Корректировка на {adjustment.amount:+,.2f} ₽ создана", color="success"),
                False,  # Закрыть модал
                {"timestamp": datetime.now().isoformat()}  # Триггер обновления
            )

    except ValidationError as e:
        return dbc.Alert(str(e), color="danger"), True, no_update
```

### 10.6. Интегрировать модал в layout

В функции `create_calendar_layout` добавить модал:

```python
def create_calendar_layout(user_id: int = 1):
    """Создать layout страницы календаря."""
    return html.Div([
        # ... существующий layout ...
        create_reconciliation_modal(),  # NEW
    ])
```

### 10.7. Импорты

Добавить необходимые импорты:

```python
from app.services import ReconciliationService
from app.core import ValidationError
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 10.1-10.7.
2.  **Базовая проверка:**
    - `python -m py_compile app/components/calendar.py`
    - Визуальная проверка: запустить приложение, открыть календарь, проверить модал сверки
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 11
    - Проверь ветку main
    - `git add . && git commit -m "feat(ui): add reconciliation modal to calendar [protocol-0009/10]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
