# Solution v2: Dashboard Foundation -- format_rub(), Color Palette, KPI Redesign (All Critique Items Resolved)

## Обзор решения

Решение состоит из трёх логических слоёв: (1) создание глобального форматтера `format_rub()` в `app/utils/formatters.py` с aliasing `format_amount()` для обратной совместимости и заменой всех inline-паттернов в dashboard.py, calendar.py, analytics.py; (2) обновление CSS-переменных с точной line-by-line картой замен во всех 4 CSS-файлах; (3) переработка KPI-карточек с удалением градиентов, новой типографикой 16px/.kpi-title и кнопкой "Сверка" через редирект на `/calendar?open_recon=1`. Ключевое решение по критике: `format_balance()` в calendar.py теперь возвращает строку С символом рубля (через `format_rub()` внутри), а все 4 callsite обновляются для устранения дублирования "₽ ₽".

## Архитектура

### Компоненты

**1. format_rub() -- глобальный форматтер (app/utils/formatters.py)**

Новая функция заменяет `format_amount()` и все inline-форматирования:
- Принимает `Decimal | float | int`
- Округление до 2 знаков, `.00` не показывается (15000 -> "15 000 ₽", 1234.56 -> "1 234.56 ₽")
- Разделитель тысяч: пробел (обычный, не неразрывный -- HTML рендерит корректно)
- Символ ₽ в конце с пробелом
- `show_sign=True` и `amount > 0` -> префикс `+`
- Знак минус: U+2212 (типографский) вместо U+002D
- Guard: None -> "0 ₽", строка -> попытка конвертации через Decimal(str), при ошибке -> "0 ₽"

`format_amount()` переопределяется как тонкий alias: `def format_amount(amount: Decimal) -> str: return format_rub(amount)`. Это покрывает 28 callsites в 5 файлах (goals.py ~25, transactions.py ~1, calendar_wishlist.py ~1, wishlist_service.py ~1) без единого изменения этих файлов.

**Обоснование scope discrepancy**: batch-1.md Задача 3 перечисляет 8 компонентов для миграции на format_rub(). Из них 3 требуют прямых изменений (dashboard.py, calendar.py, analytics.py), потому что содержат inline-форматирование (`f"$..."`, `f"{:,.0f}"` и т.д.). Остальные 5 файлов (goals.py, transactions.py, transaction_modals.py, wishlist.py, onboarding_wizard.py) вызывают `format_amount()`, который автоматически делегирует к `format_rub()` через alias. Поведенческое изменение (отбрасывание `.00`) пропагируется автоматически и улучшает читаемость -- формат "15 000 ₽" вместо "15 000.00 ₽".

**Документирование изменения to_data()**: `wishlist_service.py` line 317 вызывает `format_amount(item.amount)`. Формат результата в `WishlistItemData.amount` изменится с `"15 000.00 ₽"` на `"15 000 ₽"`. Проверено: ни Python callbacks, ни `wishlist_hover.js` не выполняют string matching на это значение. JS hover работает с `HoverBalances.base_balances` (raw числовые строки), а `WishlistItemData.amount` используется только для display в `html.Span` (lines 105, 396 в wishlist.py). Изменение безопасно.

**2. format_balance() в calendar.py -- рефакторинг**

`format_balance()` обновляется: внутри использует `format_rub()`, возвращает строку С символом ₽:

```python
def format_balance(balance: Decimal) -> tuple[str, str]:
    formatted = format_rub(balance)  # "15 000 ₽" или "−1 200 ₽"
    if balance < 0:
        return formatted, "balance-negative"
    elif balance < WARNING_BALANCE_THRESHOLD:
        return formatted, "balance-warning"
    else:
        return formatted, "balance-positive"
```

Все 4 callsite обновляются для устранения ручного добавления "₽":

