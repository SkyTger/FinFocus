# Solution v2: DOM Restructure with CSS Checkbox Hack Tooltip

## Обзор решения
Tooltip реализуется как sibling-элемент кликабельной области дня (не вложенный), что полностью решает проблему bubbling click events. Expand/collapse списка операций выполняется через CSS checkbox hack без server round-trip. На мобильных устройствах tooltip отключается через CSS media query.

## Архитектура

### Принципиальные изменения от v1

1. **DOM Restructure** - tooltip как sibling, не child
2. **CSS Checkbox Hack** - expand без callback
3. **Использование TransactionInfo напрямую** - без дублирования TypedDict
4. **is_skipped поле** - добавляется в TransactionInfo и визуализируется

### Компоненты

**1. build_day_cell() - реструктуризация (calendar.py)**
```python
def build_day_cell(...) -> html.Div:
    # Кликабельная область (для create-modal)
    clickable_content = html.Div(
        [day_number, icons, balance],
        id={"type": "calendar-day", "date": day_date.isoformat()},
        n_clicks=0,
        className="calendar-day-content",
    )

    # Tooltip как sibling элемент (НЕ вложен в clickable_content!)
    tooltip = _build_day_tooltip(day_date, balance, transactions) if transactions else None

    # Wrapper без n_clicks
    return html.Div(
        [clickable_content, tooltip],
        className=" ".join(css_classes),
    )
```

**2. _build_day_tooltip() - tooltip builder (calendar.py)**
- Использует TransactionInfo напрямую (без TooltipTransactionItem)
- Добавляет hidden checkbox для expand/collapse
- Limit первых MAX_VISIBLE_TRANSACTIONS операций
- Кнопка "ещё N..." как label для checkbox
- Hidden секция с остальными операциями

**3. _build_tooltip_transaction_row() - строка операции (calendar.py)**
- Pattern-Matching ID: `{"type": "tooltip-txn", "date": ..., "id": ..., "is_virtual": ..., "template_id": ...}`
- Визуализация is_skipped через CSS класс
- Иконка recurring для virtual операций

**4. CSS Checkbox Hack - expand без server**
```css
.tooltip-expand-checkbox {
    display: none;
}
.tooltip-expand-checkbox:checked ~ .tooltip-hidden-txns {
    display: block;
}
.tooltip-expand-checkbox:checked ~ .tooltip-expand-btn {
    display: none;
}
```

**5. TransactionInfo extension (calendar_service.py)**
- Добавить поле `is_skipped: bool` в TransactionInfo TypedDict
- Заполнять его в get_all_transactions_for_period()

### Диаграмма взаимодействия
```
User hovers day cell wrapper (.calendar-day)
        │
        ▼
┌───────────────────┐
│ CSS :hover shows  │  (No server call)
│ .calendar-day-    │
│ tooltip           │
└───────────────────┘
        │
User clicks "ещё N..." (label)
        │
        ▼
┌───────────────────────────┐
│ CSS checkbox toggled      │  (No server call!)
│ :checked ~ .hidden-txns   │
│ Shows full list           │
└───────────────────────────┘
        │
User clicks transaction row (tooltip-txn)
        │
        ▼
┌─────────────────────────────────┐
│ Pattern-Matching callback       │  (Server call)
│ Sets edit-transaction-id Store  │
│ OR recurring-edit-context Store │
│ Opens edit-modal or scope-modal │
└─────────────────────────────────┘
        │
        │ (NO bubbling to calendar-day!)
        │ (tooltip is sibling, not child)
        ▼
┌─────────────────────────────────┐
│ Edit modal opens                │
│ Create modal does NOT open      │
└─────────────────────────────────┘
```

## Файловая структура
```
app/services/calendar_service.py  — MODIFIED: +is_skipped в TransactionInfo
app/components/calendar.py        — MODIFIED: DOM restructure, +tooltip functions, +callback
app/assets/calendar.css           — MODIFIED: +glassmorphism tooltip styles (~180 lines)
tests/test_calendar_tooltip.py    — NEW: unit tests for tooltip functions
```

## Ключевые интерфейсы

