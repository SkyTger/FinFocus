# Solution v1: Dashboard Foundation -- format_rub() + Color Palette + KPI Redesign

## Обзор решения

Решение состоит из трех логических уровней: (1) создание глобального форматтера `format_rub()` в `app/utils/formatters.py` и замена всех вызовов `format_amount()` плюс inline-форматирований на него, (2) обновление CSS-переменных и добавление типографических классов в `app/assets/custom.css`, (3) переработка KPI-карточек и скрытие AI/Exchange в `app/components/dashboard.py`. Ключевое архитектурное решение -- `format_rub()` становится единственной точкой форматирования денег, заменяя как `format_amount()`, так и все inline-паттерны вроде `f"${amount:,.2f}"` и `f"{balance:,.0f}".replace(",", " ")`.

## Архитектура

### Компоненты

**1. format_rub() -- глобальный форматтер (app/utils/formatters.py)**

Текущая функция `format_amount()` делает: `f"{amount:,.2f} ₽".replace(",", " ")` -- т.е. всегда показывает 2 десятичных знака, не поддерживает знак `+`, не использует типографский минус.

Новая `format_rub()` заменяет `format_amount()` и все inline-форматирования:
- Округление до 2 знаков, но `.00` не показывается (15000 -> "15 000 ₽", 1234.56 -> "1 234.56 ₽")
- Разделитель тысяч: неразрывный пробел (обычный пробел в Python, так как HTML сам поддерживает)
- Символ ₽ в конце с пробелом
- Если `show_sign=True` и `amount > 0` -> префикс `+`
- Знак минус: U+2212 (типографский) вместо U+002D

**Решение по обратной совместимости**: Сохранить `format_amount()` как alias для `format_rub()` (deprecated), чтобы все существующие вызовы в goals.py, transactions.py, calendar_wishlist.py, analytics.py не требовали ручной замены импортов. Это резко сокращает blast radius. В export (`__init__.py`) добавить оба имени.

**Обоснование**: В codebase ~40 вызовов `format_amount()` (goals.py ~25, transactions.py ~1, calendar_wishlist.py ~1, wishlist_service.py ~1, analytics.py ~4, calendar.py ~1). Изменять все 40 мест рискованно. Alias `format_amount = format_rub` безопасен.

**2. Inline-форматирования (6 паттернов)**

В codebase обнаружены следующие inline-паттерны, которые НЕ используют `format_amount()`:

| Паттерн | Файлы | Количество |
|---------|-------|-----------|
| `f"${amount:,.2f}"` | dashboard.py | 9 мест |
| `f"{balance:,.0f}".replace(",", " ")` | calendar.py | 5 мест |
| `f"{expected:,.2f} ₽"` | calendar.py (reconciliation) | 2 места |
| `f"{diff:+,.2f} ₽"` | calendar.py (preview) | 1 место |
| `f"{adjustment.amount:+,.2f} ₽"` | calendar.py (log/alert) | 2 места |
| `f"{total:,.0f} ₽"` | analytics.py | 2 места |
| `%{value:,.0f} ₽` (Plotly template) | analytics.py | 2 места (Plotly hovertemplate -- не меняем, это шаблон Plotly) |
| `#28a745` hardcoded в Python | dashboard.py | 6 мест |

**3. CSS-переменные (app/assets/custom.css)**

Обновление `:root` -- замена `--primary-green: #28a745` и `--light-green: #20c997` на новую палитру, плюс добавление семантических переменных.

**4. KPI-карточки (app/components/dashboard.py)**

Переработка `create_metric_card()` и `build_overview_cards()`:
- Убрать gradient, убрать кнопки "Deposit"/"Send"
- Белый фон + бордер/тень
- Новые CSS-классы для типографики
- Кнопка "Сверка" на Total Balance
- Callback для открытия модала сверки из Dashboard

**5. Модал сверки -- интеграция с Calendar**

Модал сверки уже реализован в `calendar.py` с ID `reconciliation-modal`. Он включен в layout `create_calendar_layout()`. Для Dashboard нужен другой подход: нельзя иметь два модала с одним ID на разных страницах.

