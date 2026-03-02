# Батч 2: Дневной график (ядро)

**Epic**: Epic-05-UI (Dashboard UI Redesign)
**Дата старта**: TBD (после батча 1)
**Статус**: 🔄 Планирование
**Протокол**: 0022-daily-cashflow-chart

---

## 🎯 Цель батча

Реализовать дневной график кассового календаря на Dashboard — центральный элемент новой UI спецификации:
1. Метод `DashboardService.get_daily_cashflow()` для агрегации дневных данных
2. Plotly grouped bar chart (доход зелёный / расход красный)
3. Линия баланса (running balance) с цветом по статусу OK/Attention/Risk
4. Маркер минимума месяца (кружок + подпись "Мин: дата, сумма")
5. Hover tooltip (дата, доход, расход, баланс)
6. Клик на день → модал создания операции с предвыбранной датой
7. Переключатель Month (дни) / Year (месяцы)
8. X-ось: подписи на кратных 7, сегодня подсвечено
9. Сетка: горизонтальные тихие (opacity 10-15%), вертикальные отсутствуют

**Приоритет**: Must Have — ядро Dashboard redesign, блокирует батч 3 (layout).

---

## ✅ Задачи (детальный checklist)

### Задача 1: TypedDicts для дневных данных
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1`

- [ ] Обновить `app/schema/dashboard.py`:
  - `DailyCashflow` TypedDict:
    ```python
    class DailyCashflow(TypedDict):
        date: date  # день месяца (YYYY-MM-DD)
        income: Decimal  # сумма доходов за день
        expense: Decimal  # сумма расходов за день
        balance: Decimal  # running balance (кумулятивный остаток)
    ```
  - `DailyBalancePoint` TypedDict (для маркера минимума):
    ```python
    class DailyBalancePoint(TypedDict):
        date: date  # дата минимума
        balance: Decimal  # значение минимума
        status: Literal["ok", "attention", "risk"]  # статус баланса
    ```
  - `MonthlyCashflowData` TypedDict:
    ```python
    class MonthlyCashflowData(TypedDict):
        daily: list[DailyCashflow]  # дни месяца
        min_balance_point: DailyBalancePoint | None  # минимум месяца
        current_date: date  # сегодня (для подсветки)
    ```
- [ ] Обновить `app/schema/__init__.py` — экспорт новых TypedDicts

**Файлы**: `app/schema/dashboard.py`, `app/schema/__init__.py`

---

### Задача 2: Метод `DashboardService.get_daily_cashflow()`
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 9 (API/Services)`

**Сигнатура**:
```python
def get_daily_cashflow(
    self,
    user_id: int,
    year: int,
    month: int
) -> MonthlyCashflowData:
    """
    Возвращает дневной cashflow для графика Dashboard.

    НЕ переиспользует CalendarService напрямую для производительности.

    Логика:
    1. Получить все операции месяца (TransactionService)
    2. Агрегировать доход/расход по дням
    3. Вычислить running balance (кумулятивный остаток):
       balance[day] = starting_balance + Σ(income - expense)[1..day]
    4. Найти минимум месяца (день + значение)
    5. Определить статус минимума:
       - balance < 0 → "risk"
       - balance < 5000 → "attention"
       - balance >= 5000 → "ok"

    Returns:
        MonthlyCashflowData с daily, min_balance_point, current_date
    """
```

**Детали реализации**:
- [ ] Получить starting_balance пользователя (User.starting_balance)
- [ ] Получить все операции месяца:
  - `TransactionService.get_by_date_range(user_id, start_date, end_date)`
  - start_date = первое число месяца
  - end_date = последнее число месяца
- [ ] Агрегировать по дням:
  - Доход: сумма INCOME операций за день
  - Расход: сумма EXPENSE операций за день (положительное число)
  - Для TRANSFER: не учитывать (или учитывать как 0/0)
  - Для ADJUSTMENT: считать как INCOME (если > 0) или EXPENSE (если < 0)