| Callsite (строка) | Было | Станет |
|---|---|---|
| Line 294 (`build_stats_cards`, income) | `f"+{income_formatted} ₽"` | `format_rub(total_income, show_sign=True)` |
| Line 309 (`build_stats_cards`, expense) | `f"-{expense_formatted} ₽"` | `format_rub(-total_expense)` |
| Line 324 (`build_stats_cards`, balance) | `f"{balance_formatted} ₽"` | просто `balance_formatted` (уже содержит ₽) |
| Line 681 (`build_day_cell`) | `f"{balance_text} ₽"` | просто `balance_text` (уже содержит ₽) |

**3. Inline-форматирования -- ПОЛНАЯ КАРТА**

**dashboard.py (12 inline spots)**:

| # | Строка | Паттерн | Замена |
|---|--------|---------|--------|
| 1 | 254 | `"$100.00"` (exchange card) | Не менять -- скрытая карточка |
| 2 | 290 | `f"${metrics['total_balance']:,.2f}"` | `format_rub(metrics['total_balance'])` |
| 3 | 291 | `f"${metrics['period_income']:,.2f}"` | `format_rub(metrics['period_income'])` |
| 4 | 292 | `f"${metrics['period_expense']:,.2f}"` | `format_rub(metrics['period_expense'])` |
| 5 | 295 | `f"${metrics['savings_current']:,.2f}"` | `format_rub(metrics['savings_current'])` |
| 6 | 298 | `f"${metrics['savings_target']:,.2f}"` | `format_rub(metrics['savings_target'])` |
| 7 | 301 | `"$0.00"` | `format_rub(0)` (результат: "0 ₽") |
| 8 | 476 | `f"${metrics['period_income']:,.0f}"` | `format_rub(metrics['period_income'])` |
| 9 | 494 | `f"${metrics['period_expense']:,.0f}"` | `format_rub(metrics['period_expense'])` |
| 10 | 552 | `f"+${tx['amount']:,.2f}"` | `format_rub(tx['amount'], show_sign=True)` |
| 11 | 555 | `f"-${tx['amount']:,.2f}"` | `format_rub(-Decimal(str(tx['amount'])))` |
| 12 | 558 | `f"${tx['amount']:,.2f}"` | `format_rub(tx['amount'])` |

**calendar.py (12 inline spots)**:

| # | Строка | Функция | Паттерн | Замена |
|---|--------|---------|---------|--------|
| 1 | 95 | `format_balance()` | `f"{balance:,.0f}".replace(",", " ")` | `format_rub(balance)` (внутри функции) |
| 2 | 419 | `_build_tooltip_balance()` | `f"{balance:,.0f}".replace(",", " ") + " ₽"` | `format_rub(balance)` |
| 3 | 465 | `_build_tooltip_transaction_row()` | `f"+{amount:,.0f}".replace(",", " ")` | `format_rub(amount, show_sign=True)` |
| 4 | 468 | `_build_tooltip_transaction_row()` | `f"{amount:+,.0f}".replace(",", " ")` | `format_rub(amount, show_sign=True)` |
| 5 | 471 | `_build_tooltip_transaction_row()` | `f"{amount:,.0f}".replace(",", " ")` | `format_rub(amount)` |
| 6 | 475 | `_build_tooltip_transaction_row()` | `f"-{amount:,.0f}".replace(",", " ")` | `format_rub(-amount)` |
| 7 | 478 | `_build_tooltip_transaction_row()` | `f"-{amount:,.0f}".replace(",", " ")` | `format_rub(-amount)` |
| 8 | 1347 | `toggle_reconciliation_modal()` | `f"{expected:,.2f} ₽"` | `format_rub(expected)` |
| 9 | 1385 | `toggle_reconciliation_modal()` | `f"{expected:,.2f} ₽"` | `format_rub(expected)` |
| 10 | 1452 | `update_reconciliation_preview()` | `f"Разница: {diff:+,.2f} ₽"` | `f"Разница: {format_rub(diff, show_sign=True)}"` |
| 11 | 1525 | `apply_reconciliation()` | `f"{adjustment.amount:+,.2f} ₽"` (logger) | `format_rub(adjustment.amount, show_sign=True)` |
| 12 | 1530 | `apply_reconciliation()` | `f"{adjustment.amount:+,.2f} ₽"` (Alert) | `format_rub(adjustment.amount, show_sign=True)` |

