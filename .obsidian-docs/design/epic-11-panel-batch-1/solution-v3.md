# Solution v3: MoneyLayersService — единая формула резерва «по дате D», шапка без вердикта

## Обзор решения

Три сущностных изменения относительно v2 и шесть инженерных.

**Сущностно:**

1. **Вердикт-светофор полностью убран** (решение владельца, п. 3а). Шапка = «Свободно сегодня: N ₽» + разбор «баланс − платежи − резерв». Из контракта уходят `VerdictLevel`, `LayersVerdict.level/text/dip_threshold`, `DIP_RATIO`, `DIP_FLOOR`, `VERDICT_TEXTS`, `VERDICT_COLORS`, сигнальная шина. `LayersVerdict` переименован в `TodaySlice` (только срез дня), а минимум окна переехал в `MoneyLayersData.min_free`/`min_free_date` — он нужен графику для маркера (FR-3.e), а не шапке.

2. **Слой «Резерв» — единая формула от даты D, без режимного ветвления** (замечания №1, №2; Подход A критика, проверенный численно ниже на 9 кейсах). Формула:
   ```
   consumed(D)   = Σ savings_* с датой в [month_start(D), D]
   committed(D)  = Σ savings_* с датой в (D, month_end(D)]
   goals_part(D) = max(0, monthly_budget − consumed(D) − committed(D))
   ```
   Из пути модели уходят `BudgetReservationService.get_settings` (кроме `monthly_budget`), `get_budget_progress` и приватный `_get_reserve_sum_for_month`. Никакого наследования базы через границу месяца: месяц берётся по дню D. Риск «Высокая» из таблицы v2 исчезает вместе с ветвлением.

3. **Обрезка «Резерва» — в одном месте** (решение владельца, п. 3б). `cushion_part(D) = cushion_threshold` без `min(..., balance)`. Вся защита «не больше, чем есть» — исключительно в каскаде `_split_day`. Тултип слоя говорит **факт дня**, а не настроенное число, когда полоса сжата.

**Инженерно:** операции собираются **одним** вызовом на диапазон `[month_start(reference_date), window_end]` (замечание №6 — источник данных за границей месяца появился, а `payments_end` теперь чисто арифметический фильтр); `is_empty` считается из уже полученных данных без отдельного `count(*)` (№8); `MAX_MILESTONES_IN_WINDOW` приведён в листинге контракта (№9); `_axis_dtick` заменён на `_axis_tickvals` — явные тики-даты вместо спорных единиц dtick (№10); список правок в тестах закрыт grep'ом — три теста, не два (№3); в план тестов добавлен блок «таблица ожидаемых слоёв» — параметризованный тест с числами по всем трём слоям (№7); деградация обозначается в UI без вердикта — пометкой в разборе (замена замечания №8 критики v2 после снятия вердикта).

## Архитектура

### Компоненты

**1. `app/schema/money_layers.py` (новый) — контракт модели**

TypedDict'ы `DayLayers`, `UpcomingPayment`, `GoalMilestone`, `TodaySlice`, `MoneyLayersData`; литерал `LayerKey`; константы `WINDOW_DAYS = 45`, `MAX_MILESTONES_IN_WINDOW = 3`, `LAYER_COLORS`, `LAYER_LABELS`. Ноль зависимостей от Dash/SQLAlchemy (стиль `app/schema/dashboard.py`). Пометка в модуль-докстринге: контракт спроектирован под кусок 1 и не претендует на стабильность до куска 2.

Всё, что относилось к вердикту (`VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`), **не создаётся** — решение владельца п. 3а.

**2. `app/services/money_layers_service.py` (новый) — ядро FR-1**

Единственный публичный метод `get_money_layers(user_id, reference_date=None) -> MoneyLayersData`. Read-only.

Три диапазона дат — это ключевое изменение относительно v2, где их было два и данных не хватало:

| Диапазон | Границы | Назначение |
|---|---|---|
| **Окно оси** `[reference_date, window_end]` | `reference_date + 44` (45 дней вкл.) | Дни в `days[]`, ось X, зона поиска минимума, вехи целей |
| **Диапазон сбора операций** `[collect_start, window_end]` | `collect_start = month_start(reference_date)` | ЕДИНСТВЕННЫЙ вызов `get_all_transactions_for_period`. Левая граница — начало месяца `reference_date`, потому что `consumed(reference_date)` требует savings-операций **до** сегодня в пределах текущего месяца |
| **Горизонт слоя «Платежи»** `payments_end` | последний день календарного месяца `reference_date` | Чисто арифметический фильтр суффиксной суммы (C-5) |

Приватные шаги:

- `_horizons(reference_date) -> Horizons` → `(collect_start, window_end, payments_end)`;
- `_forecast_balances()` → `CalendarService.calculate_daily_balances(user_id, reference_date, window_end)` — единственный источник прогнозного остатка (AC-3 по построению);
- `_collect_operations()` → **один** `CalendarService.get_all_transactions_for_period(user_id, collect_start, window_end)`. Возвращает две материализованные структуры: `payments: list[UpcomingPayment]` (расходные операции) и `savings_by_date: dict[date, Decimal]` (только `savings_reserve` + `savings_contribution`);
- `_payments_tail_by_day()` → `payments(D) = Σ` платежей с датой в `(D, payments_end]`, где учитываются только платежи с датой `>= reference_date` (операции первых дней месяца, уже прошедшие, в слой «Платежи» не входят — они уже вычтены из `balance`). `payments(D) = 0` для `D >= payments_end` — видимая честность C-5;
- `_goals_part_by_day()` → единая формула (ниже);
- `_split_day()` → каскад сжатия слоёв, сумма == остаток во всех ветках. **Единственный** механизм обрезки «Резерва» (решение владельца п. 3б);
- `_today_slice()` → `TodaySlice` (free/balance/payments/reserve на `reference_date`);
- `_window_min_free()` → `(min_free, min_free_date)` по всему окну — для маркера графика FR-3.e;
- `_goal_milestones()` → материализация активных целей в `GoalMilestone` **внутри сессии**;
- `_is_empty()` → чистая функция от уже полученных данных, **без запросов** (№8).

**Семантика слоя «Резерв» — единая формула (закрывает 🔴№1 и 🔴№2).**

```
cushion_part           = cushion_threshold                     # константа по окну
month_start(D)         = date(D.year, D.month, 1)
month_end(D)           = date(D.year, D.month, monthrange(D.year, D.month)[1])
consumed(D)            = Σ savings_by_date[d] для d в [month_start(D), D]
committed(D)           = Σ savings_by_date[d] для d в (D, month_end(D)]
goals_part(D)          = max(0, monthly_budget − consumed(D) − committed(D))
reserve_raw(D)         = cushion_part + goals_part(D)
```

Три свойства, которых не было в v2:

- **Ноль двойного счёта.** Каждая savings-операция попадает ровно в одно из двух слагаемых — по своей дате относительно D. Никакого агрегата «прогресс за месяц» (`get_budget_progress`), который не знает про D. Никакого приватного `_get_reserve_sum_for_month`, который считает будущий exception одновременно с суффиксной суммой платежей.
- **Ноль наследования через границу месяца.** Месяц берётся по дню D. `goals_part` не накапливается: см. трассировку кейса №9 в «Модели данных» — на 30 сентября `goals_part = 0`, а не 30 000.
- **Ноль зависимости от режима.** Формула спрашивает у кассового календаря «какие savings-операции стоят на этих датах», а не у бюджетного сервиса «сколько израсходовано за месяц». В `fixed_date` взнос транзакции не создаёт (`create_contribution_transaction` → `None`, `budget_reservation_service.py:669-672`), но заменивший его exception стоит в списке операций; в `from_balance` взнос — это `SAVINGS_CONTRIBUTION` в списке операций. Оба режима видны одной линзой. Это прямой ответ на структурную заметку критика: вопрос «сколько лежит в остатке на день D» задаётся тому источнику, который знает ответ.

**Почему `committed(D)` ограничен `month_end(D)`, а слой «Платежи» — `payments_end`.** Это разные величины и это не ошибка. `payments_end` = конец месяца **`reference_date`** (C-5 буквально: слой «Платежи» не показывает следующий месяц). `month_end(D)` = конец месяца **дня D**. Для `D <= payments_end` они совпадают, и `committed(D)` равен savings-части слоя «Платежи» — деньги не удваиваются: они лежат в оранжевом, и потому вычтены из синего. Для `D > payments_end` оранжевый слой пуст (C-5), но синий продолжает жить по бюджету месяца дня D — что и требует эскиз («в сентябре в резерве снова лежит непотраченный бюджет нового месяца»). Инвариант AC-3 при этом держится конструктивно: `free` выводится вычитанием.

**Обрезка «Резерва» — один механизм (решение владельца п. 3б, закрывает 🟡№4).** `cushion_part` больше не сжимается через `min(threshold, balance)`. Если `balance(D) < payments(D) + reserve_raw(D)`, каскад `_split_day` гасит дефицит из `reserve`, затем из `payments`. Синяя полоса на здоровых данных стоит ровно на настроенном числе; просаживается только там, где денег физически меньше, — и это осмысленный сигнал «в этот день вы залезаете в подушку».

**Честная подпись слоя (обязательство п. 3б).** Тултип «Резерв» строится из **фактического** значения дня, а не из настройки:
- если `reserve_today == cushion_threshold + goals_reserve_today` (полоса не сжата) — «Порог подушки {cushion_threshold} + бюджет целей {goals_reserve_today}»;
- если полоса сжата — «В этот день на резерв остаётся {reserve_today} из {cushion_threshold + goals_reserve_today} — вы залезаете в подушку». Цифра в тултипе всегда совпадает с высотой полосы.
Поэтому в контракт добавлено поле `reserve_configured_today` — настроенная сумма — рядом с фактическим `TodaySlice.reserve`. Расхождение цифры и картинки, которое критик назвал P1-болью внутри одного блока, исключено конструктивно: UI не имеет доступа к настройке без факта.

**3. `app/services/cushion_service.py` (изменяется — ДОБАВЛЕНИЕ метода)**

`get_threshold_amount(user_id) -> Decimal` — `target * percent / 100` без `_get_current_balance()`. Проверено по коду: `threshold_amount` в `get_settings` (`cushion_service.py:104-107`) от баланса не зависит; баланс нужен только для `current_amount`/`progress` (`:100`, `:113-118`). Колонки суммы порога в схеме нет — `cushion_threshold_manual` булев (`database.py:107`), сумма всегда по формуле. Возвращает `Decimal("0")` при отсутствии пользователя (тихий дефолт, без `ValidationError` — на чистой базе это штатный путь).

**4. `app/components/dashboard.py` (изменяется) — FR-2…FR-6**

- `build_free_header(data, profile) -> html.Div` (переименован из `build_verdict_header` — в нём больше нет вердикта). Состав: приветствие, метка «Свободно сегодня», сумма, разбор «баланс − платежи − резерв», аватар+имя, кнопка «Сверка», шестерёнка. Без чипа, без сигнальной шины, без цветовой окраски по уровню.
- `build_layers_chart(data) -> dbc.Card` — вместо `_build_daily_cashflow_chart()` / `_build_yearly_cashflow_chart()`.
- `_build_layer_legend(data)` / `_build_payments_tooltip(data)` / `_build_reserve_tooltip(data)` — HTML-легенда вне поля графика (`showlegend=False`) с `dbc.Tooltip` (FR-4 + заметка vision-критика). Только текстовые компоненты; `dangerously_allow_html` и `dcc.Markdown` в новых путях запрещены.
- `_build_header_empty_state()` / `_build_chart_empty_state()` — FR-6.
- `_axis_tickvals(dates) -> list[date]` — явный список тиков (заменяет `_axis_dtick`, №10).
- `_load_dashboard_components(period_state)` — сигнатура **сокращается** (решение по 🟡№3, ниже).
- `open_create_from_chart` перепривязывается на `dashboard-layers-chart-graph`, дата берётся из `point["x"]` (ISO-строка).

**5. `app/components/profile_modal.py` (изменяется — прямые изменения, решение владельца)**

Второй `Input("dashboard-settings-cog", "n_clicks")` и ветка `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")` вместо жёсткого `==` (:119). Единственный Input сейчас — `sidebar-profile-container` (:96). `suppress_callback_exceptions=True` (`main.py:41`) снимает риск отсутствия элемента вне дашборда.

**6. `app/assets/panel.css` (новый) — стили `pnl-*`** на CSS-переменных проекта. Отдельный файл — установленный паттерн (`analytics.css`, `calendar.css`, `goals.css`, `wishlist.css`).

### Диаграмма взаимодействия

```
┌───────────────────────────────────────────────────────────────────┐
│ app/components/dashboard.py                                       │
│   load_dashboard_data(pathname, profile_updated, period_state)    │
│   refresh_dashboard_after_crud(trigger, period_state, pathname)   │
│                    │                                              │
│                    ▼                                              │
│   _load_dashboard_components(period_state)   ← «period» УБРАН      │
└────────────────────┬──────────────────────────────────────────────┘
                     │ get_money_layers(user_id)   [1 вызов]
                     ▼
┌───────────────────────────────────────────────────────────────────┐
│ MoneyLayersService   (НОВЫЙ, read-only, без flush/commit)          │
│                                                                   │
│  _horizons()  → collect_start = month_start(ref)                  │
│                 window_end    = ref + 44        (ось, 45 дней)    │
│                 payments_end  = month_end(ref)  (C-5)             │
│                                                                   │
│  _forecast_balances(ref .. window_end) ──────────────┐            │
│                                                       │            │
│  _collect_operations(collect_start .. window_end) ────┼──┐  ОДИН   │
│      ├─► payments:        list[UpcomingPayment]       │  │  вызов  │
│      └─► savings_by_date: dict[date, Decimal]         │  │  (№6)   │
│                                                       │  │         │
│  _payments_tail_by_day()  Σ в (D, payments_end]  ─────┤  │         │
│  _goals_part_by_day()     ЕДИНАЯ формула по месяцу D ─┤  │         │
│      goals(D)=max(0, budget − consumed(D) − committed(D))         │
│  reserve_raw(D) = cushion_threshold + goals(D)   БЕЗ min()        │
│                                                       │  │         │
│  _split_day()  free = bal − pay − res (+каскад)  ─────┘  │  ← ЕДИН-│
│                                                          │    СТВЕН-│
│  _today_slice()      срез reference_date                 │    НАЯ  │
│  _window_min_free()  минимум по 45 дням (FR-3.e)         │    обрез-│
│  _goal_milestones()  материализация В СЕССИИ ──┐         │    ка   │
│  _is_empty()  БЕЗ запроса: из days+savings+     │        │  (п.3б) │
│               templates_exist+starting_balance  │        │         │
└────────────────────────────────────────────────┼────────┼─────────┘
                                                 │        │
        ┌────────────────────────────────────────┘        │
        ▼                     ▼                  ▼        ▼
┌──────────────┐  ┌───────────────────────┐  ┌────────────────────────┐
│ GoalService  │  │ CushionService        │  │ CalendarService        │
│ get_all_by_  │  │ get_threshold_amount()│  │ calculate_daily_       │
│ user(ACTIVE) │  │   ← НОВЫЙ, БЕЗ        │  │   balances             │
└──────────────┘  │     пересчёта баланса │  │ get_all_transactions_  │
                  └───────────────────────┘  │   for_period  (1 раз)  │
                  ┌───────────────────────┐  └──────────┬─────────────┘
                  │ BudgetReservation     │             ▼
                  │ Service               │      RecurringService
                  │ get_settings() →      │      (виртуальные +
                  │   monthly_budget      │       exceptions)
                  │   ТОЛЬКО              │
                  └───────────────────────┘
                    ✗ get_budget_progress          — БОЛЬШЕ НЕ ВЫЗЫВАЕТСЯ
                    ✗ _get_reserve_sum_for_month    — БОЛЬШЕ НЕ ВЫЗЫВАЕТСЯ
                    ✗ mode / day_of_month           — БОЛЬШЕ НЕ ЧИТАЮТСЯ
                     ↑ ни один существующий метод не меняется (C-3)

Возврат: MoneyLayersData ─┬─► build_free_header()   «Свободно сегодня: N ₽»
                          │                          + разбор, БЕЗ вердикта
                          ├─► build_layers_chart()   stacked bars 45 дней
                          │                          + маркер min_free
                          └─► _build_layer_legend()  dbc.Tooltip (FR-4)

app/components/profile_modal.py ← НОВЫЙ Input("dashboard-settings-cog")
```