- [ ] Вычислить running balance:
  - balance[1] = starting_balance + (income[1] - expense[1])
  - balance[2] = balance[1] + (income[2] - expense[2])
  - ...
  - balance[N] = balance[N-1] + (income[N] - expense[N])
- [ ] Найти минимум месяца:
  - min_balance = min(balance[1..N])
  - min_date = день с минимальным балансом
  - min_status = "risk" | "attention" | "ok" (по условиям выше)
- [ ] Вернуть MonthlyCashflowData:
  - daily: список DailyCashflow для каждого дня месяца (1..N)
  - min_balance_point: DailyBalancePoint для минимума
  - current_date: datetime.date.today()

**Файлы**: `app/services/dashboard_service.py`

---

### Задача 3: Plotly график Month (grouped bar chart)
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Центральный график)`

**Действия**:
- [ ] Создать функцию `_build_daily_cashflow_chart()` в `app/components/dashboard.py`:
  - Параметры: `data: MonthlyCashflowData`, `period: Literal["month", "year"]`
  - Возвращает: `dcc.Graph` с Plotly figure
- [ ] **Month режим** — grouped bar chart:
  - X-ось: дни месяца (1, 2, 3, ..., N)
  - Y-ось: сумма (0..max(income+expense))
  - Столбцы доход (зелёный `#27ae60`):
    - `go.Bar(x=dates, y=incomes, name="Доход", marker_color="#27ae60")`
  - Столбцы расход (красный `#e74c3c`):
    - `go.Bar(x=dates, y=expenses, name="Расход", marker_color="#e74c3c")`
  - Barmode: `"group"` (столбцы рядом)
- [ ] **Линия баланса (running balance)**:
  - `go.Scatter(x=dates, y=balances, name="Баланс", mode="lines+markers")`
  - Толщина: 2-3px (`line=dict(width=2.5)`)
  - Цвет по статусу:
    - Логика: для каждого дня определить статус balance[day]
    - Если balance < 0 → красный (`#c0152f`)
    - Если 0 <= balance < 5000 → жёлтый (`#f39c12`)
    - Если balance >= 5000 → зелёный (`#27ae60`)
    - **Реализация**: использовать `line=dict(color=...)` с массивом цветов или сегменты (сложно в Plotly)
    - **Упрощение**: единый цвет по минимуму месяца (min_balance_point.status)
      - "ok" → зелёный
      - "attention" → жёлтый
      - "risk" → красный
- [ ] **Маркер минимума месяца**:
  - `go.Scatter(x=[min_date], y=[min_balance], mode="markers+text")`
  - Marker: кружок/бриллиант, размер 12px, цвет по статусу (красный/жёлтый/зелёный)
  - Text: `f"Мин: {min_date.day} {format_rub(min_balance)}"`
  - Позиция: `textposition="top center"` или `"bottom center"` (в зависимости от графика)

**Файлы**: `app/components/dashboard.py`

---

### Задача 4: X-ось, Y-ось, сетка
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Центральный график)`

- [ ] **X-ось**:
  - Подписи на кратных 7: дни 1, 8, 15, 22, 29 (если месяц 30-31 дней)
  - Tickvals: `[1, 8, 15, 22, 29]`
  - Ticktext: `["1", "8", "15", "22", "29"]`
  - Сегодня подсвечено: если `current_date.day` в месяце → добавить вертикальную линию (shape):
    ```python
    shapes=[
        dict(
            type="line",
            x0=current_date.day, x1=current_date.day,
            y0=0, y1=1, yref="paper",
            line=dict(color="#3498db", width=2, dash="dot")
        )
    ]
    ```
- [ ] **Y-ось**:
  - Минимум: 0 (не показывать отрицательные если нет)
  - Максимум: рассчитывается от `max(доход + расход)`
  - Формат чисел: `format_rub()` (но без ₽ на оси, только пробелы тысяч)
- [ ] **Сетка**:
  - Горизонтальные линии: `xaxis=dict(showgrid=False)`
  - Вертикальные линии: `yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.1)", gridwidth=1)`
  - Opacity: 10-15% (`rgba(0,0,0,0.1)`)