**Решение**: Добавить callback в dashboard.py, который при клике на "Сверка" перенаправляет на `/calendar?open_recon=1`. Это переиспользует существующий механизм (уже реализован в протоколе 0014). Альтернатива -- вынести модал в глобальный layout (main.py), но это потребует рефакторинга calendar.py и выходит за scope батча. Навигация `/calendar?open_recon=1` -- минимальное изменение.

### Диаграмма взаимодействия

```
format_rub() [новая]
    │
    ├── format_amount() [alias, deprecated]
    │       │
    │       ├── goals.py (~25 вызовов) -- без изменений
    │       ├── transactions.py (1 вызов) -- без изменений
    │       ├── calendar_wishlist.py (1 вызов) -- без изменений
    │       ├── wishlist_service.py (1 вызов) -- без изменений
    │       └── analytics.py (4 вызова, inline format_rub для 2 мест)
    │
    ├── dashboard.py (9 мест inline $) -- заменить на format_rub()
    ├── calendar.py (10 мест inline) -- заменить на format_rub()
    └── onboarding_wizard.py (0 мест, только ₽ в InputGroupText)

CSS Variables [custom.css]
    │
    ├── --color-primary: #2ecc71 (было --primary-green: #28a745)
    ├── --color-primary-dark: #27ae60 (было --light-green: #20c997)
    ├── + 15 новых семантических переменных
    │
    ├── calendar.css (4 hardcoded #28a745) -- заменить на var()
    ├── transactions.css (2 hardcoded #28a745) -- заменить на var()
    ├── onboarding.css (2 hardcoded #28a745, 1 #20c997) -- заменить на var()
    └── custom.css (6 hardcoded #28a745, #1e7e34 etc) -- заменить на var()

KPI Cards [dashboard.py]
    │
    ├── create_metric_card() -- переработка (убрать gradient)
    ├── build_overview_cards() -- format_rub() + новые карточки
    ├── _build_kpi_card() -- новая функция (или переработка create_metric_card)
    ├── AI/Exchange -- закомментировать в layout
    └── Кнопка "Сверка" → /calendar?open_recon=1
```

## Файловая структура

```
app/utils/formatters.py         — format_rub() + format_amount alias
app/utils/__init__.py           — экспорт format_rub
app/assets/custom.css           — новые CSS-переменные + типографические классы
app/assets/calendar.css         — замена #28a745 на var(--color-primary)
app/assets/transactions.css     — замена #28a745 на var(--color-primary)
app/assets/onboarding.css       — замена #28a745 на var(--color-primary)
app/components/dashboard.py     — KPI переработка, format_rub, AI/Exchange скрытие
app/components/calendar.py      — замена inline formatting на format_rub()
app/components/analytics.py     — замена 2 inline мест на format_rub()
tests/test_formatters.py        — 8+ тестов для format_rub() (новый файл)
```

## Ключевые интерфейсы

```python
# app/utils/formatters.py

MINUS_SIGN = "\u2212"  # Типографский минус


def format_rub(
    amount: Decimal | float | int,
    show_sign: bool = False,
) -> str:
    """Форматирует сумму в рублях.

    Args:
        amount: Сумма (Decimal, float или int)
        show_sign: Показывать '+' для положительных значений

    Returns:
        Отформатированная строка, например "15 000 ₽" или "+2 350.50 ₽"

    Examples:
        >>> format_rub(15000)
        '15 000 ₽'
        >>> format_rub(2350.50, show_sign=True)
        '+2 350.50 ₽'
        >>> format_rub(-1200)
        '−1 200 ₽'
        >>> format_rub(0)
        '0 ₽'
        >>> format_rub(Decimal("1234.56"))
        '1 234.56 ₽'
    """
    ...


# Обратная совместимость: alias для format_amount
def format_amount(amount: Decimal) -> str:
    """Форматирует сумму для отображения (deprecated, use format_rub).

    Args:
        amount: Сумма операции

    Returns:
        str: Отформатированная строка (например, "15 000 ₽")
    """
    return format_rub(amount)
```