**analytics.py (4 inline spots, 2 Plotly template)**:

| # | Строка | Паттерн | Замена |
|---|--------|---------|--------|
| 1 | 169 | `f"<b>{total:,.0f}</b><br>₽"` (Plotly annotation) | `f"<b>{format_rub(total)}</b>"` |
| 2 | 286 | `f"{total:,.0f} ₽"` (html.H4) | `format_rub(total)` |
| 3 | 160 | `"%{value:,.0f} ₽"` (Plotly hovertemplate) | **Оставить как есть** |
| 4 | 244 | `"%{y:,.0f} ₽"` (Plotly hovertemplate) | **Оставить как есть** |

**4. CSS-переменные -- ПОЛНАЯ LINE-BY-LINE КАРТА**

**custom.css (7 changes)**:

| Строка | Было | Станет |
|--------|------|--------|
| 5 | `--primary-green: #28a745` | `--color-primary: #2ecc71` + alias `--primary-green: var(--color-primary)` |
| 6 | `--light-green: #20c997` | `--color-primary-dark: #27ae60` + alias `--light-green: var(--color-primary-dark)` |
| 28 | `rgba(40, 167, 69, 0.1)` | `rgba(46, 204, 113, 0.1)` |
| 100 | `#1e7e34` | `var(--color-primary-dark)` |
| 101 | `#1c7430` | `#1e8449` |
| 166 | `#1e7e34` | `var(--color-primary-dark)` |
| 187 | `rgba(40, 167, 69, 0.25)` | `rgba(46, 204, 113, 0.25)` |

**calendar.css (6 changes)**:

| Строка | Было | Станет |
|--------|------|--------|
| 144 | `color: #28a745` | `color: var(--color-primary-dark)` |
| 198 | `color: #28a745` | `color: var(--color-primary)` |
| 216 | `border-left: 2px solid #28a745` | `border-left: 2px solid var(--color-primary)` |
| 330 | `color: #28a745` | `color: var(--color-primary-dark)` |
| 373 | `color: #28a745` | `color: var(--color-primary-dark)` |
| 385 | `color: #17a2b8` | `color: var(--color-secondary)` |

**transactions.css (2 changes)**:

| Строка | Было | Станет |
|--------|------|--------|
| 9 | `border-left: 3px solid #28a745` | `border-left: 3px solid var(--color-primary)` |
| 24 | `color: #28a745` | `color: var(--color-primary)` |

**onboarding.css (3 changes)**:

| Строка | Было | Станет |
|--------|------|--------|
| 12 | `#28a745 0%, #20c997 100%` | `var(--color-primary) 0%, var(--color-primary-dark) 100%` |
| 34 | `border-color: #28a745` | `border-color: var(--color-primary)` |
| 35 | `rgba(40, 167, 69, 0.25)` | `rgba(46, 204, 113, 0.25)` |

**dashboard.py Python hardcoded colors (7 changes)**:

| Строка | Было | Станет |
|--------|------|--------|
| 147 | gradient | Удаляется -- KPI переработка |
| 212 | `color: "#28a745"` (AI card) | Не менять -- скрытая карточка |
| 369 | `marker_color="#28a745"` | `marker_color="#27ae60"` |
| 378 | `marker_color="#17a2b8"` | `marker_color="#e74c3c"` |
| 433 | `["#28a745", "#17a2b8"]` | `["#27ae60", "#e74c3c"]` |
| 471 | `"backgroundColor": "#28a745"` | `"backgroundColor": "#27ae60"` |
| 489 | `"backgroundColor": "#17a2b8"` | `"backgroundColor": "#e74c3c"` |

**5. KPI-карточки переработка**

Функция `create_metric_card()` (lines 134-198) удаляется. Новая функция `_build_kpi_card()`:
- Белый фон, border `1px solid var(--color-border)`, border-radius: 10px, padding: 20px
- Опциональный `border-top: 3px solid {status_color}`
- Title: className="kpi-title" (16px, medium, серый)
- Value: className="kpi-number" (40px, semibold, тёмный)
- Subtitle: className="kpi-subtitle" (12px, regular, серый)
- Опциональная CTA кнопка

