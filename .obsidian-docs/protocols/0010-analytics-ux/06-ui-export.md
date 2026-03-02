# Шаг 6: Transactions UI — CSV Export

## Briefing
- **Цель:** Добавить кнопку экспорта и dcc.Download для скачивания CSV файла транзакций.
- **Ключевые файлы:**
  - `app/components/transactions.py` (модифицировать) — кнопка экспорта, callback
- **Additional info:**
  - Кнопка "Экспорт" рядом с кнопкой "Добавить операцию"
  - dcc.Download для скачивания файла
  - Экспорт с учетом текущих фильтров (date range, category, uncategorized_only)
  - Filename: transactions_YYYY-MM-DD.csv

## Sub-tasks

### 1. Добавить dcc.Download компонент

**Файл:** `app/components/transactions.py`

В `create_transactions_layout()` добавить:
```python
dcc.Download(id="csv-download"),
```

### 2. Добавить кнопку экспорта в header

Найти место где находится кнопка "Добавить операцию" и добавить рядом:

```python
# Buttons row
html.Div([
    dbc.Button(
        [html.I(className="bi bi-plus-lg me-1"), "Добавить операцию"],
        id="add-transaction-btn",
        color="success",
        className="me-2",
    ),
    dbc.Button(
        [html.I(className="bi bi-download me-1"), "Экспорт"],
        id="export-csv-btn",
        color="outline-secondary",
    ),
], className="mb-3"),
```

### 3. Добавить callback для экспорта

```python
from datetime import datetime


@callback(
    Output("csv-download", "data"),
    Input("export-csv-btn", "n_clicks"),
    State("filter-date-start", "date"),  # Если есть фильтры
    State("filter-date-end", "date"),
    State("filter-category", "value"),
    State("filter-uncategorized", "value"),
    prevent_initial_call=True,
)
def trigger_export(n_clicks, start_date, end_date, category_id, uncategorized_only):
    """Генерация и скачивание CSV файла."""
    if not n_clicks:
        raise PreventUpdate

    # Parse dates if provided
    from datetime import date as date_type

    start = None
    end = None
    if start_date:
        start = date_type.fromisoformat(start_date)
    if end_date:
        end = date_type.fromisoformat(end_date)

    # Generate CSV
    with get_db_session() as session:
        csv_bytes = TransactionService().export_to_csv(
            session,
            user_id=1,
            start_date=start,
            end_date=end,
            category_id=category_id,
            uncategorized_only=bool(uncategorized_only),
        )

    # Generate filename with current date
    filename = f"transactions_{datetime.now().strftime('%Y-%m-%d')}.csv"

    return dcc.send_bytes(csv_bytes, filename)
```

### 4. Обработка случая без фильтров

Если на странице нет компонентов фильтрации, упростить callback:

```python
@callback(
    Output("csv-download", "data"),
    Input("export-csv-btn", "n_clicks"),
    prevent_initial_call=True,
)
def trigger_export(n_clicks):
    """Генерация и скачивание CSV файла (все транзакции)."""
    if not n_clicks:
        raise PreventUpdate

    with get_db_session() as session:
        csv_bytes = TransactionService().export_to_csv(
            session,
            user_id=1,
        )

    filename = f"transactions_{datetime.now().strftime('%Y-%m-%d')}.csv"
    return dcc.send_bytes(csv_bytes, filename)
```

### 5. Добавить импорт dcc.send_bytes

В начале файла убедиться что есть:
```python
from dash import dcc
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи.

2.  **Базовая проверка:**
    ```bash
    source .venv/bin/activate
    python -m py_compile app/components/transactions.py
    ```

3.  **Фиксация:**
    - **Добавь запись в `log.md`**
    - **Обнови `context.md`**: Current Step = 7
    - Проверь ветку main

4.  **Сделай коммит:**
    ```bash
    git add app/components/transactions.py .protocols/
    git commit -m "feat(ui): add CSV export button [protocol-0010/06]"
    git push
    ```

5.  **Отчет пользователю** в установленном формате.