```python
# app/components/dashboard.py -- новая KPI-карточка

def _build_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    icon: str = "",
    icon_color: str = "#2c3e50",
    status_border_color: str | None = None,
    action_button: dbc.Button | None = None,
) -> dbc.Card:
    """Создает KPI-карточку по спецификации.

    Args:
        title: Заголовок 12px серый (например, "Баланс")
        value: Главное число в формате format_rub() (например, "45 000 ₽")
        subtitle: Подпись 12px серый (например, "+2 350 vs вчера")
        icon: Bootstrap Icon class (например, "bi-wallet2")
        icon_color: Цвет иконки
        status_border_color: Цвет верхнего бордера (2-4px)
        action_button: CTA кнопка (только для Total Balance)

    Returns:
        dbc.Card: KPI-карточка
    """
    ...
```

## Модель данных

Изменений в ORM-моделях нет. Все изменения чисто в слое представления (UI).

## Обработка ошибок

1. **format_rub()** -- принимает Decimal/float/int; для None или некорректных значений можно добавить guard с возвратом "0 ₽" (defensive, хотя в текущем коде все вызывающие места передают числа)
2. **Кнопка "Сверка"** -- перенаправление на /calendar?open_recon=1 через dcc.Link, никаких новых callback ошибок
3. **Обратная совместимость format_amount** -- alias гарантирует, что все 40+ существующих вызовов продолжат работать без изменений

## План реализации

### Шаг 1: format_rub() + тесты (блокирует шаги 2-4)

**Файлы**: `app/utils/formatters.py`, `app/utils/__init__.py`, `tests/test_formatters.py`

1.1. Реализовать `format_rub()` с логикой:
   - Конвертировать amount в Decimal если float/int
   - Определить знак (положительный, отрицательный, ноль)
   - Отделить целую и дробную части
   - Если дробная часть `.00` -- не показывать её
   - Форматировать целую часть с разделителем тысяч (пробел)
   - Собрать строку: `[+/-]число[ .дробная] ₽`

1.2. Переопределить `format_amount()` как alias: `def format_amount(amount: Decimal) -> str: return format_rub(amount)`. Текущая format_amount всегда показывает 2 десятичных -- новая format_rub отбрасывает `.00`. Это **изменение поведения**: `format_amount(Decimal("15000"))` ранее возвращала `"15 000.00 ₽"`, теперь вернет `"15 000 ₽"`.

**Важный нюанс**: Необходимо проверить, не ломает ли отбрасывание `.00` какую-то логику. В goals.py вызовы `format_amount(current)` и `format_amount(target)` используются для отображения в UI -- отбрасывание `.00` улучшает читаемость. В transactions.py `format_amount(tx.amount)` -- аналогично. В wishlist_service.py `to_data()` -- аналогично.

**Решение**: Если нужна обратная совместимость с `.00`, добавить параметр `always_cents: bool = False`. Но спецификация явно говорит "если .00 -- не показывать", поэтому отбрасываем.

1.3. Обновить `app/utils/__init__.py` -- добавить `format_rub` в экспорт.

1.4. Создать `tests/test_formatters.py` с 8+ тестами:
   - test_format_rub_positive: `15000` -> `"15 000 ₽"`
   - test_format_rub_negative: `-1200` -> `"−1 200 ₽"` (с типографским минусом)
   - test_format_rub_with_sign_positive: `2350.50, show_sign=True` -> `"+2 350.50 ₽"`
   - test_format_rub_with_sign_negative: `-1200, show_sign=True` -> `"−1 200 ₽"`
   - test_format_rub_zero: `0` -> `"0 ₽"`
   - test_format_rub_large_number: `1000000` -> `"1 000 000 ₽"`
   - test_format_rub_decimal_no_cents: `Decimal("15000.00")` -> `"15 000 ₽"`
   - test_format_rub_decimal_with_cents: `Decimal("1234.56")` -> `"1 234.56 ₽"`
   - test_format_amount_alias: `format_amount(Decimal("5000"))` -> `"5 000 ₽"` (обратная совместимость)

### Шаг 2: CSS-переменные + типографика

**Файлы**: `app/assets/custom.css`, `app/assets/calendar.css`, `app/assets/transactions.css`, `app/assets/onboarding.css`