## Файловая структура

```
НОВЫЕ:
app/schema/money_layers.py            TypedDict'ы модели, LayerKey, константы
                                      (WINDOW_DAYS=45, MAX_MILESTONES_IN_WINDOW=3,
                                       LAYER_COLORS, LAYER_LABELS)
                                      БЕЗ VerdictLevel/VERDICT_*/DIP_* (п. 3а)
app/services/money_layers_service.py  MoneyLayersService: композиция над Calendar/
                                      Cushion/BudgetReservation(только budget)/Goal
app/assets/panel.css                  Стили pnl-* (шапка + блок графика + легенда)
tests/test_money_layers_service.py    Таблица ожидаемых слоёв (№7), инвариант AC-3,
                                      «таяние», границы месяцев, порог подушки,
                                      is_empty, детач, fail-open

ИЗМЕНЯЕМЫЕ:
app/services/cushion_service.py       +get_threshold_amount() — ДОБАВЛЕНИЕ метода
app/components/dashboard.py           крупнейший blast — см. Blast Radius
app/components/profile_modal.py       +Input("dashboard-settings-cog") и ветка
app/schema/__init__.py                реэкспорт новых типов + __all__
app/services/__init__.py              реэкспорт MoneyLayersService + типов + __all__
app/assets/custom.css                 чистка: #dashboard-overview-cards,
                                      .db-period-switcher, .kpi-*
tests/test_dashboard_callbacks.py     ТРИ теста (:62, :188, :212) + докстринг модуля
tests/test_cushion_service.py         +тесты get_threshold_amount

НЕ ИЗМЕНЯЮТСЯ (доказательство C-3):
app/services/calendar_service.py, dashboard_service.py, goal_service.py,
budget_reservation_service.py, recurring_service.py, app/components/sidebar.py
tests/test_dashboard_service.py, tests/test_calendar_service.py,
tests/test_budget_reservation_service.py, tests/test_goal_service.py
```

## Ключевые интерфейсы

```python
# app/schema/money_layers.py
"""Контракт модели «свободно / платежи / резерв» по дням (EPIC-11, кусок 1).

Note:
    Контракт спроектирован под кусок 1 (шапка + график полос).
    Стабильность до куска 2 (карточки-двери) не гарантируется —
    осознанное решение, зафиксировано в memory/spec-context/epic-11.md.

Note:
    Цветового вердикта состояния (ok/dip/problem) в контракте НЕТ —
    решение владельца 2026-08-24 (memory/spec-context/epic-11.md, п. 3а):
    любой порог просадки произволен, проблемные дни пользователь видит
    на самом графике. Поле min_free оставлено не для вердикта, а для
    маркера минимума на графике (FR-3.e).
"""

from datetime import date
from decimal import Decimal
from typing import Literal, NamedTuple, TypedDict

LayerKey = Literal["free", "payments", "reserve"]
"""Ключ слоя декомпозиции прогнозного остатка."""

WINDOW_DAYS = 45
"""Длина окна оси графика в днях (включая сегодня).

Соответствует принятому эскизу .visual/finfocus-panel-dashboard/v3.html
(22 авг — 5 окт 2026). Горизонт слоя «Платежи» — отдельная величина,
конец календарного месяца (C-5), см. MoneyLayersService._horizons.
"""

MAX_MILESTONES_IN_WINDOW = 3
"""Максимум вех целей внутри окна (ближайшие по target_date).

Остальные попадают сводкой «и ещё N целей» в тултип слоя «Резерв»:
45-дневная ось не должна зарастать флажками (заметка vision-критика
про вертикальный ритм). Плюс не более одной вехи beyond_window.
"""

TARGET_X_TICKS = 11
"""Целевое число подписей на оси X (в принятом эскизе v3 — 11)."""

LAYER_COLORS: dict[LayerKey, str] = {
    "free": "#2ecc71",      # Свободно — зелёный (эскиз v3)
    "payments": "#f0b775",  # Платежи — оранжевый приглушённый (эскиз v3)
    "reserve": "#3498db",   # Резерв — синий (эскиз v3)
}
"""Цвета слоёв графика — единственный источник правды (паттерн STATUS_COLORS)."""

LAYER_LABELS: dict[LayerKey, str] = {
    "free": "Свободно",
    "payments": "Платежи",
    "reserve": "Резерв целей и подушки",
}
"""Подписи слоёв в HTML-легенде (формулировки эскиза v3)."""


class Horizons(NamedTuple):
    """Три границы модели — почему их три, см. докстринг _horizons.

    Attributes:
        collect_start: Левая граница ЕДИНСТВЕННОГО сбора операций —
            начало календарного месяца reference_date. Нужна потому,
            что consumed(reference_date) требует savings-операций,
            датированных ДО сегодня в пределах текущего месяца.
        window_end: Последний день окна оси (reference_date + 44).
        payments_end: Последний день горизонта слоя «Платежи»
            (конец календарного месяца reference_date, C-5).
    """

    collect_start: date
    window_end: date
    payments_end: date


class DayLayers(TypedDict):
    """Декомпозиция прогнозного остатка одного дня окна на три слоя.

    Инвариант: free + payments + reserve == forecast_balance (AC-3).

    Attributes:
        date: Дата дня окна.
        free: Слой «Свободно» — реально доступные деньги.
        payments: Слой «Платежи» — уйдут на запланированные платежи
            в интервале (date, конец календарного месяца reference_date].
            За границей месяца всегда 0 — видимое ограничение C-5.
        reserve: Слой «Резерв» — ФАКТ дня после каскада _split_day.
            Может быть меньше reserve_configured, если остатка меньше:
            это и есть сигнал «вы залезаете в подушку».
        reserve_configured: Настроенный резерв дня ДО каскада
            (cushion_threshold + goals_part). Нужен тултипу, чтобы
            честно объяснить сжатие, а не утверждать настройку
            (решение владельца п. 3б).
        forecast_balance: Прогнозный остаток из CalendarService.
    """

    date: date
    free: Decimal
    payments: Decimal
    reserve: Decimal
    reserve_configured: Decimal
    forecast_balance: Decimal


class UpcomingPayment(TypedDict):
    """Предстоящий платёж для слоя «Платежи» и тултипа легенды (FR-4).

    Attributes:
        date: Дата платежа.
        amount: Сумма, всегда положительная (для ADJUSTMENT — abs).
        description: Описание операции или None.
        category_name: Название категории или None.
        is_recurring: True для регулярных операций (маркер 🔁).
    """

    date: date
    amount: Decimal
    description: str | None
    category_name: str | None
    is_recurring: bool


class GoalMilestone(TypedDict):
    """Веха цели на оси времени графика (FR-3.c).

    Материализуется из ORM-объекта Goal ВНУТРИ сессии — иначе
    DetachedInstanceError на вычисляемом property progress_percentage
    (образец: TransactionInfo, calendar_service.py:27-33).

    Attributes:
        goal_id: ID цели.
        name: Название цели.
        target_date: Дата достижения.
        target_amount: Целевая сумма.
        progress_percent: Прогресс 0..100 (Goal.progress_percentage).
        beyond_window: True — цель за правым краем окна 45 дней
            (рисуется стрелкой-аннотацией у края, как в эскизе v3).
    """

    goal_id: int
    name: str
    target_date: date
    target_amount: Decimal
    progress_percent: float
    beyond_window: bool


class TodaySlice(TypedDict):
    """Срез модели на reference_date — источник цифр шапки (FR-2).

    Пришёл на место LayersVerdict из v2. Поля level / text /
    dip_threshold УДАЛЕНЫ решением владельца (п. 3а): шапка
    не выносит оценок, только показывает разбор. Минимум окна
    переехал в MoneyLayersData — он нужен графику, не шапке.

    Attributes:
        free: Слой «Свободно» на reference_date — главное число шапки.
        balance: Прогнозный остаток на reference_date (разбор).
        payments: Слой «Платежи» на reference_date (разбор).
        reserve: Слой «Резерв» на reference_date, ФАКТ дня (разбор).
    """

    free: Decimal
    balance: Decimal
    payments: Decimal
    reserve: Decimal


class MoneyLayersData(TypedDict):
    """Полный результат модели FR-1 — единый источник шапки и графика.

    Attributes:
        days: Декомпозиция по дням окна (reference_date .. window_end).
        today: Срез «сегодня» для шапки.
        min_free: Минимум слоя «Свободно» по ВСЕМУ окну — для маркера
            минимума на графике (FR-3.e). НЕ используется для оценки
            состояния: вердикта в куске 1 нет (решение владельца п. 3а).
        min_free_date: Дата этого минимума (первая при равенстве).
        upcoming_payments: Платежи до payments_end для тултипа (FR-4).
        milestones: Вехи целей для оси времени (FR-3.c).
        reference_date: Дата отсчёта («сегодня»).
        window_end: Последний день окна оси (reference_date + 44).
        payments_end: Последний день горизонта платежей (конец месяца, C-5).
        cushion_threshold: Порог подушки в слое «Резерв» (расшифровка).
        goals_reserve_today: Часть слоя «Резерв» от бюджета целей на сегодня
            (до каскада — настроенная).
        reserve_configured_today: cushion_threshold + goals_reserve_today.
            Сравнение с today['reserve'] показывает, сжат ли слой —
            тултип обязан говорить факт, а не настройку (п. 3б).
        degraded: True — часть модели посчитана в деградации (fail-open,
            см. «Обработка ошибок»). UI помечает разбор оговоркой
            «часть данных недоступна» и НЕ показывает заниженные числа
            как достоверные. Пришло на место снятого «приглушения
            вердикта» (замечание №8 критики v2 после п. 3а).
        is_empty: True — у пользователя нет данных ВООБЩЕ (FR-6);
            НЕ «нули в окне». Считается без отдельного запроса.
        window_is_flat: True — данные есть, но в окне ни одной операции
            (график рисуется плоским, пустое состояние НЕ подменяет его).
    """

    days: list[DayLayers]
    today: TodaySlice
    min_free: Decimal
    min_free_date: date
    upcoming_payments: list[UpcomingPayment]
    milestones: list[GoalMilestone]
    reference_date: date
    window_end: date
    payments_end: date
    cushion_threshold: Decimal
    goals_reserve_today: Decimal
    reserve_configured_today: Decimal
    degraded: bool
    is_empty: bool
    window_is_flat: bool
```

