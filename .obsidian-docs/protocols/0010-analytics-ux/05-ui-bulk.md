# Шаг 5: Transactions UI — Bulk Actions

## Briefing
- **Цель:** Добавить multi-select (checkboxes) и bulk actions panel для массового присвоения категорий.
- **Ключевые файлы:**
  - `app/components/transactions.py` (модифицировать) — checkboxes, bulk panel, callbacks
  - `app/assets/transactions.css` (модифицировать) — стили bulk panel
- **Additional info:**
  - Checkbox в каждой строке таблицы (Pattern-Matching ID: `{"type": "tx-checkbox", "index": tx_id}`)
  - dcc.Store для хранения selected IDs (max 100)
  - Bulk panel появляется когда len(selected) > 0
  - Warning если выбрано > 100: "Выберите не более 100 операций"
  - Кнопка "Применить" вызывает bulk_update_category()
  - Кнопка "Снять выбор" очищает selection
  - Checkbox "Выбрать все" в header (выбирает visible uncategorized, max 100)

## Sub-tasks

### 1. Добавить dcc.Store для selected IDs

**Файл:** `app/components/transactions.py`

В `create_transactions_layout()` добавить:
```python
dcc.Store(id="selected-transaction-ids", data=[]),
```

### 2. Добавить checkboxes в таблицу

Модифицировать `_build_transactions_table()`:

```python
def _build_transactions_table(transactions, frequent_categories, selected_ids):
    """Построение таблицы транзакций."""

    # Header с "Выбрать все" checkbox
    header = html.Thead(html.Tr([
        html.Th(
            dbc.Checkbox(
                id="select-all-checkbox",
                className="tx-select-all",
            ),
            style={"width": "40px"}
        ),
        html.Th("Дата"),
        html.Th("Тип"),
        html.Th("Сумма"),
        html.Th("Описание"),
        html.Th("Категория"),
        html.Th("Действия"),
    ]))

    rows = []
    for tx in transactions:
        is_selected = tx.id in selected_ids

        row = html.Tr([
            # Checkbox cell
            html.Td(
                dbc.Checkbox(
                    id={"type": "tx-checkbox", "index": tx.id},
                    value=is_selected,
                    className="tx-checkbox",
                ),
            ),
            # ... other cells (date, type, amount, description) ...
            # Category cell (with chips if uncategorized)
            # ... action buttons ...
        ])
        rows.append(row)

    return dbc.Table([header, html.Tbody(rows)], ...)
```

### 3. Добавить Bulk Actions Panel

В `create_transactions_layout()` после таблицы:

```python
# Bulk Actions Panel (hidden by default)
html.Div(
    id="bulk-actions-panel",
    className="tx-bulk-panel",
    style={"display": "none"},
    children=[
        html.Div([
            # Counter badge
            dbc.Badge(
                id="bulk-count-badge",
                color="primary",
                className="me-2",
            ),
            html.Span("выбрано", className="me-3"),

            # Warning for > 100
            html.Span(
                id="bulk-warning",
                className="text-warning me-3",
                style={"display": "none"},
            ),

            # Category dropdown
            dcc.Dropdown(
                id="bulk-category-dropdown",
                options=[],
                placeholder="Выберите категорию...",
                className="d-inline-block me-2",
                style={"width": "200px"},
            ),

            # Apply button
            dbc.Button(
                "Применить",
                id="bulk-apply-btn",
                color="success",
                size="sm",
                className="me-2",
            ),

            # Clear selection button
            dbc.Button(
                "Снять выбор",
                id="bulk-clear-btn",
                color="secondary",
                outline=True,
                size="sm",
            ),
        ], className="d-flex align-items-center"),
    ],
),
```

### 4. Callback: Toggle individual checkbox

```python
@callback(
    Output("selected-transaction-ids", "data"),
    Input({"type": "tx-checkbox", "index": ALL}, "value"),
    State({"type": "tx-checkbox", "index": ALL}, "id"),
    prevent_initial_call=True,
)
def toggle_checkbox(values, ids):
    """Обновление списка выбранных транзакций."""
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    selected = []
    for checkbox_id, is_checked in zip(ids, values):
        if is_checked:
            selected.append(checkbox_id["index"])

    return selected
```