**6. Period Switcher и русские label** (решение пользователя)

- "Overview" -> "Обзор"
- "Month"/"Year" -> "Месяц"/"Год"
- "This Month"/"This Year" -> "За месяц"/"За год"
- "Income"/"Expense" -> "Доходы"/"Расходы"
- "Cashflow" -> "Денежный поток"
- "Statistic" -> "Статистика"
- "Recent Transactions" -> "Недавние операции"
- "No transactions yet" -> "Нет операций"

**7. Скрытие AI/Exchange** -- закомментировать в layout с TODO Epic-08.

**8. Plotly hovertemplate** -- оставить без изменений (Plotly template, comma separator приемлем для MVP).

## Файловая структура

```
Модифицируемые файлы (9):
  app/utils/formatters.py           — format_rub() + format_amount alias
  app/utils/__init__.py             — экспорт format_rub
  app/assets/custom.css             — новые CSS-переменные + типографика
  app/assets/calendar.css           — 6 замен hardcoded цветов
  app/assets/transactions.css       — 2 замены hardcoded цветов
  app/assets/onboarding.css         — 3 замены hardcoded цветов
  app/components/dashboard.py       — KPI, format_rub, AI/Exchange, русские label
  app/components/calendar.py        — format_balance() рефакторинг + 11 inline замен
  app/components/analytics.py       — 2 inline замены

Новые файлы (1):
  tests/test_formatters.py          — 10 тестов для format_rub()
```

## Ключевые интерфейсы

```python
# app/utils/formatters.py

MINUS_SIGN = "\u2212"  # Типографский минус

def format_rub(
    amount: Decimal | float | int,
    show_sign: bool = False,
) -> str:
    """Форматирует сумму в рублях."""
    if amount is None:
        return "0 ₽"
    try:
        value = Decimal(str(amount))
    except Exception:
        return "0 ₽"
    is_negative = value < 0
    abs_value = abs(value)
    quantized = abs_value.quantize(Decimal("0.01"))
    int_part = int(quantized)
    frac_part = quantized - int_part
    int_str = f"{int_part:,}".replace(",", " ")
    if frac_part == 0:
        number_str = int_str
    else:
        frac_str = f"{frac_part:.2f}"[1:]
        number_str = f"{int_str}{frac_str}"
    if is_negative:
        result = f"{MINUS_SIGN}{number_str} ₽"
    elif show_sign and value > 0:
        result = f"+{number_str} ₽"
    else:
        result = f"{number_str} ₽"
    return result

def format_amount(amount: Decimal) -> str:
    """deprecated, используйте format_rub."""
    return format_rub(amount)
```

```python
# app/components/dashboard.py

def _build_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    icon: str = "",
    icon_color: str = "var(--color-text-primary)",
    status_border_color: str | None = None,
    action_button: html.Div | None = None,
) -> dbc.Card:
    """Создает KPI-карточку по спецификации Dashboard UI."""
    ...
```

```python
# app/components/calendar.py

def format_balance(balance: Decimal) -> tuple[str, str]:
    """Форматирует баланс с определением CSS класса. Возвращает строку С ₽."""
    formatted = format_rub(balance)
    if balance < 0:
        return formatted, "balance-negative"
    elif balance < WARNING_BALANCE_THRESHOLD:
        return formatted, "balance-warning"
    else:
        return formatted, "balance-positive"
```

## План реализации

### Шаг 1: format_rub() + тесты
**Файлы**: `app/utils/formatters.py`, `app/utils/__init__.py`, `tests/test_formatters.py`
- Реализовать format_rub(), переопределить format_amount() как alias
- Обновить __init__.py экспорт
- 10 unit тестов
- Pytest: 493 тестов (483 + 10)

### Шаг 2: CSS-переменные + типографика
**Файлы**: `app/assets/custom.css`, `calendar.css`, `transactions.css`, `onboarding.css`
- 15 новых CSS-переменных в :root
- 2 deprecated alias (--primary-green, --light-green)
- 18 замен hardcoded цветов (7+6+2+3)
- 9 типографических классов