```python
# app/services/calendar_service.py - расширенный TransactionInfo
class TransactionInfo(TypedDict):
    """Информация о транзакции для UI календаря."""
    id: int | None
    template_id: int | None
    transaction_type: str
    amount: str
    description: str | None
    date: str
    is_virtual: bool
    is_recurring: bool
    is_exception: bool
    category_id: int | None
    category_name: str | None
    is_skipped: bool  # NEW: пропущена ли операция


# app/components/calendar.py - константы
MAX_VISIBLE_TRANSACTIONS = 5
TOOLTIP_HIDE_DELAY_MS = 150  # Задержка перед скрытием для UX


# app/components/calendar.py - новые функции
def _build_day_tooltip(
    day_date: date,
    balance: Decimal,
    transactions: list[TransactionInfo],
) -> html.Div | None:
    """Создаёт tooltip для дня с операциями.

    Tooltip является sibling-элементом кликабельной области дня,
    не вложенным, что предотвращает конфликт click handlers.

    Args:
        day_date: Дата дня
        balance: Остаток на день
        transactions: Список операций дня

    Returns:
        html.Div с tooltip или None если нет операций
    """
    if not transactions:
        return None

    visible_txns = transactions[:MAX_VISIBLE_TRANSACTIONS]
    hidden_txns = transactions[MAX_VISIBLE_TRANSACTIONS:]

    # Уникальный ID для checkbox hack
    checkbox_id = f"tooltip-expand-{day_date.isoformat()}"

    tooltip_children = [
        # Balance header
        _build_tooltip_balance(balance),
        # Visible transactions
        *[_build_tooltip_transaction_row(txn, day_date) for txn in visible_txns],
    ]

    if hidden_txns:
        # Hidden checkbox (управляет expand через CSS)
        tooltip_children.append(
            dcc.Checklist(
                id=checkbox_id,
                options=[{"label": "", "value": "expanded"}],
                value=[],
                className="tooltip-expand-checkbox",
                inputClassName="tooltip-expand-checkbox-input",
                labelClassName="tooltip-expand-checkbox-label",
            )
        )
        # Label-кнопка "ещё N..."
        tooltip_children.append(
            html.Label(
                f"ещё {len(hidden_txns)}...",
                htmlFor=checkbox_id,
                className="tooltip-expand-btn",
            )
        )
        # Hidden transactions container
        tooltip_children.append(
            html.Div(
                [_build_tooltip_transaction_row(txn, day_date) for txn in hidden_txns],
                className="tooltip-hidden-txns",
            )
        )

    return html.Div(
        tooltip_children,
        className="calendar-day-tooltip",
        role="tooltip",
        **{"aria-label": f"Операции на {day_date.strftime('%d.%m.%Y')}"},
    )


def _build_tooltip_balance(balance: Decimal) -> html.Div:
    """Строит header tooltip с балансом."""
    balance_text, balance_class = format_balance(balance)
    return html.Div(
        f"Остаток: {balance_text} ₽",
        className=f"tooltip-balance {balance_class}",
    )


def _build_tooltip_transaction_row(
    txn: TransactionInfo,
    day_date: date,
) -> html.Div:
    """Строит строку операции внутри tooltip.

    Args:
        txn: Данные операции (TransactionInfo)
        day_date: Дата дня (для ID Pattern-Matching)

    Returns:
        html.Div с кликабельной строкой операции
    """
    # Определяем emoji категории
    category_emoji = "📋"  # default
    if txn.get("category_name"):
        category_emoji = get_category_emoji(txn["category_id"])

    # Формат суммы
    amount = Decimal(txn["amount"])
    if txn["transaction_type"] == "income":
        amount_text = f"+{amount:,.0f}".replace(",", " ")
        amount_class = "income"
    else:
        amount_text = f"-{amount:,.0f}".replace(",", " ")
        amount_class = "expense"

    # Описание
    description = txn.get("description") or txn.get("category_name") or "Операция"

    # CSS классы
    row_classes = ["tooltip-txn-row"]
    if txn.get("is_skipped"):
        row_classes.append("skipped")

    # Иконка recurring
    recurring_icon = None
    if txn.get("is_virtual") or txn.get("is_recurring"):
        recurring_icon = html.Span("🔁", className="tooltip-recurring-icon", title="Повторяющаяся")

    return html.Div(
        [
            html.Span(category_emoji, className="tooltip-txn-icon"),
            html.Span(description, className="tooltip-txn-desc"),
            recurring_icon,
            html.Span(amount_text, className=f"tooltip-txn-amount {amount_class}"),
        ],
        id={
            "type": "tooltip-txn",
            "date": day_date.isoformat(),
            "id": txn.get("id"),
            "is_virtual": txn.get("is_virtual", False),
            "template_id": txn.get("template_id"),
        },
        n_clicks=0,
        className=" ".join(row_classes),
        role="button",
        **{"aria-label": f"{description}: {amount_text}"},
    )


# Callback для клика по операции в tooltip
@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("edit-transaction-id", "data", allow_duplicate=True),
        Output("recurring-edit-context", "data", allow_duplicate=True),
        Output("recurring-edit-scope-modal", "is_open", allow_duplicate=True),
    ],
    Input({"type": "tooltip-txn", "date": ALL, "id": ALL, "is_virtual": ALL, "template_id": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_edit_from_tooltip(n_clicks_list: list[int | None]):
    """Открывает модал редактирования при клике на операцию в tooltip.

    ADR-003 guard clauses applied.
    """
    triggered_id = ctx.triggered_id

    # Guard #1: triggered_id exists
    if not triggered_id:
        raise PreventUpdate

    # Guard #2: correct type
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != "tooltip-txn":
        raise PreventUpdate

    # Guard #3: real click (not DOM update)
    if not ctx.triggered or ctx.triggered[0].get("value") is None:
        raise PreventUpdate

    # Guard #4: n_clicks > 0
    clicked_idx = None
    for idx, item in enumerate(ctx.inputs_list[0]):
        if item.get("id") == triggered_id:
            clicked_idx = idx
            break

    if clicked_idx is None:
        raise PreventUpdate

    n_clicks = n_clicks_list[clicked_idx]
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    # Extract data from triggered_id
    is_virtual = triggered_id.get("is_virtual", False)
    txn_id = triggered_id.get("id")
    template_id = triggered_id.get("template_id")
    txn_date = triggered_id.get("date")

    if is_virtual:
        # Virtual recurring: open scope modal
        recurring_context = {
            "template_id": template_id,
            "instance_date": txn_date,
            "action": "edit",
        }
        logger.debug(f"Opening recurring scope modal for template {template_id} on {txn_date}")
        return False, no_update, recurring_context, True
    else:
        # Regular or exception: open edit modal directly
        logger.debug(f"Opening edit modal for transaction {txn_id}")
        return True, txn_id, no_update, False
```

