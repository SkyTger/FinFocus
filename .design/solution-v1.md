# Solution v1: CSS-only Hover Tooltip with Embedded Transaction List

## Обзор решения
Реализация CSS-based tooltip внутри каждой ячейки дня календаря. Tooltip строится как скрытый `html.Div` внутри `build_day_cell()` и становится видимым через CSS `:hover`. Expand/collapse списка операций управляется через Pattern-Matching callback с dcc.Store для хранения состояния "развёрнуто".

Преимущества CSS-only подхода:
1. Нет задержки серверного round-trip при hover
2. Плавные анимации через CSS transitions
3. Отсутствие "мерцания" при быстром движении мыши
4. Совместимость с существующими callbacks

## Архитектура

### Компоненты

**1. build_day_cell() — модификация (calendar.py)**
- Добавляет `_build_day_tooltip()` внутрь ячейки дня
- Tooltip рендерится только если есть транзакции
- Передаёт транзакции и баланс в tooltip builder

**2. _build_day_tooltip() — новая функция (calendar.py)**
- Строит glassmorphism tooltip с остатком и операциями
- Ограничивает отображение до MAX_VISIBLE_TRANSACTIONS (5)
- Добавляет кнопку "ещё N..." если операций больше
- Добавляет expandable секцию для остальных операций

**3. TooltipTransactionItem — TypedDict (schema/calendar_tooltip.py)**
- Стандартизированная структура для операции в tooltip
- Включает: id, amount, description, type, is_virtual, template_id, category_icon

**4. CSS стили (.calendar-day-tooltip) — (assets/calendar.css)**
- Glassmorphism: backdrop-filter, rgba background
- Позиционирование: absolute внутри relative day cell
- Анимации: opacity/transform transitions
- Adaptive positioning (left/right edge detection)

**5. Callbacks (calendar.py)**
- `expand_tooltip_transactions()` — toggle expand/collapse через Store
- `open_edit_from_tooltip()` — Pattern-Matching callback для клика по операции

### Диаграмма взаимодействия
```
User hovers day cell
        │
        ▼
┌───────────────────┐
│ CSS :hover shows  │  (No server call)
│ .calendar-day-    │
│ tooltip           │
└───────────────────┘
        │
User clicks "ещё N..."
        │
        ▼
┌───────────────────────────┐
│ Pattern-Matching callback │  (Server call)
│ Updates dcc.Store         │
│ "tooltip-expanded-{date}" │
└───────────────────────────┘
        │
        ▼
┌───────────────────────┐
│ CSS class toggled:    │
│ .tooltip-expanded     │
│ Shows full list       │
└───────────────────────┘
        │
User clicks transaction row
        │
        ▼
┌─────────────────────────────────┐
│ Pattern-Matching callback       │
│ Sets edit-transaction-id Store  │
│ OR recurring-edit-context Store │
│ Opens edit-modal or scope-modal │
└─────────────────────────────────┘
```

## Файловая структура
```
app/schema/calendar_tooltip.py  — NEW: TooltipTransactionItem TypedDict
app/components/calendar.py      — MODIFIED: +_build_day_tooltip(), +callbacks
app/assets/calendar.css         — MODIFIED: +glassmorphism tooltip styles (~150 lines)
tests/test_calendar_tooltip.py  — NEW: unit tests for tooltip functions
```

## Ключевые интерфейсы

```python
# app/schema/calendar_tooltip.py
class TooltipTransactionItem(TypedDict):
    """Элемент операции для отображения в tooltip."""
    id: int | None  # None for virtual recurring
    template_id: int | None  # For recurring instances
    amount: str  # Formatted with sign
    description: str
    transaction_type: str  # "income" | "expense"
    is_virtual: bool
    category_icon: str | None  # Bootstrap icon class


# app/components/calendar.py - new functions
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


# Callbacks
@callback(
    [
        Output("edit-modal", "is_open", allow_duplicate=True),
        Output("edit-transaction-id", "data", allow_duplicate=True),
        Output("recurring-edit-context", "data", allow_duplicate=True),
        Output("recurring-edit-scope-modal", "is_open", allow_duplicate=True),
        # ... edit form fields
    ],
    Input({"type": "tooltip-txn", "date": ALL, "txn_id": ALL, "is_virtual": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_edit_from_tooltip(n_clicks_list: list[int | None]):
    """Открывает модал редактирования при клике на операцию в tooltip.

    ADR-003 guard clauses applied.
    """
    ...
```

