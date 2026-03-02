# Шаг 4: Transactions UI — Chips

## Briefing
- **Цель:** Добавить быстрые кнопки категорий (chips) для операций без категории на странице /transactions.
- **Ключевые файлы:**
  - `app/components/transactions.py` (модифицировать) — chips row в таблице, callback
  - `app/assets/transactions.css` (создать или модифицировать) — стили chips
- **Additional info:**
  - Chips показываются ТОЛЬКО для реальных транзакций (is_recurring=False) без категории
  - Virtual recurring (из календаря) в таблице транзакций НЕ показываются — таблица показывает только реальные записи из БД
  - Клик на chip мгновенно присваивает категорию через update_transaction()
  - Кнопка "..." открывает полный dropdown (через существующий edit modal)
  - Используем dcc.Store для кэширования frequent-categories при загрузке страницы
  - Pattern-Matching ID: `{"type": "tx-chip-btn", "index": tx_id, "category": cat_id}`

## Sub-tasks

### 1. Добавить dcc.Store для frequent categories

**Файл:** `app/components/transactions.py`

В `create_transactions_layout()` добавить:
```python
dcc.Store(id="frequent-categories-store", data=[]),
```

### 2. Добавить callback загрузки frequent categories

```python
@callback(
    Output("frequent-categories-store", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)
def load_frequent_categories(pathname):
    """Загрузка частых категорий при открытии страницы."""
    if pathname != "/transactions":
        raise PreventUpdate

    with get_db_session() as session:
        # Загружаем expense категории (основной use case для chips)
        categories = CategoryService().get_frequent_for_type(
            session, user_id=1, category_type="expense", limit=6
        )
        # Сериализуем для JSON
        return [
            {"id": cat["id"], "name": cat["name"], "icon": cat["icon"]}
            for cat in categories
        ]
```

### 3. Модифицировать _build_transactions_table()

Добавить chips row для операций без категории:

```python
def _build_transactions_table(transactions, frequent_categories):
    """Построение таблицы транзакций."""
    # ... existing header code ...

    rows = []
    for tx in transactions:
        # Определяем отображение категории
        if tx.category_id:
            # Есть категория — показываем как обычно
            category_cell = html.Td(
                f"{tx.category_icon or ''} {tx.category_name}",
                className="align-middle"
            )
        else:
            # Нет категории — показываем chips
            category_cell = html.Td(
                _build_chips_row(tx.id, frequent_categories),
                className="align-middle tx-chips-cell"
            )

        row = html.Tr([
            # ... other cells ...
            category_cell,
            # ... action buttons ...
        ])
        rows.append(row)

    return dbc.Table([header, html.Tbody(rows)], ...)


def _build_chips_row(tx_id: int, frequent_categories: list) -> html.Div:
    """Построение row с chips для быстрого присвоения категории."""
    chips = []

    for cat in frequent_categories[:5]:  # Max 5 chips
        chips.append(
            dbc.Button(
                f"{cat['icon'] or ''} {cat['name'][:10]}",
                id={"type": "tx-chip-btn", "index": tx_id, "category": cat["id"]},
                size="sm",
                color="outline-secondary",
                className="tx-chip-btn me-1 mb-1",
            )
        )

    # Кнопка "..." для открытия edit modal
    chips.append(
        dbc.Button(
            "...",
            id={"type": "tx-chip-more", "index": tx_id},
            size="sm",
            color="outline-secondary",
            className="tx-chip-more",
        )
    )

    return html.Div(chips, className="tx-chips")
```

### 4. Добавить callback для клика на chip

```python
@callback(
    Output("global-transaction-trigger", "data", allow_duplicate=True),
    Input({"type": "tx-chip-btn", "index": ALL, "category": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def apply_chip_category(n_clicks_list):
    """Применение категории при клике на chip."""
    # Guard: проверка реального клика
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id
    if not triggered_id:
        raise PreventUpdate

    tx_id = triggered_id["index"]
    category_id = triggered_id["category"]

    with get_db_session() as session:
        TransactionService().update_transaction(
            session,
            transaction_id=tx_id,
            data={"category_id": category_id},
        )
        session.commit()

    # Trigger refresh
    return {"timestamp": datetime.now().isoformat(), "source": "chips"}
```

### 5. Добавить callback для кнопки "..."

```python
@callback(
    Output("edit-modal", "is_open", allow_duplicate=True),
    Output("edit-transaction-id", "data", allow_duplicate=True),
    Output("modal-source", "data", allow_duplicate=True),
    Input({"type": "tx-chip-more", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_edit_from_chip_more(n_clicks_list):
    """Открытие edit modal при клике на '...'."""
    if ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id
    if not triggered_id:
        raise PreventUpdate

    tx_id = triggered_id["index"]
    return True, tx_id, "transactions"
```

### 6. Модифицировать refresh callback для обновления таблицы

Убедиться что `refresh_table_after_crud()` также получает frequent_categories из Store.

### 7. Добавить CSS стили

**Файл:** `app/assets/transactions.css` (создать если не существует)

```css
/* === Chips для категоризации === */
.tx-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}

.tx-chip-btn {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 12px;
    white-space: nowrap;
}

.tx-chip-btn:hover {
    background-color: var(--bs-success);
    border-color: var(--bs-success);
    color: white;
}

.tx-chip-more {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 12px;
}

.tx-chips-cell {
    min-width: 200px;
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
    - **Обнови `context.md`**: Current Step = 5
    - Проверь ветку main

4.  **Сделай коммит:**
    ```bash
    git add app/components/transactions.py app/assets/transactions.css .protocols/
    git commit -m "feat(ui): add category chips for quick categorization [protocol-0010/04]"
    git push
    ```

5.  **Отчет пользователю** в установленном формате.
