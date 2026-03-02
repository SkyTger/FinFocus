# Шаг 3: Устранение дублирования — _build_transactions_table

## Briefing
- **Цель:** Устранить ~200 строк дублирующегося кода в transactions.py. Вынести формирование таблицы в отдельную функцию `_build_transactions_table()`. Рефакторинг callbacks для использования `get_db_session()`.
- **Ключевые файлы:**
  - `app/components/transactions.py` (модифицировать)
- **Additional info:**
  - Код формирования таблицы повторяется в 5 местах: load_transactions(), create_transaction(), update_transaction(), delete_transaction()
  - После рефакторинга callbacks должны использовать context manager `get_db_session()`
  - Добавить логирование операций
  - Убрать импорты `create_database_engine`, `get_session` — заменить на `get_db_session`

## Sub-tasks

### 1. Создать функцию _build_transactions_table()

Добавить в начало файла (после импортов и helper-функций format_amount, format_date):

```python
def _build_transactions_table(transactions: list) -> list:
    """Формирует HTML таблицу транзакций.

    Args:
        transactions: Список объектов Transaction

    Returns:
        list: [thead, tbody] для dbc.Table
    """
    # Заголовок таблицы
    table_header = html.Thead([
        html.Tr([
            html.Th("Дата"),
            html.Th("Тип"),
            html.Th("Сумма", className="text-end"),
            html.Th("Описание"),
            html.Th("Действия", className="text-end")
        ])
    ])

    # Пустая таблица
    if not transactions:
        return [
            table_header,
            html.Tbody([
                html.Tr([
                    html.Td("Нет операций", colSpan=5, className="text-center text-muted")
                ])
            ])
        ]

    # Строки таблицы
    table_rows = []
    for tx in transactions:
        # Определяем стиль для типа операции
        if tx.transaction_type == TransactionType.INCOME:
            type_badge = dbc.Badge("Доход", color="success", className="rounded-pill")
            amount_class = "text-success fw-bold text-end"
            amount_prefix = "+"
        else:
            type_badge = dbc.Badge("Расход", color="danger", className="rounded-pill")
            amount_class = "text-danger fw-bold text-end"
            amount_prefix = "-"

        row = html.Tr([
            html.Td(format_date(tx.transaction_date)),
            html.Td(type_badge),
            html.Td(f"{amount_prefix}{format_amount(tx.amount)}", className=amount_class),
            html.Td(tx.description or "-", className="text-muted"),
            html.Td([
                dbc.ButtonGroup([
                    dbc.Button(
                        html.I(className="bi bi-pencil"),
                        id={"type": "edit-btn", "index": tx.id},
                        color="secondary",
                        size="sm",
                        outline=True,
                        className="me-1"
                    ),
                    dbc.Button(
                        html.I(className="bi bi-trash"),
                        id={"type": "delete-btn", "index": tx.id},
                        color="danger",
                        size="sm",
                        outline=True
                    )
                ])
            ], className="text-end")
        ])
        table_rows.append(row)

    return [table_header, html.Tbody(table_rows)]
```

### 2. Обновить импорты

Заменить:
```python
from models.database import get_session, create_database_engine, TransactionType
from services.transaction_service import TransactionService, ValidationError
```

На:
```python
from app.core import get_db_session, ValidationError
from app.models.database import TransactionType
from app.services import TransactionService
from loguru import logger
```

### 3. Рефакторинг load_transactions()

```python
@callback(
    Output("transactions-table", "children"),
    Input("url", "pathname")
)
def load_transactions(pathname):
    """Загружает список операций из БД."""
    if pathname != "/transactions":
        raise PreventUpdate

    with get_db_session() as session:
        service = TransactionService(session)
        transactions = service.get_all_by_user(user_id=1)
        logger.debug(f"Загружено {len(transactions)} транзакций")
        return _build_transactions_table(transactions)
```

### 4. Рефакторинг create_transaction()

```python
@callback(
    [Output("create-modal", "is_open", allow_duplicate=True),
     Output("transactions-table", "children", allow_duplicate=True),
     Output("create-amount-input", "value"),
     Output("create-type-select", "value"),
     Output("create-date-picker", "date"),
     Output("create-description-input", "value")],
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

    try:
        transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка парсинга даты: {date_str}")
        raise PreventUpdate

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
            # Загружаем обновленный список
            transactions = service.get_all_by_user(user_id=1)
            updated_table = _build_transactions_table(transactions)

        # Закрываем модал и очищаем форму
        return False, updated_table, None, "EXPENSE", date.today().isoformat(), ""

    except ValidationError as e:
        logger.warning(f"Ошибка валидации при создании: {e}")
        raise PreventUpdate
```

### 5. Рефакторинг open_edit_modal()

Заменить создание engine/session на `get_db_session()`:
```python
# Было:
# engine = create_database_engine()
# session = get_session(engine)
# try:
#     ...
# finally:
#     session.close()

# Стало:
with get_db_session() as session:
    service = TransactionService(session)
    tx = service.get_by_id(transaction_id)
    ...
```

### 6. Рефакторинг update_transaction()

Аналогично — заменить на `get_db_session()`, использовать `_build_transactions_table()`.

### 7. Рефакторинг delete_transaction()

Аналогично — заменить на `get_db_session()`, использовать `_build_transactions_table()`.

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 1-7.
2.  **Верификация:**
    - `python -m py_compile app/components/transactions.py`
    - `python run.py`
    - Открыть http://localhost:8050/transactions
    - Проверить: **создание** новой операции
    - Проверить: **редактирование** операции (клик на карандаш)
    - Проверить: **удаление** операции (клик на корзину)
    - Проверить логи в консоли и файле
3.  **Фиксация:**
    - Добавь запись в `log.md` с указанием количества удалённых строк
    - Обнови `context.md`: `Current Step` → 4
    - Проверь ветку main
4.  **Коммит**: `git add . && git commit -m "refactor(transactions): extract _build_transactions_table, use get_db_session [protocol-0001/03]"`. Push.
5.  **Отчет пользователю** в установленном формате.