## Модель данных

Используем существующий `TransactionInfo` TypedDict из `calendar_service.py`:
```python
class TransactionInfo(TypedDict):
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
```

Для tooltip добавляем вспомогательный TypedDict (опционально, можно работать напрямую с TransactionInfo):
```python
# app/schema/calendar_tooltip.py
class TooltipTransactionItem(TypedDict):
    """Элемент операции для tooltip — subset TransactionInfo с форматированием."""
    id: int | None
    template_id: int | None
    amount_formatted: str  # "+15 000 ₽" или "-5 000 ₽"
    description: str  # description или category_name или "Операция"
    transaction_type: str
    is_virtual: bool
    category_emoji: str  # Emoji из ICON_TO_EMOJI или default
```

## CSS Glassmorphism Implementation

```css
/* === CALENDAR DAY TOOLTIP === */

.calendar-day {
    position: relative; /* For tooltip absolute positioning */
}

.calendar-day-tooltip {
    /* Hidden by default */
    display: none;
    opacity: 0;

    /* Glassmorphism */
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);

    /* Positioning */
    position: absolute;
    z-index: 1000;
    top: 100%;
    left: 50%;
    transform: translateX(-50%) translateY(8px);
    min-width: 220px;
    max-width: 280px;

    /* Styling */
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    padding: 12px;

    /* Animation */
    transition: opacity 0.2s ease, transform 0.2s ease;
}

/* Show on hover */
.calendar-day:hover .calendar-day-tooltip {
    display: block;
    opacity: 1;
    transform: translateX(-50%) translateY(4px);
}

/* Edge detection — right side */
.calendar-day:nth-child(6) .calendar-day-tooltip,
.calendar-day:nth-child(7) .calendar-day-tooltip {
    left: auto;
    right: 0;
    transform: translateX(0) translateY(8px);
}
.calendar-day:nth-child(6):hover .calendar-day-tooltip,
.calendar-day:nth-child(7):hover .calendar-day-tooltip {
    transform: translateX(0) translateY(4px);
}

/* Tooltip header (balance) */
.tooltip-balance {
    font-weight: 600;
    font-size: 14px;
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

/* Transaction row */
.tooltip-txn-row {
    display: flex;
    align-items: center;
    padding: 6px 0;
    cursor: pointer;
    border-radius: 6px;
    transition: background-color 0.15s ease;
}

.tooltip-txn-row:hover {
    background-color: rgba(40, 167, 69, 0.1);
}

/* Transaction icon/emoji */
.tooltip-txn-icon {
    width: 24px;
    font-size: 14px;
    flex-shrink: 0;
}

/* Transaction description */
.tooltip-txn-desc {
    flex: 1;
    font-size: 12px;
    color: #495057;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-right: 8px;
}

/* Transaction amount */
.tooltip-txn-amount {
    font-size: 12px;
    font-weight: 600;
    flex-shrink: 0;
}

.tooltip-txn-amount.income {
    color: #28a745;
}

.tooltip-txn-amount.expense {
    color: #dc3545;
}

/* Expand button */
.tooltip-expand-btn {
    font-size: 11px;
    color: #6c757d;
    cursor: pointer;
    padding: 4px 0;
    text-align: center;
    transition: color 0.15s ease;
}

.tooltip-expand-btn:hover {
    color: #28a745;
}

/* Hidden transactions (expandable) */
.tooltip-hidden-txns {
    display: none;
    max-height: 200px;
    overflow-y: auto;
}

.tooltip-expanded .tooltip-hidden-txns {
    display: block;
}

.tooltip-expanded .tooltip-expand-btn {
    display: none;
}

/* Responsive */
@media (max-width: 768px) {
    .calendar-day-tooltip {
        display: none !important; /* Disable on mobile, use tap */
    }
}
```