**Файлы**: `app/components/dashboard.py`

---

### Задача 5: Hover tooltip
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Интерактивность)`

- [ ] Настроить hovertemplate для столбцов и линии:
  - **Столбцы доход/расход**:
    ```python
    hovertemplate=(
        "<b>%{x} числа</b><br>"
        "Доход: %{y:,.0f} ₽<br>"  # для дохода
        "<extra></extra>"
    )
    ```
  - **Линия баланса**:
    ```python
    hovertemplate=(
        "<b>%{x} числа</b><br>"
        "Баланс: %{y:,.0f} ₽<br>"
        "<extra></extra>"
    )
    ```
  - **Совмещённый tooltip** (если возможно в Plotly):
    - При наведении на день показывать: Дата, Доход, Расход, Баланс
    - Реализация: использовать `hovermode="x unified"` в layout

**Файлы**: `app/components/dashboard.py`

---

### Задача 6: Клик на день → модал создания операции
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Интерактивность)`

- [ ] Добавить callback `open_create_from_chart()`:
  - Input: `Input("daily-cashflow-chart", "clickData")`
  - Outputs:
    - `Output("create-transaction-modal", "is_open", allow_duplicate=True)`
    - `Output("preselected-date", "data", allow_duplicate=True)`
  - Логика:
    - Получить `clickData["points"][0]["x"]` (день месяца)
    - Вычислить full date: `date(year, month, day)`
    - Открыть модал: `is_open=True`
    - Preselect дату: `preselected-date` Store = `date.isoformat()`
  - ADR-003 guard clauses: проверить `clickData is None`
- [ ] Интегрировать с Preselection Store Pattern (уже реализован в протоколе 0012):
  - Использовать `preselected-date` Store из `transaction_modals.py`
  - Callback `set_preselection_on_modal_open()` автоматически применит дату

**Файлы**: `app/components/dashboard.py`

---

### Задача 7: Переключатель Month / Year
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Режим переключения)`

- [ ] Добавить dbc.ButtonGroup над графиком:
  ```python
  dbc.ButtonGroup([
      dbc.Button("Месяц", id="chart-period-month", color="primary", outline=True),
      dbc.Button("Год", id="chart-period-year", color="primary", outline=True),
  ], id="chart-period-toggle")
  ```
- [ ] Добавить dcc.Store для хранения выбранного периода:
  ```python
  dcc.Store(id="chart-period", data="month")  # default: month
  ```
- [ ] Callback `toggle_chart_period()`:
  - Inputs:
    - `Input("chart-period-month", "n_clicks")`
    - `Input("chart-period-year", "n_clicks")`
  - Outputs:
    - `Output("chart-period", "data")`
    - `Output("chart-period-month", "outline")`
    - `Output("chart-period-year", "outline")`
  - Логика:
    - Если клик на "Месяц" → period = "month", outline=[False, True]
    - Если клик на "Год" → period = "year", outline=[True, False]
    - ADR-003 guard clauses: проверить `n_clicks is None`
- [ ] Callback `update_chart_on_period_change()`:
  - Inputs:
    - `Input("chart-period", "data")`
    - `Input("dashboard-refresh-trigger", "data")` (для автообновления)
  - Output: `Output("daily-cashflow-chart", "figure")`
  - Логика:
    - Если period = "month" → вызвать `get_daily_cashflow()`, построить дневной график
    - Если period = "year" → вызвать `get_yearly_cashflow()` (новый метод), построить месячный график
      - **Год режим**: столбцы по месяцам (1..12), линия среднего баланса
      - **Детали**: см. задачу 8

**Файлы**: `app/components/dashboard.py`

---

### Задача 8: Year режим (агрегированный по месяцам)
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 1 (Режим переключения)`

