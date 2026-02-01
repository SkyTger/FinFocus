# Solution v3: CSS-Only Tooltip with HTML Input Checkbox Hack

## Обзор решения
Tooltip реализуется как sibling-элемент кликабельной области дня с glassmorphism стилем. Expand/collapse списка операций выполняется через CSS checkbox hack с `html.Input(type="checkbox")` вместо dcc.Checklist для корректной работы htmlFor. На мобильных устройствах tooltip отключается через CSS media query.

## Архитектура

### Принципиальные изменения от v2

1. **html.Input вместо dcc.Checklist** - гарантирует работу htmlFor для CSS checkbox hack
2. **CSS порядок элементов исправлен** - checkbox ПЕРВЫМ в DOM для работы sibling selectors
3. **category_icon в TransactionInfo** - для использования ICON_TO_EMOJI mapping
4. **is_skipped в TransactionInfo** - для визуализации пропущенных операций

### Компоненты

**1. TransactionInfo (расширенный) - calendar_service.py**
```python
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
    category_icon: str | None  # NEW: Bootstrap icon class (bi-cart, etc.)
    is_skipped: bool           # NEW: пропущена ли операция
```

**2. build_day_cell() - реструктуризация (calendar.py)**
```python
def build_day_cell(...) -> html.Div:
    """Создает ячейку дня с tooltip как sibling."""
    # Кликабельная область (для create-modal)
    clickable_content = html.Div(
        [day_number, icons, balance],
        id={"type": "calendar-day", "date": day_date.isoformat()},
        n_clicks=0,
        className="calendar-day-content",
    )

    # Tooltip как sibling элемент (НЕ вложен в clickable_content!)
    tooltip = _build_day_tooltip(day_date, balance, transactions) if transactions else None

    # Wrapper без n_clicks - position: relative для tooltip
    return html.Div(
        [clickable_content, tooltip],
        className=" ".join(css_classes),
    )
```

**3. _build_day_tooltip() - tooltip builder (calendar.py)**
```python
def _build_day_tooltip(
    day_date: date,
    balance: Decimal,
    transactions: list[TransactionInfo],
) -> html.Div | None:
    """Создаёт tooltip для дня с операциями.

    Tooltip является sibling-элементом кликабельной области,
    не вложенным, что предотвращает конфликт click handlers.
    """
    if not transactions:
        return None

    visible_txns = transactions[:MAX_VISIBLE_TRANSACTIONS]
    hidden_txns = transactions[MAX_VISIBLE_TRANSACTIONS:]

    # Уникальный ID для checkbox hack
    checkbox_id = f"tooltip-expand-{day_date.isoformat()}"

    tooltip_children = []

    # Checkbox ПЕРВЫМ для CSS sibling selectors (:checked ~ ...)
    if hidden_txns:
        tooltip_children.append(
            html.Input(
                id=checkbox_id,
                type="checkbox",
                className="tooltip-expand-checkbox",
            )
        )

    # Balance header
    tooltip_children.append(_build_tooltip_balance(balance))

    # Visible transactions
    for txn in visible_txns:
        tooltip_children.append(_build_tooltip_transaction_row(txn, day_date))

    if hidden_txns:
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
```

