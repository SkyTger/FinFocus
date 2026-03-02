# Шаг 5: UI — форма создания recurring

## Briefing
- **Цель:** Расширить форму создания операции для поддержки recurring транзакций. Добавить селектор периода повторения и опциональную дату окончания.
- **Ключевые файлы:**
  - `app/components/transactions.py` (изменить)
  - `app/assets/transactions.css` (изменить/создать)
- **Additional info:**
  - Форма создания уже существует (`create-modal`)
  - Нужно добавить: checkbox "Повторять", select периода, date picker окончания
  - Callback `create_transaction()` нужно расширить для записи шаблона

## Sub-tasks

### 1. Добавить UI элементы в create_modal

В `app/components/transactions.py` найти `create_modal` и добавить новые поля:

```python
# После существующих полей формы добавить:

# Checkbox "Повторяющаяся операция"
dbc.Row([
    dbc.Col([
        dbc.Checkbox(
            id="create-is-recurring",
            label="Повторяющаяся операция",
            value=False,
        ),
    ], width=12),
], className="mb-3"),

# Секция recurring (скрыта по умолчанию)
html.Div(
    id="create-recurring-section",
    style={"display": "none"},
    children=[
        # Период повторения
        dbc.Row([
            dbc.Col([
                dbc.Label("Период повторения"),
                dbc.Select(
                    id="create-recurring-period",
                    options=[
                        {"label": "Еженедельно", "value": "weekly"},
                        {"label": "Раз в 2 недели", "value": "biweekly"},
                        {"label": "Ежемесячно", "value": "monthly"},
                        {"label": "Ежеквартально", "value": "quarterly"},
                    ],
                    value="monthly",
                ),
            ], width=6),
            dbc.Col([
                dbc.Label("Дата окончания (опционально)"),
                dbc.Input(
                    id="create-recurring-end-date",
                    type="date",
                    placeholder="Бессрочно",
                ),
            ], width=6),
        ], className="mb-3"),
    ],
),
```

### 2. Добавить callback для toggle recurring section

```python
@callback(
    Output("create-recurring-section", "style"),
    Input("create-is-recurring", "value"),
    prevent_initial_call=True,
)
def toggle_recurring_section(is_recurring: bool):
    """Показывает/скрывает секцию настроек recurring."""
    if is_recurring:
        return {"display": "block"}
    return {"display": "none"}
```

### 3. Модифицировать callback `create_transaction()`

Расширить существующий callback:

**Добавить новые State:**
```python
State("create-is-recurring", "value"),
State("create-recurring-period", "value"),
State("create-recurring-end-date", "value"),
```

**Модифицировать логику:**
```python
def create_transaction(
    n_clicks,
    amount,
    transaction_type,
    transaction_date,
    description,
    is_recurring,  # NEW
    recurring_period,  # NEW
    recurring_end_date,  # NEW
):
    # ... существующая валидация ...

    # Подготовка данных
    transaction_data = {
        "amount": Decimal(str(amount)),
        "transaction_type": TransactionType(transaction_type),
        "transaction_date": date.fromisoformat(transaction_date),
        "description": description or None,
        "is_recurring": is_recurring or False,
    }

    # Если recurring, добавляем поля
    if is_recurring:
        transaction_data["recurring_period"] = recurring_period or "monthly"
        if recurring_end_date:
            transaction_data["recurring_end_date"] = date.fromisoformat(recurring_end_date)

    # ... создание через TransactionService ...
```

### 4. Обновить TransactionService.create_transaction()

Убедиться что TransactionService корректно обрабатывает новые поля:

```python
def create_transaction(
    self,
    session: Session,
    user_id: int,
    data: dict,
) -> Transaction:
    """Создает новую финансовую операцию или шаблон recurring."""
    # ... существующая валидация ...

    # Валидация recurring полей
    if data.get("is_recurring"):
        if not data.get("recurring_period"):
            raise ValidationError("Период повторения обязателен для recurring операций")

        from app.services.recurring_service import VALID_RECURRING_PERIODS
        if data["recurring_period"] not in VALID_RECURRING_PERIODS:
            raise ValidationError(f"Недопустимый период: {data['recurring_period']}")

    # Создание транзакции
    transaction = Transaction(
        user_id=user_id,
        amount=data["amount"],
        transaction_type=data["transaction_type"],
        transaction_date=data["transaction_date"],
        description=data.get("description"),
        is_recurring=data.get("is_recurring", False),
        recurring_period=data.get("recurring_period"),
        recurring_end_date=data.get("recurring_end_date"),
    )

    # ...
```

### 5. Добавить CSS стили

В `app/assets/transactions.css` (создать если не существует):

```css
/* Recurring section */
#create-recurring-section {
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
    margin-top: 10px;
    border-left: 3px solid #28a745;
}

#create-recurring-section .form-label {
    font-weight: 500;
    color: #495057;
}

/* Checkbox styling */
#create-is-recurring {
    font-weight: 500;
}
```

### 6. Добавить reset формы при закрытии модала

Расширить callback `toggle_create_modal()`:

```python
@callback(
    [
        Output("create-modal", "is_open"),
        Output("create-amount", "value"),
        Output("create-type", "value"),
        Output("create-date", "value"),
        Output("create-description", "value"),
        Output("create-is-recurring", "value"),  # NEW
        Output("create-recurring-period", "value"),  # NEW
        Output("create-recurring-end-date", "value"),  # NEW
    ],
    # ... inputs ...
)
def toggle_create_modal(...):
    # При закрытии сбрасываем все поля
    if not open_modal:
        return (
            False,  # is_open
            "",  # amount
            "expense",  # type
            date.today().isoformat(),  # date
            "",  # description
            False,  # is_recurring
            "monthly",  # recurring_period
            None,  # recurring_end_date
        )
    # ...
```

### 7. Добавить визуальную индикацию в таблице

В функции построения таблицы добавить иконку для recurring:

```python
def build_transaction_row(transaction):
    # ...
    recurring_badge = ""
    if transaction.is_recurring:
        recurring_badge = html.I(
            className="bi bi-arrow-repeat text-success me-2",
            title="Повторяющаяся операция"
        )
    # ...
```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-7.
2. **Верификация:** После завершения ВСЕХ подзадач:
   - `black app/components/transactions.py app/services/transaction_service.py`
   - `flake8 app/components/transactions.py app/services/transaction_service.py`
   - Запусти приложение и вручную протестируй:
     - Создание обычной операции (работает как раньше)
     - Создание recurring операции (появляется в БД с is_recurring=True)
     - Checkbox показывает/скрывает секцию recurring
3. **Фиксация:** После успешной верификации:
   - **Добавь запись в `log.md`**: Опиши UI изменения.
   - **Обнови `context.md`**: Увеличь `Current Step` на 1.
   - Проверь ветку main.
4. **Сделай коммит**: `git add . && git commit -m "feat(ui): add recurring creation form [protocol-0005/05]"`. Сделай пуш.
5. **Отчет пользователю** по установленному формату.