**ОПЦИОНАЛЬНО** (можно отложить, если блокирует батч):
- [ ] Метод `DashboardService.get_yearly_cashflow(user_id, year)`:
  - Возвращает `YearlyCashflowData` с агрегацией по месяцам:
    - monthly: list[MonthlyCashflow] (12 месяцев)
    - avg_balance: Decimal (средний баланс года)
  - Логика аналогична get_daily_cashflow(), но агрегация по месяцам
- [ ] График для Year режима:
  - X-ось: месяцы (Янв, Фев, Мар, ..., Дек)
  - Столбцы: доход/расход за месяц
  - Линия: средний баланс месяца (или running balance на конец месяца)

**Альтернатива**: Если Year режим не критичен для MVP, можно скрыть кнопку "Год" и реализовать позже.

**Файлы**: `app/services/dashboard_service.py`, `app/components/dashboard.py`, `app/schema/dashboard.py`

---

### Задача 9: Unit тесты для `get_daily_cashflow()`
**Действия**:
- [ ] Обновить `tests/test_dashboard_service.py`:
  - `test_get_daily_cashflow_basic()` — месяц с несколькими операциями, проверить daily, min_balance_point
  - `test_get_daily_cashflow_no_transactions()` — пустой месяц, баланс = starting_balance
  - `test_get_daily_cashflow_negative_balance()` — баланс уходит в минус, статус = "risk"
  - `test_get_daily_cashflow_attention_balance()` — баланс < 5000, статус = "attention"
  - `test_get_daily_cashflow_ok_balance()` — баланс >= 5000, статус = "ok"
  - `test_get_daily_cashflow_min_balance_point()` — минимум в середине месяца
  - `test_get_daily_cashflow_multiple_days()` — операции в разные дни, running balance правильный
  - `test_get_daily_cashflow_adjustment()` — ADJUSTMENT операция учитывается как income/expense
  - `test_get_daily_cashflow_transfer()` — TRANSFER не учитывается (или 0/0)
  - `test_get_daily_cashflow_current_date()` — current_date = today
- [ ] Запустить pytest — все тесты должны проходить (≥ 501 тестов, было 491 + 10 новых)

**Файлы**: `tests/test_dashboard_service.py`

---

### Задача 10: Финализация
- [ ] Black: переформатировать изменённые файлы
- [ ] Flake8: исправить E501, F401 (если есть)
- [ ] Pytest: запустить полный набор тестов (≥ 501)
- [ ] Проверить Dashboard в браузере:
  - График Month показывает дни 1..N
  - Столбцы доход (зелёный) / расход (красный)
  - Линия баланса с цветом по статусу
  - Маркер минимума месяца
  - Hover tooltip показывает дату, доход, расход, баланс
  - Клик на день открывает модал создания операции с предвыбранной датой
  - Переключатель Month/Year работает
  - X-ось: подписи на кратных 7, сегодня подсвечено
  - Сетка: горизонтальные тихие, вертикальные отсутствуют
- [ ] Обновить `feature_progress.md` — добавить батч 16

---

## 📊 Затронутые файлы с описанием изменений

### Новые файлы
Нет новых файлов в этом батче (TypedDicts добавляются в существующий `dashboard.py` schema).

### Модифицированные файлы

| Файл | Изменения | Строк (примерно) |
|------|-----------|------------------|
| `app/schema/dashboard.py` | +3 TypedDicts (DailyCashflow, DailyBalancePoint, MonthlyCashflowData) | +30 строк |
| `app/schema/__init__.py` | Экспорт новых TypedDicts | +3 строки |
| `app/services/dashboard_service.py` | `get_daily_cashflow()` метод (~150 строк логики) | +150 строк |
| `app/components/dashboard.py` | `_build_daily_cashflow_chart()` функция (~200 строк Plotly), переключатель Month/Year, 3 callbacks | +300 строк |
| `tests/test_dashboard_service.py` | +10 unit тестов для get_daily_cashflow() | +150 строк |

**Всего**: 5 файлов, ~633 строк добавлено

---

## ✅ Acceptance Criteria

