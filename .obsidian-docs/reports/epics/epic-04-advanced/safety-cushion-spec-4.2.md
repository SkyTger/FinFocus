# Epic-04.2: Финансовая подушка — Calendar Integration

**Статус:** Blocked (ждёт 4.1)
**Протокол:** 4.2 (второй из двух)
**Дата:** 2026-01-28
**Зависимости:** safety-cushion-spec-4.1.md
**Предыдущий:** Протокол 4.1 (Backend + Goals UI)

---

## Цель протокола

Добавить визуализацию порога подушки в кассовом календаре: подсветка дней ниже порога, маркер первого пересечения, дефицит в ячейках, KPI в шапке.

---

## Scope протокола 4.2

### Включено
- CalendarService: 3 новых метода для threshold
- Calendar UI: подсветка дней ниже порога
- Calendar UI: маркер первого дня пересечения
- Calendar UI: дефицит "−X тыс. ₽" в ячейках
- Calendar UI: KPI "−X тыс. ₽ до порога" в шапке
- Calendar CSS
- Unit тесты для CalendarService

### Исключено (уже в протоколе 4.1)
- Schema User fields
- SafetyCushionService
- Goals UI карточка/модал

---

## Предусловия (из протокола 4.1)

Протокол 4.1 должен быть завершён:
- User.cushion_threshold существует
- SafetyCushionService.get_settings() работает
- Пользователь может настроить подушку на /goals

---

## CalendarService расширение

**Файл:** `app/services/calendar_service.py`

### Новые методы

```python
def get_days_below_threshold(
    self,
    user_id: int,
    year: int,
    month: int,
    threshold: Decimal,
) -> list[date]:
    """Получить список дней с балансом ниже порога."""
    if threshold <= 0:
        return []

    balances = self.calculate_daily_balances(
        user_id,
        date(year, month, 1),
        self._get_month_end(year, month),
    )

    return [day for day, balance in balances.items() if balance < threshold]


def get_first_threshold_crossing(
    self,
    user_id: int,
    year: int,
    month: int,
    threshold: Decimal,
) -> date | None:
    """Получить первый день в месяце, где баланс < порог."""
    days_below = self.get_days_below_threshold(user_id, year, month, threshold)
    return min(days_below) if days_below else None


def calculate_deficit(self, balance: Decimal, threshold: Decimal) -> Decimal:
    """Рассчитать дефицит до порога."""
    if threshold <= 0 or balance >= threshold:
        return Decimal(0)
    return threshold - balance
```

### Хелпер для форматирования дефицита

**Файл:** `app/utils/formatters.py`

```python
def format_deficit(deficit: Decimal) -> str:
    """Форматировать дефицит: −7 тыс. ₽"""
    if deficit <= 0:
        return ""

    thousands = int(deficit / 1000)
    if thousands == 0:
        return f"−{int(deficit)} ₽"

    return f"−{thousands} тыс. ₽"
```

---

## Calendar UI — Подсветка

**Файл:** `app/components/calendar.py`

### Условие отображения

Подсветка показывается **только если** `cushion_threshold > 0`:
- threshold = 0 → подушка не настроена, не показывать
- threshold > 0 → показывать подсветку для дней с balance < threshold

### Модификация build_day_cell()

```python
def build_day_cell(
    day_date: date,
    balance: Decimal,
    transactions: list[TransactionInfo],
    is_today: bool = False,
    is_current_month: bool = True,
    is_weekend: bool = False,
    # Новые параметры для threshold
    threshold: Decimal = Decimal(0),
    is_first_crossing: bool = False,
) -> html.Div:
    """Построить ячейку дня с учётом порога подушки."""

    css_classes = ["calendar-day"]
    # ... существующие классы ...

    # Подсветка ниже порога
    if threshold > 0 and balance < threshold:
        css_classes.append("calendar-day-below-threshold")

    # Маркер первого пересечения
    if is_first_crossing:
        css_classes.append("calendar-day-threshold-crossed")

    # Дефицит в ячейке
    deficit_text = None
    if threshold > 0 and balance < threshold:
        deficit = threshold - balance
        deficit_text = format_deficit(deficit)

    # ... построение ячейки ...
```

### Структура ячейки с дефицитом

```
┌─────────────┐
│ 27          │  ← номер дня
│ ↓ ↑         │  ← иконки транзакций
│ 38 000 ₽    │  ← баланс
│ −7 тыс. ₽   │  ← дефицит (новое)
└─────────────┘
```

### Модификация load_and_navigate_calendar()

```python
@callback(...)
def load_and_navigate_calendar(...):
    # ... существующий код ...

    # Получить threshold из User
    cushion_service = SafetyCushionService(session)
    settings = cushion_service.get_settings(user_id)
    threshold = settings["threshold"]

    # Получить первый день пересечения
    first_crossing = None
    if threshold > 0:
        first_crossing = calendar_service.get_first_threshold_crossing(
            user_id, year, month, threshold
        )

    # Передать в build_calendar_grid()
    grid = build_calendar_grid(
        ...,
        threshold=threshold,
        first_crossing_date=first_crossing,
    )
```

---

## Calendar UI — KPI в шапке

**Файл:** `app/components/calendar.py`

### Модификация build_stats_cards()

Добавить вторую строку под "Баланс на конец месяца" **только при дефиците**:

```
┌─────────────────────┐
│ Баланс на конец     │
│ 38 000 ₽            │
│ −7 тыс. ₽ до порога │  ← только если дефицит
└─────────────────────┘
```

```python
def build_stats_cards(
    summary: MonthSummary,
    threshold: Decimal = Decimal(0),
) -> html.Div:
    """Построить статистические карточки месяца."""

    # ... существующие карточки Income, Expense ...

    # Карточка баланса с дефицитом
    end_balance = summary["end_balance"]
    deficit = Decimal(0)
    if threshold > 0 and end_balance < threshold:
        deficit = threshold - end_balance

    balance_card = dbc.Card([
        dbc.CardBody([
            html.P("Баланс на конец", className="stats-label"),
            html.H4(format_currency(end_balance), className="stats-value"),
            # Дефицит — только если есть
            html.P(
                f"{format_deficit(deficit)} до порога",
                className="stats-deficit",
            ) if deficit > 0 else None,
        ])
    ])

    return html.Div([income_card, expense_card, balance_card], ...)
```

---

## Calendar CSS

**Файл:** `app/assets/calendar.css`

```css
/* Подсветка дня ниже порога */
.calendar-day-below-threshold {
    background-color: rgba(255, 152, 0, 0.15) !important;
}

/* Маркер первого дня пересечения */
.calendar-day-threshold-crossed {
    border-left: 3px solid #ff9800 !important;
}

/* Дефицит в ячейке дня */
.calendar-day-deficit {
    font-size: 0.7rem;
    color: #ff9800;
    margin-top: 2px;
}

/* Дефицит в KPI шапки */
.stats-deficit {
    font-size: 0.85rem;
    color: #ff9800;
    margin-top: 4px;
    margin-bottom: 0;
}
```

---

## Правила поведения

1. **Условие подсветки**: только если `cushion_threshold > 0`
2. **При изменении операции**: подсветка пересчитывается автоматически (существующий refresh)
3. **Маркер пересечения**: только на **первом** дне ниже порога в месяце
4. **Баланс восстановился**: подсветка исчезает с этого дня
5. **Формат дефицита**: округление до тысяч ("−7 тыс. ₽")

---

## Технический план

### Шаг 1: CalendarService методы

**Файл:** `app/services/calendar_service.py`
- get_days_below_threshold()
- get_first_threshold_crossing()
- calculate_deficit()

### Шаг 2: formatters.py

**Файл:** `app/utils/formatters.py`
- format_deficit()

### Шаг 3: build_day_cell() модификация

**Файл:** `app/components/calendar.py`
- Новые параметры: threshold, is_first_crossing
- CSS классы для подсветки
- Дефицит в ячейке

### Шаг 4: build_stats_cards() модификация

**Файл:** `app/components/calendar.py`
- Параметр threshold
- KPI дефицита под балансом

### Шаг 5: load_and_navigate_calendar() модификация

**Файл:** `app/components/calendar.py`
- Получение threshold через SafetyCushionService
- Получение first_crossing
- Передача в build функции

### Шаг 6: Calendar CSS

**Файл:** `app/assets/calendar.css`
- .calendar-day-below-threshold
- .calendar-day-threshold-crossed
- .calendar-day-deficit
- .stats-deficit

### Шаг 7: Unit тесты

**Файл:** `tests/test_calendar_threshold.py`
- test_get_days_below_threshold_none()
- test_get_days_below_threshold_some()
- test_get_first_threshold_crossing()
- test_calculate_deficit()
- test_format_deficit()

---

## Acceptance Criteria (протокол 4.2)

### Подсветка календаря
- [ ] Подсветка **только если** `cushion_threshold > 0`
- [ ] Дни с `balance < threshold` подсвечены слабым оранжевым
- [ ] Маркер на первом дне пересечения порога в месяце
- [ ] Дефицит "−X тыс. ₽" в ячейках ниже порога

### KPI в шапке
- [ ] "−X тыс. ₽ до порога" под балансом на конец месяца
- [ ] Показывается **только при дефиците**

### Поведение
- [ ] Подсветка обновляется при изменении операций
- [ ] Подсветка обновляется при изменении настроек подушки
- [ ] Маркер перемещается при изменении первого дня провала

### Backend
- [ ] CalendarService методы работают
- [ ] format_deficit() форматирует корректно
- [ ] Unit тесты проходят

---

## Результат протокола

После завершения протоколов 4.1 + 4.2:
- Полноценная фича "Финансовая подушка"
- Настройка на /goals
- Визуализация в календаре
- Пользователь видит риски провала ниже порога заранее

---

## Тестирование end-to-end

1. Настроить подушку на /goals (цель: 100 000 ₽, порог: 30 000 ₽)
2. Перейти на /calendar
3. Проверить: дни с балансом < 30 000 ₽ подсвечены оранжевым
4. Проверить: маркер на первом дне ниже порога
5. Проверить: дефицит в ячейках ("−X тыс. ₽")
6. Проверить: KPI в шапке если баланс на конец < порога
7. Изменить операцию → проверить обновление подсветки
8. Сбросить подушку → подсветка исчезает

---

## Ссылки

- Основная спека: `safety-cushion-spec.md`
- Протокол 4.1: `safety-cushion-spec-4.1.md`
- ROADMAP.md: Epic-04 (Advanced Features)