```python
# app/services/money_layers_service.py

class MoneyLayersService:
    """Модель «свободно / платежи / резерв» по дням (FR-1).

    Read-only надстройка: композиция над CalendarService (прогнозный
    остаток и перечень операций), BudgetReservationService (только
    monthly_budget), CushionService (порог подушки) и GoalService (вехи).
    Ни одного существующего метода не меняет, в БД не пишет (C-2, C-3).

    Два горизонта показа (решение владельца 2026-08-24):
        * окно оси — WINDOW_DAYS = 45 дней от reference_date (эскиз v3);
        * горизонт слоя «Платежи» — конец календарного месяца (C-5).
          За границей месяца payments(D) == 0: ограничение видно честно,
          а не скрыто сужением оси.

    Инвариант декомпозиции: для каждого дня D окна
        free(D) + payments(D) + reserve(D) == CalendarService.balance(D)
    (AC-3) — обеспечен конструктивно, free выводится вычитанием, а
    _split_day сохраняет сумму во всех ветках.

    Note:
        Слой «Резерв» считается ОДНОЙ формулой от даты D, без ветвления
        по режиму резервирования. Формула спрашивает у кассового
        календаря «какие savings-операции стоят на этих датах»,
        а не у BudgetReservationService «сколько израсходовано за
        месяц»: get_budget_progress отвечает на другой вопрос
        (докстринг budget_reservation_service.py:173-179 — «единообразно
        для обоих режимов считает взносы»), и попытка вывести из него
        «сколько лежит в остатке на день D» даёт двойной счёт при
        частичном взносе (critique-v2, блокер №1).
    """

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """

    def get_money_layers(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> MoneyLayersData:
        """Строит модель слоёв на окно 45 дней от reference_date.

        Args:
            user_id: ID пользователя.
            reference_date: Дата отсчёта (по умолчанию date.today()).

        Returns:
            MoneyLayersData: Дни окна, срез «сегодня», минимум окна,
                платежи, вехи целей. Все ORM-объекты материализованы —
                результат безопасен после закрытия сессии.

        Note:
            Никогда не бросает при отсутствии данных — возвращает
            корректную модель с is_empty=True (FR-6). Сбои частей
            (бюджет целей, подушка, цели) деградируют fail-open с
            логом logger.opt(exception=True) (NFR-2) и выставляют
            degraded=True, чтобы UI не показал заниженные числа как
            достоверные. Сбой calculate_daily_balances не глотается —
            без остатка модели нет.
        """

    # --- Приватные шаги ---

    def _horizons(self, reference_date: date) -> Horizons:
        """Три границы модели: сбор операций, ось, слой «Платежи».

        Границ три, а не две (в v2 их было две, и данных за границей
        месяца было нечем считать — critique-v2, №6):

        * collect_start = 1-е число месяца reference_date. Единственный
          сбор операций начинается ОТ НАЧАЛА МЕСЯЦА, а не от сегодня,
          потому что consumed(reference_date) по формуле резерва —
          это savings-операции в [month_start, reference_date], то есть
          в том числе УЖЕ ПРОШЕДШИЕ дни текущего месяца (взнос 10-го
          при сегодня 22-м).
        * window_end = reference_date + WINDOW_DAYS - 1 (ось графика).
        * payments_end = последний день месяца reference_date (C-5) —
          применяется ТОЛЬКО как арифметический фильтр суффиксной
          суммы слоя «Платежи», сбор операций им не ограничен.

        Returns:
            Horizons: (collect_start, window_end, payments_end).
        """

    def _collect_operations(
        self, user_id: int, collect_start: date, window_end: date
    ) -> tuple[list[UpcomingPayment], dict[date, Decimal]]:
        """ОДИН сбор операций на весь диапазон — платежи + savings.

        Один вызов CalendarService.get_all_transactions_for_period
        (collect_start .. window_end) обслуживает и слой «Платежи»,
        и формулу резерва. Второго вызова нет (NFR-1).

        Классификация повторяет DashboardService._get_daily_income_expense
        (dashboard_service.py:476-545):
          * expense / savings_reserve / savings_contribution → платёж
            на amount;
          * adjustment с Decimal(amount) < 0 → платёж на abs(amount)
            (знак хранится в самом amount: ReconciliationService
            создаёт транзакцию с amount=difference, которая может быть
            отрицательной, reconciliation_service.py:131-135;
            get_all_transactions_for_period сериализует amount=str(txn.amount),
            calendar_service.py:803/:849 — знак сохраняется);
          * income / transfer → не платёж.
        Пропущенные (is_skipped=True) отбрасываются — их нет и в балансе.

        Returns:
            tuple: (payments, savings_by_date), где
                payments — расходные операции с датой >= reference_date
                    (прошедшие дни месяца в слой «Платежи» не входят:
                    они уже вычтены из balance);
                savings_by_date — {дата: Σ savings_reserve +
                    savings_contribution} по ВСЕМУ диапазону сбора,
                    включая прошедшие дни месяца. Ровно эти суммы
                    CalendarService вычитает из баланса
                    (_get_daily_changes :270-283 для обычных,
                    _get_recurring_daily_changes :426-437 для recurring
                    и exceptions) — потому формула резерва и не двоится.
        """

    def _payments_tail_by_day(
        self,
        payments: list[UpcomingPayment],
        window_dates: list[date],
        payments_end: date,
    ) -> dict[date, Decimal]:
        """Суффиксные суммы платежей: {D: Σ платежей в (D, payments_end]}.

        Строго «после D»: платежи с датой ровно D уже вычтены из
        forecast_balance(D) кассовым календарём — иначе двойной счёт.
        Даёт «таяние» (FR-1.d): монотонно не растёт, payments(payments_end)
        == 0 и payments(D) == 0 для всех D > payments_end (C-5 видимо).
        Один проход справа налево, O(len(window_dates) + len(payments)).
        """

    def _goals_part_by_day(
        self,
        savings_by_date: dict[date, Decimal],
        window_dates: list[date],
        monthly_budget: Decimal,
    ) -> dict[date, Decimal]:
        """Бюджет целей, ещё лежащий в остатке на день D — ЕДИНАЯ формула.

        Для каждого дня D окна (месяц берётся ПО ДНЮ D, никакого
        наследования базы через границу месяца — critique-v2, блокер №2):

            consumed(D)  = Σ savings_by_date[d], d в [month_start(D), D]
            committed(D) = Σ savings_by_date[d], d в (D, month_end(D)]
            goals(D)     = max(0, monthly_budget − consumed(D) − committed(D))

        Смысл слагаемых:
          * consumed(D) — savings-операции, уже вычтенные из balance(D)
            кассовым календарём. Их нельзя держать в синем слое: денег
            в остатке нет.
          * committed(D) — savings-операции, которым ещё предстоит уйти
            в пределах месяца дня D. Они лежат в слое «Платежи»
            (та же операция — тот же список), поэтому вычитаются, чтобы
            не удвоиться.
        Каждая операция попадает РОВНО в одно слагаемое — по своей дате
        относительно D. Двойного вычитания нет ни в одном режиме
        резервирования: формула вообще не знает о режиме.

        Note:
            Для D за границей месяца reference_date данные есть:
            сбор операций идёт до window_end (см. _horizons). В v2 этой
            ветке формулы не было чем считать (critique-v2, №6).

        Note:
            Прошлые месяцы в окно не попадают (окно начинается сегодня),
            поэтому month_start(D) >= collect_start для всех D окна,
            КРОМЕ вырожденного случая reference_date == 1-е число, где
            они совпадают. Данных всегда достаточно.

        Note:
            Величина monthly_savings_budget — одна настройка на все
            месяцы (users.monthly_savings_budget, database.py:99),
            месячной истории бюджета в схеме нет (C-4). Поэтому
            budget(D) == monthly_budget для любого D.
        """

    def _split_day(
        self, balance: Decimal, payments: Decimal, reserve: Decimal
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Каскад сжатия слоёв — ЕДИНСТВЕННЫЙ механизм обрезки (п. 3б).

        1. free = balance − payments − reserve; если free >= 0 — готово.
        2. Иначе free = 0, дефицит гасится сначала из reserve
           (до нуля), затем из payments.
        3. Если balance < 0 — free = balance (отрицательное),
           payments = reserve = 0.

        Порядок гашения (сначала reserve, потом payments) фиксирован
        и продуктово осмыслен: «сначала вы залезаете в подушку, и лишь
        потом не хватает на обязательные платежи».

        Второго механизма сжатия нет: min(threshold, balance) из v2
        убран из cushion_part решением владельца (п. 3б) — два
        независимых сжатия одного слоя давали неопределённый порядок
        применения и «дышащую» синюю полосу без объяснения
        (critique-v2, №4).

        Returns:
            tuple[Decimal, Decimal, Decimal]: (free, payments, reserve),
                сумма которых равна balance при любом входе.
        """

    def _today_slice(self, days: list[DayLayers]) -> TodaySlice:
        """Срез первого дня окна (== reference_date) для шапки.

        Вердикта не считает: уровней состояния в куске 1 нет
        (решение владельца п. 3а). Только четыре числа разбора.
        """

    def _window_min_free(self, days: list[DayLayers]) -> tuple[Decimal, date]:
        """Минимум слоя «Свободно» по ВСЕМУ окну — для маркера (FR-3.e).

        Минимум ищется по всем 45 дням, а не по остатку месяца:
        просадка после зарплаты (эскиз: 4 сентября) обязана попадать
        в кадр. При равенстве берётся первая дата.

        Note:
            Величина используется ТОЛЬКО графиком (маркер минимума).
            Оценочного вывода из неё не делается — вердикт снят
            решением владельца.
        """

    def _goal_milestones(
        self, user_id: int, reference_date: date, window_end: date
    ) -> list[GoalMilestone]:
        """Вехи активных целей: в окне + ближайшая за его краем.

        Материализует поля ORM-объектов Goal (включая вычисляемое
        property progress_percentage) в GoalMilestone ВНУТРИ сессии —
        GoalService.get_all_by_user возвращает list[Goal], и обращение
        к нему после закрытия сессии даст DetachedInstanceError.

        Returns:
            list[GoalMilestone]: до MAX_MILESTONES_IN_WINDOW вех внутри
                окна (ближайшие по target_date) + не более одной
                с beyond_window=True (ближайшая после window_end).
        """

    def _is_empty(
        self,
        days: list[DayLayers],
        savings_by_date: dict[date, Decimal],
        payments: list[UpcomingPayment],
        has_recurring_templates: bool,
        starting_balance: Decimal,
    ) -> bool:
        """«Нет данных вообще» — БЕЗ отдельного запроса (critique-v2, №8).

        Критерий: starting_balance == 0 И recurring-шаблонов нет
        И в диапазоне сбора нет ни платежей, ни savings-операций
        И forecast_balance каждого дня окна == 0.

        Почему это корректно для AC-5 (чистая база): на чистой базе
        все четыре условия истинны по построению — операций нет,
        шаблонов нет, starting_balance = 0, значит и балансы нулевые.

        Почему это не ломает window_is_flat: у пользователя с историей
        и пустым окном forecast_balance(D) != 0 (накопленный остаток) —
        либо starting_balance != 0, либо есть шаблоны. Такой
        пользователь получает is_empty=False, window_is_flat=True
        и ВИДИТ график (плоская стопка), а не «Добавьте первую
        операцию». Единственный ложноположительный сценарий —
        история, которая свела остаток ровно в 0.00 и не оставила
        ни одного шаблона, при starting_balance == 0 и полностью
        пустом окне; для него пустое состояние с кнопкой «Сверка»
        всё равно осмысленно (показывать плоскую нулевую стопку
        не информативнее).

        Note:
            Флаг users.first_launch для критерия не годится:
            OnboardingService.skip() сбрасывает его в False, не создавая
            данных (onboarding_service.py:168-182).

        Note:
            has_recurring_templates берётся из уже выполненной работы
            (наличие виртуальных инстансов в собранном диапазоне ИЛИ
            один лёгкий exists-запрос через RecurringService, если
            диапазон пуст) — отдельного count(transactions) по всей
            истории, как в v2, нет.
        """
```

```python
# app/services/cushion_service.py — ДОБАВЛЯЕМЫЙ метод

    def get_threshold_amount(self, user_id: int) -> Decimal:
        """Порог подушки без пересчёта баланса.

        Лёгкая альтернатива get_settings() для потребителей, которым
        нужен только порог: get_settings() внутри вызывает
        _get_current_balance() → CalendarService.get_balance_on_date(),
        а тот полностью обходит recurring-историю от самого раннего
        шаблона (calendar_service.py:364-407). Для threshold_amount
        баланс не нужен вовсе — формула target * percent / 100
        (см. get_settings, строки 104-107; баланс участвует только
        в current_amount и progress, :100 и :113-118).

        Args:
            user_id: ID пользователя.

        Returns:
            Decimal: Порог подушки; Decimal("0") если пользователь
                не найден или подушка не настроена (target == 0).
                Не бросает ValidationError — отсутствие пользователя
                на чистой базе штатно (в отличие от _get_user).
        """
```

```python
# app/components/dashboard.py — новые/изменённые строители и точка загрузки

def build_free_header(
    data: MoneyLayersData,
    profile: UserProfile,
) -> html.Div:
    """Шапка «Свободно сегодня: N ₽» (FR-2, FR-5).

    Состав слева: приветствие «Привет, {name}» (поглощает вытесняемый
    dashboard-greeting), метка «Свободно сегодня», сумма (tabular-nums),
    разбор «баланс {balance} − платежи {payments} − резерв {reserve}».
    Справа: аватар-эмодзи + имя, кнопка «Сверка»
    (id="open-recon-from-dashboard-header-btn"), шестерёнка
    (id="dashboard-settings-cog" → модал профиля).

    Вердикта НЕТ (решение владельца п. 3а): ни чипа, ни сигнальной
    шины, ни оценочной подписи, ни окраски суммы по уровню. Сумма
    рендерится нейтральным цветом текста; единственное исключение —
    отрицательное значение показывается в цвете риска, потому что
    это факт знака числа, а не оценка состояния.

    При data['degraded'] под разбором добавляется нейтральная сноска
    «часть данных недоступна, показано без бюджета целей» — деградация
    обозначена, а не выдана за достоверную цифру (замена снятому
    «приглушению вердикта», critique-v2 №8).

    Не дверь-переход: на контейнере нет dcc.Link, n_clicks,
    cursor:pointer (FR-2.e).

    Args:
        data: Модель слоёв из MoneyLayersService.
        profile: Профиль (name, avatar_id) из OnboardingService.

    Returns:
        html.Div с классом pnl-breaker.
    """


def build_layers_chart(data: MoneyLayersData) -> dbc.Card:
    """График полос: стопка Свободно/Платежи/Резерв по 45 дням (FR-3).

    Три go.Bar в barmode="stack" (снизу вверх: free, payments, reserve)
    по датам оси X, вертикальная линия «сегодня», маркер минимума слоя
    «Свободно» (data['min_free_date']), вехи целей аннотациями (в окне +
    стрелка за краем). Легенда Plotly отключена (showlegend=False) —
    вынесена в HTML (заметка vision-критика + FR-4).

    Args:
        data: Модель слоёв из MoneyLayersService.

    Returns:
        dbc.Card с dcc.Graph(id="dashboard-layers-chart-graph") либо
        пустым состоянием при data['is_empty'] (FR-6).
    """


def _axis_tickvals(window_dates: list[date]) -> list[date]:
    """Явные даты подписей оси X — без спорных единиц dtick.

    Берёт каждый k-й день окна, где k = max(1, round(len / TARGET_X_TICKS)).
    Для 45 дней k = 4 → 12 подписей (в эскизе v3 — 11).

    Заменяет _axis_dtick из v2: там докстринг обещал миллисекунды,
    а формула возвращала дни (critique-v2, №10). Plotly для оси
    type="date" принимает dtick в миллисекундах либо строкой ("D4",
    "M1"), и обе записи легко перепутать. Явные tickvals + tickmode
    ="array" снимают неоднозначность единиц полностью и заодно дают
    контроль над попаданием граничных дат в подписи.

    Args:
        window_dates: Даты окна по возрастанию (data['days'] → date).

    Returns:
        list[date]: Даты для xaxis.tickvals (первая — reference_date).
    """


def _load_dashboard_components(period_state: dict | None) -> tuple:
    """Единая точка загрузки данных и построения UI дашборда.

    Аргумент `period` УДАЛЁН из сигнатуры (было `(period, period_state)`,
    dashboard.py:1255-1258). Причина: period-switcher снимается вместе
    с callback'ом update_period_state, единственным Input которого он
    был (:1397-1408) — Store dashboard-period перестаёт обновляться,
    и аргумент навсегда получал бы дефолт "month" из layout. Мёртвый
    параметр, с которым пришлось бы спорить весь кусок 2 (critique-v2,
    №3), не заводится вовсе.

    Store dashboard-period ОСТАЁТСЯ в layout с data={"period":"month"}:
    его читает open_create_from_chart как guard. period_state
    по-прежнему передаётся — на случай, если кусок 2 вернёт выбор
    периода.

    Args:
        period_state: Данные из dcc.Store dashboard-period.

    Returns:
        tuple: (free_header, layers_chart, recent, upcoming, cushion)
            — 5 значений вместо прежних 6 (ушли cards+stats,
            пришёл free_header).
    """
```

**Состав Output'ов после правки:**

| Callback | Outputs (в порядке) / Inputs |
|---|---|
| `load_dashboard_data` | Outputs: `dashboard-free-header.children`, `dashboard-layers-chart.children`, `dashboard-recent-transactions.children`, `dashboard-upcoming-transactions.children`, `dashboard-cushion-card.children` — **5** (было 7). `dashboard-greeting` Output удаляется. Inputs: `url.pathname`, `profile-updated.data` (**`period-switcher.value` снят**). State: `dashboard-period.data`. Сигнатура становится `(pathname, profile_updated, period_state)`. Ветка ошибки: `(error_alert,) * 5` |
| `refresh_dashboard_after_crud` | те же 5 с `allow_duplicate=True` (было 6); сигнатура не меняется, но `period` больше не выводится из Store |
| `update_period_state` | **удаляется** вместе с `period-switcher` |
| `open_create_from_chart` | Input → `dashboard-layers-chart-graph.clickData`; guard по `period_state` сохраняется; дата берётся из `point["x"]` (ISO-строка) вместо `int(point["x"])` |

**Судьба `dashboard-greeting`.** Элемент и Output удаляются, приветствие поглощается шапкой (FR-2 требует имя пользователя в шапке; два «привета» рядом — то же дублирование, что и два главных числа). Дух протокола 0026 соблюдён: приветствие по-прежнему обновляется **внутри** `load_dashboard_data` первым Output'ом, а не отдельным callback'ом. Хелпер `_build_greeting_text()` (`dashboard.py:82-91`) сохраняется и вызывается из `build_free_header`; его тесты `TestBuildGreetingText` не правятся.

## Модель данных

Схема БД не меняется (C-4) — проверено по коду, всё сырьё есть.

| Что нужно модели | Откуда берётся (проверено) | Достаточность |
|---|---|---|
| Прогнозный остаток по дням окна | `CalendarService.calculate_daily_balances` (`users.starting_balance` + `transactions` + recurring, `calendar_service.py:100-167`) | достаточно |
| Платежи и savings-операции всего диапазона | **один** `CalendarService.get_all_transactions_for_period` → `TransactionInfo` (`amount` строкой **со знаком** — `str(txn.amount)`, :803/:849; есть `description`, `category_name`, `is_recurring`, `is_exception`, `is_skipped`) | достаточно |
| Порог подушки | `users.cushion_target`, `users.cushion_threshold_percent` через новый `CushionService.get_threshold_amount` | достаточно (колонки суммы порога в схеме нет — только процент + булев флаг, `database.py:105-107`) |
| Месячный бюджет целей | `users.monthly_savings_budget` (`database.py:99`) через `BudgetReservationService.get_settings()['monthly_budget']` | достаточно |
| ~~Режим резервирования~~ | **не требуется** — формула не ветвится по режиму | — |
| ~~`used_budget` / материализованный резерв~~ | **не требуется** — `get_budget_progress` и `_get_reserve_sum_for_month` из пути модели ушли | — |
| Вехи целей | `goals.target_date/target_amount/current_amount/status` через `GoalService.get_all_by_user(ACTIVE)` (`target_date` NOT NULL, `database.py:260`) | достаточно |
| Аватар и имя для шапки | `users.avatar_id`, `users.name` через `OnboardingService.get_profile` | достаточно |
| Наличие recurring-шаблонов для `is_empty` | `RecurringService.get_templates_for_user` (`recurring_service.py:114-137`) — один лёгкий запрос, и то только когда собранный диапазон пуст | достаточно |

**Вывод по C-4:** миграции не нужны, отдельного решения об изменении схемы не требуется.

### Численная трассировка формулы резерва

Единая конфигурация, если не сказано иное: `monthly_budget = 15 000`, `cushion_threshold = 30 000`, режим `fixed_date` c датой резерва 25-е (recurring `SAVINGS_RESERVE` 15 000 на 25-е каждого месяца), `reference_date = 22 августа`. Все девять кейсов проверены против фактического поведения кода: `_get_recurring_daily_changes` вычитает `savings_reserve`/`savings_contribution` из баланса (`calendar_service.py:426-437`); `_get_daily_changes` вычитает их же для обычных транзакций (`:270-283`) и исключает exceptions (`:230-233`), которые приходят через recurring-ветку; `get_all_transactions_for_period` возвращает и виртуальные инстансы, и exceptions вместо них (`:817-870`, `recurring_service.py:699-714`).

**Кейсы 1–3: `fixed_date`, доля взноса (это ровно то, на чём v2 упал).**