### 5. Callback: Select all checkbox

```python
@callback(
    Output("selected-transaction-ids", "data", allow_duplicate=True),
    Output("select-all-checkbox", "value"),
    Input("select-all-checkbox", "value"),
    State("transactions-table-data", "data"),  # Need to add this Store
    prevent_initial_call=True,
)
def toggle_select_all(select_all, table_data):
    """Выбор/снятие всех операций (max 100)."""
    if select_all:
        # Выбрать все uncategorized (max 100)
        uncategorized_ids = [
            tx["id"] for tx in table_data
            if tx.get("category_id") is None
        ][:100]
        return uncategorized_ids, len(uncategorized_ids) == len(table_data)
    else:
        return [], False
```

### 6. Callback: Render bulk panel

```python
@callback(
    Output("bulk-actions-panel", "style"),
    Output("bulk-count-badge", "children"),
    Output("bulk-warning", "children"),
    Output("bulk-warning", "style"),
    Output("bulk-apply-btn", "disabled"),
    Output("bulk-category-dropdown", "options"),
    Input("selected-transaction-ids", "data"),
)
def render_bulk_panel(selected_ids):
    """Отображение/скрытие bulk panel."""
    if not selected_ids:
        return {"display": "none"}, "", "", {"display": "none"}, True, []

    count = len(selected_ids)
    show_warning = count > 100
    warning_text = "Максимум 100 операций" if show_warning else ""
    warning_style = {"display": "inline"} if show_warning else {"display": "none"}

    # Load categories for dropdown
    with get_db_session() as session:
        categories = CategoryService().get_for_dropdown(session)
        options = [
            {"label": f"{cat['icon'] or ''} {cat['name']}", "value": cat["id"]}
            for cat in categories
        ]

    return (
        {"display": "block"},
        str(count),
        warning_text,
        warning_style,
        show_warning,  # Disabled if > 100
        options,
    )
```

### 7. Callback: Apply bulk category

```python
@callback(
    Output("global-transaction-trigger", "data", allow_duplicate=True),
    Output("selected-transaction-ids", "data", allow_duplicate=True),
    Input("bulk-apply-btn", "n_clicks"),
    State("selected-transaction-ids", "data"),
    State("bulk-category-dropdown", "value"),
    prevent_initial_call=True,
)
def apply_bulk_category(n_clicks, selected_ids, category_id):
    """Применение категории к выбранным операциям."""
    if not n_clicks or not selected_ids or not category_id:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            TransactionService().bulk_update_category(
                session,
                user_id=1,
                transaction_ids=selected_ids,
                category_id=category_id,
            )
            session.commit()
    except ValidationError as e:
        # TODO: Show error alert
        raise PreventUpdate

    # Trigger refresh and clear selection
    return {"timestamp": datetime.now().isoformat(), "source": "bulk"}, []
```

### 8. Callback: Clear selection

```python
@callback(
    Output("selected-transaction-ids", "data", allow_duplicate=True),
    Input("bulk-clear-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_selection(n_clicks):
    """Очистка выбора."""
    if not n_clicks:
        raise PreventUpdate
    return []
```

### 9. Добавить CSS стили

**Файл:** `app/assets/transactions.css`

```css
/* === Bulk Actions Panel === */
.tx-bulk-panel {
    position: sticky;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #f8f9fa;
    border-top: 1px solid #dee2e6;
    padding: 12px 16px;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
    z-index: 1000;
}

.tx-checkbox {
    margin: 0;
}

.tx-select-all {
    margin: 0;
}

/* Warning text */
.tx-bulk-panel .text-warning {
    font-size: 0.875rem;
}
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
    - **Обнови `context.md`**: Current Step = 6
    - Проверь ветку main

4.  **Сделай коммит:**
    ```bash
    git add app/components/transactions.py app/assets/transactions.css .protocols/
    git commit -m "feat(ui): add bulk actions for mass categorization [protocol-0010/05]"
    git push
    ```

5.  **Отчет пользователю** в установленном формате.