### Шаг 3: Переработка dashboard.py
**Файлы**: `app/components/dashboard.py`
- Удалить create_metric_card(), создать _build_kpi_card()
- 12 inline замен на format_rub()
- Кнопка "Сверка" -> dcc.Link /calendar?open_recon=1
- Русские label + Period Switcher
- Скрыть AI/Exchange

### Шаг 4: Обновить calendar.py
**Файлы**: `app/components/calendar.py`
- Рефакторинг format_balance() (с ₽)
- 4 callsite обновления
- 11 inline замен

### Шаг 5: Обновить analytics.py
**Файлы**: `app/components/analytics.py`
- 2 inline замены

### Шаг 6: Финализация
- Black + Flake8
- Pytest >= 493
- Ручная проверка в браузере
- Обновить ROADMAP.md и feature_progress.md

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| format_amount alias (.00 убирается) | Средняя | 0 тестов зависят от ".00 ₽" формата |
| Двойной ₽ в format_balance callsites | Высокая если не отследить | Полная карта 4 callsite |
| Пропущенные inline spots | Средняя | Полная line-by-line карта: 12+12+2 |
| CSS каскад .btn-success | Низкая | Alias обеспечивает автоматическое обновление |
| WishlistItemData.amount формат | Низкая | Только display, ни Python ни JS string matching |
| Plotly hovertemplate запятая | Низкая | Приемлемо для MVP |

## Requirements Traceability Matrix (RTM)

| # | Requirement | Секция spec | Реализация | Тип |
|---|-------------|-------------|------------|-----|
| 1 | format_rub(amount, show_sign) | batch-1.md Задача 2 | Шаг 1: format_rub() в formatters.py | Must |
| 2 | format_rub(15000) -> "15 000 ₽" | batch-1.md Задача 2 | Шаг 1.4: test_format_rub_positive_integer | Must |
| 3 | format_rub(-1200) -> "−1 200 ₽" (U+2212) | batch-1.md Задача 2 | Шаг 1.4: test_format_rub_negative | Must |
| 4 | Обновить __init__.py экспорт | batch-1.md Задача 2 | Шаг 1.3 | Must |
| 5 | Dashboard KPI: Total Balance, Income, Expense, Savings | batch-1.md Задача 3-4 | Шаг 3: _build_kpi_card() + format_rub() | Must |
| 6 | Calendar tooltip (баланс, операции) | batch-1.md Задача 3 | Шаг 4: format_rub() в tooltip + reconciliation | Must |
| 7 | Goals: карточка, взносы | batch-1.md Задача 3 | Шаг 1.2: format_amount alias | Must |
| 8 | Transactions: таблица | batch-1.md Задача 3 | Шаг 1.2: format_amount alias | Must |
| 9 | Wishlist: карточка, модал | batch-1.md Задача 3 | Шаг 1.2: format_amount alias | Must |
| 10 | Onboarding Wizard | batch-1.md Задача 3 | Нет inline formatting | Info |
| 11 | _build_kpi_card() белый фон | batch-1.md Задача 4 | Шаг 3.2: className="kpi-card" | Must |
| 12 | Total Balance: кнопка "Сверка" | batch-1.md Задача 4 | Шаг 3.3: dcc.Link -> /calendar?open_recon=1 | Must |
| 13 | Скрыть AI Assistant и Exchange | batch-1.md Задача 5 | Шаг 3.8: комментарий + TODO Epic-08 | Must |
| 14 | .kpi-number 40px semibold | batch-1.md Задача 6 | Шаг 2.3: CSS класс | Must |
| 15 | .kpi-title 16px medium | batch-1.md Задача 6 | Шаг 2.3: CSS класс | Must |
| 16 | --color-primary: #2ecc71 | batch-1.md Задача 1 | Шаг 2.1: :root | Must |
| 17 | 15 новых CSS-переменных | batch-1.md Задача 1 | Шаг 2.1 | Must |
| 18 | Unit тесты format_rub (>=8) | batch-1.md Задача 7 | Шаг 1.4: 10 тестов | Must |
| 19 | Black + Flake8 OK | batch-1.md Задача 8 | Шаг 6 | Must |
| 20 | Period Switcher: "Месяц"/"Год" | Решение пользователя #2 | Шаг 3.7 | Must |