### Visual
- [ ] График Month показывает дни месяца (1..N) на X-оси
- [ ] Столбцы доход зелёные (`#27ae60`), расход красные (`#e74c3c`)
- [ ] Линия баланса (running balance) толщина 2-3px, цвет по статусу:
  - Зелёный — баланс >= 5000
  - Жёлтый — 0 <= баланс < 5000
  - Красный — баланс < 0
- [ ] Маркер минимума месяца (кружок) с подписью "Мин: дата, сумма"
- [ ] X-ось: подписи на кратных 7 (1, 8, 15, 22, 29)
- [ ] Сегодня подсвечено вертикальной пунктирной линией (синяя)
- [ ] Сетка: только горизонтальные линии, opacity 10-15%

### UX
- [ ] Hover на день → tooltip с датой, доходом, расходом, балансом
- [ ] Клик на день → модал создания операции с предвыбранной датой
- [ ] Переключатель Month/Year работает без перезагрузки страницы
- [ ] После создания операции график автоматически обновляется (Refresh Trigger)

### Functional
- [ ] `get_daily_cashflow()` корректно агрегирует доход/расход по дням
- [ ] Running balance вычисляется правильно (кумулятивный остаток)
- [ ] Минимум месяца определяется правильно (день + значение + статус)
- [ ] ADJUSTMENT операции учитываются как income/expense
- [ ] TRANSFER операции не учитываются (или 0/0)

### Technical
- [ ] Все тесты проходят (pytest ≥ 501)
- [ ] Black + Flake8 OK (0 ошибок)
- [ ] Производительность: `get_daily_cashflow()` выполняется < 200ms (для месяца ~100 операций)
- [ ] Нет регрессий в других страницах

---

## 🔗 Зависимости и риски

### Зависимости
- **Блокируется**: Батч 1 (формат ₽, CSS-переменные)
- **Блокирует**: Батч 3 (layout) — таблицы операций используют Refresh Trigger

### Риски

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Производительность `get_daily_cashflow()` для больших данных | Средняя | Высокое | Оптимизация запроса к БД (индексы по date), кэширование результата |
| Plotly не поддерживает сегменты линии разных цветов | Высокая | Среднее | Упрощение: единый цвет линии по минимуму месяца (не динамический) |
| Конфликт Preselection Store с Calendar/Wishlist | Низкая | Среднее | Использовать единый Store `preselected-date` из протокола 0012 |
| Year режим блокирует батч | Средняя | Низкое | Отложить Year режим в отдельный батч (не критично для MVP) |

---

## 📝 Примечания

### Производительность
- **get_daily_cashflow() vs CalendarService**: Не переиспользуем CalendarService.get_balance_on_date() для каждого дня (30 запросов), а делаем 1 запрос для всех операций месяца + агрегация в Python.
- **Ожидаемая скорость**: < 200ms для месяца ~100 операций (vs ~600ms если через CalendarService)

### Plotly линия баланса — цвет сегментов
- **Проблема**: Plotly не поддерживает разные цвета сегментов линии "из коробки"
- **Решение 1 (упрощённое)**: Единый цвет линии по минимуму месяца (min_balance_point.status)
  - Если min_balance < 0 → вся линия красная
  - Если 0 <= min_balance < 5000 → вся линия жёлтая
  - Если min_balance >= 5000 → вся линия зелёная
- **Решение 2 (сложное)**: Разбить линию на несколько traces по статусам (много кода, может быть артефакты)
- **Рекомендация**: Решение 1 для MVP, Решение 2 — будущий эпик (если критично)

### Year режим
- **Опционально**: Если реализация Year режима усложняет батч, можно:
  1. Скрыть кнопку "Год" (оставить только "Месяц")
  2. Реализовать Year в отдельном батче/эпике
- **Критичность**: Низкая для MVP (Month режим достаточен)

### Маркер минимума
- **Реализация**: `go.Scatter` с 1 точкой + text
- **Позиционирование текста**: Если минимум внизу графика → `textposition="top center"`, если вверху → `"bottom center"` (автоматически по `y`)

---

**Статус**: ✅ Scope батча 2 финализирован, готов к протоколу 0022