| # | Взнос | Что в БД | `savings_by_date` в августе | `consumed(22)` | `committed(22)` | `goals_part(22)` | Ожидание | v2 давал |
|---|---|---|---|---|---|---|---|---|
| 1 | нет | виртуальный инстанс 25 авг = 15 000 | {25 авг: 15 000} | 0 | 15 000 | max(0, 15 000−0−15 000) = **0** | 0 — бюджет ещё в слое «Платежи», уйдёт 25-го | 0 ✓ |
| 2 | **5 000** 10 авг (частичный) | exception 25 авг = 10 000 (`budget−contributions`, `budget_reservation_service.py:290-298`), транзакции взноса НЕТ (`:669-672`) | {25 авг: 10 000} | 0 | 10 000 | max(0, 15 000−0−10 000) = **5 000** | 5 000 — именно столько отдано цели и физически лежит в остатке | **0** ✗ (двойное вычитание) |
| 3 | 15 000 полностью | exception 25 авг = 0 (`max(new_reserve,0)`) | {25 авг: 0} | 0 | 0 | max(0, 15 000−0−0) = **15 000** | 15 000 — весь бюджет лежит в остатке, резерв не уйдёт | 15 000 ✓ |

Кейс 2 — тот самый интервал между вырожденными границами, на котором формула v2 врала. Новая формула даёт правильные 5 000 и не использует ни `_get_reserve_sum_for_month`, ни `get_budget_progress`.

**Кейсы 4–5: день относительно даты резерва (`fixed_date`, взносов нет).**

| # | D | `consumed(D)` = Σ в [1 авг, D] | `committed(D)` = Σ в (D, 31 авг] | `goals_part(D)` | Смысл |
|---|---|---|---|---|---|
| 4 | 24 авг (до резерва) | 0 | 15 000 | max(0, 15 000−0−15 000) = **0** | бюджет в оранжевом слое |
| 5 | 26 авг (после резерва) | 15 000 | 0 | max(0, 15 000−15 000−0) = **0** | резерв ушёл из баланса — синий слой его не держит |

В обоих случаях `goals_part = 0`, но по разным причинам, и обе верны: до 25-го деньги в «Платежах», после 25-го их в остатке нет. Синяя полоса на всём августе = 30 000 (только подушка). Это ровно то, что должно быть: бюджет августа сначала «обещан», потом «ушёл», и ни в один момент не удвоен.

**Кейс 6: `fixed_date`, частичный взнос, день после резерва.** Взнос 5 000 сделан 10 авг, exception 25 авг = 10 000. D = 26 авг: `consumed` = 10 000 (exception), `committed` = 0 → `goals_part = 15 000 − 10 000 = 5 000`. Верно: 10 000 ушли резервом, 5 000 остались в остатке (транзакции взноса в `fixed_date` нет), и они по-прежнему обещаны целям.

**Кейсы 7–8: `from_balance` (взнос создаёт `SAVINGS_CONTRIBUTION`, recurring-шаблона резерва нет).**

| # | Взнос | `savings_by_date` | D | `consumed(D)` | `committed(D)` | `goals_part(D)` | Ожидание | v2 давал |
|---|---|---|---|---|---|---|---|---|
| 7 | 5 000 **10 авг** (прошлое) | {10 авг: 5 000} | 22 авг | 5 000 | 0 | max(0, 15 000−5 000−0) = **10 000** | 10 000 — остаток бюджета ещё не тронут и лежит в остатке | 10 000 ✓ |
| 8 | 5 000 **28 авг** (**будущая** дата, `add_contribution` принимает любую, `goal_service.py:126-131`) | {28 авг: 5 000} | 22 авг | 0 | 5 000 | max(0, 15 000−0−5 000) = **10 000** | 10 000 — 5 000 лежат в слое «Платежи» (уйдут 28-го), остальные 10 000 в синем | **5 000** ✗ (`used_contributions` из `get_budget_progress` считает весь месяц включительно, `_get_contributions_sum_for_month` :441-464 → та же 5 000 вычтена дважды) |

Кейс 8 — симметричный дефект v2, который критик описал по коду. Новая формула его не имеет: операция 28 авг попадает только в `committed(22)`.

**Кейс 9: граница месяца и правый край окна (это блокер №2).** `fixed_date`, резерв 15 000 25-го каждого месяца, взносов нет, зарплата 120 000 5-го, `reference_date = 22 авг`, `window_end = 5 окт`. `savings_by_date` = {25 авг: 15 000, 25 сент: 15 000} (виртуальные инстансы recurring-шаблона в собранном диапазоне до 5 окт).

| D | месяц D | `consumed(D)` | `committed(D)` | `goals_part(D)` | v2 давал | Комментарий |
|---|---|---|---|---|---|---|
| 22 авг | авг | 0 | 15 000 (25 авг) | **0** | 0 | бюджет августа в «Платежах» |
| 31 авг | авг | 15 000 (25 авг) | 0 | **0** | **15 000** ✗ | резерв августа исполнен — держать его в синем нельзя |
| 1 сент | сент | 0 | 15 000 (25 сент) | **0** | 15 000 ✗ | новый месяц, бюджет сентября ещё впереди. Оранжевый слой при этом 0 (C-5), и это видимое ограничение |
| 24 сент | сент | 0 | 15 000 | **0** | 15 000 ✗ | |
| 26 сент | сент | 15 000 (25 сент) | 0 | **0** | **30 000** ✗ | v2 накапливал оба исполненных резерва |
| 30 сент | сент | 15 000 | 0 | **0** | 30 000 ✗ | |
| 5 окт | окт | 0 | 0 (резерв 25 окт вне окна и вне диапазона сбора) | **15 000** | 30 000 ✗ | бюджет октября ещё целиком в остатке и никуда в пределах окна не уйдёт — правильно держать его в синем |

**`goals_part` на 45-дневном окне не накапливается: максимум по окну равен `monthly_budget` (15 000), а не сумме исполненных резервов.** Синяя полоса = 30 000 (подушка) на всём августе-сентябре и 45 000 в начале октября — то есть держит порог подушки плюс непотраченный бюджет месяца дня D, ровно как обещает легенда. «Свободно» на правом крае окна не занижено на 30 000, как было бы в v2, и утверждение эскиза «после зарплаты стало свободно» не ломается.

Особый случай 5 окт заслуживает пояснения: `committed(5 окт) = 0`, потому что резерв 25 октября лежит за `window_end` и в диапазон сбора не входит. Формально это то же ограничение горизонта, что C-5 для платежей, и оно консервативно в **безопасную** сторону: модель показывает бюджет октября как зарезервированный (в синем), а не как свободный. Это правильная асимметрия: показать больше свободных денег, чем есть, — опасно; показать меньше — нет.

**Проверка примера эскиза (сходимость AC-3 и главного числа).** Остаток 84 500 на 22 авг, платежи до конца месяца 37 500 (включая резерв 15 000 на 25-е), бюджет целей 15 000, порог подушки 30 000:

| D | balance | payments (D, 31 авг] | reserve_configured | reserve (факт) | free |
|---|---|---|---|---|---|
| 22 авг | 84 500 | 37 500 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 25 авг | 54 500 | 7 500 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 28 авг | 48 300 | 1 300 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 31 авг | 47 000 | 0 | 30 000 + 0 = 30 000 | 30 000 | 17 000 |
| 5 сент (+120 000) | 167 000 | 0 | 30 000 + 0 = 30 000 | 30 000 | 137 000 |

Сумма слоёв == balance на каждой строке (AC-3); `payments` тает до 0 (FR-1.d) и остаётся 0 за 31 августа (C-5 видимо); `free > 0`. Отличие от арифметики v2 (там `free = 2 000`) — не ошибка, а следствие исправленной формулы: бюджет целей 15 000 в этом сценарии уже сидит в оранжевом слое как резерв 25-го, и держать его ещё и в синем значило бы вычесть дважды. Число эскиза (32 000 при разборе 84 500 − 37 500 − 15 000) исходило из допущения, что резерв целей **не** входит в «обещано»; в реальных данных проекта recurring-резерв входит в список операций, поэтому корректный разбор — 84 500 − 37 500 − 30 000 = 17 000. Расхождение с моковым числом эскиза фиксируется явно (в осадок решений): это цена согласованности с кассовым календарём, то есть ровно то, ради чего эпик и затевался.

**Пример сжатой полосы (проверка п. 3б, честная подпись).** Порог подушки 30 000, бюджет целей 0, `balance(4 сент) = 18 000`, `payments(4 сент) = 0`:
- `reserve_configured = 30 000`, `reserve_raw = 30 000`;
- `_split_day(18 000, 0, 30 000)`: `free = −12 000 < 0` → `free = 0`, дефицит 12 000 гасится из reserve → `reserve = 18 000`, `payments = 0`;
- `DayLayers`: `free = 0`, `payments = 0`, `reserve = 18 000`, `reserve_configured = 30 000`, сумма = 18 000 == balance ✓;
- тултип: «В этот день на резерв остаётся 18 000 ₽ из 30 000 ₽ — вы залезаете в подушку». Цифра совпадает с высотой полосы. В v2 тултип назвал бы 30 000 при полосе 18 000 — та самая P1-боль внутри одного блока.

## Обработка ошибок

Четыре уровня, по образцу `PurchaseRecommendationService.get_safe_dates_map` (`purchase_recommendation_service.py:72-83` — fail-open + `logger.opt(exception=True)`, идиома протокола 0027: loguru игнорирует `exc_info`).

1. **Штатное отсутствие данных — тихий дефолт, без лога.** Пользователь не найден / подушка не настроена → `get_threshold_amount` возвращает `Decimal("0")` без исключения и без варнинга. `BudgetReservationService.get_settings` для отсутствующего пользователя сам возвращает дефолт с `monthly_budget = 0` (`:65-72`) — это штатный путь чистой базы, шума не создаём.

2. **Сбой компонента — fail-open + лог с трейсбеком + `degraded=True`.** Сбой чтения бюджета → `monthly_budget = 0` → `goals_part = 0`; сбой `GoalService` → `milestones = []`; неожиданный сбой `get_threshold_amount` → `cushion_threshold = 0`. Каждый — `logger.opt(exception=True).warning(...)` (NFR-2). Инвариант AC-3 сохраняется, `free` выводится вычитанием.
   **Направление деградации обозначается в UI, а не только в логах.** `goals_part = 0` или `cushion_threshold = 0` означает, что весь резерв уходит в «Свободно» — деградация в **опасную** сторону (пользователь видит больше свободных денег, чем есть). Раньше это предлагалось гасить «приглушением вердикта»; вердикта больше нет (п. 3а), поэтому решение другое: флаг `degraded` в модели, а в шапке — нейтральная сноска под разбором «часть данных недоступна, показано без бюджета целей» и **отсутствие** сноски-объяснения слоя «Резерв» в тултипе (вместо утверждения неверного состава). Число не подменяется и не скрывается: подменённое число хуже помеченного. Тест: monkeypatch-падение чтения бюджета → `degraded is True` и сноска в DOM.

3. **Сбой `calculate_daily_balances` не глотается** — без остатка модели нет, исключение уходит в callback (уровень 4).

4. **Границы горизонтов.**
   - `reference_date` = последний день месяца → `payments_end == reference_date`, `payments(D) == 0` для всех дней окна (модель валидна, оранжевой полосы нет — честное «платежей до конца месяца больше нет»). При этом `collect_start` = 1-е число того же месяца, то есть `consumed` считается корректно.
   - `reference_date` = 1-е число → `collect_start == reference_date`, окно и диапазон сбора совпадают слева.
   - Февраль / 31-е / переход через год: `monthrange` в `_horizons` и в `_goals_part_by_day`; окно 45 дней всегда пересекает минимум две границы месяца, а при `reference_date` в конце месяца — три (пример: 25 дек → окно до 7 фев, месяцы дек/янв/фев). Тесты на все три.
   - `calculate_daily_balances(ref, ref+44)` — `start < end` всегда, `ValueError` (`calendar_service.py:122-126`) недостижим.
   - Окно 45 дней укладывается в `MAX_FORECAST_DAYS = 366` (`recurring_service.py:25`).

5. **Callback'и Dash.** `load_dashboard_data`: `try/except` → `dbc.Alert("Не удалось загрузить данные...")` во все 5 Output'ов; `logger.error(f"...{e}")` (`dashboard.py:1389`) заменяется на `logger.opt(exception=True).error(...)` — сейчас трейсбека нет (NFR-2). `refresh_dashboard_after_crud` (`:1451`) — то же, затем `PreventUpdate`.

**Пустое состояние (FR-6, AC-5):**