## Blast Radius

### Прямые изменения (9 файлов + 1 новый)

- `app/utils/formatters.py` -- format_rub() + format_amount alias (~35 строк)
- `app/utils/__init__.py` -- экспорт format_rub (+2 строки)
- `app/assets/custom.css` -- :root переменные, типографика, hardcoded (~80 строк)
- `app/assets/calendar.css` -- 6 замен (~6 строк)
- `app/assets/transactions.css` -- 2 замены (~2 строки)
- `app/assets/onboarding.css` -- 3 замены (~3 строки)
- `app/components/dashboard.py` -- KPI, format_rub, AI/Exchange, русские label (~180 строк)
- `app/components/calendar.py` -- format_balance() + 11 inline замен (~35 строк)
- `app/components/analytics.py` -- 2 inline замены (~5 строк)
- `tests/test_formatters.py` -- НОВЫЙ, 10 тестов (~90 строк)

### Связанные файлы (через alias, НЕ модифицируются)

- `app/components/goals.py` -- 25 вызовов format_amount() -> alias
- `app/components/transactions.py` -- 1 вызов format_amount() -> alias
- `app/components/calendar_wishlist.py` -- 1 вызов format_amount() -> alias
- `app/services/wishlist_service.py` -- 1 вызов format_amount() в to_data() -> alias
- `app/components/wishlist.py` -- display pre-formatted amount
- `app/assets/wishlist_hover.js` -- JS formatter, не затронут
- `app/components/calendar.py` line 923 -- alias import

### Проверить после реализации

- [ ] Dashboard: 4 KPI без градиентов, белый фон с бордером, числа X XXX ₽
- [ ] Dashboard: кнопка "Сверка" -> /calendar?open_recon=1
- [ ] Dashboard: AI/Exchange скрыты
- [ ] Dashboard: Period Switcher "Месяц"/"Год", "Обзор"
- [ ] Dashboard: график -- зелёный доход, красный расход, русские label
- [ ] Calendar: баланс в ячейках X XXX ₽ (без двойного ₽)
- [ ] Calendar: tooltip и reconciliation в формате ₽
- [ ] Goals: карточки целей X XXX ₽ (без .00)
- [ ] Transactions: таблица X XXX ₽
- [ ] Analytics: donut и summary в формате ₽
- [ ] Wishlist: суммы X XXX ₽
- [ ] 493+ тестов проходят
- [ ] Black + Flake8 OK

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 #1: Inaccurate inline count in calendar.py (10 vs 12) | Полная line-by-line карта: 12 spots |
| 🟡 #2: format_balance() double-₽ risk | format_balance() С ₽, все 4 callsite обновлены |
| 🟡 #3: Missing CSS rgba references | Полная карта: 18 замен в 4 файлах |
| 🟡 #4: .00 truncation risk in to_data() | Задокументировано: только display, безопасно |
| 🟡 #5: dashboard.py inline count (9 vs 11+) | Полная карта: 12 spots |
| 🟡 #6: Scope discrepancy 8 vs 3 files | Явное обоснование: 3 direct + 5 via alias |
| 🟢 #7: .kpi-title 12px vs 16px | 16px per spec |
| 🟢 #8: --color-separator unused | API для batch 5.3 |
| 🟢 #9: Period Switcher не переведен | Переведено по решению пользователя |
| 🟢 #10: create_metric_card() deprecation | Явно: удалить + создать _build_kpi_card() |

## Ответы на вопросы критика

1. **format_balance()**: Возвращать С ₽ (решение пользователя). Все callsite обновлены.
2. **Period Switcher**: Перевести в батче 5.1 (решение пользователя). "Месяц"/"Год".
3. **.kpi-title**: 16px per spec.
4. **Plotly hovertemplate**: Приемлемо для MVP, кастомизация в batch 5.2.
5. **"$0.00" fallback**: `format_rub(0)` -> "0 ₽".