## Модель данных

### TransactionInfo (расширенный)
```python
class TransactionInfo(TypedDict):
    """Информация о транзакции для UI календаря."""
    id: int | None
    template_id: int | None
    transaction_type: str  # "income" | "expense" | "transfer" | "adjustment"
    amount: str  # Decimal в строковом формате
    description: str | None
    date: str  # ISO format
    is_virtual: bool  # True для виртуальных recurring
    is_recurring: bool  # True для recurring (виртуальных и exceptions)
    is_exception: bool  # True для exceptions
    category_id: int | None
    category_name: str | None
    is_skipped: bool  # NEW: True для пропущенных recurring экземпляров
```

## CSS Glassmorphism Implementation

```css
/* ==================== CALENDAR DAY TOOLTIP ==================== */

:root {
    --tooltip-hide-delay: 150ms;
}

.calendar-day {
    position: relative;
}

.calendar-day-content {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    cursor: pointer;
}

.calendar-day-tooltip {
    display: none;
    opacity: 0;
    pointer-events: none;

    /* Glassmorphism */
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);

    position: absolute;
    z-index: 1000;
    top: 100%;
    left: 50%;
    transform: translateX(-50%) translateY(8px);
    min-width: 220px;
    max-width: 280px;

    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.4);
    box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.12),
        inset 0 1px 0 rgba(255, 255, 255, 0.5);
    padding: 12px;

    transition:
        opacity 0.2s ease var(--tooltip-hide-delay),
        transform 0.2s ease var(--tooltip-hide-delay);
}

.calendar-day:hover .calendar-day-tooltip {
    display: block;
    opacity: 1;
    pointer-events: auto;
    transform: translateX(-50%) translateY(4px);
    transition-delay: 0s;
}

/* Edge detection */
.calendar-day:nth-child(7n-1) .calendar-day-tooltip,
.calendar-day:nth-child(7n) .calendar-day-tooltip {
    left: auto;
    right: 0;
    transform: translateX(0) translateY(8px);
}

.calendar-day:nth-child(7n-1):hover .calendar-day-tooltip,
.calendar-day:nth-child(7n):hover .calendar-day-tooltip {
    transform: translateX(0) translateY(4px);
}

@supports not (backdrop-filter: blur(12px)) {
    .calendar-day-tooltip {
        background: rgba(255, 255, 255, 0.96);
    }
}

/* Tooltip content */
.tooltip-balance {
    font-weight: 600;
    font-size: 14px;
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.tooltip-txn-row {
    display: flex;
    align-items: center;
    padding: 6px 4px;
    cursor: pointer;
    border-radius: 6px;
    transition: background-color 0.15s ease;
    gap: 4px;
}

.tooltip-txn-row:hover {
    background-color: rgba(40, 167, 69, 0.1);
}

.tooltip-txn-row.skipped {
    opacity: 0.5;
}

.tooltip-txn-row.skipped .tooltip-txn-desc {
    text-decoration: line-through;
}

.tooltip-txn-icon {
    width: 20px;
    font-size: 14px;
    flex-shrink: 0;
    text-align: center;
}

.tooltip-txn-desc {
    flex: 1;
    font-size: 12px;
    color: #495057;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
}

.tooltip-recurring-icon {
    font-size: 10px;
    flex-shrink: 0;
    margin-right: 4px;
}

.tooltip-txn-amount {
    font-size: 12px;
    font-weight: 600;
    flex-shrink: 0;
    white-space: nowrap;
}

.tooltip-txn-amount.income { color: #28a745; }
.tooltip-txn-amount.expense { color: #dc3545; }

/* CSS Checkbox Hack */
.tooltip-expand-checkbox,
.tooltip-expand-checkbox-input,
.tooltip-expand-checkbox-label {
    position: absolute;
    opacity: 0;
    pointer-events: none;
    height: 0;
    width: 0;
}

.tooltip-expand-btn {
    display: block;
    font-size: 11px;
    color: #6c757d;
    cursor: pointer;
    padding: 6px 0 2px;
    text-align: center;
    transition: color 0.15s ease;
}

.tooltip-expand-btn:hover { color: #28a745; }

.tooltip-hidden-txns {
    display: none;
    max-height: 200px;
    overflow-y: auto;
}

.tooltip-expand-checkbox-input:checked ~ .tooltip-hidden-txns { display: block; }
.tooltip-expand-checkbox-input:checked ~ .tooltip-expand-btn { display: none; }

/* Mobile: disable tooltip */
@media (max-width: 768px) {
    .calendar-day-tooltip { display: none !important; }
}
```