## Обработка ошибок

1. **Пустой tooltip**: Если `transactions` пустой, `_build_day_tooltip()` возвращает `None` — tooltip не рендерится
2. **Виртуальные операции**: При клике на виртуальную операцию (is_virtual=True) открывается recurring-edit-scope-modal вместо edit-modal
3. **Отсутствующая категория**: Используем fallback emoji "📋" если category_name отсутствует
4. **ADR-003 guards**: Все callbacks защищены от автовызовов при DOM update

## План реализации

1. **Шаг 1: Schema** (~10 мин)
   - Создать `app/schema/calendar_tooltip.py` с `TooltipTransactionItem`
   - Обновить `app/schema/__init__.py` с экспортом

2. **Шаг 2: CSS Styles** (~30 мин)
   - Добавить glassmorphism стили в `app/assets/calendar.css`
   - Тестирование визуального отображения в браузере

3. **Шаг 3: Tooltip Builder** (~45 мин)
   - Реализовать `_build_day_tooltip()` в `calendar.py`
   - Реализовать `_build_tooltip_transaction_row()`
   - Интегрировать в `build_day_cell()`

4. **Шаг 4: Expand/Collapse Callback** (~30 мин)
   - Добавить dcc.Store для состояния expand
   - Callback для toggle expand (без server round-trip через CSS class)
   - Альтернатива: чистый CSS-only expand через checkbox hack

5. **Шаг 5: Edit Callback** (~45 мин)
   - Pattern-Matching callback для клика по операции
   - Интеграция с edit-transaction-id Store
   - Интеграция с recurring-edit-context для виртуальных

6. **Шаг 6: Unit Tests** (~30 мин)
   - Тесты для `_build_day_tooltip()`
   - Тесты для edge cases (пустой список, >5 операций, виртуальные)

7. **Шаг 7: Финализация** (~15 мин)
   - Black + Flake8
   - Ручное тестирование всех сценариев
   - Обновление документации

## Зависимости
Новые библиотеки не требуются. Используем существующий стек:
- Dash Bootstrap Components (dbc)
- CSS backdrop-filter (поддержка: Chrome 76+, Firefox 103+, Safari 9+)

**Fallback для старых браузеров**:
```css
@supports not (backdrop-filter: blur(12px)) {
    .calendar-day-tooltip {
        background: rgba(255, 255, 255, 0.95);
    }
}
```

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Tooltip перекрывает соседние ячейки | Средняя | Edge detection через CSS nth-child; z-index management |
| Автовызов callback при hover (DOM update) | Высокая | ADR-003 guard clauses; CSS-only expand вместо callback |
| Мерцание tooltip при быстром движении мыши | Низкая | CSS transition delays; debounce через :hover |
| backdrop-filter не поддерживается | Низкая | @supports fallback с solid background |
| Клик по tooltip закрывает его (mouse leave) | Средняя | Увеличить padding; добавить delay на hide |
| Конфликт с existing day click (create modal) | Высокая | stopPropagation в tooltip click handlers; отдельные ID patterns |

### Решение конфликта click handlers

Проблема: клик по дню открывает create-modal, клик по операции в tooltip должен открывать edit-modal.

Решение:
1. Tooltip transaction rows имеют Pattern-Matching ID: `{"type": "tooltip-txn", ...}`
2. Day cell имеет Pattern-Matching ID: `{"type": "calendar-day", ...}`
3. Callback для tooltip-txn проверяет `ctx.triggered_id["type"] == "tooltip-txn"`
4. Callback для calendar-day проверяет `ctx.triggered_id["type"] == "calendar-day"`
5. CSS pointer-events на tooltip предотвращает bubbling:
   ```css
   .calendar-day-tooltip {
       pointer-events: auto;
   }
   ```
6. В JavaScript-слое Dash отдельные ID patterns не конфликтуют