**4. _build_tooltip_transaction_row() - строка операции (calendar.py)**
```python
from app.utils.formatters import ICON_TO_EMOJI

def _build_tooltip_transaction_row(
    txn: TransactionInfo,
    day_date: date,
) -> html.Div:
    """Строит строку операции внутри tooltip."""
    # Emoji из category_icon через ICON_TO_EMOJI mapping
    category_emoji = "📋"  # default
    category_icon = txn.get("category_icon")
    if category_icon:
        category_emoji = ICON_TO_EMOJI.get(category_icon, "📋")

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
        recurring_icon = html.Span(
            "🔁", className="tooltip-recurring-icon", title="Повторяющаяся"
        )

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
```

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
│ html.Input checkbox       │  (No server call!)
│ toggled via htmlFor       │
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
app/services/calendar_service.py  — MODIFIED: +is_skipped, +category_icon в TransactionInfo
app/components/calendar.py        — MODIFIED: DOM restructure, +tooltip functions, +callback
app/assets/calendar.css           — MODIFIED: +glassmorphism tooltip styles (~200 lines)
tests/test_calendar_tooltip.py    — NEW: unit tests for tooltip functions (~15 tests)
```

## Ключевые интерфейсы

```python
# app/services/calendar_service.py - расширенный TransactionInfo
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
    category_icon: str | None  # NEW: Bootstrap icon class (bi-cart, bi-house, etc.)
    is_skipped: bool  # NEW: True для пропущенных recurring экземпляров


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

    Args:
        day_date: Дата дня
        balance: Остаток на день
        transactions: Список операций дня

    Returns:
        html.Div с tooltip или None если нет операций
    """
    ...


def _build_tooltip_balance(balance: Decimal) -> html.Div:
    """Строит header tooltip с балансом."""
    ...


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
    ...


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
        # Note: logger already imported in calendar.py (from loguru import logger)
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
    date: str  # ISO format (YYYY-MM-DD)
    is_virtual: bool  # True для виртуальных recurring instances
    is_recurring: bool  # True для recurring (виртуальных и exceptions)
    is_exception: bool  # True для exceptions (материализованных recurring)
    category_id: int | None  # ID категории (None = без категории)
    category_name: str | None  # Название категории для UI
    category_icon: str | None  # Bootstrap icon class (bi-cart, bi-house)
    is_skipped: bool  # True для пропущенных recurring экземпляров
```

### Изменения в CalendarService

В методах `get_transactions_by_date()` и `get_all_transactions_for_period()` добавить заполнение новых полей:

```python
# get_transactions_by_date() - для обычных транзакций
txn_info: TransactionInfo = {
    # ... existing fields ...
    "category_icon": txn.category_rel.icon if txn.category_rel else None,
    "is_skipped": getattr(txn, 'is_skipped', False),
}

# get_all_transactions_for_period() - для regular transactions
TransactionInfo(
    # ... existing fields ...
    category_icon=txn.category_rel.icon if txn.category_rel else None,
    is_skipped=getattr(txn, 'is_skipped', False),
)

# get_all_transactions_for_period() - для exceptions
TransactionInfo(
    # ... existing fields ...
    category_icon=instance.category_rel.icon if instance.category_rel else None,
    is_skipped=instance.is_skipped,
)
```

### VirtualTransaction (RecurringService)

Добавить `category_icon` в VirtualTransaction dict:

```python
# В generate_instances() метод RecurringService
virtual_txn: VirtualTransaction = {
    # ... existing fields ...
    "category_id": template.category_id,
    "category_name": template.category_rel.name if template.category_rel else None,
    "category_icon": template.category_rel.icon if template.category_rel else None,
}
```

## CSS Glassmorphism Implementation

```css
/* ==================== CALENDAR DAY TOOLTIP ==================== */

:root {
    --tooltip-hide-delay: 150ms;
}

.calendar-day {
    position: relative;  /* For tooltip positioning */
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

/* Edge detection - right edge columns */
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

/* Fallback for browsers without backdrop-filter */
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

/* CSS Checkbox Hack - checkbox FIRST in DOM for sibling selectors */
.tooltip-expand-checkbox {
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

/* Checkbox must be BEFORE these elements in DOM for ~ selector to work */
.tooltip-expand-checkbox:checked ~ .tooltip-hidden-txns { display: block; }
.tooltip-expand-checkbox:checked ~ .tooltip-expand-btn { display: none; }

/* Mobile: disable tooltip, use existing click behavior */
@media (max-width: 768px) {
    .calendar-day-tooltip { display: none !important; }
}
```

## Обработка ошибок

1. **Пустой tooltip**: `_build_day_tooltip()` возвращает `None` если `transactions` пустой
2. **Виртуальные операции**: При клике на `is_virtual=True` открывается `recurring-edit-scope-modal`
3. **Отсутствующая категория**: Fallback emoji "📋" при `category_icon=None`
4. **ADR-003 guards**: 4 guard clauses в callback `open_edit_from_tooltip()`
5. **Skipped операции**: Визуализируются с opacity и line-through через CSS класс `.skipped`
6. **is_skipped не в TransactionInfo для regular**: Используем `getattr(txn, 'is_skipped', False)` для безопасности

## План реализации

1. **Шаг 1: Extend TransactionInfo** (~20 мин)
   - Добавить `is_skipped: bool` и `category_icon: str | None` в TypedDict
   - Обновить все места заполнения TransactionInfo в CalendarService
   - Обновить VirtualTransaction в RecurringService

2. **Шаг 2: CSS Styles** (~30 мин)
   - Добавить glassmorphism стили в calendar.css
   - Реализовать checkbox hack с правильным порядком селекторов
   - Добавить mobile media query

3. **Шаг 3: DOM Restructure** (~30 мин)
   - Изменить `build_day_cell()` для создания sibling structure
   - Добавить `calendar-day-content` wrapper для кликабельной области
   - Tooltip как sibling к content

4. **Шаг 4: Tooltip Builder Functions** (~45 мин)
   - `_build_day_tooltip()` с checkbox hack
   - `_build_tooltip_balance()`
   - `_build_tooltip_transaction_row()` с ICON_TO_EMOJI

5. **Шаг 5: Edit Callback** (~45 мин)
   - Pattern-Matching callback для tooltip-txn clicks
   - ADR-003 guard clauses
   - Интеграция с existing Stores

6. **Шаг 6: Unit Tests** (~45 мин)
   - Test TransactionInfo с новыми полями
   - Test tooltip builder functions
   - Test callback guards

7. **Шаг 7: Финализация** (~15 мин)
   - Black formatting
   - Flake8 lint
   - pytest run

**Общее время**: ~4 часа

## Зависимости

Новые библиотеки не требуются. Используются только существующие:
- `from app.utils.formatters import ICON_TO_EMOJI`
- `from loguru import logger` (уже импортирован в calendar.py)
- `from decimal import Decimal` (уже импортирован в calendar.py)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| html.Input htmlFor не работает | Низкая | Тестирование на первом шаге CSS, fallback к clientside_callback |
| Checkbox reset при re-render | Средняя | Локальное состояние в CSS, сброс при навигации приемлем (по решению пользователя) |
| Tooltip перекрывает соседние ячейки | Низкая | z-index 1000, edge detection для правых колонок |
| backdrop-filter не поддерживается | Низкая | @supports fallback с solid background |
| category_icon None для старых данных | Низкая | Fallback emoji "📋" в _build_tooltip_transaction_row() |

## Учтённые замечания из критики

| Замечание из critique v2 | Как решено |
|--------------------------|------------|
| 🟡 dcc.Checklist htmlFor несовместимость | Заменён на `html.Input(type="checkbox")` с прямым ID для htmlFor. Label ссылается на input ID напрямую |
| 🟡 get_category_emoji не определена | Убрана функция. Используется `ICON_TO_EMOJI.get(txn["category_icon"], "📋")` напрямую. Добавлено поле `category_icon` в TransactionInfo |
| 🟡 CSS sibling selector порядок | Checkbox добавляется ПЕРВЫМ в tooltip_children через `tooltip_children.insert(0, ...)` перед balance и transactions |
| 🟢 logger.debug без import | Задокументировано: `from loguru import logger` уже импортирован в calendar.py (строка 12) |
| 🟢 Decimal import | Задокументировано: `from decimal import Decimal` уже импортирован в calendar.py (строка 5) |

## Ответы на вопросы критика

1. **Вопрос:** get_category_emoji implementation - планируется ли создать отдельный helper или использовать существующий ICON_TO_EMOJI mapping?
   **Ответ:** По решению пользователя (#1) — используем существующий ICON_TO_EMOJI dict и поле category_icon из TransactionInfo напрямую, без дополнительного helper'а. Добавляем `category_icon: str | None` в TransactionInfo и заполняем его из `category_rel.icon`. В tooltip используем `ICON_TO_EMOJI.get(txn["category_icon"], "📋")`.

2. **Вопрос:** Checkbox state persistence - при навигации между месяцами tooltip перерисовывается и checkbox сбрасывается. Это приемлемое поведение?
   **Ответ:** По решению пользователя (#2) — сброс expand state при навигации между месяцами приемлем для MVP. Это упрощает реализацию и соответствует ожиданиям пользователя (новый месяц = новый контекст).

3. **Вопрос:** Mobile touch long-press - есть ли альтернативный UX для просмотра операций дня на mobile?
   **Ответ:** По решению пользователя (#3) — не нужен альтернативный UX для mobile. Достаточно существующего клика на день для открытия create-modal. Tooltip отключается через `@media (max-width: 768px) { .calendar-day-tooltip { display: none !important; } }`.