- `is_empty=True` ⟺ критерий `_is_empty` (без запроса, см. докстринг). Тогда шапка рендерит `_build_header_empty_state()` («Пока нечего показать» + «Добавьте первую операцию или сверьте баланс» + кнопка «Сверка»), а график — `_build_chart_empty_state()`: **вместо `dcc.Graph` отдаётся `html.Div`**, Plotly вообще не вызывается → оси −1..1 и «50.001k» физически невозможны (AC-5).
- `window_is_flat=True` (данные есть, в окне ни одной операции) — **график рисуется**: плоская стопка на уровне остатка, шапка показывает реальное «Свободно». Пустое состояние здесь **не** подменяет график — иначе регрессия класса «Аналитика молча показывает нули». Отдельный тест.
- Для непустых, но малых данных оси фиксируются: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)` (нет «50.001k»), `xaxis=dict(type="date", tickmode="array", tickvals=_axis_tickvals(...), tickformat="%-d %b", tickangle=0)` (нет склеек на 45 днях, единицы шага не двусмысленны).

**Безопасность.** Тултип легенды рендерит пользовательский `description` только через `html.Div`/`html.Span` — Dash экранирует текст. `dangerously_allow_html` и `dcc.Markdown` в новых путях запрещены (правило реализации).

## План реализации

Оценки — в человеко-часах для одного разработчика, знакомого с проектом. Итого **≈ 31–37 ч** (v2: 30–36; шаг 4 подешевел на снятии режимного ветвления, шаги 6 и 13 подорожали на честном покрытии и полном списке тестов).

| # | Шаг | Оценка | Зависит от |
|---|---|---|---|
| 1 | `app/schema/money_layers.py` — TypedDict'ы (`DayLayers`, `UpcomingPayment`, `GoalMilestone`, `TodaySlice`, `MoneyLayersData`), `Horizons`, `LayerKey`, константы (`WINDOW_DAYS`, `MAX_MILESTONES_IN_WINDOW`, `TARGET_X_TICKS`, `LAYER_COLORS`, `LAYER_LABELS`) + реэкспорт в `app/schema/__init__.py`. Вердикт-типов и `DIP_*` НЕ создавать (п. 3а) | **1.5 ч** | — |
| 2 | `CushionService.get_threshold_amount()` + тесты в `tests/test_cushion_service.py` (порог по проценту, `target=0`, отсутствующий пользователь, monkeypatch-assert «`calculate_daily_balances` не вызывался») | **1.5 ч** | — |
| 3 | `app/services/money_layers_service.py` — каркас: `_horizons` (три границы), `_forecast_balances`, `_collect_operations` (**один** вызов, две выходные структуры), `_payments_tail_by_day`, `_split_day`, `_today_slice`, `_window_min_free`, `_is_empty` + реэкспорт в `app/services/__init__.py` | **4.5 ч** | 1, 2 |
| 4 | `_goals_part_by_day` — **единая** формула от даты D. Существенно проще шага 4 в v2: нет режимного ветвления, нет `get_budget_progress`, нет `_get_reserve_sum_for_month`, нет отдельной ветки за границей месяца. Реализация — два префиксных/суффиксных прохода по `savings_by_date` в разрезе месяцев окна | **2.5 ч** (v2: 4 ч) | 3 |
| 5 | `_goal_milestones` (материализация в сессии, ≤`MAX_MILESTONES_IN_WINDOW` в окне + одна `beyond_window`) | **1.5 ч** | 3 |
| 6 | `tests/test_money_layers_service.py`. **Блок A — «таблица ожидаемых слоёв» (закрывает 🟡№7, обязателен)**: `@pytest.mark.parametrize` с явными **числами по всем трём слоям** для матрицы `режим (fixed_date / from_balance) × доля взноса (0 / частичный / полный бюджет) × позиция дня (до даты резерва / день резерва / после / последний день месяца / первый день следующего / после резерва следующего месяца / правый край окна)`. Обязательно включены кейсы 1–9 из «Модели данных», то есть ровно те, на которых упали бы дефекты №1 (кейс 2: `fixed_date` + частичный взнос → `goals_part == 5 000`; кейс 8: `from_balance` + взнос будущей датой → `goals_part == 10 000`) и №2 (кейс 9: 31 авг → 0; 26 сент → 0; 30 сент → 0 — не 15 000/30 000). Каждый параметр задаёт `(free, payments, reserve)` числами, а не только их сумму. **Блок B** — инвариант AC-3 параметризованно по всем 45 дням (положительный / нулевой / отрицательный остаток, дефицитный каскад, оба режима, дни по обе стороны границы месяца). **Блок C** — «таяние» и `payments == 0` за `payments_end`; `payments(D)` не включает платежи дня D. **Блок D** — `_split_day` три ветки с assert суммы; сжатая полоса: `reserve < reserve_configured`, `reserve == balance` при `payments == 0`. **Блок E** — `cushion_part` НЕ сжимается вне каскада (перенакопленная подушка 922 155 при пороге 30 000 → `reserve_configured == 30 000`); порог, а не `target`. **Блок F** — границы: последний день месяца, 1-е число, февраль, 31-е, переход через год, окно через три месяца. **Блок G** — `is_empty` (чистая база) vs `window_is_flat` (история есть, окно пустое) + assert «в `_is_empty` нет обращений к БД» (monkeypatch счётчика запросов). **Блок H** — ADJUSTMENT оба знака; `is_skipped` не в слое. **Блок I** — детач: модель читаема после закрытия сессии. **Блок J** — fail-open: падение чтения бюджета → `degraded is True`, `goals_part == 0`, лог с трейсбеком; сумма слоёв по-прежнему == balance. Даты относительные (`date.today()` + хелперы `conftest.py`), без `pytest.skip`. Всего ~34 теста | **9 ч** (v2: 7 ч) | 3, 4, 5 |
| 7 | `app/assets/panel.css` — `pnl-*` из эскиза v3 на переменных проекта, `tabular-nums`, вертикальный ритм, `@media (prefers-reduced-motion: reduce)`. Классы сигнальной шины и чипа вердикта НЕ заводить (п. 3а) | **2 ч** (v2: 2.5) | — |
| 8 | `build_free_header()` + `_build_header_empty_state()`; кнопка «Сверка» с новым id; шестерёнка `dashboard-settings-cog`; поглощение приветствия; сноска `degraded` | **2.5 ч** | 1, 7 |
| 9 | `build_layers_chart()` + `_build_layer_legend()` + `_build_payments_tooltip()` + `_build_reserve_tooltip()` (честная подпись, п. 3б) + `_build_chart_empty_state()` + `_axis_tickvals()`; заметки vision-критика (легенда вне поля, ярлык минимума со сдвигом `yshift`/`ay`) | **4 ч** | 1, 7 |
| 10 | `profile_modal.py` — второй Input и ветка `triggered_id in (...)`; ручная проверка обеих ветвей | **0.5 ч** | 8 |
| 11 | Переключение `_load_dashboard_components` (**сигнатура `(period_state)`**) и callback'ов: новые Output-ID, 5 значений, снятие `Input("period-switcher","value")` и callback'а `update_period_state`, перепривязка `open_create_from_chart` на `dashboard-layers-chart-graph` + ISO-дата, clientside «Сверка» на новый id, `logger.opt(exception=True)` в обеих ветках ошибок | **3 ч** | 8, 9 |
| 12 | Удаление мёртвого кода в `dashboard.py` (`build_overview_cards`, `_build_kpi_card`, `build_cashflow_chart`, `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`, `build_statistics_card`, `create_ai_assistant_card`, `create_exchange_card`, `build_recent_transactions_card`) + чистка `custom.css` (`#dashboard-overview-cards`, `.db-period-switcher`, `.kpi-*` — grep проведён, вне дашборда не используются) | **2 ч** | 11 |
| 13 | `tests/test_dashboard_callbacks.py` — **три** теста (полный список по grep, ниже) + докстринг модуля («7-й Output» → «первый Output шапки»): `test_load_dashboard_data_decorator_declares_greeting_output` (:62-70) → на `dashboard-free-header`; `test_returns_seven_values_with_greeting_last` (:188-210) → 5 значений, ассерт приветствия переносится на содержимое шапки; `test_wrong_pathname_prevents_update` (:212-222) → снять `period_value=` из вызова. Плюс проверка: не осталось ни одного вызова `load_dashboard_data(..., period_value=...)` | **1.5 ч** (v2: 1 ч) | 11 |
| 14 | Прогон `pytest -q` (565 прежних + новые), `black`, `flake8`; ручная AC-1…AC-6 на наполненной и чистой базе; замер NFR-1 | **2.5 ч** | все |

Порядок сохраняет принцип «тесты модели до UI». Шаг 6 — самый дорогой не случайно: критик прямо указал, что отсутствие таблицы ожидаемых слоёв — причина, по которой оба блокера дожили до v2.

## Зависимости