## Обработка ошибок

1. **Пустой tooltip**: `_build_day_tooltip()` возвращает `None` если `transactions` пустой
2. **Виртуальные операции**: При клике на `is_virtual=True` открывается `recurring-edit-scope-modal`
3. **Отсутствующая категория**: Fallback emoji "📋"
4. **ADR-003 guards**: 4 guard clauses в callback
5. **Skipped операции**: Визуализируются с opacity и line-through

## План реализации

1. **Шаг 1: Extend TransactionInfo** (~15 мин)
2. **Шаг 2: CSS Styles** (~30 мин)
3. **Шаг 3: DOM Restructure** (~30 мин)
4. **Шаг 4: Tooltip Builder** (~45 мин)
5. **Шаг 5: Edit Callback** (~45 мин)
6. **Шаг 6: Unit Tests** (~30 мин)
7. **Шаг 7: Финализация** (~15 мин)

**Общее время**: ~3.5 часа

## Зависимости

Новые библиотеки не требуются.

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| dcc.Checklist не работает с CSS hack | Низкая | Fallback: html.Input type=checkbox |
| Checkbox reset при re-render | Средняя | Локальное состояние в CSS, приемлемо |
| Tooltip перекрывает соседние ячейки | Низкая | z-index 1000, edge detection |
| backdrop-filter не поддерживается | Низкая | @supports fallback |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 Конфликт click handlers | DOM restructure: tooltip как sibling. Clickable area имеет Pattern-Matching ID, tooltip — отдельный div. Нет bubbling |
| 🟡 Store per date не масштабируется | CSS checkbox hack: expand через dcc.Checklist + CSS :checked. Никаких Store |
| 🟡 Отсутствует is_skipped визуализация | Добавлено `is_skipped: bool` в TransactionInfo. CSS класс `.skipped` с opacity и line-through |
| 🟡 Нет delay на hide tooltip | transition-delay 150ms на hide, 0s на появление |
| 🟡 TooltipTransactionItem дублирует | Убран. Используем TransactionInfo напрямую |
| 🟢 Edge detection nth-child | Исправлено на `7n-1` и `7n` |
| 🟢 MAX_VISIBLE_TRANSACTIONS | Добавлена константа = 5 |
| 🟢 Нет aria-атрибутов | Добавлены role="tooltip", aria-label |

## Ответы на вопросы критика

1. **Click handler priority**: DOM restructure. Tooltip как sibling к calendar-day-content. Клик не bubbles т.к. siblings.

2. **Store cleanup**: CSS checkbox hack. Никаких Store. Состояние локальное, reset при re-render — приемлемо.

3. **Mobile UX**: Отключен через CSS `@media (max-width: 768px)`. Tap открывает create-modal.

4. **Edit recurring flow**: Иконка 🔁 для recurring. При клике на virtual → recurring-edit-scope-modal.