2.1. Обновить `:root` в `custom.css`:
   - Заменить `--primary-green: #28a745` на `--color-primary: #2ecc71`
   - Заменить `--light-green: #20c997` на `--color-primary-dark: #27ae60`
   - Сохранить `--primary-green` и `--light-green` как alias (для постепенной миграции):
     ```css
     --primary-green: var(--color-primary);  /* deprecated */
     --light-green: var(--color-primary-dark);  /* deprecated */
     ```
   - Добавить 15 новых переменных по спецификации (секция 2)
   - Добавить CSS-переменную `--color-expense: #e74c3c` (вместо #17a2b8 для расходов)

2.2. Обновить hardcoded цвета в CSS-файлах:
   - `calendar.css`: 4 места `#28a745` -> `var(--color-primary)`, 1 место `#17a2b8` -> `var(--color-expense)`
   - `transactions.css`: 2 места `#28a745` -> `var(--color-primary)`
   - `onboarding.css`: 2 места `#28a745` -> `var(--color-primary)`, 1 место `#20c997` -> `var(--color-primary-dark)`, 1 rgba -> `rgba(46, 204, 113, 0.25)`
   - `custom.css`: обновить hardcoded #1e7e34 -> `--color-primary-hover: #27ae60`, rgba(40,167,69) -> rgba(46,204,113)

2.3. Добавить типографические классы:
   ```css
   .kpi-number { font-size: 40px; font-weight: 600; color: var(--color-text-primary); }
   .kpi-title { font-size: 12px; font-weight: 500; color: var(--color-text-secondary); text-transform: uppercase; }
   .kpi-subtitle { font-size: 12px; font-weight: 400; color: var(--color-text-secondary); }
   .kpi-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px; padding: 20px; }
   .kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
   .table-amount { font-size: 14px; color: var(--color-text-primary); text-align: right; }
   .table-description { font-size: 13px; color: var(--color-text-muted); }
   .link-show-all { font-size: 13px; font-weight: 600; color: var(--color-secondary); text-decoration: none; }
   .link-show-all:hover { text-decoration: underline; color: var(--color-secondary-dark); }
   ```

### Шаг 3: Переработка dashboard.py

**Файлы**: `app/components/dashboard.py`

3.1. Импортировать `format_rub` из `app.utils.formatters`.

3.2. Создать новую функцию `_build_kpi_card()` (или переработать `create_metric_card()`):
   - Белый фон, бордер `1px solid var(--color-border)` или тень
   - Радиус 10px, padding 20px
   - Заголовок: className="kpi-title"
   - Число: className="kpi-number"
   - Subtitle: className="kpi-subtitle"
   - Опциональный верхний бордер `border-top: 3px solid {status_color}`
   - Опциональная CTA кнопка (для Total Balance)

3.3. Переработать `build_overview_cards()`:
   - Заменить `f"${metrics['total_balance']:,.2f}"` на `format_rub(metrics['total_balance'])`
   - Заменить `f"${metrics['period_income']:,.2f}"` на `format_rub(metrics['period_income'])`
   - Заменить `f"${metrics['period_expense']:,.2f}"` на `format_rub(metrics['period_expense'])`
   - Savings: `format_rub(metrics['savings_current'])` и `format_rub(metrics['savings_target'])`
   - Русские подписи: "Баланс", "Доходы", "Расходы", "Накопления" вместо английских
   - Период: "За месяц" / "За год" вместо "This Month" / "This Year"
   - Total Balance: добавить кнопку "Сверка" (dcc.Link to `/calendar?open_recon=1`)

3.4. Обновить `build_cashflow_chart()`:
   - `marker_color="#28a745"` -> `marker_color="#27ae60"` (income)
   - `marker_color="#17a2b8"` -> `marker_color="#e74c3c"` (expense -- красный по спецификации)
   - Русские label: "Доходы" / "Расходы" вместо "Income" / "Expense"
   - Заголовок: "Денежный поток" вместо "Cashflow"

3.5. Обновить `build_statistics_card()`:
   - Заменить `f"${metrics['period_income']:,.0f}"` -> `format_rub(metrics['period_income'])`
   - Заменить `f"${metrics['period_expense']:,.0f}"` -> `format_rub(metrics['period_expense'])`
   - Обновить цвета: `#28a745` -> `#27ae60`, `#17a2b8` -> `#e74c3c`

3.6. Обновить `build_recent_transactions_card()`:
   - Заменить `f"+${tx['amount']:,.2f}"` -> `format_rub(tx['amount'], show_sign=True)` для income
   - Заменить `f"-${tx['amount']:,.2f}"` -> `format_rub(-tx['amount'])` для expense (или format_rub с отрицательным)
   - Убрать бейдж "Completed"
   - Русские label: "Недавние операции", "За месяц" / "За год"

3.7. Скрыть AI Assistant и Exchange:
   - В `create_dashboard_layout()`: закомментировать `create_ai_assistant_card()` и `create_exchange_card()` с TODO
   - Оставить функции `create_ai_assistant_card()` и `create_exchange_card()` в файле

### Шаг 4: Обновить calendar.py inline formatting

**Файлы**: `app/components/calendar.py`

4.1. Импортировать `format_rub` из `app.utils.formatters`.

4.2. Обновить `format_balance()` -- вернуть formatted строку с ₽ (сейчас возвращает без ₽, знак ₽ добавляется в месте вызова). **Важно**: `format_balance()` возвращает `tuple[str, str]` -- строку и CSS-класс. Не менять сигнатуру, только обновить formatting внутри.

4.3. Заменить inline в `_build_tooltip_balance()`:
   - `f"{balance:,.0f}".replace(",", " ") + " ₽"` -> `format_rub(balance)`

4.4. Заменить inline в `_build_tooltip_transaction_row()`:
   - `f"+{amount:,.0f}".replace(",", " ")` -> используем format_rub(amount) или специализированную версию (для tooltip нужны компактные числа без копеек -- format_rub уже отбрасывает .00)

4.5. Заменить в reconciliation callbacks:
   - `f"{expected:,.2f} ₽"` -> `format_rub(expected)` (2 места)
   - `f"Разница: {diff:+,.2f} ₽"` -> `f"Разница: {format_rub(diff, show_sign=True)}"`
   - `f"{adjustment.amount:+,.2f} ₽"` -> `format_rub(adjustment.amount, show_sign=True)` (2 места -- log и alert)

4.6. Обновить `build_stats_cards()`:
   - `f"+{income_formatted} ₽"` и `f"-{expense_formatted} ₽"` -- здесь format_balance уже дает строку без ₽, затем ₽ дописывается. Заменить на `format_rub(total_income, show_sign=True)` и аналогично.

4.7. Обновить `build_day_cell()`:
   - `f"{balance_text} ₽"` -- balance_text уже из format_balance(). Нужно скоординировать.
   - **Решение**: `format_balance()` остается для CSS-класса, но строку формируем через `format_rub()`.

### Шаг 5: Обновить analytics.py inline formatting

**Файлы**: `app/components/analytics.py`

5.1. Заменить 2 места с inline:
   - `f"{total:,.0f} ₽"` -> `format_rub(total)`
   - `f"<b>{total:,.0f}</b><br>₽"` -> f-string с format_rub (Plotly text annotation)

5.2. Plotly hovertemplate (`%{value:,.0f} ₽`, `%{y:,.0f} ₽`) -- это шаблоны Plotly, не Python форматирование. Их нельзя заменить на format_rub(). Оставить как есть -- пробел как разделитель тысяч в Plotly требует кастомного `hovertemplate` или `customdata`. **Решение**: оставить Plotly hovertemplates без изменений в этом батче; разделитель запятая в tooltip Plotly -- приемлемо для MVP, полная кастомизация Plotly tooltips отложена.

### Шаг 6: Финализация

6.1. Black: переформатировать все измененные файлы
6.2. Flake8: проверить E501, F401
6.3. Pytest: запустить полный набор >= 491 тестов
6.4. Ручная проверка в браузере (Dashboard, Calendar, Goals, Transactions, Analytics)
6.5. Обновить ROADMAP.md и feature_progress.md

## Зависимости

Новых библиотек не требуется. Все зависимости уже в проекте (Dash, Plotly, SQLAlchemy, etc).

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Изменение поведения format_amount (отбрасывание .00) ломает сравнения в тестах | Средняя | Проверить все тесты, использующие format_amount. grep по тестам на "format_amount" и ".00 ₽" |
| Пропущенные inline $ форматирования | Средняя | `grep -r "\$.*:,\|:,..*\$" app/` перед финализацией. В данном анализе найдены все 9 мест в dashboard.py и 10 в calendar.py |
| CSS каскад: замена #28a745 на #2ecc71 меняет оттенок Bootstrap .btn-success | Низкая | Bootstrap .btn-success использует свою переменную --bs-success, не наш --primary-green. Но custom.css переопределяет .btn-success: строки 95-96. Обновить эти строки на новый цвет |
| Reconciliation модал -- Dash duplicate output ID при двух страницах | Нет | Решение: навигация /calendar?open_recon=1, не дублирование модала |
| Plotly hovertemplate остается с запятой как разделитель | Низкая | Приемлемо для MVP; Plotly format `,.0f` использует запятую. Полная кастомизация -- отложена |
| calendar.py format_balance() возвращает строку без ₽, код добавляет ₽ отдельно | Средняя | Рефакторинг: format_balance() -> возвращает (format_rub(balance), css_class). Все 3 callsite обновить |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|----------------------------------------|-------------|----------------------|-----|
| 1 | Создать функцию format_rub() в app/utils/formatters.py | batch-1.md:Задача 2 | Шаг 1: format_rub() с show_sign, MINUS_SIGN, .00 отбрасывание | Must |
| 2 | Входные параметры: amount: Decimal / float, show_sign: bool = False | batch-1.md:Задача 2 | Шаг 1: сигнатура format_rub(amount: Decimal/float/int, show_sign: bool = False) | Must |
| 3 | format_rub(15000) -> "15 000 ₽" | batch-1.md:Задача 2 | Шаг 1: test_format_rub_positive | Must |
| 4 | format_rub(-1200, show_sign=True) -> "−1 200 ₽" | batch-1.md:Задача 2 | Шаг 1: test_format_rub_with_sign_negative, MINUS_SIGN U+2212 | Must |
| 5 | Обновить app/utils/__init__.py — экспорт format_rub | batch-1.md:Задача 2 | Шаг 1.3: добавить в __all__ | Must |
| 6 | Dashboard: KPI-карточки Total Balance, Income, Expense, Savings | batch-1.md:Задача 3 | Шаг 3.2-3.3: build_overview_cards() с format_rub() | Must |
| 7 | Calendar: Tooltip дней (баланс, операции) | batch-1.md:Задача 3 | Шаг 4.3-4.4: format_rub() в _build_tooltip_balance, _build_tooltip_transaction_row | Must |
| 8 | Goals: карточка цели, таблица взносов | batch-1.md:Задача 3 | Шаг 1.2: format_amount alias -> format_rub (goals.py не меняется) | Must |
| 9 | Transactions: таблица операций | batch-1.md:Задача 3 | Шаг 1.2: format_amount alias (transactions.py не меняется) | Must |
| 10 | Wishlist: карточка, модал | batch-1.md:Задача 3 | Шаг 1.2: format_amount alias (wishlist_service.py не меняется) | Must |
| 11 | Onboarding Wizard: поле starting_balance | batch-1.md:Задача 3 | Нет inline formatting (только ₽ в InputGroupText -- OK) | Info |
| 12 | Обновить _build_kpi_card() | batch-1.md:Задача 4 | Шаг 3.2: _build_kpi_card() или переработка create_metric_card() | Must |
| 13 | Total Balance: кнопка "Сверка" (зелёная) | batch-1.md:Задача 4 | Шаг 3.3: dcc.Link -> /calendar?open_recon=1 | Must |
| 14 | Скрыть AI Assistant и Exchange | batch-1.md:Задача 5 | Шаг 3.7: закомментировать вызовы, TODO Epic-08 | Must |
| 15 | CSS .kpi-number 40px | batch-1.md:Задача 6 | Шаг 2.3: CSS класс .kpi-number | Must |
| 16 | CSS .kpi-title 16px | batch-1.md:Задача 6 | Шаг 2.3: CSS класс .kpi-title (spec говорит 12-14px для заголовка карточки, 16px для medium) | Must |
| 17 | Новые CSS-переменные (15 штук) | batch-1.md:Задача 1 | Шаг 2.1: :root с --color-* переменными | Must |
| 18 | --color-primary: #2ecc71 | batch-1.md:Задача 1 | Шаг 2.1 | Must |
| 19 | Unit тесты format_rub (8 тестов) | batch-1.md:Задача 7 | Шаг 1.4: tests/test_formatters.py | Must |
| 20 | Black + Flake8 OK | batch-1.md:Задача 8 | Шаг 6.1-6.2 | Must |

## Blast Radius

### Прямые изменения (8 файлов)

- `app/utils/formatters.py` -- добавить format_rub(), переписать format_amount() как alias (~30 строк)
- `app/utils/__init__.py` -- добавить format_rub в экспорт (+1 строка)
- `app/assets/custom.css` -- новые переменные :root, типографические классы, обновление hardcoded цветов (~70 строк)
- `app/components/dashboard.py` -- полная переработка KPI-карточек, format_rub(), скрытие AI/Exchange (~150 строк)
- `app/components/calendar.py` -- замена 10+ inline форматирований на format_rub() (~30 строк)
- `app/components/analytics.py` -- замена 2 inline мест (~5 строк)
- `app/assets/calendar.css` -- замена 5 hardcoded #28a745/#17a2b8 на var() (~5 строк)
- `app/assets/transactions.css` -- замена 2 hardcoded #28a745 на var() (~2 строки)
- `app/assets/onboarding.css` -- замена 3 hardcoded цветов на var() (~3 строки)

### Новые файлы (1)

- `tests/test_formatters.py` -- 8+ тестов для format_rub() (~80 строк)

### Связанные файлы (затронуты через alias, но НЕ модифицируются)

- `app/components/goals.py` -- ~25 вызовов format_amount() -> работает через alias, визуально числа без .00
- `app/components/transactions.py` -- 1 вызов format_amount() -> работает через alias
- `app/components/wishlist.py` -- использует данные из wishlist_service.to_data() -> format_amount -> alias
- `app/services/wishlist_service.py` -- вызывает format_amount() -> alias
- `app/components/calendar_wishlist.py` -- 1 вызов format_amount() -> alias
- `app/components/onboarding_wizard.py` -- нет format вызовов, только ₽ в InputGroupText (ОК)
- `app/components/transaction_modals.py` -- нет format вызовов для денег (поля ввода)
- `app/assets/wishlist_hover.js` -- JS форматтер, уже использует ₽ (руб), не затронут

### Проверить после реализации

- [ ] Dashboard: 4 KPI-карточки отображаются без градиентов, числа в формате X XXX ₽
- [ ] Dashboard: кнопка "Сверка" на Total Balance ведет на /calendar?open_recon=1
- [ ] Dashboard: AI Assistant и Exchange не видны
- [ ] Dashboard: график Cashflow с зеленым (#27ae60) доходом и красным (#e74c3c) расходом
- [ ] Calendar: баланс в ячейках дней отображается в формате X XXX ₽
- [ ] Calendar: tooltip с балансом и суммами операций в формате X XXX ₽
- [ ] Calendar: модал сверки -- расчетный баланс и разница в формате X XXX ₽
- [ ] Goals: карточки целей, таблица взносов -- числа в формате X XXX ₽ (без .00)
- [ ] Transactions: таблица операций -- суммы в формате X XXX ₽
- [ ] Analytics: donut chart и bar chart -- числа в формате X XXX ₽
- [ ] Wishlist widget на Dashboard -- суммы в формате X XXX ₽
- [ ] Цвет зеленый accent #2ecc71 (проверить sidebar hover, кнопки, active state)
- [ ] Все 491+ тестов проходят (pytest)
- [ ] Black + Flake8 OK
- [ ] CSV экспорт -- символ ₽ корректно отображается в Excel (UTF-8 BOM)