Новых библиотек нет. `plotly.graph_objs` (`go.Bar` + `barmode="stack"` — базовая возможность стека), `dash_bootstrap_components.Tooltip` (dbc уже зависимость), `calendar.monthrange`, `datetime.timedelta` — всё используется в проекте. Причина эпика — упрощение; окно 45 дней укладывается в `MAX_FORECAST_DAYS = 366`, внешних календарных библиотек не требует.

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Единая формула резерва даёт неверную раскладку на конфигурации, не попавшей в таблицу | **Низкая** (было «Высокая» при режимном ветвлении) | Формула не ветвится и оперирует одним источником — списком savings-операций из того же кассового календаря, что даёт баланс. Блок A шага 6 задаёт **числами все три слоя** по матрице `режим × доля взноса × позиция дня` и включает 9 трассированных кейсов, из которых два ловят дефект №1 и три — дефект №2. Инвариант AC-3 (блок B) больше не считается главной защитой: он по построению слеп к раскладке, и это признано явно |
| Границы месяцев в `_goals_part_by_day` реализованы с off-by-one (`[month_start, D]` vs `(D, month_end]`) | Средняя | Границы прописаны в докстринге интервалами; блок F шага 6 покрывает первый день месяца, последний день месяца, февраль, 31-е, переход через год и окно, пересекающее три месяца; блок A содержит по дню с каждой стороны каждой границы |
| «Свободно сегодня» на числах эскиза даёт 17 000, а не 32 000 (мок эскиза считал резерв целей вне «обещано») | Средняя | Расхождение с моковым числом эскиза зафиксировано явно (в осадок решений) с обоснованием: recurring-резерв целей физически входит в список операций и уже сидит в слое «Платежи»; держать его ещё и в «Резерве» — двойной счёт. Композиция эскиза при этом не меняется. Проверка на шаге 14: разбор в шапке арифметически сходится с суммой слоёв графика на сегодня |
| Сбор операций на диапазон `[month_start, window_end]` (до 75 дней) дороже v2 (≤31 день) | Средняя | Это цена, без которой формула резерва за границей месяца нечем считать (№6). Вызов один, а не два. `get_all_transactions_for_period` — один запрос обычных транзакций + генерация виртуальных инстансов по шаблонам (O(шаблоны × дни)). Компенсация: сняты `get_budget_progress` (внутри которого ещё один `get_settings`, `:190`) и `_get_reserve_sum_for_month`, а `get_threshold_amount` убрал полный обход recurring-истории. Замер на шаге 14 |
| `free` уходит в минус при остатке ниже платежей+резерва — отрицательная полоса в стопке | Средняя | Детерминированный каскад `_split_day` (единственный механизм сжатия, п. 3б); блок D шага 6 на все три ветки с assert суммы; при `balance < 0` зелёная полоса отрицательная — честное отображение факта, а не тихое обнуление |
| Сжатая синяя полоса воспринимается как ошибка расчёта | Низкая | Честная подпись (п. 3б): тултип называет ФАКТ дня и настройку рядом («остаётся 18 000 из 30 000 — вы залезаете в подушку»); `reserve_configured` в контракте гарантирует, что UI не может утверждать настройку вместо факта |
| Fail-open по бюджету целей показывает больше свободных денег, чем есть | Средняя | Флаг `degraded` + нейтральная сноска в разборе шапки + отсутствие утверждающего тултипа «Резерв»; тест в блоке J шага 6. Вердикта для «приглушения» больше нет (п. 3а), поэтому механизм пометки — текстовый |
| Снятие `period-switcher` ломает вызовы `load_dashboard_data` в тестах | Низкая | Полный список закрыт grep'ом `period_value=`: ровно 2 файло-строки (`tests/test_dashboard_callbacks.py:204`, `:219`) в 2 тестах + 1 тест на контракт декоратора = 3 теста. Все три в шаге 13, оценка пересмотрена до 1.5 ч. Аргумент `period` удаляется сейчас, мёртвый параметр не заводится |
| Латентный дефект `_calculate_recurring_before_date` (учитывает только income/expense, `calendar_service.py:400-407`, тогда как `_get_recurring_daily_changes` :426-437 учитывает и `savings_*`) искажает базу окна | Средняя | Подтверждено проверкой по коду. Инвариант AC-3 не ломает (`free` выводится из того, что вернул `calculate_daily_balances`), но абсолютные величины «Свободно» могут смещаться у пользователей с давним recurring-резервом. Правка вне scope (C-3); кандидат на отдельный протокол, запись в осадок |
| Тултип легенды (FR-4) hover-only — не работает на touch | Низкая (в scope) | `dbc.Tooltip(trigger="hover focus")` + элемент с `tabIndex=0`. Полноценный touch — Epic-08 |
| Аватар в шапке дублирует аватар в сайдбаре (C-1 запрещает трогать сайдбар) | Средняя | Осознанная временная цена куска 1, снимается в куске 3 (сайдбар → полоска-меню). В осадке решений |
| Правка `profile_modal.py` ломает вход в профиль из сайдбара | Низкая | Ветка расширяется через `triggered_id in (...)`, логика загрузки профиля не меняется; ручная проверка обоих входов (шаг 10) |
| Вехи целей загромождают 45-дневную ось | Низкая | ≤`MAX_MILESTONES_IN_WINDOW = 3` в окне, остальные — сводкой в тултипе «Резерв»; одна стрелка-аннотация `beyond_window` у правого края (эскиз v3) |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|---|---|---|---|
| FR-1.a | «Для каждого дня горизонта (текущий календарный месяц, начиная с сегодня) модель выдаёт декомпозицию прогнозного остатка на три слоя» | FR-1 | **ОСОЗНАННОЕ ОТСТУПЛЕНИЕ, решение владельца 2026-08-24 (`memory/spec-context/epic-11.md`, п. 2):** окно оси — 45 дней (`WINDOW_DAYS`), а не календарный месяц. Календарным месяцем ограничен только слой «Платежи» (`payments_end`). C-5 в design.md ограничивает *слой*, не ось. `MoneyLayersData['days']` — 45 дней | FR |
| FR-1.b | «*Свободно* — реально доступные деньги» | FR-1 | `DayLayers['free']` = `balance − payments − reserve` через `_split_day()` | FR |
| FR-1.c | «*Платежи* — деньги ещё на счету, но уйдут на уже запланированные платежи (регулярные + разовые предстоящие) до конца календарного месяца» | FR-1 | `_collect_operations` (регулярные + разовые + exceptions из `get_all_transactions_for_period`) → `_payments_tail_by_day` — суффиксная сумма в `(D, payments_end]`, только для платежей с датой `>= reference_date`; за `payments_end` слой строго `0` | FR |
| FR-1.d | «слой "тает" по мере исполнения платежей и пересчитывается на границе месяца» | FR-1 | Суффиксная сумма даёт монотонное таяние; `payments(payments_end) == 0`. «Пересчёт на границе месяца» = `payments_end` привязан к месяцу `reference_date`: 1-го числа горизонт платежей скачком становится новым месяцем, слой наполняется заново, при этом **ось не дёргается** (окно скользящее). Блок C шага 6 | FR |
| FR-1.e | «*Резерв* — резерв целей (бюджет накоплений) + подушка» | FR-1 | `reserve_configured(D) = cushion_threshold + goals_part(D)`, где `cushion_threshold` — **порог** подушки (решение владельца п. 1), `goals_part(D)` — **единая формула** `max(0, budget − consumed(D) − committed(D))` (замечания №1, №2). Фактический `reserve(D)` — результат каскада `_split_day`, **единственного** механизма обрезки (решение владельца п. 3б). Численная трассировка на 9 кейсах в «Модели данных»; блок A шага 6 задаёт числа | FR |
| FR-1.f | «Сумма трёх слоёв на день D равна прогнозному остатку на D (согласована с балансом кассового календаря)» | FR-1 | Конструктивно: `free` выводится вычитанием из `calculate_daily_balances`, `_split_day` сохраняет сумму во всех ветках. Блок B шага 6 — параметризованно по 45 дням. **Оговорка:** этот инвариант по построению слеп к раскладке слоёв и потому НЕ считается главной защитой корректности (см. FR-1.e и блок A) | FR |
| FR-1.g | «Модель — единый источник для шапки, графика и (в куске 2) карточек щитка» | FR-1 | Один вызов `get_money_layers()` в `_load_dashboard_components()` кормит `build_free_header()` и `build_layers_chart()`. Оговорка: контракт куска 1 не претендует на стабильность до куска 2 (докстринг модуля) | FR |
| FR-2.a | «Вверху дашборда: "Свободно сегодня: N ₽" (N — срез модели FR-1 на сегодня)» | FR-2 | `build_free_header()`: метка «Свободно сегодня» + `format_rub(data['today']['free'])`; тест `today['free'] == days[0]['free']` и `days[0]['date'] == reference_date` | FR |
| FR-2.b | «цветовой вердикт состояния (порядок / впереди просадка / проблема)» | FR-2 | **ТРЕБОВАНИЕ СНЯТО РЕШЕНИЕМ ВЛАДЕЛЬЦА 2026-08-24** (`memory/spec-context/epic-11.md`, п. 3а). Не реализуется: нет уровней ok/dip/problem, порогов просадки, цветных чипов, сигнальной шины, оценочных подписей. Из контракта не создаются `VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`, поля `level`/`text`/`dip_threshold`. Причина владельца: любой порог произволен (всегда зелёный / всегда красный / плывёт от даты — critique-v2 №5), проблемные дни видны на самом графике. **Это осознанное отступление от буквы спеки, а не покрытие.** Что осталось: минимум окна (`min_free`, `min_free_date`) — но исключительно как данные для маркера графика FR-3.e, без оценочного вывода | FR |
| FR-2.c | «краткий разбор "баланс − платежи − резерв"» | FR-2 | `pnl-breakdown`: «баланс {balance} − платежи {payments} − резерв {reserve}» из `TodaySlice` через `format_rub`. При `degraded=True` добавляется нейтральная сноска «часть данных недоступна…» | FR |
| FR-2.d | «Справа — аватар пользователя и служебная иконка настроек» | FR-2 | `get_avatar_emoji(profile['avatar_id'])` + `profile['name']` в `pnl-avatar`; шестерёнка `id="dashboard-settings-cog"` → **новый Input в `profile_modal.py`** (решение владельца п. 5), открывает модал профиля. `/settings` вне scope, `title="Профиль и настройки"` | FR |
| FR-2.e | «Шапка не является дверью-переходом» | FR-2 | На `pnl-breaker` нет `dcc.Link`, `n_clicks`, `cursor:pointer`; кликабельны только «Сверка» и шестерёнка | FR |
| FR-2.f | «Шапка-вердикт **заменяет текущий ряд 4 KPI-карточек** (два "главных числа" рядом недопустимы)» | FR-2 | Удаляются `build_overview_cards()`, `_build_kpi_card()`, `build_statistics_card()`; `dashboard-overview-cards` и `dashboard-statistics-card` уходят из layout; на их место — `dashboard-free-header`. Приветствие тоже поглощается | FR |
| FR-3.a | «Текущий график (grouped bars + линия баланса, протокол 0022) заменяется полностью» | FR-3 | Удаляются `_build_daily_cashflow_chart()`, `_build_yearly_cashflow_chart()`, `build_cashflow_chart()`; `dashboard-cashflow-chart` → `dashboard-layers-chart` | FR |
| FR-3.b | «стопка полос Свободно (зелёный) / Платежи (оранжевый) / Резерв (синий) по дням» | FR-3 | `barmode="stack"`, три `go.Bar` по датам; `LAYER_COLORS`: `#2ecc71` / `#f0b775` / `#3498db`; порядок снизу вверх free → payments → reserve (как в v3) | FR |
| FR-3.c | «вехи целей на оси времени» | FR-3 | `GoalMilestone` + аннотации Plotly (флажок ⚑, название, дата); ≤`MAX_MILESTONES_IN_WINDOW = 3` в окне + одна `beyond_window` стрелкой у правого края. При окне 45 дней и валидации `create_goal` (`target_date >= today + 7`, `goal_service.py:91-98`) вехи попадают в кадр регулярно | FR |
| FR-3.d | «вертикальная линия "сегодня"» | FR-3 | `fig.add_shape` (`yref="paper"`) на `reference_date`, `dash="dash"`, подпись «сегодня» — как в v3. Линия у левого края окна (композиция эскиза) | FR |
| FR-3.e | «маркер минимума остатка» | FR-3 | Маркер-кружок на `data['min_free_date']` + аннотация `format_rub(data['min_free'])` со сдвигом (`yshift`/`ay`, заметка vision-критика). Минимум по всем 45 дням — не вырождается в «сегодня». **Это единственный потребитель `min_free`:** оценочного вывода из него нет (см. FR-2.b) | FR |
| FR-3.f | «График и шапка — единый визуальный блок: "свободно сегодня" есть срез графика на сегодня» | FR-3 | Одна модель на оба блока; тест `today['free'] == days[0]['free']`; визуально `pnl-meter` примыкает к `pnl-breaker` | FR |
| FR-4.a | «У легенды графика — пояснение с конкретикой: для "Платежей" — список предстоящих платежей с датами» | FR-4 | `_build_payments_tooltip()`: `dbc.Tooltip` на элементе легенды «Платежи», строки «{описание} · {дата} · {сумма}» из `upcoming_payments`, до 8 + «и ещё N». Только текстовые компоненты (без `dcc.Markdown`) | FR |
| FR-4.b | «для остальных слоёв — что входит в слой» | FR-4 | «Свободно»: «Остаток минус платежи до конца месяца и резерв». «Резерв целей и подушки»: **честная подпись по факту дня** (решение владельца п. 3б) — «Порог подушки {cushion_threshold} + бюджет целей {goals_reserve_today}», а при сжатой полосе «В этот день на резерв остаётся {reserve} из {reserve_configured} — вы залезаете в подушку». Цифра всегда совпадает с высотой полосы | FR |
| FR-5.a | «Вход в "Сверку" с дашборда сохраняется (сейчас — кнопка на KPI-карточке баланса)» | FR-5 | Кнопка «Сверка» переезжает в правый блок шапки, id `open-recon-from-dashboard-header-btn`, тот же clientside `ClientsideFunction("triggers","timestamp_trigger")` → `open-recon-trigger`. Баннерная кнопка `open-recon-from-dashboard-banner-btn` не трогается | FR |
| FR-5.b | «Судьба показателя "Доходы за месяц" решается проектированием явно: сохранить в новом месте или убрать осознанно (не потерять молча)» | FR-5 | **Решение: убрать с дашборда осознанно.** Основание: не отвечает ни на один вопрос иерархии внимания design.md; его проекция — «цифра месяца» карточки «Аналитика» (кусок 2). Данные сохранны: `CalendarService.get_month_summary`, `DashboardService.get_overview_metrics` (сервис не удаляется — C-3), раздел `/analytics`. Запись в `memory/spec-context/epic-11.md` | FR |
| FR-6.a | «При нулевых данных (новый пользователь, 0 операций) шапка и график показывают спроектированное пустое состояние» | FR-6 | `is_empty` через `_is_empty()` — **без отдельного запроса** (замечание №8): `starting_balance == 0` И нет recurring-шаблонов И нет операций в диапазоне сбора И все `forecast_balance` окна == 0. `_build_header_empty_state()` + `_build_chart_empty_state()`. Отдельно `window_is_flat` — график рисуется, а не подменяется | FR |
| FR-6.b | «без осей −1..1, склеек подписей и прочих артефактов деградации» | FR-6 | При `is_empty` Plotly не вызывается вовсе (`html.Div` вместо `dcc.Graph`) → оси −1..1 невозможны. Для непустых: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)` (нет «50.001k»); `xaxis=dict(type="date", tickmode="array", tickvals=_axis_tickvals(...), tickformat="%-d %b", tickangle=0)` — ~12 подписей на 45 днях, явные даты вместо `dtick` в спорных единицах (замечание №10) | FR |
| NFR-1 | «Загрузка дашборда с новой моделью и графиком — не медленнее текущего дашборда; ориентир < 2 секунд на локальной базе с наполненными данными» | NFR-1 | **Бюджет вызовов на `get_money_layers` (пересмотрен под 45 дней и единый сбор — замечания №6, №8):** 1 `calculate_daily_balances(ref, ref+44)` — 45 дней, внутри 1 полный обход recurring-истории через `_calculate_recurring_before_date`; **1** `get_all_transactions_for_period(month_start(ref), window_end)` — до 75 дней, **единственный** сбор, второго вызова нет; 1 `BudgetReservationService.get_settings` (только `monthly_budget`); 1 `CushionService.get_threshold_amount` (**без** обхода баланса); 1 `GoalService.get_all_by_user`; ≤1 `RecurringService.get_templates_for_user` для `is_empty` (только когда диапазон сбора пуст). **Ушли относительно v2:** `get_budget_progress` (внутри которого ещё один `get_settings`, `budget_reservation_service.py:190`), `_get_reserve_sum_for_month`, отдельный `count(transactions)` из `_detect_empty`. **Честная оговорка:** ещё один полный обход recurring-истории остаётся вне модели — в `_build_cushion_card_readonly` (`dashboard.py:395-398`), который C-1 запрещает трогать. Диапазон сбора вырос (≤75 дней против ≤31 в v2) — это цена источника данных за границей месяца. Замер на шаге 14 | NFR |
| NFR-2 | «Сбои расчёта модели логируются через loguru с трейсбеком (`logger.opt(exception=True)` — идиома проекта, протокол 0027), не молча» | NFR-2 | `logger.opt(exception=True).warning(...)` в fail-open ветках (бюджет целей, цели, неожиданный сбой порога) + флаг `degraded` для UI; `logger.opt(exception=True).error(...)` в `load_dashboard_data` / `refresh_dashboard_after_crud` вместо `logger.error(f"...{e}")` (`dashboard.py:1389`, `:1451`). Штатное «нет пользователя / подушка не настроена» — тихий дефолт без трейсбека (сигнал, не шум) | NFR |
| C-1 | «Остальные разделы (календарь, цели, операции, аналитика) и сайдбар в этом куске не трогаются. Таблицы операций, wishlist-виджет и карточка подушки на дашборде остаются как есть» | C-1 | Правки в `dashboard.py`, `profile_modal.py` (решение владельца п. 5: C-1 про сайдбар и другие разделы, а не про глобальный модал), `cushion_service.py` (добавление метода), `custom.css`, новых файлах. `sidebar.py`, `calendar.py`, `goals.py`, `transactions.py`, `analytics.py` не меняются. `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `build_wishlist_widget()`, `dashboard-cushion-card` остаются в layout и в tuple | C |
| C-2 | «Decimal для денег, session-контракт flush()/commit(), сервисы не знают о Dash» | C-2 | Все денежные поля TypedDict — `Decimal`; `MoneyLayersService` read-only (не вызывает `flush()`/`commit()` — писать нечего); `get_threshold_amount` read-only; импортов `dash`/`plotly` в сервисах и схеме нет | C |
| C-3 | «Существующее поведение сервисов не меняется — модель FR-1 строится надстройкой/композицией; полный прогон тестов (565 на 2026-08-21) остаётся зелёным» | C-3 | Ни один существующий метод `CalendarService`/`DashboardService`/`CushionService`/`BudgetReservationService`/`GoalService`/`RecurringService` не редактируется. **Одно явно зафиксированное отступление:** в `CushionService` **добавляется** новый метод `get_threshold_amount()` — C-3 запрещает менять поведение, а не расширять API. Фиксируется решением, не молча. **Улучшение относительно v2:** зависимости от **приватного** `BudgetReservationService._get_reserve_sum_for_month` больше нет — нарушение инкапсуляции, введённое v2, снято вместе с режимным ветвлением. `tests/test_dashboard_service.py`, `test_calendar_service.py`, `test_budget_reservation_service.py`, `test_goal_service.py` не правятся (доказательство C-3); правится только `test_dashboard_callbacks.py` (контракт callback'а, 3 теста) и дополняется `test_cushion_service.py` | C |
| C-4 | «Схема БД не меняется» | C-4 | Проверено по таблице «Модель данных»: `users.starting_balance/cushion_target/cushion_threshold_percent/monthly_savings_budget/avatar_id/name`, `transactions.*`, `goals.target_date/target_amount/current_amount/status` — всё есть. Отдельно проверено: колонки «ручная сумма порога подушки» в схеме нет (только `cushion_threshold_manual` — булев флаг, `database.py:107`), поэтому `threshold_amount` всегда вычисляется формулой. Отдельно: месячной истории бюджета целей в схеме нет (`monthly_savings_budget` — одна настройка, `database.py:99`), поэтому `budget(D) == monthly_budget` для любого D — это зафиксировано в докстринге `_goals_part_by_day`, а не подразумевается. **Поля `reservation_mode`/`reservation_day` моделью больше не читаются** (формула не ветвится). Миграций нет | C |
| C-5.a | «Горизонт слоя "Платежи" — до конца календарного месяца (принятое решение design.md; платежи начала следующего месяца до зарплаты не видны — осознанное ограничение)» | C-5 | `payments_end = date(y, m, monthrange(y, m)[1])`; `_payments_tail_by_day` не смотрит за `payments_end`, для `D >= payments_end` возвращает `0`. **Уточнение относительно v2:** `payments_end` — теперь чисто арифметический фильтр, а не граница сбора данных; сбор идёт до `window_end` (замечание №6). C-5 соблюдён так же буквально: в слой «Платежи» ни одна операция следующего месяца не попадает. Ось при этом 45 дней (решение владельца п. 2), поэтому **ограничение видно честно**: за 31 августа оранжевой полосы просто нет. Задокументировано в докстринге сервиса и в тултипе легенды | C |
| C-5.b | «Механику "основного дохода" не реализовывать» | C-5 | Нет ни поля, ни ветвления по «основному доходу»; горизонт платежей фиксирован календарным месяцем, окно оси — константой | C |
| AC-1 | «Наполненная база → видна шапка "Свободно сегодня: N ₽" с цветовым вердиктом и разбором, и N совпадает со значением слоя "Свободно" модели на сегодняшнюю дату (срез графика)» | AC-1 | Покрыто **частично, с явным отступлением:** шапка, число N и разбор — реализованы (`build_free_header`, тест `today['free'] == days[0]['free']`, ручная проверка шага 14). Часть «**с цветовым вердиктом**» — **СНЯТА решением владельца п. 3а** (см. FR-2.b). При приёмке этот фрагмент AC-1 не проверяется — он не должен считаться проваленным критерием, но и не считается выполненным | AC |
| AC-2 | «Отображается график стопки трёх полос с легендой "Свободно / Платежи / Резерв", вехами целей, линией "сегодня" и маркером минимума; старый график доходы/расходы+баланс и ряд 4 KPI-карточек отсутствуют» | AC-2 | `build_layers_chart()` + `_build_layer_legend()`; физическое удаление `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`, `build_cashflow_chart`, `build_overview_cards`, `_build_kpi_card`, `build_statistics_card` (шаг 12) + grep-проверка в чек-листе | AC |
| AC-3 | «Для любого дня D горизонта сумма трёх слоёв модели равна прогнозному остатку на D из кассового календаря (CalendarService) — проверено unit-тестом» | AC-3 | Блок B шага 6: для всех 45 дней `free + payments + reserve == forecast_balance` и `forecast_balance == calculate_daily_balances()[date]`; кейсы: положительный / нулевой / отрицательный остаток, дефицитный каскад, оба режима, дни по обе стороны границы месяца. **Явная оговорка (замечание №7):** этот тест по построению зелёный при любой раскладке слоёв, поэтому корректность модели держит блок A («таблица ожидаемых слоёв»), а не AC-3 | AC |
| AC-4 | «Наведение/клик на пояснение легенды "Платежи" показывает список конкретных предстоящих платежей с датами до конца месяца» | AC-4 | `dbc.Tooltip(target="pnl-legend-payments", trigger="hover focus")` со строками из `upcoming_payments`; элемент легенды с `tabIndex=0`. Тултип объясняет и пустой случай («до конца месяца платежей больше нет») | AC |
| AC-5 | «Чистая база (онбординг пропущен, 0 операций) → шапка и график показывают осмысленное пустое состояние без артефактов (осей −1..1, "50.001k", склеек подписей)» | AC-5 | Ветка `is_empty` (Plotly не вызывается) + тесты блока G: «чистая база → `is_empty=True`, слои нулевые, исключений нет»; «онбординг пропущен (`skip()` → `first_launch=False`, `starting_balance=0`) → `is_empty=True`» (проверено: `first_launch` для критерия не годится, `onboarding_service.py:168-182`); «в `_is_empty` нет обращений к БД». Ручная проверка на чистой базе (шаг 14) | AC |
| AC-6 | «Вход в сверку с дашборда работает: модал сверки открывается и применяется, как до редизайна» | AC-6 | `open-recon-from-dashboard-header-btn` → тот же clientside → `open-recon-trigger` → существующий `create_reconciliation_modal()` в `main.py` (не трогается); баннерный вход сохранён; второй потребитель триггера в `calendar.py:1262-1309` не затронут (контракт Store не меняется) | AC |
| AC-7 | «Новая модель покрыта unit-тестами (включая границу месяца и "таяние" платежей); полный прогон pytest зелёный; black + flake8 без новых замечаний» | AC-7 | `tests/test_money_layers_service.py` — ~34 теста в 10 блоках (шаг 6), включая **блок A «таблица ожидаемых слоёв»**, без которого AC-7 достигался бы формально при неработающей модели (замечание №7); блоки C и F — явно про таяние и границы месяцев; дополнения в `test_cushion_service.py`; шаг 14 — `pytest -q` (565 + новые), `black`, `flake8` | AC |
| Эскиз | «легенду графика вынести из поля» (заметка vision-критика) | memory/spec-context | `showlegend=False` в Plotly; HTML-легенда `_build_layer_legend()` под заголовком блока графика | Заметка |
| Эскиз | «ярлык минимума ("9 800 ₽") не ставить вплотную к тику даты» | memory/spec-context | Аннотация минимума со сдвигом (`yshift`/`ay`) + развёрнутая плашка «Минимум свободного» в свободной зоне поля, не под тиком | Заметка |
| Эскиз | «выровнять вертикальный ритм карточки "Цели"» | memory/spec-context | Не применимо к куску 1 (карточки-двери — кусок 2). Заметка остаётся в осадке | Заметка |
| Эскиз | Ось «~45 дней» (`v3.html` aria-label: «с 22 августа по 5 октября 2026») | .visual + осадок | `WINDOW_DAYS = 45`; `_axis_tickvals` → 12 подписей (в эскизе 11); минимум, зарплата и веха за краем попадают в кадр | Эскиз |
| Эскиз | Вердикт-чип «Всё в порядке» зелёной плашкой (brief.md эскиза, п. 1) | .visual + осадок | **НЕ РЕАЛИЗУЕТСЯ — решение владельца п. 3а** (принято 2026-08-24, позже принятия эскиза). Отступление от принятого эскиза зафиксировано явно; композиция шапки сохраняется, место чипа занимает разбор | Эскиз |
| Эскиз | «Свободно сегодня: 32 000 ₽» при разборе «84 500 − 37 500 − 15 000» | .visual + осадок | **Числовое расхождение зафиксировано явно:** на реальных данных проекта recurring-резерв целей входит в список операций и потому сидит в слое «Платежи»; корректный разбор — `84 500 − 37 500 − 30 000 (порог подушки) = 17 000`. Моковая арифметика эскиза предполагала, что резерв целей вне «обещано». Композиция и метафора эскиза не меняются; расхождение — в осадок решений | Эскиз |

## Blast Radius

### Прямые изменения

- `app/schema/money_layers.py` — **НОВЫЙ**: `DayLayers`, `UpcomingPayment`, `GoalMilestone`, `TodaySlice`, `MoneyLayersData`, `Horizons`; `LayerKey`; `WINDOW_DAYS`, `MAX_MILESTONES_IN_WINDOW`, `TARGET_X_TICKS`, `LAYER_COLORS`, `LAYER_LABELS`. **Не создаются** (п. 3а): `VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`.
- `app/services/money_layers_service.py` — **НОВЫЙ**: `MoneyLayersService.get_money_layers()` + `_horizons`, `_forecast_balances`, `_collect_operations`, `_payments_tail_by_day`, `_goals_part_by_day`, `_split_day`, `_today_slice`, `_window_min_free`, `_goal_milestones`, `_is_empty`.
- `app/assets/panel.css` — **НОВЫЙ**: `pnl-*` (шапка, блок графика, HTML-легенда). Без классов сигнальной шины/чипа вердикта.
- `app/services/cushion_service.py` — **ДОБАВЛЕНИЕ** `get_threshold_amount()`; существующие методы не тронуты (явное отступление от буквы C-3).
- `app/components/dashboard.py` — крупнейший blast: удаление 4 KPI-карточек, `build_statistics_card`, обоих старых графиков и мёртвого кода; добавление `build_free_header`, `build_layers_chart`, `_build_layer_legend`, `_build_payments_tooltip`, `_build_reserve_tooltip`, `_build_header_empty_state`, `_build_chart_empty_state`, `_axis_tickvals`; перекройка `create_dashboard_layout` (снятие `period-switcher` :118-128, `dashboard-greeting` :108-112, `dashboard-overview-cards` :129-133, `dashboard-statistics-card` :170), `_load_dashboard_components` (**сигнатура `(period_state)`**, 5 значений), `load_dashboard_data` (5 Output'ов, снятие `Input("period-switcher","value")`, `logger.opt`), `refresh_dashboard_after_crud` (5 Output'ов, `logger.opt`), `open_create_from_chart` (Input → `dashboard-layers-chart-graph`, ISO-дата), clientside «Сверка» (новый id); **удаление** callback'а `update_period_state` (:1397-1408).
- `app/components/profile_modal.py` — **прямые изменения** (решение владельца п. 5): второй `Input("dashboard-settings-cog", "n_clicks")` и ветка `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")` (сейчас единственный Input :96 и жёсткое сравнение :119).
- `app/schema/__init__.py` — реэкспорт новых типов и констант (+ `__all__`).
- `app/services/__init__.py` — реэкспорт `MoneyLayersService` и типов модели (+ `__all__`).
- `app/assets/custom.css` — удаление `#dashboard-overview-cards .row`, `.db-period-switcher` (все правила), `.kpi-card` / `.kpi-card-icon` / `.kpi-trend*` / `.kpi-number` / `.kpi-title` / `.kpi-subtitle` (:195-268) — grep проведён, вне `dashboard.py` и `custom.css` не используются; `.an-period-switcher` в analytics — отдельный класс; правка `.db-page` / `.db-left-col` под новую сетку.
- `tests/test_money_layers_service.py` — **НОВЫЙ**: FR-1 / AC-3 / AC-7, 10 блоков (см. шаг 6).
- `tests/test_dashboard_callbacks.py` — **три** теста: `test_load_dashboard_data_decorator_declares_greeting_output` (:62-70), `test_returns_seven_values_with_greeting_last` (:188-210), `test_wrong_pathname_prevents_update` (:212-222) + докстринг модуля (:9-11, ссылка на «7-й Output»). `TestBuildGreetingText` и подписки на `profile-updated` не трогаются.
- `tests/test_cushion_service.py` — тесты `get_threshold_amount`.

### Связанные файлы

- `app/main.py` — `suppress_callback_exceptions=True` (:41) и глобальные Store'ы (`open-recon-trigger` :95, `profile-updated` :91, `balance-toast-dismissed` :93), `create_reconciliation_modal()`, `create_profile_modal()`. Проверить, что снятый `period-switcher` не ломает старт.
- `app/components/calendar.py` — второй потребитель `open-recon-trigger` (:1262-1309): контракт триггера менять нельзя.
- `app/components/sidebar.py` — `sidebar-profile-container` остаётся первым Input'ом модала; C-1 запрещает правки; визуальный дубль аватара — осознанная цена до куска 3.
- `app/config/avatars.py` — `get_avatar_emoji()`, `AVATARS`, `DEFAULT_AVATAR_ID` для шапки.
- `app/components/wishlist.py` — `build_wishlist_widget()` вызывается прямо из `create_dashboard_layout` (:167): при перекройке layout нельзя потерять вызов (C-1).
- `app/components/transaction_modals.py` — `create-modal`, `preselected-date`, `modal-source`: Output'ы `open_create_from_chart`, парсинг клика меняется (`int(point["x"])` → ISO-дата).
- `app/services/dashboard_service.py` — **НЕ меняется** (C-3), но `get_overview_metrics`, `get_daily_cashflow`, `get_yearly_cashflow`, `get_cashflow_data` теряют вызывающего на дашборде: остаются в публичном API и под тестами, удалять нельзя.
- `app/services/calendar_service.py` — **НЕ меняется**; латентный дефект `_calculate_recurring_before_date` (:400-407 учитывает только income/expense, тогда как `_get_recurring_daily_changes` :426-437 учитывает и `savings_*`) подтверждён и остаётся вне scope — кандидат на отдельный протокол.
- `app/services/budget_reservation_service.py` — **НЕ меняется**; `get_budget_progress` и `_get_reserve_sum_for_month` моделью **не вызываются** (в отличие от v2) — приватный метод остаётся без вызывающих, нарушения инкапсуляции нет.
- `app/services/recurring_service.py` — **НЕ меняется**; `get_templates_for_user` (:114-137) используется как есть для `is_empty`.
- `app/assets/clientside_triggers.js` — namespace `triggers`, `timestamp_trigger` / `open_create_modal`: переиспользуются новыми id, файл не меняется.
- `tests/test_dashboard_service.py`, `tests/test_calendar_service.py`, `tests/test_budget_reservation_service.py`, `tests/test_goal_service.py`, `tests/test_purchase_recommendation.py` — не должны требовать правок; если потребовали — признак нарушения C-3.
- `tests/test_bootstrap.py`, `tests/test_serializers.py` — smoke-тесты layout/сериализации: могут поймать несериализуемые объекты или отсутствующие id.
- `.obsidian-docs/knowledge-bank/modules/services.md`, `modules/schema.md`, `modules/ui-components.md`, `patterns/plotly-charts.md`, `architecture.md` — обновление KB после реализации (Dual-Y-Axis паттерн перестаёт применяться на дашборде; появляется паттерн stacked-decomposition).
- `memory/spec-context/epic-11.md` — записать: судьба «Доходов за месяц» (убрать), достаточность схемы БД, поглощение `dashboard-greeting` шапкой, **единая формула резерва без режимного ветвления**, **числовое расхождение с моковой арифметикой эскиза (17 000 против 32 000) и его причина**, отступление от эскиза в части вердикт-чипа, добавление `get_threshold_amount` как отступление от буквы C-3, удаление аргумента `period`, латентный дефект `_calculate_recurring_before_date`.

### Проверить после реализации

- [ ] `pytest -q` — 565 прежних зелёные + новые; в `test_dashboard_service.py`, `test_calendar_service.py`, `test_budget_reservation_service.py`, `test_goal_service.py` ни одной правки (доказательство C-3).
- [ ] `grep -rn "period_value" app tests` — пусто.
- [ ] `grep -rn "build_overview_cards\|_build_kpi_card\|_build_daily_cashflow_chart\|_build_yearly_cashflow_chart\|build_cashflow_chart\|build_statistics_card\|dashboard-overview-cards\|dashboard-statistics-card\|dashboard-greeting\|period-switcher\|update_period_state\|kpi-" app tests` — по дашборду пусто (остаются только `an-period-switcher` в analytics).
- [ ] `grep -rn "VERDICT_\|dip_threshold\|DIP_RATIO\|DIP_FLOOR\|VerdictLevel" app tests` — пусто (вердикт снят, п. 3а).
- [ ] `grep -rn "_get_reserve_sum_for_month\|get_budget_progress" app/services/money_layers_service.py` — пусто (замечание №1: зависимость снята).
- [ ] Открыть `/` и `/dashboard`: нет ошибок в консоли про nonexistent object `period-switcher`, `dashboard-overview-cards`, `dashboard-statistics-card`, `dashboard-greeting`, `daily-cashflow-chart`.
- [ ] AC-1: число в шапке == высота зелёной полосы «сегодня» (hover) == `days[0]['free']`; разбор арифметически сходится.
- [ ] AC-3 вручную: на наполненной базе для 3 произвольных дней (один до, один после границы месяца) сумма слоёв из hover == остаток того же дня в `/calendar`.
- [ ] **🔴№1 вручную:** режим `fixed_date`, бюджет 15 000, резерв 25-го, взнос **5 000** (частичный) — синяя полоса сегодня содержит ровно 5 000 бюджета целей поверх порога подушки; не 0 и не 15 000.
- [ ] **🔴№1 вручную (симметрия):** режим `from_balance`, бюджет 15 000, взнос 5 000 с датой **в будущем** этого месяца — синяя полоса содержит 10 000 бюджета целей, взнос виден в оранжевом слое.
- [ ] **🔴№2 вручную:** `fixed_date`, резерв 25-го, взносов нет — синяя полоса на последнем дне месяца, на 1-м числе следующего и на дне после резерва следующего месяца равна порогу подушки (бюджет целей 0), **не растёт** к правому краю окна. На правом крае (месяц без резерва в окне) содержит один месячный бюджет, не два.
- [ ] **🟡№4 / п. 3б:** день с остатком ниже порога подушки — синяя полоса упирается в остаток, а тултип называет ФАКТ дня и настройку рядом; цифра тултипа == высота полосы.
- [ ] AC-4: hover и Tab-фокус на легенде «Платежи» → список с датами; проверить месяц без платежей (тултип объясняющий, не пустой).
- [ ] AC-5: чистая база — шапка и график в пустом состоянии, в DOM нет `dcc.Graph` от графика слоёв.
- [ ] Отдельно: база с историей и пустым окном → **график рисуется** (плоская стопка), пустое состояние не подменяет его.
- [ ] AC-6: кнопка в шапке и кнопка в баннере обе открывают модал сверки; сверка применяется; вход с `/calendar` не сломан.
- [ ] Шестерёнка в шапке открывает модал профиля; клик по аватару в сайдбаре — тоже (обе ветки живы).
- [ ] Границы: `reference_date` = последний день месяца (окно 45 дней, `payments == 0` всюду, `consumed` считается от 1-го числа); `reference_date` = 1-е число; февраль; переход через год.
- [ ] NFR-1: замер времени рендера на наполненной базе — < 2 сек и не хуже прежнего; в логах ровно один `calculate_daily_balances` и ровно один `get_all_transactions_for_period` от модели.
- [ ] NFR-2: monkeypatch-падение чтения `monthly_budget` → трейсбек через `logger.opt(exception=True)`, `degraded=True`, в шапке видна сноска «часть данных недоступна», дашборд рендерится. Отдельно: чистая база **не** генерирует варнинг-с-трейсбеком.
- [ ] `black --check app tests` и `flake8 app tests` — без новых замечаний.
- [ ] Wishlist-виджет, таблицы недавних/предстоящих операций и карточка подушки на месте и живые (C-1).

## Учтённые замечания из критики

| Замечание из critique v2 | Как решено |
|---|---|
| 🔴 №1. Двойное вычитание в режимной формуле `goals_part`: в `fixed_date` при **частичном** взносе `_get_reserve_sum_for_month` и `Σ savings_* в (D, month_end]` считают один и тот же будущий exception (трассировка критика: 15 000 − 10 000 − 10 000 → 0 вместо 5 000). Симметрично в `from_balance` при взносе с будущей датой (`used_budget` из `get_budget_progress` считает весь месяц включительно) | Принят **Подход A** критика, самостоятельно проверенный на 9 кейсах (см. «Численная трассировка»). Единая формула без режимного ветвления: `goals_part(D) = max(0, budget − consumed(D) − committed(D))`, где `consumed(D)` = Σ savings-операций в `[month_start(D), D]` (уже ушло из `balance(D)`), `committed(D)` = Σ в `(D, month_end(D)]` (лежит в слое «Платежи»). Каждая операция попадает ровно в одно слагаемое — по своей дате относительно D. Кейс критика даёт **5 000** (кейс 2 таблицы), симметричный кейс `from_balance` с будущей датой — **10 000** (кейс 8). Из пути модели **удалены** `get_budget_progress`, приватный `_get_reserve_sum_for_month` (нарушение инкапсуляции, введённое v2, снято) и чтение `reservation_mode`. Риск «Высокая» в таблице рисков понижен до «Низкая» вместе со снятым ветвлением; шаг 4 плана подешевел с 4 ч до 2.5 ч. Обязательные тесты критика — в блоке A шага 6 с явными числами по всем трём слоям |
| 🔴 №2. Наследование базы резерва через границу месяца (`goals_part(D) = goals_part(month_end) + Σ ...`) накапливает исполненные резервы: синяя полоса раздута к правому краю окна, «Свободно» занижено; обоснование v2 неверно по знаку | Наследования **нет**: месяц бюджета берётся **по месяцу дня D** (`month_start(D)`, `month_end(D)`), одна и та же формула для всех D окна, никакой отдельной ветки за границей месяца. Ошибка v2 по знаку признана: когда резерв уходит из баланса, `free = balance − payments − reserve` уменьшается автоматически, и добавлять ту же сумму в `reserve` значит вычесть её из `free` второй раз. **Показано, что `goals_part` не накапливается на 45-дневном окне** (кейс 9 таблицы): 31 авг → 0, 1 сент → 0, 26 сент → 0, 30 сент → 0 (v2 давал 15 000 / 15 000 / 30 000 / 30 000). Максимум `goals_part` по окну равен одному `monthly_budget`, а не сумме исполненных резервов. Три ручные проверки в чек-листе |
| 🟡 №3. Снятие `period-switcher` убирает позиционный `period_value` — падают ВСЕ тесты с `period_value=`, не два названных; судьба мёртвого аргумента `period` не решена явно | **Полный список закрыт grep'ом** `period_value=` по `tests/` и `app/`: ровно два вызова — `tests/test_dashboard_callbacks.py:204` (в `test_returns_seven_values_with_greeting_last`) и `:219` (в `test_wrong_pathname_prevents_update`). Плюс третий затронутый тест — `test_load_dashboard_data_decorator_declares_greeting_output` (:62-70, ассерт на Output `dashboard-greeting`), плюс докстринг модуля (:9-11, «7-й Output»). **Итого 3 теста + докстринг**, все перечислены в шаге 13; оценка пересмотрена 1 ч → **1.5 ч**. Судьба `period` решена **явно и в эту сторону**: аргумент **удаляется** из `_load_dashboard_components` сейчас (сигнатура становится `(period_state)`), мёртвый параметр не заводится. Основание: `update_period_state` — единственный писатель Store, он снимается вместе с единственным своим Input'ом, значит `period` навсегда получал бы дефолт из layout. Store `dashboard-period` **остаётся** (его читает `open_create_from_chart` как guard), `period_state` в сигнатуре сохраняется |
| 🟡 №4. `cushion_part = min(threshold, max(balance, 0))` делает слой «Резерв» немонотонным, дублирует каскад `_split_day`, и тултип называет число, не совпадающее с высотой полосы | Реализовано решение владельца п. 3б: `min(...)` из `cushion_part` **убран**, `cushion_part = cushion_threshold` — константа по окну. Вся защита «не больше, чем есть» — исключительно в каскаде `_split_day` (**один** механизм, порядок гашения зафиксирован: сначала `reserve`, затем `payments`). Честная подпись обеспечена конструктивно: в контракт добавлены `DayLayers['reserve_configured']` и `MoneyLayersData['reserve_configured_today']`, тултип строится из ФАКТА дня («на резерв остаётся 18 000 из 30 000 — вы залезаете в подушку»), а не из настройки. Цифра тултипа всегда == высота полосы. Числовой пример сжатия — в «Модели данных»; блоки D и E шага 6 + пункт чек-листа |
| 🟡 №5. Относительный `dip_threshold` привязан к сумме платежей окна, которая тает по ходу месяца → вердикт смягчается к 30-му и жестчает 1-го на неизменных данных | **Потеряло предмет: вердикт снят полностью** решением владельца п. 3а. Из контракта не создаются `DIP_RATIO`, `DIP_FLOOR`, `VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `LayersVerdict.level/text/dip_threshold`; сигнальной шины и чипа в шапке нет; шапка не выносит оценок. Механики дрейфа больше не существует. `min_free`/`min_free_date` сохранены, но исключительно как данные для маркера графика (FR-3.e) — оценочного вывода из них не делается. Отступление от буквы FR-2.b и от эскиза зафиксировано в RTM **двумя отдельными строками** явно, не молча. Смежное замечание критика об fail-open («приглушить вердикт») тоже потеряло предмет — вместо этого введён флаг `degraded` и текстовая пометка в разборе: опасное направление деградации обозначено в UI, а число не подменяется |
| 🟡 №6. Нет источника данных за границей месяца: `_collect_upcoming_payments` ограничен `payments_end`, а формула резерва требует операций до `window_end`; бюджет NFR-1 занижен | Введён **третий** горизонт: `collect_start = month_start(reference_date)`. Операции собираются **одним** вызовом `get_all_transactions_for_period(collect_start, window_end)` — до 75 дней; `payments_end` стал **чисто арифметическим фильтром** суффиксной суммы слоя «Платежи» (C-5 соблюдён так же буквально). Левая граница сдвинута к началу месяца не произвольно: `consumed(reference_date)` требует savings-операций, датированных ДО сегодня в текущем месяце (взнос 10-го при сегодня 22-м). Второго вызова нет. **Бюджет вызовов NFR-1 переписан** под 45 дней и единый сбор с явным перечислением ушедших вызовов (`get_budget_progress` вместе с вложенным `get_settings`, `_get_reserve_sum_for_month`, `count(transactions)`); оценки шагов 3 и 4 пересмотрены (3: 4 → 4.5 ч; 4: 4 → 2.5 ч) |
| 🟡 №7. Тесты слепы к раскладке слоёв — AC-3 зелёный при неверной модели; оба блокера дожили до v2 именно из-за отсутствия теста на абсолютные величины | В план шага 6 добавлен **блок A «таблица ожидаемых слоёв»** — параметризованный тест, задающий **ЧИСЛАМИ все три слоя** для матрицы `режим (fixed_date/from_balance) × доля взноса (0 / частичный / полный бюджет) × позиция дня (до даты резерва / день резерва / после / последний день месяца / первый день следующего / после резерва следующего месяца / правый край окна)`. В таблицу **включены кейсы, на которых упали бы дефекты №1 и №2**: кейс 2 (`fixed_date` + взнос 5 000 из 15 000 → `goals_part == 5 000`, v2 дал бы 0), кейс 8 (`from_balance` + взнос с будущей датой → `goals_part == 10 000`, v2 дал бы 5 000), кейс 9 (31 авг / 26 сент / 30 сент → 0, v2 дал бы 15 000 / 30 000 / 30 000). Оценка шага 6 поднята 7 → **9 ч**, число тестов 22 → ~34. Слепота AC-3 признана **явно в RTM** (строки FR-1.f и AC-3): инвариант больше не объявляется главной защитой корректности |
| 🟢 №8. `_detect_empty` — лишний запрос ради флага, истинного один раз в жизни базы | Отдельного `count(transactions)` **нет**. `_is_empty` — чистая функция от уже полученных данных: `starting_balance == 0` И recurring-шаблонов нет И в диапазоне сбора нет ни платежей, ни savings-операций И все `forecast_balance` окна == 0. Корректность для AC-5 (чистая база) показана в докстринге: все четыре условия истинны по построению. Не ломает `window_is_flat`: у пользователя с историей и пустым окном `forecast_balance != 0` либо есть шаблоны, значит `is_empty=False`, `window_is_flat=True` и график **рисуется**. Единственный ложноположительный сценарий (история, сведшая остаток ровно в 0, без шаблонов, при `starting_balance == 0`) назван честно, и для него пустое состояние с кнопкой «Сверка» осмысленно. Тест «в `_is_empty` нет обращений к БД» — в блоке G шага 6. Строка бюджета вызовов NFR-1 обновлена (≤1 лёгкий `get_templates_for_user` вместо `count`) |
| 🟢 №9. `MAX_MILESTONES_IN_WINDOW` объявлен в Blast Radius, но отсутствует в листинге контракта | Константа **приведена в листинге** `app/schema/money_layers.py` с докстрингом (наравне с остальными), значение 3, обоснование — 45-дневная ось не должна зарастать флажками. Заодно добавлена `TARGET_X_TICKS = 11` (число подписей эскиза), чтобы `_axis_tickvals` не содержал магической константы |
| 🟢 №10. `_axis_dtick` возвращает «шаг в миллисекундах», а формула даёт дни | Функция **заменена** на `_axis_tickvals(window_dates) -> list[date]` — явный список дат для `xaxis=dict(tickmode="array", tickvals=...)`. Причина замены, а не правки докстринга: Plotly для оси `type="date"` принимает `dtick` и в миллисекундах, и строкой (`"D4"`, `"M1"`), поэтому единицы перепутать легко, а проверить трудно. Явные `tickvals` снимают неоднозначность полностью и дают контроль над попаданием граничных дат в подписи. Формула шага (`k = max(1, round(len / TARGET_X_TICKS))`, для 45 дней k = 4 → 12 подписей) сохранена как производная, а не как магическое число |

## Ответы на вопросы критика

**[факт] Откуда `_reserve_by_day` берёт `Σ SAVINGS_RESERVE/CONTRIBUTION с датой в [payments_end+1, D]` для дней за границей месяца, если единственный сбор операций (`_collect_upcoming_payments`) ограничен `payments_end`?**

**Критик прав: в v2 источника не было.** Проверено по коду: `get_all_transactions_for_period(user_id, start_date, end_date)` фильтрует обычные транзакции по `transaction_date >= start_date, <= end_date` (`calendar_service.py:786-796`) и генерирует recurring-инстансы ровно на тот же интервал (`:817-822` → `get_instances_with_exceptions(user_id, start_date, end_date)`, `recurring_service.py:666-671`). Никакого «заглядывания» за `end_date` метод не делает. Значит при вызове с `end_date = payments_end` операций после конца месяца в модели физически нет, и формула v2 для `D > payments_end` была невычислима — шаг 4 плана v2 нереализуем как написан.

В v3 источник появился и назван: **один** вызов `_collect_operations(user_id, collect_start, window_end)`, где `collect_start = month_start(reference_date)`, `window_end = reference_date + 44`. Левая граница сдвинута к началу месяца не «на всякий случай»: `consumed(reference_date) = Σ savings_* в [month_start, reference_date]` требует операций, датированных **до сегодня** в текущем месяце (взнос 10-го при сегодня 22-м — кейс 7 трассировки). `payments_end` больше не участвует в сборе данных, а только в арифметике суффиксной суммы слоя «Платежи». Бюджет вызовов NFR-1 обновлён: диапазон сбора ≤75 дней вместо ≤31, вызов один, при этом ушли `get_budget_progress` (внутри которого ещё один `get_settings`, `budget_reservation_service.py:190`), `_get_reserve_sum_for_month` и `count(transactions)` из `_detect_empty`.

**[факт] Проверялась ли формула `fixed_date` на частичном взносе (не равном полному бюджету)?**

**Нет — и критик прав, что в интервале между вырожденными границами формула v2 врёт.** Проверка по коду подтверждает механику полностью:

1. `GoalService.add_contribution` вызывает `create_contribution_transaction`, который в `fixed_date` возвращает `None` (`budget_reservation_service.py:667-672`) — транзакции взноса нет; `GoalContribution` создаётся с `transaction_id=None` (`goal_service.py:180-186`).
2. Затем вызывается `adjust_reserve_for_contribution` (`goal_service.py:190-194`), которая при `contribution_date < reserve_date` считает сумму взносов месяца до даты резерва (`:888-900`) и создаёт/обновляет exception через `RecurringService.create_exception` с `new_amount = max(budget − contributions_sum, 0)`.
3. `create_exception` создаёт **реальную строку** `Transaction` с `is_recurring=False`, `recurring_parent_id=template_id`, `transaction_date=original_date` (`recurring_service.py:480-493`).
4. `_get_reserve_sum_for_month` суммирует `SAVINGS_RESERVE` за месяц с фильтром `is_recurring.is_(False)` (`:466-498`) → **этот exception попадает в сумму**.
5. `get_all_transactions_for_period` через `get_instances_with_exceptions` возвращает **тот же exception** вместо виртуального инстанса (`recurring_service.py:706-711`, `calendar_service.py:846-870`), а `_collect_upcoming_payments` классифицирует `savings_reserve` как платёж → **тот же exception попадает и в суффиксную сумму**.

Трассировка критика воспроизводится точно: бюджет 15 000, резерв 25-го, взнос 5 000 10-го, сегодня 22-е → exception 25 авг = 10 000; `materialized` = 10 000; `Σ savings_* в (22, 31]` = 10 000; `goals_part = max(0, 15 000 − 10 000 − 10 000) = 0` при правильном ответе **5 000**. Оба примера v2 — вырожденные границы: при взносе 0 exception отсутствует, `materialized = 0` и хвост = 15 000; при взносе = полному бюджету exception = 0 и обе величины нулевые. Формула v2 верна ровно в этих двух точках.

Формула v3 проверена на **9 кейсах** в секции «Модель данных», включая три доли взноса (0 / частичный / полный), дни по обе стороны даты резерва, оба режима, симметричный кейс `from_balance` с будущей датой взноса и три точки за границей месяца. Кейс 2 даёт 5 000, кейс 8 — 10 000, кейс 9 показывает отсутствие накопления. Все девять вошли в блок A шага 6 как параметры с явными числами по всем трём слоям.

**[факт] Какие ещё тесты, кроме двух названных, вызывают `load_dashboard_data` с аргументом `period_value=` и потребуют правки?**

Полный список по grep. `grep -rn "period_value" app tests` даёт:
- `tests/test_dashboard_callbacks.py:204` — внутри `test_returns_seven_values_with_greeting_last` (класс `TestLoadDashboardDataGreeting`, :186-210);
- `tests/test_dashboard_callbacks.py:219` — внутри `test_wrong_pathname_prevents_update` (:212-222) — тест, который критик и назвал;
- `app/components/dashboard.py:1359, 1376, 1377, 1402, 1404, 1408` — сама сигнатура `load_dashboard_data` и callback `update_period_state`.

**Итого вызовов callback'а с `period_value=` в тестах — ровно два**, оба в `tests/test_dashboard_callbacks.py`, и это единственный тестовый файл, обращающийся к `load_dashboard_data` (grep по `load_dashboard_data` в `tests/` даёт только этот файл: :9 докстринг, :21 импорт, :53/:69 интроспекция декоратора, :202/:217 вызовы). Критик прав, что v2 назвал не тот состав: `test_wrong_pathname_prevents_update` действительно упадёт с `TypeError`, а `test_returns_seven_values_with_greeting_last` упадёт и по аргументу, и по числу значений.

**Затронуто три теста**, а не два и не «все» — третий не из-за `period_value`, а из-за снимаемого Output'а: `test_load_dashboard_data_decorator_declares_greeting_output` (:62-70) ассертит `'Output("dashboard-greeting", "children")' in _decorator_source(...)`. Плюс правки требует докстринг модуля (:9-11), который фиксирует «7-й Output» как контракт. Тесты `test_load_dashboard_data_decorator_declares_profile_updated_input` (:50), `test_toggle_balance_toast_decorator_declares_profile_updated_input` (:57) и весь класс `TestBuildGreetingText` (:72+) **не трогаются** — Input `profile-updated` сохраняется, хелпер `_build_greeting_text()` живёт. Оценка шага 13 пересмотрена: 1 ч → **1.5 ч**.

**Судьба мёртвого аргумента `period` решена явно:** он **удаляется** из `_load_dashboard_components` сейчас (сигнатура `(period_state)`), а не сохраняется с пометкой unused. Основание по коду: `update_period_state` (`dashboard.py:1397-1408`) — единственный писатель Store `dashboard-period`, и его единственный Input — `period-switcher` (:1399); снимая элемент, мы снимаем и callback, значит Store навсегда остаётся с дефолтом layout `{"period": "month"}` (:99-102). Аргумент, который может принимать только одно значение, — это не параметр. Store при этом **остаётся**: его читает `open_create_from_chart` как guard (:1462, :1477-1478).

**[решение] Что показывает синяя полоса в тултипе, если `cushion_part` сжат через `min(threshold, balance)`: настроенный порог или фактическое значение дня?**

**Закрыто решением владельца** (`memory/spec-context/epic-11.md`, п. 3б, 2026-08-24): обрезка слоя «Резерв» выполняется **в одном месте** — каскадом `_split_day`; `min(threshold, max(balance, 0))` из `cushion_part` убирается. Пояснение слоя **обязано отражать факт дня**, а не утверждать настроенное число, когда полоса ниже: расхождение цифры и картинки — та самая P1-боль эпика. Просадка синей полосы трактуется как осмысленный сигнал «в этот день вы залезаете в подушку».

Реализация: `cushion_part(D) = cushion_threshold` без `min`; `DayLayers['reserve']` — факт после каскада, `DayLayers['reserve_configured']` — настройка; тултип рендерит факт и настройку рядом, когда они расходятся («на резерв остаётся 18 000 из 30 000 — вы залезаете в подушку»), и одну настройку, когда совпадают. Цифра в тултипе всегда равна высоте полосы. Порядок гашения дефицита в каскаде зафиксирован (`reserve`, затем `payments`) — неопределённости «в каком порядке применяются два механизма», на которую указал критик, больше нет, потому что механизм один.

**[решение] Приемлем ли дрейф порога вердикта по дню месяца, или порог следует привязать к базе, постоянной внутри месяца?**

**Вопрос закрыт снятием самой механики.** Решение владельца (`memory/spec-context/epic-11.md`, п. 3а, 2026-08-24): **цветовой вердикт-светофор полностью убран из шапки**. Шапка содержит только «Свободно сегодня: N ₽» и разбор «баланс − платежи − резерв» — никаких уровней ok/dip/problem, порогов просадки, цветных чипов, оценочных подписей и сигнальной шины. Причина владельца дословно совпадает с диагнозом критика: «любой порог произволен — либо всегда зелёный, либо всегда красный, либо плывёт от даты (критика v2, замечание №5); проблемные дни пользователь видит на самом графике». Отброшены (в осадке): «факт о ближайшем минимуме в шапке» и «предупреждение только при отрицательном остатке» — не сейчас.

Следствия исполнены: из контракта не создаются `VerdictLevel`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR` и поля `level`/`text`/`dip_threshold`; `LayersVerdict` переименован в `TodaySlice` и сведён к четырём числам разбора; минимум окна переехал в `MoneyLayersData.min_free`/`min_free_date` и обслуживает **только** маркер графика (FR-3.e). Отступление от FR-2.b и от вердикт-чипа принятого эскиза зафиксировано в RTM двумя отдельными строками как решение владельца — явно, не молча, и без декларации ложного покрытия.

Смежное замечание критика (аспект 4: fail-open по бюджету целей деградирует в опасную сторону, «стоит приглушить вердикт») тоже потеряло свой инструмент. Решение вместо него: флаг `MoneyLayersData['degraded']` + нейтральная сноска в разборе шапки «часть данных недоступна, показано без бюджета целей» + отказ от утверждающего тултипа слоя «Резерв» в деградации. Число не подменяется и не скрывается — подменённое число хуже помеченного; но и не выдаётся за достоверное.
