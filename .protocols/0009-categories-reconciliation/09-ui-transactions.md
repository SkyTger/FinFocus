# Шаг 9: UI Transactions

## Briefing
- **Цель:** Добавить dropdown выбора категории в формы создания/редактирования, колонку с иконкой категории в таблицу, фильтр "Без категории".
- **Ключевые файлы:**
  - `app/components/transactions.py` (модифицировать)
  - `app/assets/transactions.css` (модифицировать при необходимости)
- **Additional info:**
  - Dropdown категорий фильтруется по типу транзакции (income/expense)
  - При смене типа транзакции — обновить список категорий в dropdown
  - Фильтр "Без категории" — checkbox для показа только некатегоризированных
  - Колонка категории показывает иконку + название

## Sub-tasks

### 9.1. Добавить dropdown категорий в форму создания

В layout формы создания добавить dcc.Dropdown для категории:

```python
# После поля transaction_type, перед description
dbc.FormGroup([
    dbc.Label("Категория (опционально)"),
    dcc.Dropdown(
        id="create-category-dropdown",
        placeholder="Выберите категорию",
        clearable=True,
        options=[]  # Заполняется callback'ом
    )
]),
```

### 9.2. Добавить callback для обновления категорий по типу

```python
@callback(
    Output("create-category-dropdown", "options"),
    Input("create-type-dropdown", "value"),
    prevent_initial_call=True
)
def update_category_options(transaction_type: str | None):
    """Обновить список категорий при смене типа транзакции."""
    if not transaction_type:
        return []

    # Guard clause для pattern-matching
    if ctx.triggered[0].get('value') is None:
        raise PreventUpdate

    with get_db_session() as session:
        service = CategoryService(session)
        # Мапим transaction_type на category_type
        category_type = "income" if transaction_type == "income" else "expense"
        options = service.get_for_dropdown(category_type=category_type)

        return [
            {"label": f"{opt['icon']} {opt['label']}", "value": opt["value"]}
            for opt in options
        ]
```

### 9.3. Обновить callback создания транзакции

В callback `create_transaction` добавить получение category_id:

```python
@callback(
    # ... существующие Output ...
    Input("create-category-dropdown", "value"),  # NEW
    # ... остальные Input ...
)
def create_transaction(
    # ... существующие параметры ...
    category_id: int | None,  # NEW
    # ... остальные параметры ...
):
    """Создать новую транзакцию."""
    # ... существующая логика ...

    transaction = service.create_transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=TransactionType(transaction_type),
        transaction_date=transaction_date,
        description=description,
        category_id=category_id,  # NEW
        # ... остальные параметры ...
    )
```

### 9.4. Добавить dropdown категорий в форму редактирования

Аналогично добавить в модал редактирования:

```python
dbc.FormGroup([
    dbc.Label("Категория"),
    dcc.Dropdown(
        id="edit-category-dropdown",
        placeholder="Выберите категорию",
        clearable=True,
        options=[]
    )
]),
```

### 9.5. Обновить callback открытия модала редактирования

При открытии модала загружать текущую категорию и список опций:

```python
@callback(
    # ... существующие Output ...
    Output("edit-category-dropdown", "value"),
    Output("edit-category-dropdown", "options"),
    # ... существующие Input ...
)
def open_edit_modal(...):
    """Открыть модал редактирования с данными транзакции."""
    # ... существующая логика ...

    # Загрузить категории для типа транзакции
    category_type = "income" if transaction.transaction_type == TransactionType.INCOME else "expense"
    category_options = category_service.get_for_dropdown(category_type=category_type)
    dropdown_options = [
        {"label": f"{opt['icon']} {opt['label']}", "value": opt["value"]}
        for opt in category_options
    ]

    return (
        # ... существующие возвраты ...
        transaction.category_id,  # Текущая категория
        dropdown_options,         # Опции для dropdown
    )
```

### 9.6. Добавить колонку категории в таблицу

В функции построения таблицы добавить колонку:

```python
# В заголовках таблицы
html.Th("Категория", className="text-center"),

# В строках таблицы
html.Td(
    [
        html.I(className=f"{tx.category_rel.icon} me-1") if tx.category_rel else None,
        tx.category_rel.name if tx.category_rel else "—"
    ],
    className="text-center"
),
```

### 9.7. Добавить фильтр "Без категории"

В панель фильтров добавить checkbox:

```python
dbc.Checkbox(
    id="filter-no-category",
    label="Без категории",
    value=False,
    className="ms-3"
),
```

### 9.8. Обновить callback загрузки транзакций

Добавить фильтрацию по отсутствию категории:

```python
@callback(
    Output("transactions-table", "children"),
    # ... существующие Input ...
    Input("filter-no-category", "value"),  # NEW
)
def load_transactions(
    # ... существующие параметры ...
    filter_no_category: bool,  # NEW
):
    """Загрузить и отобразить транзакции."""
    # ... существующая логика ...

    # Фильтр по отсутствию категории
    if filter_no_category:
        transactions = [tx for tx in transactions if tx.category_id is None]

    # ... построение таблицы ...
```

### 9.9. Импорты

Добавить необходимые импорты в начало файла:

```python
from app.services import CategoryService
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 9.1-9.9.
2.  **Базовая проверка:**
    - `python -m py_compile app/components/transactions.py`
    - Визуальная проверка: запустить приложение и проверить UI
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 10
    - Проверь ветку main
    - `git add . && git commit -m "feat(ui): add category dropdown and filter to transactions [protocol-0009/09]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
