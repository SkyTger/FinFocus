# Шаг 6: UI — визуализация и редактирование recurring

## Briefing
- **Цель:** Добавить визуализацию recurring операций в календаре (иконки). Реализовать wizard "изменить экземпляр vs изменить серию" при редактировании.
- **Ключевые файлы:**
  - `app/components/calendar.py` (изменить)
  - `app/components/transactions.py` (изменить)
  - `app/assets/calendar.css` (изменить)
- **Additional info:**
  - Виртуальные recurring: иконка `bi-arrow-repeat`
  - Exceptions: иконка `bi-arrow-repeat` + `bi-pencil`
  - Skipped: иконка `bi-arrow-repeat` с opacity 0.5
  - При редактировании recurring — показать диалог выбора

## Sub-tasks

### 1. Обновить календарь для отображения recurring

В `app/components/calendar.py` модифицировать функцию построения ячейки дня:

```python
def build_day_cell(day_date: date, transactions: list[TransactionInfo], balance: Decimal):
    """Строит ячейку дня календаря с recurring индикаторами."""

    transaction_items = []
    for txn in transactions:
        # Определяем иконки
        icons = []

        if txn["is_recurring"]:
            recurring_class = "recurring-indicator"
            if txn.get("is_skipped"):
                recurring_class += " skipped"

            icons.append(html.I(
                className=f"bi bi-arrow-repeat {recurring_class}",
                title="Повторяющаяся операция"
            ))

            if txn["is_exception"]:
                icons.append(html.I(
                    className="bi bi-pencil-fill exception-indicator",
                    title="Изменённый экземпляр"
                ))

        # Сумма с иконками
        amount_class = "text-success" if txn["transaction_type"] == "income" else "text-danger"
        transaction_items.append(
            html.Div(
                className="calendar-transaction",
                children=[
                    html.Span(icons, className="transaction-icons"),
                    html.Span(
                        f"{'+' if txn['transaction_type'] == 'income' else '-'}"
                        f"{txn['amount']}",
                        className=amount_class
                    ),
                ],
                # Добавляем data-атрибуты для редактирования
                **{
                    "data-id": txn.get("id"),
                    "data-template-id": txn.get("template_id"),
                    "data-is-virtual": str(txn["is_virtual"]).lower(),
                    "data-date": txn["date"],
                }
            )
        )

    # ... остальная логика ячейки ...
```

### 2. Добавить CSS стили для recurring

В `app/assets/calendar.css`:

```css
/* Recurring indicators */
.recurring-indicator {
    color: #28a745;
    font-size: 0.75rem;
    margin-right: 4px;
}

.recurring-indicator.skipped {
    opacity: 0.4;
    text-decoration: line-through;
}

.exception-indicator {
    color: #fd7e14;
    font-size: 0.65rem;
    margin-left: 2px;
}

.transaction-icons {
    display: inline-flex;
    align-items: center;
    margin-right: 4px;
}

.calendar-transaction {
    display: flex;
    align-items: center;
    padding: 2px 4px;
    border-radius: 4px;
    margin-bottom: 2px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.calendar-transaction:hover {
    background-color: rgba(0, 0, 0, 0.05);
}

/* Virtual transaction styling */
.calendar-transaction[data-is-virtual="true"] {
    border-left: 2px solid #28a745;
    padding-left: 6px;
}
```

### 3. Создать диалог выбора "экземпляр vs серия"

В `app/components/transactions.py` добавить новый модал:

```python
# Модал выбора scope редактирования
recurring_edit_scope_modal = dbc.Modal(
    id="recurring-edit-scope-modal",
    is_open=False,
    centered=True,
    children=[
        dbc.ModalHeader(dbc.ModalTitle("Изменить повторяющуюся операцию")),
        dbc.ModalBody([
            html.P("Выберите, что вы хотите изменить:"),
            dbc.RadioItems(
                id="recurring-edit-scope",
                options=[
                    {
                        "label": "Только этот экземпляр",
                        "value": "instance",
                    },
                    {
                        "label": "Этот и все будущие",
                        "value": "future",
                    },
                    {
                        "label": "Всю серию (все экземпляры)",
                        "value": "all",
                    },
                ],
                value="instance",
                className="mb-3",
            ),
            html.P(
                "Примечание: изменение всей серии удалит все существующие изменения.",
                className="text-muted small"
            ),
        ]),
        dbc.ModalFooter([
            dbc.Button(
                "Отмена",
                id="recurring-edit-cancel",
                color="secondary",
                outline=True,
            ),
            dbc.Button(
                "Продолжить",
                id="recurring-edit-continue",
                color="primary",
            ),
        ]),
    ],
)

# Store для хранения контекста редактирования
recurring_edit_context = dcc.Store(
    id="recurring-edit-context",
    data=None,  # {template_id, instance_date, scope}
)
```

### 4. Добавить callback для открытия scope диалога

