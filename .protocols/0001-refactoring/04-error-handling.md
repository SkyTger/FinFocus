# Шаг 4: Обработка ошибок — Alert для ValidationError

## Briefing
- **Цель:** Добавить отображение ошибок валидации пользователю через dbc.Alert. Реализовать безопасный парсинг дат. Устранить silent error handling.
- **Ключевые файлы:**
  - `app/components/transactions.py` (модифицировать)
- **Additional info:**
  - Сейчас ValidationError приводит к `raise PreventUpdate` — пользователь не понимает что пошло не так
  - Добавим Alert компонент который показывает текст ошибки
  - Создадим helper функцию `parse_date_safe()` для безопасного парсинга дат
  - Alert автоматически закрывается (dismissable)

## Sub-tasks

### 1. Добавить Alert в layout

В функции `create_transactions_layout()` добавить Alert перед таблицей:

```python
def create_transactions_layout():
    """Создает layout страницы управления операциями."""
    return html.Div([
        # Заголовок с описанием
        html.Div([
            # ... существующий код ...
        ], className="d-flex justify-content-between align-items-center mb-4"),

        # Alert для ошибок (ДОБАВИТЬ)
        dbc.Alert(
            id="transaction-error-alert",
            is_open=False,
            color="danger",
            dismissable=True,
            duration=5000,  # Автозакрытие через 5 сек
            className="mb-3"
        ),

        # Таблица операций
        dbc.Card([
            # ... существующий код ...
        ]),

        # ... остальной layout ...
    ])
```

### 2. Создать helper функцию parse_date_safe()

Добавить после существующих helper функций:

```python
def parse_date_safe(date_str: str) -> date | None:
    """Безопасно парсит строку даты.

    Args:
        date_str: Дата в формате YYYY-MM-DD

    Returns:
        date | None: Объект date или None при ошибке
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка парсинга даты '{date_str}': {e}")
        return None
```

### 3. Обновить create_transaction() callback

Добавить Output для Alert и обрабатывать ValidationError:

```python
@callback(
    [Output("create-modal", "is_open", allow_duplicate=True),
     Output("transactions-table", "children", allow_duplicate=True),
     Output("create-amount-input", "value"),
     Output("create-type-select", "value"),
     Output("create-date-picker", "date"),
     Output("create-description-input", "value"),
     Output("transaction-error-alert", "children", allow_duplicate=True),
     Output("transaction-error-alert", "is_open", allow_duplicate=True)],
    Input("create-submit-btn", "n_clicks"),
    [State("create-amount-input", "value"),
     State("create-type-select", "value"),
     State("create-date-picker", "date"),
     State("create-description-input", "value")],
    prevent_initial_call=True
)
def create_transaction(n_clicks, amount, transaction_type, date_str, description):
    """Создает новую транзакцию через TransactionService."""
    if not n_clicks or not amount:
        raise PreventUpdate

    # Безопасный парсинг даты
    transaction_date = parse_date_safe(date_str)
    if not transaction_date:
        return (
            True,  # Модал остаётся открытым
            no_update,
            no_update, no_update, no_update, no_update,
            "Неверный формат даты",
            True  # Показать Alert
        )

    try:
        with get_db_session() as session:
            service = TransactionService(session)
            service.create_transaction(
                user_id=1,
                amount=Decimal(str(amount)),
                transaction_type=TransactionType[transaction_type],
                transaction_date=transaction_date,
                description=description if description else None
            )
            transactions = service.get_all_by_user(user_id=1)
            updated_table = _build_transactions_table(transactions)

        # Успех: закрываем модал, очищаем форму, скрываем Alert
        return (
            False,
            updated_table,
            None, "EXPENSE", date.today().isoformat(), "",
            "",
            False
        )

    except ValidationError as e:
        logger.warning(f"Ошибка валидации: {e}")
        return (
            True,  # Модал остаётся открытым
            no_update,
            no_update, no_update, no_update, no_update,
            str(e),  # Текст ошибки
            True  # Показать Alert
        )
```

### 4. Обновить update_transaction() callback

Аналогично добавить Output для Alert и обработку ошибок:

```python
@callback(
    [Output("edit-modal", "is_open", allow_duplicate=True),
     Output("transactions-table", "children", allow_duplicate=True),
     Output("transaction-error-alert", "children", allow_duplicate=True),
     Output("transaction-error-alert", "is_open", allow_duplicate=True)],
    Input("edit-submit-btn", "n_clicks"),
    [State("edit-transaction-id", "data"),
     State("edit-amount-input", "value"),
     State("edit-type-select", "value"),
     State("edit-date-picker", "date"),
     State("edit-description-input", "value")],
    prevent_initial_call=True
)
def update_transaction(n_clicks, transaction_id, amount, transaction_type, date_str, description):
    """Обновляет транзакцию через TransactionService."""
    if not n_clicks or not transaction_id:
        raise PreventUpdate

    transaction_date = parse_date_safe(date_str)
    if not transaction_date:
        return True, no_update, "Неверный формат даты", True

    try:
        with get_db_session() as session:
            service = TransactionService(session)
            service.update_transaction(
                transaction_id=transaction_id,
                amount=Decimal(str(amount)),
                transaction_type=TransactionType[transaction_type],
                transaction_date=transaction_date,
                description=description if description else None
            )
            transactions = service.get_all_by_user(user_id=1)
            updated_table = _build_transactions_table(transactions)

        return False, updated_table, "", False

    except ValidationError as e:
        logger.warning(f"Ошибка валидации при обновлении: {e}")
        return True, no_update, str(e), True
```

### 5. Добавить импорт no_update

В начале файла добавить:
```python
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, no_update
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 1-5.
2.  **Верификация:**
    - `python -m py_compile app/components/transactions.py`
    - `python run.py`
    - Открыть http://localhost:8050/transactions
    - Проверить: создать операцию с суммой 0 → должен появиться красный Alert "Сумма операции должна быть больше 0"
    - Проверить: создать операцию с датой > 1 год в будущем → должен появиться Alert
    - Проверить: нормальное создание → Alert не появляется
    - Проверить: Alert закрывается автоматически через 5 сек или по кнопке X
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: `Current Step` → 5
    - Проверь ветку main
4.  **Коммит**: `git add . && git commit -m "feat(transactions): add validation error alerts [protocol-0001/04]"`. Push.
5.  **Отчет пользователю** в установленном формате.