```python
@callback(
    [
        Output("recurring-edit-scope-modal", "is_open"),
        Output("recurring-edit-context", "data"),
    ],
    [
        Input({"type": "edit-btn", "index": ALL}, "n_clicks"),
    ],
    [
        State({"type": "edit-btn", "index": ALL}, "id"),
        State("transactions-data", "data"),  # Данные о транзакциях
    ],
    prevent_initial_call=True,
)
def handle_edit_click(n_clicks_list, ids, transactions_data):
    """Обрабатывает клик на редактирование.

    Если транзакция recurring — показывает диалог выбора scope.
    Иначе — открывает обычный edit modal.
    """
    # Guard clause для Pattern-Matching
    if ctx.triggered[0].get('value') is None:
        raise PreventUpdate

    triggered_id = ctx.triggered_id
    if not triggered_id or not triggered_id.get("index"):
        raise PreventUpdate

    transaction_id = triggered_id["index"]

    # Найти транзакцию в данных
    transaction = next(
        (t for t in transactions_data if t["id"] == transaction_id),
        None
    )

    if not transaction:
        raise PreventUpdate

    # Если recurring — показать диалог scope
    if transaction.get("is_recurring") or transaction.get("recurring_parent_id"):
        return (
            True,  # Открыть scope modal
            {
                "transaction_id": transaction_id,
                "template_id": transaction.get("recurring_parent_id") or transaction_id,
                "instance_date": transaction.get("transaction_date"),
                "is_template": transaction.get("is_recurring", False),
            }
        )

    # Обычная транзакция — открыть edit modal напрямую
    # (логика обычного редактирования)
    return no_update, no_update
```

### 5. Добавить callback для обработки выбора scope

```python
@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("recurring-edit-scope-modal", "is_open", allow_duplicate=True),
        # ... другие outputs для заполнения edit формы ...
    ],
    Input("recurring-edit-continue", "n_clicks"),
    [
        State("recurring-edit-scope", "value"),
        State("recurring-edit-context", "data"),
    ],
    prevent_initial_call=True,
)
def process_recurring_edit_scope(n_clicks, scope, context):
    """Обрабатывает выбор scope редактирования."""
    if not n_clicks or not context:
        raise PreventUpdate

    template_id = context["template_id"]
    instance_date = context["instance_date"]

    if scope == "instance":
        # Создаем/редактируем exception для этой даты
        # Открываем edit modal с данными экземпляра
        pass

    elif scope == "future":
        # Останавливаем текущий шаблон с instance_date - 1
        # Создаем новый шаблон начиная с instance_date
        pass

    elif scope == "all":
        # Редактируем сам шаблон
        # Предупреждаем об удалении всех exceptions
        pass

    return (
        True,  # Открыть edit modal
        False,  # Закрыть scope modal
        # ... заполненные данные формы ...
    )
```

### 6. Добавить функционал пропуска экземпляра

Добавить кнопку "Пропустить" в edit modal для recurring:

```python
# В edit modal footer
dbc.Button(
    "Пропустить",
    id="edit-skip-instance",
    color="warning",
    outline=True,
    style={"display": "none"},  # Показывается только для recurring
),
```

Callback:

```python
@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("transactions-table", "children", allow_duplicate=True),
    ],
    Input("edit-skip-instance", "n_clicks"),
    [
        State("recurring-edit-context", "data"),
    ],
    prevent_initial_call=True,
)
def skip_recurring_instance(n_clicks, context):
    """Пропускает экземпляр recurring операции."""
    if not n_clicks or not context:
        raise PreventUpdate

    with get_db_session() as session:
        recurring_service = RecurringService(session)
        recurring_service.skip_instance(
            context["template_id"],
            date.fromisoformat(context["instance_date"])
        )
        session.commit()

    # Обновить таблицу
    return False, build_transactions_table()  # Закрыть modal, обновить таблицу
```

### 7. Интегрировать с календарем

Обновить calendar.py для использования `get_all_transactions_for_period()`:

```python
def load_calendar_data(user_id: int, year: int, month: int):
    """Загружает данные для календаря включая recurring."""
    with get_db_session() as session:
        calendar_service = CalendarService(session)

        # Получить период
        first_day = date(year, month, 1)
        _, last_day_num = monthrange(year, month)
        last_day = date(year, month, last_day_num)

        # Получить все транзакции включая recurring
        transactions_by_date = calendar_service.get_all_transactions_for_period(
            user_id, first_day, last_day, include_recurring=True
        )

        # Рассчитать балансы
        balances = calendar_service.calculate_daily_balances(
            user_id, year, month, include_recurring=True
        )

        return transactions_by_date, balances
```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-7.
2. **Верификация:** После завершения ВСЕХ подзадач:
   - `black app/components/*.py`
   - `flake8 app/components/*.py`
   - Запусти приложение и вручную протестируй:
     - Recurring операции отображаются с иконками в календаре
     - При клике на recurring — появляется диалог scope
     - "Только этот экземпляр" создает exception
     - "Пропустить" помечает экземпляр как is_skipped
3. **Фиксация:** После успешной верификации:
   - **Добавь запись в `log.md`**: Опиши UI/UX решения.
   - **Обнови `context.md`**: Увеличь `Current Step` на 1.
   - Проверь ветку main.
4. **Сделай коммит**: `git add . && git commit -m "feat(ui): add recurring visualization and edit wizard [protocol-0005/06]"`. Сделай пуш.
5. **Отчет пользователю** по установленному формату.
