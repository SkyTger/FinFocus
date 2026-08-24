# Solution v2: MoneyLayersService — окно 45 дней, порог подушки, режимно-корректный резерв

## Обзор решения

Относительно v1 изменено три сущностных вещи и восемь инженерных. **Сущностно:** (1) подушка в слое «Резерв» — `threshold_amount` (порог, `target × percent / 100`), а не полный `target`, чем главное число «Свободно сегодня» перестаёт залипать на нуле и становится согласованным с `PurchaseRecommendationService`; (2) разведены два горизонта — ось графика 45 дней (`reference_date .. +44`), слой «Платежи» до конца календарного месяца (C-5 становится **видимым** ограничением: за 31 августа оранжевая полоса нулевая); (3) слой «Резерв» считается режимно-корректно (`from_balance` / `fixed_date` считаются по-разному) и корректно продолжается за границей месяца — бюджет следующего месяца добавляется в резерв только тогда, когда он **уже вычтен** из прогнозного остатка recurring-резервом.

**Инженерно:** `cushion_target`/`threshold_amount` берутся новым лёгким геттером `CushionService.get_threshold_amount()` без пересчёта баланса (снимает 2 полных обхода recurring-истории за рендер); `is_empty` переопределён через «нет данных вообще» с отдельным кейсом «данные есть, окно пустое»; сигнатура `_load_dashboard_components` приведена к фактической и `dashboard-greeting` **поглощается шапкой** осознанно, с переписыванием контрактного теста; `profile_modal.py` признан файлом прямых изменений; вехи целей материализуются в TypedDict внутри сессии; `DIP_THRESHOLD` заменён на относительный порог от масштаба пользователя; `is_past` убран; `dtick` производный от длины окна; чистка `.kpi-*` утверждена без оговорок. План получил оценки трудозатрат.

## Архитектура

### Компоненты

**1. `app/schema/money_layers.py` (новый) — контракт модели**

TypedDict'ы `DayLayers`, `UpcomingPayment`, `GoalMilestone`, `LayersVerdict`, `MoneyLayersData`; литералы `VerdictLevel`, `LayerKey`; константы `LAYER_COLORS` / `LAYER_LABELS` / `VERDICT_TEXTS` / `VERDICT_COLORS`, `WINDOW_DAYS = 45`, `DIP_RATIO`, `DIP_FLOOR`. Ноль зависимостей от Dash и SQLAlchemy — чистые типы (стиль `app/schema/dashboard.py`). Явная пометка в модуль-докстринге: контракт спроектирован под кусок 1 и не претендует на стабильность до куска 2 (снимает оговорку критика по аспекту 2).

**2. `app/services/money_layers_service.py` (новый) — ядро FR-1**

Единственный публичный метод `get_money_layers(user_id, reference_date=None) -> MoneyLayersData`. Read-only, ничего не пишет, ни один существующий метод не меняет.

Два горизонта:

| Горизонт | Границы | Что определяет |
|---|---|---|
| **Окно оси** `window_end` | `reference_date + WINDOW_DAYS - 1` = +44 дня (45 дней вкл.) | Дни в `days[]`, ось X графика, зона поиска минимума, вехи целей в кадре |
| **Горизонт платежей** `payments_end` | последний день календарного месяца `reference_date` | Верхняя граница суффиксной суммы слоя «Платежи» (C-5 буквально) |

Приватные шаги:

- `_horizons(reference_date) -> tuple[date, date]` → `(window_end, payments_end)`;
- `_forecast_balances()` → `CalendarService.calculate_daily_balances(user_id, reference_date, window_end)` — единственный источник прогнозного остатка (AC-3 по построению);
- `_collect_upcoming_payments()` → `CalendarService.get_all_transactions_for_period(user_id, reference_date, payments_end)`; классификация как в `DashboardService._get_daily_income_expense` (`dashboard_service.py:476-545`): `expense` / `savings_reserve` / `savings_contribution` → платёж на `amount`; `adjustment` с `Decimal(info["amount"]) < 0` → платёж на `abs(...)`; `income` / `transfer` → не платёж; `is_skipped=True` — отбрасывается. Сортировка по дате;
- `_payments_tail_by_day()` → суффиксные суммы `payments(D) = Σ` платежей с датой в `(D, payments_end]`. Строгое «после D»: платёж дня D уже вычтен из `balance(D)` кассовым календарём (`_get_daily_changes` 240-313, `_get_recurring_daily_changes` 409-437). Для `D >= payments_end` → `Decimal("0")` — **та самая видимая честность C-5**;
- `_reserve_by_day()` → `reserve(D) = cushion_part + goals_part(D)` (детально ниже);
- `_split_day()` → каскад сжатия слоёв, сумма == остаток во всех ветках;
- `_build_verdict()` → срез «сегодня» + минимум слоя «Свободно» **по всему окну 45 дней**;
- `_goal_milestones()` → материализация активных целей в `GoalMilestone` **внутри сессии**.

**Семантика слоя «Резерв» (закрывает 🔴№1 и 🟡№3).**

`cushion_part = min(threshold_amount, max(balance(D), 0))`. Порог — решение владельца; `min(...)` с остатком — защита от кейса «перенакопленная подушка / остаток меньше порога» (реальный кейс аудита 922 155 при цели 100 000): нельзя «защищать» больше, чем физически есть, иначе `free` тонет в каскаде и синяя полоса лжёт о высоте.

`goals_part(D)` — часть месячного бюджета целей, которая **на день D ещё физически лежит в остатке**, различая режимы:

- **`from_balance`**: взнос создаёт транзакцию `SAVINGS_CONTRIBUTION` → уже вычтен из остатка кассовым календарём. Поэтому
  `goals_part = max(0, monthly_budget − used_contributions − Σ savings_* платежей в (D, month_end])`;
  где `used_contributions` = `BudgetReservationService.get_budget_progress()['used_budget']`.
- **`fixed_date`**: взнос транзакцию **не** создаёт (`create_contribution_transaction` возвращает `None`, `budget_reservation_service.py:669-672`); вместо этого exception уменьшает будущий recurring-резерв (`recalculate_current_month_exception`, 224-304). Значит вычитать `used_contributions` **нельзя** — это и есть недостающий счёт 🟡№3. Вычитаем только **фактически материализовавшийся из остатка** резерв: `materialized = BudgetReservationService._get_reserve_sum_for_month(user_id, reference_date)` (466-500, `is_recurring.is_(False)` → реальные транзакции и exceptions, но не виртуальные инстансы — ровно то, что уже ушло из баланса).
  `goals_part = max(0, monthly_budget − materialized − Σ savings_* платежей в (D, month_end])`.

  Обоснование корректности на кейсе критика (режим `fixed_date`, день резерва 25-е, бюджет 15 000, взнос 15 000 сделан 10-го): exception обнуляет резерв 25-го → `Σ savings_*` в хвосте = 0; `materialized` = 0 (exception с суммой 0 в сумме даёт 0); `goals_part = 15 000 − 0 − 0 = 15 000`. Деньги остаются в синей полосе, а не утекают в «Свободно». v1 давал здесь 0.

**Слой «Резерв» за границей месяца (явное решение с обоснованием).** Подушка (`cushion_part`) 1-го числа не обнуляется — она не месячная величина; продолжается на том же уровне. Бюджет целей следующего месяца **не добавляется как «новое обязательство»**, но и не исчезает: он попадает в резерв ровно тогда и в той мере, в какой уже **вычтен из прогнозного остатка** recurring-резервом `SAVINGS_RESERVE` следующего месяца. Формально:

```
goals_part(D) = max(0, monthly_budget − consumed(D)) для D <= month_end
goals_part(D) = goals_part(month_end) + Σ SAVINGS_RESERVE/CONTRIBUTION с датой в [month_end+1, D]
                для D > month_end
```

То есть за границей месяца слой «Резерв» *продолжается на достигнутом уровне* и **подрастает в день следующего резерва** — потому что этот резерв уже ушёл из зелёного «Свободно» через баланс, и без его добавления в синий слой сумма слоёв бы «съела» его в `free` (а тот, наоборот, должен уменьшиться на эту сумму). Симметрия с C-5: платежи следующего месяца не видны, потому что их **нет в модели** (мы их не знаем); резерв следующего месяца виден, потому что он **уже есть в балансе** (recurring-шаблон известен). Это не расширение C-5, а следствие инварианта AC-3. Наблюдаемое поведение совпадает с принятым эскизом: в `v3.html` синяя полоса ровно так и растёт с 22.5px до 34.5px после начала сентября. Покрывается тестом `test_reserve_grows_at_next_month_reserve_date`.

**3. `app/services/cushion_service.py` (изменяется — минимальное ДОБАВЛЕНИЕ метода, закрывает 🟡№7)**

Добавляется `get_threshold_amount(user_id) -> Decimal` — читает `users.cushion_target` и `users.cushion_threshold_percent` и возвращает `target * percent / 100`, **без** `_get_current_balance()`. Проверено по коду: `threshold_amount` в `get_settings` (`cushion_service.py:110-113`) вообще не зависит от баланса — баланс нужен только для `current_amount`/`progress`; `cushion_threshold_manual` — булев флаг «процент задан вручную», отдельной колонки суммы в схеме нет (`app/models/database.py:105-107`), поэтому `threshold_amount` всегда вычисляется формулой. Метод возвращает `Decimal("0")` при отсутствии пользователя — тихий дефолт, без `ValidationError` и без варнинга-с-трейсбеком на штатном пути чистой базы (это второй пункт 🟡№7).

C-3 запрещает менять *поведение* существующих методов; ни один существующий метод не правится, добавляется новый — фиксируем это как явное решение (не молча), как требует дисциплина C-4-подобного класса.

**4. `app/components/dashboard.py` (изменяется) — FR-2…FR-6**

- `build_verdict_header(data, profile) -> html.Div` — вместо `build_overview_cards()`. Внутри шапки — приветствие с именем (поглощает `dashboard-greeting`, см. ниже), сумма, чип вердикта, разбор, аватар, кнопка «Сверка», шестерёнка.
- `build_layers_chart(data) -> dbc.Card` — вместо `_build_daily_cashflow_chart()` / `_build_yearly_cashflow_chart()`.
- `_build_layer_legend(data)` / `_build_payments_tooltip(data)` — HTML-легенда **вне поля графика** (`showlegend=False`) с `dbc.Tooltip` (FR-4 + заметка vision-критика). Только текстовые компоненты, без `dangerously_allow_html` / `dcc.Markdown` (фиксация замечания критика по аспекту 5).
- `_build_verdict_empty_state()` / `_build_chart_empty_state()` — FR-6.
- `_load_dashboard_components()` — сигнатура и состав tuple ниже.
- `open_create_from_chart` перепривязывается на `dashboard-layers-chart-graph`, дата берётся из `point["x"]` (ISO-строка даты) — `dashboard-period` Store больше не нужен для парсинга, но остаётся как хранитель месяца (см. ответы на вопросы).

**5. `app/components/profile_modal.py` (изменяется — прямые изменения, решение владельца, закрывает 🟡№4)**

Проверено: модал открывается единственным `Input("sidebar-profile-container", "n_clicks")` (:96) с ветвлением `ctx.triggered_id == "sidebar-profile-container"` (:119). Добавляется **второй Input** `Input("dashboard-settings-cog", "n_clicks")` и ветка `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")`. Работает без правки сайдбара (C-1 не нарушен) и без нового Store; `suppress_callback_exceptions=True` (`main.py:41`) снимает риск отсутствия элемента вне дашборда. Раздел `/settings` остаётся вне scope — шестерёнка ведёт в профиль, о чём говорит `title="Профиль и настройки"`.

**6. `app/assets/panel.css` (новый) — стили щитка**

Классы `pnl-*` на CSS-переменных проекта. Отдельный файл — установленный паттерн проекта (`analytics.css`, `calendar.css`, `goals.css`, `wishlist.css` уже так живут), `custom.css` шарится всеми страницами.

### Диаграмма взаимодействия

```
┌──────────────────────────────────────────────────────────────┐
│ app/components/dashboard.py                                  │
│   load_dashboard_data  /  refresh_dashboard_after_crud       │
│                    │                                         │
│                    ▼                                         │
│   _load_dashboard_components(period, period_state)           │
└────────────────────┬─────────────────────────────────────────┘
                     │ get_money_layers(user_id)   [1 вызов]
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ MoneyLayersService   (НОВЫЙ, read-only, без flush/commit)     │
│                                                              │
│  _horizons()  →  window_end = ref+44   (ось, 45 дней)        │
│                  payments_end = конец месяца ref  (C-5)      │
│  _forecast_balances(ref .. window_end) ───────────┐          │
│  _collect_upcoming_payments(ref .. payments_end) ─┼──┐       │
│  _payments_tail_by_day()   Σ в (D, payments_end]  │  │       │
│  _reserve_by_day()  ┌ cushion: min(threshold, bal)│  │       │
│                     └ goals:  режимно-корректно ──┼──┼──┐    │
│  _split_day()   free = bal − pay − res (+каскад)  │  │  │    │
│  _build_verdict()  min_free по ОКНУ 45 дней       │  │  │    │
│  _goal_milestones()  материализация В СЕССИИ ──┐  │  │  │    │
└────────────────────────────────────────────────┼──┼──┼──┼────┘
                                                 │  │  │  │
        ┌────────────────────────────────────────┘  │  │  │
        ▼                     ▼                    ▼  ▼  ▼
┌──────────────┐  ┌───────────────────────┐  ┌────────────────────────┐
│ GoalService  │  │ CushionService        │  │ CalendarService        │
│ get_all_by_  │  │ get_threshold_amount()│  │ calculate_daily_       │
│ user(ACTIVE) │  │   ← НОВЫЙ, БЕЗ        │  │   balances             │
└──────────────┘  │     пересчёта баланса │  │ get_all_transactions_  │
                  └───────────────────────┘  │   for_period           │
                  ┌───────────────────────┐  └──────────┬─────────────┘
                  │ BudgetReservation     │             ▼
                  │ Service               │      RecurringService
                  │ get_settings() → mode │      (виртуальные instances)
                  │ get_budget_progress() │
                  │ _get_reserve_sum_for_ │
                  │   month()  (fixed_date)│
                  └───────────────────────┘
                     ↑ ни один существующий метод не меняется (C-3)

Возврат: MoneyLayersData ─┬─► build_verdict_header()  «Свободно сегодня: N ₽»
                          ├─► build_layers_chart()    stacked bars 45 дней
                          └─► _build_layer_legend()   dbc.Tooltip (FR-4)

app/components/profile_modal.py ← НОВЫЙ Input("dashboard-settings-cog")
```

## Файловая структура

```
НОВЫЕ:
app/schema/money_layers.py            TypedDict'ы модели, литералы, константы
                                      (LAYER_COLORS/LABELS, VERDICT_*, WINDOW_DAYS=45,
                                      DIP_RATIO, DIP_FLOOR)
app/services/money_layers_service.py  MoneyLayersService: композиция над Calendar/
                                      Cushion/BudgetReservation/Goal; FR-1
app/assets/panel.css                  Стили pnl-* (шапка + блок графика + легенда)
tests/test_money_layers_service.py    Инвариант AC-3, «таяние», граница месяца,
                                      режимы резерва, порог подушки, вердикт,
                                      is_empty, детач-тест, fail-open

ИЗМЕНЯЕМЫЕ:
app/services/cushion_service.py       +get_threshold_amount() — ДОБАВЛЕНИЕ метода,
                                      существующие не тронуты (см. C-3 в RTM)
app/components/dashboard.py           крупнейший blast — см. Blast Radius
app/components/profile_modal.py       +Input("dashboard-settings-cog") и ветка
                                      triggered_id (решение владельца)
app/schema/__init__.py                реэкспорт новых типов + __all__
app/services/__init__.py              реэкспорт MoneyLayersService + типов + __all__
app/assets/custom.css                 чистка: #dashboard-overview-cards,
                                      .db-period-switcher, .kpi-* (утверждено)
tests/test_dashboard_callbacks.py     переписать контракт greeting-Output и
                                      test_returns_seven_values_with_greeting_last
tests/test_cushion_service.py         +тесты get_threshold_amount

НЕ ИЗМЕНЯЮТСЯ (доказательство C-3):
app/services/calendar_service.py, dashboard_service.py, goal_service.py,
budget_reservation_service.py, app/components/sidebar.py
tests/test_dashboard_service.py, tests/test_calendar_service.py,
tests/test_budget_reservation_service.py
```

## Ключевые интерфейсы

```python
# app/schema/money_layers.py
"""Контракт модели «свободно / платежи / резерв» по дням (EPIC-11, кусок 1).

Note:
    Контракт спроектирован под кусок 1 (шапка-вердикт + график полос).
    Стабильность до куска 2 (карточки-двери) не гарантируется —
    осознанное решение, зафиксировано в memory/spec-context/epic-11.md.
"""

from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict

LayerKey = Literal["free", "payments", "reserve"]
"""Ключ слоя декомпозиции прогнозного остатка."""

VerdictLevel = Literal["ok", "dip", "problem"]
"""Уровень вердикта шапки: порядок / впереди просадка / проблема."""

WINDOW_DAYS = 45
"""Длина окна оси графика в днях (включая сегодня).

Соответствует принятому эскизу .visual/finfocus-panel-dashboard/v3.html
(22 авг — 5 окт 2026). Горизонт слоя «Платежи» — отдельная величина,
конец календарного месяца (C-5), см. MoneyLayersService._horizons.
"""

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

VERDICT_TEXTS: dict[VerdictLevel, str] = {
    "ok": "Всё в порядке",
    "dip": "Впереди просадка",
    "problem": "Нужно вмешаться",
}
"""Текст цветового вердикта шапки (FR-2)."""

VERDICT_COLORS: dict[VerdictLevel, str] = {
    "ok": "#2ecc71",
    "dip": "#f39c12",
    "problem": "#e74c3c",
}
"""Цвет сигнальной шины и чипа вердикта (палитра эскиза)."""

DIP_RATIO = Decimal("0.10")
"""Доля предстоящих платежей окна: min_free ниже — вердикт «просадка».

Относительный порог вместо абсолютного: у пользователя с оборотом
500 000 ₽/мес абсолютные 5 000 ₽ означали бы «ok» практически всегда,
у пользователя с оборотом 40 000 ₽/мес — «dip» практически всегда
(замечание критика №9). База — сумма платежей окна, т.е. масштаб
собственных обязательств пользователя.
"""

DIP_FLOOR = Decimal("1000")
"""Нижняя граница порога просадки — чтобы при нулевых платежах порог
не выродился в 0 ₽ и «просадка до нуля» всё равно попадала в вердикт."""


class DayLayers(TypedDict):
    """Декомпозиция прогнозного остатка одного дня окна на три слоя.

    Инвариант: free + payments + reserve == forecast_balance (AC-3).

    Attributes:
        date: Дата дня окна.
        free: Слой «Свободно» — реально доступные деньги.
        payments: Слой «Платежи» — уйдут на запланированные платежи
            в интервале (date, конец календарного месяца]. За границей
            месяца всегда 0 — видимое ограничение C-5.
        reserve: Слой «Резерв» — порог подушки + бюджет целей,
            ещё физически лежащий в остатке.
        forecast_balance: Прогнозный остаток из CalendarService.
    """

    date: date
    free: Decimal
    payments: Decimal
    reserve: Decimal
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
    """Веха цели на оси времени графика (FR-3).

    Материализуется из ORM-объекта Goal ВНУТРИ сессии — модель
    уходит за пределы with get_db_session() (см. TransactionInfo,
    calendar_service.py:27-33).

    Attributes:
        goal_id: ID цели.
        name: Название цели.
        target_date: Дата достижения.
        target_amount: Целевая сумма.
        progress_percent: Прогресс 0..100 (Goal.progress_percentage,
            вычислено в сессии).
        beyond_window: True — цель за правым краем окна 45 дней
            (рисуется стрелкой-аннотацией у края, как в эскизе v3).
    """

    goal_id: int
    name: str
    target_date: date
    target_amount: Decimal
    progress_percent: float
    beyond_window: bool


class LayersVerdict(TypedDict):
    """Вердикт шапки — срез на сегодня + минимум по окну 45 дней (FR-2).

    Attributes:
        level: Уровень вердикта (ok / dip / problem).
        text: Готовый текст («Всё в порядке» и т.п.).
        free_today: Слой «Свободно» на reference_date — главное число шапки.
        balance_today: Прогнозный остаток на reference_date (разбор).
        payments_today: Слой «Платежи» на reference_date (разбор).
        reserve_today: Слой «Резерв» на reference_date (разбор).
        min_free: Минимум слоя «Свободно» по ВСЕМУ окну (45 дней).
        min_free_date: Дата этого минимума.
        dip_threshold: Фактически применённый порог просадки
            (для объяснимости вердикта в тултипе и в тестах).
    """

    level: VerdictLevel
    text: str
    free_today: Decimal
    balance_today: Decimal
    payments_today: Decimal
    reserve_today: Decimal
    min_free: Decimal
    min_free_date: date
    dip_threshold: Decimal


class MoneyLayersData(TypedDict):
    """Полный результат модели FR-1 — единый источник шапки и графика.

    Attributes:
        days: Декомпозиция по дням окна (reference_date .. window_end).
        verdict: Вердикт и срез «сегодня».
        upcoming_payments: Платежи до конца месяца для тултипа (FR-4).
        milestones: Вехи целей для оси времени (FR-3).
        reference_date: Дата отсчёта («сегодня»).
        window_end: Последний день окна оси (reference_date + 44).
        payments_end: Последний день горизонта платежей (конец месяца, C-5).
        cushion_threshold: Порог подушки в слое «Резерв» (расшифровка).
        goals_reserve_today: Часть слоя «Резерв» от бюджета целей на сегодня.
        is_empty: True — у пользователя нет данных ВООБЩЕ (FR-6);
            НЕ «нули в окне» (см. _detect_empty).
        window_is_flat: True — данные есть, но в окне ни одной операции
            (график рисуется плоским, пустое состояние НЕ подменяет его).
    """

    days: list[DayLayers]
    verdict: LayersVerdict
    upcoming_payments: list[UpcomingPayment]
    milestones: list[GoalMilestone]
    reference_date: date
    window_end: date
    payments_end: date
    cushion_threshold: Decimal
    goals_reserve_today: Decimal
    is_empty: bool
    window_is_flat: bool
```

```python
# app/services/money_layers_service.py

class MoneyLayersService:
    """Модель «свободно / платежи / резерв» по дням (FR-1).

    Read-only надстройка: композиция над CalendarService (прогнозный
    остаток и перечень операций), BudgetReservationService (режим и
    бюджет целей), CushionService (порог подушки) и GoalService (вехи).
    Ни одного существующего метода не меняет, в БД не пишет (C-2, C-3).

    Два горизонта (решение владельца 2026-08-24):
        * окно оси — WINDOW_DAYS = 45 дней от reference_date (эскиз v3);
        * горизонт слоя «Платежи» — конец календарного месяца (C-5).
          За границей месяца payments(D) == 0: ограничение видно честно,
          а не скрыто сужением оси.

    Инвариант декомпозиции: для каждого дня D окна
        free(D) + payments(D) + reserve(D) == CalendarService.balance(D)
    (AC-3) — обеспечен конструктивно, free выводится вычитанием.
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
            MoneyLayersData: Дни окна, вердикт, платежи, вехи целей.
            Все ORM-объекты материализованы — результат безопасен
            после закрытия сессии.

        Note:
            Никогда не бросает при отсутствии данных — возвращает
            корректную модель с is_empty=True (FR-6). Сбои частей
            (подушка, бюджет целей, цели) деградируют fail-open с
            логом logger.opt(exception=True) (NFR-2). Сбой
            calculate_daily_balances не глотается — без остатка
            модели нет.
        """

    # --- Приватные шаги ---

    def _horizons(self, reference_date: date) -> tuple[date, date]:
        """Два горизонта модели.

        Returns:
            tuple[date, date]: (window_end, payments_end), где
                window_end = reference_date + WINDOW_DAYS - 1 (ось графика),
                payments_end = последний день месяца reference_date (C-5).
        """

    def _collect_upcoming_payments(
        self, user_id: int, start: date, payments_end: date
    ) -> list[UpcomingPayment]:
        """Собирает расходные операции до конца календарного месяца.

        Классификация повторяет DashboardService._get_daily_income_expense
        (dashboard_service.py:476-545): expense / savings_reserve /
        savings_contribution → платёж на amount; adjustment с
        Decimal(amount) < 0 → платёж на abs(amount) (знак хранится
        в самом amount, см. ReconciliationService: amount=difference,
        reconciliation_service.py:132-135); income / transfer → не платёж.
        Пропущенные (is_skipped) отбрасываются.

        Note:
            start == payments_end + 1 (последний день месяца +) невозможен:
            reference_date <= payments_end всегда. При start == payments_end
            список платежей может быть непустым (платежи самого дня),
            но в хвост (D, end] они не попадут — это корректно.
        """

    def _payments_tail_by_day(
        self,
        payments: list[UpcomingPayment],
        start: date,
        window_end: date,
        payments_end: date,
    ) -> dict[date, Decimal]:
        """Суффиксные суммы платежей: {D: Σ платежей в (D, payments_end]}.

        Строго «после D»: платежи с датой ровно D уже вычтены из
        forecast_balance(D) кассовым календарём — иначе двойной счёт.
        Даёт «таяние» (FR-1.d): монотонно не растёт, payments(payments_end)
        == 0 и payments(D) == 0 для всех D > payments_end (C-5 видимо).
        """

    def _reserve_by_day(
        self,
        user_id: int,
        payments: list[UpcomingPayment],
        balances: dict[date, Decimal],
        start: date,
        window_end: date,
        payments_end: date,
        cushion_threshold: Decimal,
    ) -> dict[date, Decimal]:
        """Слой «Резерв» по дням: порог подушки + бюджет целей в остатке.

        cushion_part(D) = min(cushion_threshold, max(balance(D), 0))
            — порог, а не полная цель (решение владельца: единая
            семантика «неприкосновенного» с PurchaseRecommendationService,
            purchase_recommendation_service.py:74); min с остатком
            защищает от кейса «остаток меньше порога» и от
            перенакопленной подушки.

        goals_part(D) для D <= payments_end:
            max(0, monthly_budget − consumed − Σ savings_* в (D, payments_end])
            где consumed зависит от режима резервирования:
              * from_balance — used_budget (взносы создают транзакции,
                уже вычтены из остатка);
              * fixed_date — _get_reserve_sum_for_month (материализованные
                SAVINGS_RESERVE: реальные транзакции и exceptions,
                is_recurring=False), т.к. взнос в этом режиме транзакцию
                НЕ создаёт (budget_reservation_service.py:669-672) и
                вычитание used_budget дало бы недостающий счёт.

        goals_part(D) для D > payments_end:
            goals_part(payments_end)
            + Σ SAVINGS_RESERVE/CONTRIBUTION с датой в [payments_end+1, D]
            — резерв следующего месяца попадает в слой ровно тогда,
            когда он уже ушёл из остатка recurring-шаблоном. Симметрия
            с C-5: платежей следующего месяца мы не знаем, а этот
            резерв известен и УЖЕ учтён в балансе.
        """

    def _split_day(
        self, balance: Decimal, payments: Decimal, reserve: Decimal
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Каскад сжатия слоёв, сохраняющий инвариант суммы (AC-3).

        1. free = balance − payments − reserve; если free >= 0 — готово.
        2. Иначе free = 0, дефицит гасится из reserve, затем из payments.
        3. Если balance < 0 — free = balance (отрицательное),
           payments = reserve = 0.

        Returns:
            tuple[Decimal, Decimal, Decimal]: (free, payments, reserve),
                сумма которых равна balance при любом входе.
        """

    def _build_verdict(
        self,
        days: list[DayLayers],
        reference_date: date,
        payments_total: Decimal,
    ) -> LayersVerdict:
        """Вердикт по срезу «сегодня» и минимуму «Свободно» по ОКНУ.

        Минимум ищется по всем 45 дням окна, а не по остатку месяца:
        просадка после зарплаты (эскиз: 4 сентября) обязана попадать
        в вердикт, иначе шапка и график рассказывают разные истории.

        Порог просадки: dip_threshold = max(payments_total * DIP_RATIO,
        DIP_FLOOR) — относительный, от масштаба обязательств пользователя.

        Уровни: problem — free_today <= 0 или min_free < 0;
                dip — min_free < dip_threshold;
                ok — иначе.
        """

    def _goal_milestones(
        self, user_id: int, start: date, window_end: date
    ) -> list[GoalMilestone]:
        """Вехи активных целей: в окне + ближайшая за его краем.

        Материализует поля ORM-объектов Goal (включая вычисляемое
        property progress_percentage) в GoalMilestone ВНУТРИ сессии —
        GoalService.get_all_by_user возвращает list[Goal]
        (goal_service.py:222-239), и обращение к нему после закрытия
        сессии даст DetachedInstanceError.

        Returns:
            list[GoalMilestone]: до MAX_MILESTONES_IN_WINDOW = 3 вех
                внутри окна (ближайшие по target_date) + не более одной
                с beyond_window=True (ближайшая после window_end).
        """

    def _detect_empty(self, user_id: int) -> bool:
        """«Нет данных вообще» — критерий пустого состояния (FR-6).

        Возвращает True только если у пользователя нет НИ ОДНОЙ
        транзакции за всё время (включая recurring-шаблоны) И
        starting_balance == 0. Нули в окне НЕ считаются пустотой:
        пользователь с полугодовой историей и нулевым остатком месяца
        должен видеть график, а не «Добавьте первую операцию»
        (замечание критика №6). Флаг first_launch для этого не годится:
        OnboardingService.skip() сбрасывает его в False, не создавая
        данных (onboarding_service.py:168-182).
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
        (см. get_settings, строки 110-113).

        Args:
            user_id: ID пользователя.

        Returns:
            Decimal: Порог подушки; Decimal("0") если пользователь
                не найден или подушка не настроена (target == 0).
                Не бросает ValidationError — отсутствие пользователя
                на чистой базе штатно.
        """
```

```python
# app/components/dashboard.py — новые/изменённые строители и точка загрузки

def build_verdict_header(
    data: MoneyLayersData,
    profile: UserProfile,
) -> html.Div:
    """Шапка-вердикт «Свободно сегодня: N ₽» (FR-2, FR-5).

    Состав слева: приветствие «Привет, {name}» (поглощает вытесняемый
    dashboard-greeting), метка «Свободно сегодня», сумма (tabular-nums),
    чип вердикта с точкой, разбор «баланс − платежи − резерв».
    Справа: аватар-эмодзи + имя, кнопка «Сверка»
    (id="open-recon-from-dashboard-verdict-btn"), шестерёнка
    (id="dashboard-settings-cog" → модал профиля).
    Сигнальная шина слева окрашена по verdict['level'].
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
    «Свободно», вехи целей аннотациями (в окне + стрелка за краем).
    Легенда Plotly отключена (showlegend=False) — вынесена в HTML
    (заметка vision-критика + FR-4).

    Args:
        data: Модель слоёв из MoneyLayersService.

    Returns:
        dbc.Card с dcc.Graph(id="dashboard-layers-chart-graph") либо
        пустым состоянием при data['is_empty'] (FR-6).
    """


def _axis_dtick(window_days: int) -> int:
    """Шаг подписей оси X в миллисекундах, производный от длины окна.

    Целевое число подписей ~10-12: dtick = max(1, round(window_days / 11))
    дней. Для 45 дней → 4 дня (12 подписей); константа 3 дня из v1 при
    коротком окне давала 2-3 подписи (замечание критика №11).
    """


def _load_dashboard_components(
    period: str,
    period_state: dict | None,
) -> tuple:
    """Единая точка загрузки данных и построения UI дашборда.

    Сигнатура сохраняется без изменений (period, period_state) —
    оба вызывающих (load_dashboard_data, refresh_dashboard_after_crud)
    передают два аргумента. Аргумент period в куске 1 больше не влияет
    на график (period-switcher снят, режим Year удалён с дашборда), но
    остаётся в сигнатуре: Store dashboard-period продолжает жить и
    хранить {"period": "month", "year", "month"} для open_create_from_chart.
    Удаление аргумента — отдельная чистка куска 2, когда судьба Store
    станет ясна вместе с карточками-дверями.

    Args:
        period: Режим периода из Store (в куске 1 всегда "month").
        period_state: Данные из dcc.Store dashboard-period.

    Returns:
        tuple: (verdict_header, layers_chart, recent, upcoming, cushion)
            — 5 значений вместо прежних 6 (ушли cards+stats,
            пришёл verdict_header).
    """
```

**Состав Output'ов после правки (закрывает 🟡№5):**

| Callback | Outputs (в порядке) |
|---|---|
| `load_dashboard_data` | `dashboard-verdict-header.children`, `dashboard-layers-chart.children`, `dashboard-recent-transactions.children`, `dashboard-upcoming-transactions.children`, `dashboard-cushion-card.children` — **5** (было 7). `dashboard-greeting` Output **удаляется**, приветствие внутри шапки (первый Output). Ветка ошибки: `(error_alert,) * 5`. |
| `refresh_dashboard_after_crud` | те же 5 с `allow_duplicate=True` (было 6) |
| `update_period_state` | **удаляется** вместе с `period-switcher` |
| `open_create_from_chart` | Input → `dashboard-layers-chart-graph.clickData`; Outputs без изменений |

**Судьба `dashboard-greeting` — осознанное переписывание контракта.** Элемент и его Output удаляются, приветствие с именем поглощается шапкой (FR-2 требует имя пользователя в шапке; два «привета» рядом — та же болезнь дублирования, что и два главных числа). Причина исходного решения 0024/0026 («отдельный Output на элемент только этой страницы → ReferenceError на других страницах») сохраняется: приветствие по-прежнему обновляется **внутри** `load_dashboard_data` первым Output'ом (`dashboard-verdict-header`), а не отдельным callback'ом — дух протокола 0026 соблюдён, меняется только id элемента. Тесты `test_load_dashboard_data_decorator_declares_greeting_output` и `test_returns_seven_values_with_greeting_last` (`tests/test_dashboard_callbacks.py:62-70, 188-210`) переписываются на `dashboard-verdict-header` и 5 значений; хелпер `_build_greeting_text()` остаётся (его тесты `TestBuildGreetingText` не правятся) и вызывается из `build_verdict_header`.

## Модель данных

Схема БД не меняется (C-4) — проверено по коду, всё сырьё есть.

| Что нужно модели | Откуда берётся (проверено) | Достаточность |
|---|---|---|
| Прогнозный остаток по дням окна | `CalendarService.calculate_daily_balances` (`users.starting_balance` + `transactions` + recurring) | достаточно |
| Платежи до конца месяца с описаниями | `CalendarService.get_all_transactions_for_period` → `TransactionInfo` (`amount` строкой **со знаком** — `str(txn.amount)`, :803/:849; есть `description`, `category_name`, `is_recurring`, `is_skipped`) | достаточно |
| Порог подушки | `users.cushion_target`, `users.cushion_threshold_percent` через новый `CushionService.get_threshold_amount` | достаточно (колонки суммы порога в схеме нет — только процент, `database.py:105-107`) |
| Режим резервирования | `users.reservation_mode`, `users.reservation_day` через `BudgetReservationService.get_settings` | достаточно |
| Бюджет целей и использование (`from_balance`) | `users.monthly_savings_budget`, `goal_contributions` через `get_budget_progress` | достаточно |
| Материализованный резерв (`fixed_date`) | `transactions` (SAVINGS_RESERVE, `is_recurring=False`) через `_get_reserve_sum_for_month` | достаточно |
| Вехи целей | `goals.target_date/target_amount/current_amount/status` через `GoalService.get_all_by_user(ACTIVE)` (`target_date` NOT NULL, `database.py:260`) | достаточно |
| Аватар и имя для шапки | `users.avatar_id`, `users.name` через `OnboardingService.get_profile` | достаточно |
| «Нет данных вообще» для `is_empty` | `count(transactions)` по user_id + `users.starting_balance` | достаточно |

**Вывод по C-4:** миграции не нужны, отдельного решения об изменении схемы не требуется.

**Пример арифметики эскиза** (проверка 🔴№1, числа brief.md эскиза: остаток 84 500, платежи до конца месяца 37 500, бюджет целей 15 000, подушка target 100 000 при пороге 30% → threshold 30 000):

| D | balance | payments (D, 31 авг] | reserve (cushion 30 000 + goals) | free |
|---|---|---|---|---|
| 22 авг | 84 500 | 37 500 | 30 000 + 15 000 = 45 000 | 2 000 |
| 25 авг | 54 500 | 7 500 | 45 000 | 2 000 |
| 28 авг | 48 300 | 1 300 | 45 000 | 2 000 |
| 31 авг | 47 000 | 0 | 45 000 | 2 000 |
| 5 сент (зарплата +120 000) | 167 000 | 0 | 45 000 | 122 000 |

Сумма слоёв == balance на каждой строке (AC-3); `payments` тает до 0 (FR-1.d) и остаётся 0 за 31 августа (C-5 видимо); `free > 0` на типичных данных — главное число работает (в v1 здесь был жёсткий 0 во всех строках). При кейсе аудита «накоплено 922 155 при цели 100 000» `cushion_part = min(30 000, balance)` = 30 000, а не 100 000 — противоречия с карточкой «Цель достигнута» и с wishlist «безопасно после…» нет: wishlist использует тот же `threshold_amount`.

## Обработка ошибок

Четыре уровня, по образцу `PurchaseRecommendationService.get_safe_dates_map` (`purchase_recommendation_service.py:72-83` — fail-open + `logger.opt(exception=True)`, идиома протокола 0027: loguru игнорирует `exc_info`).

1. **Штатное отсутствие данных — тихий дефолт, без лога.** Пользователь не найден / подушка не настроена → `get_threshold_amount` возвращает `Decimal("0")` без исключения и без варнинга. Это снимает второй пункт 🟡№7: v1 генерировал варнинг-с-трейсбеком на каждом рендере чистой базы (шум вместо сигнала).
2. **Сбой компонента — fail-open + лог с трейсбеком.** Сбой `BudgetReservationService` → `goals_part = 0`; сбой `GoalService` → `milestones = []`; сбой `CushionService.get_threshold_amount` (неожиданный) → `cushion_threshold = 0`. Каждый — `logger.opt(exception=True).warning(...)` (NFR-2). Инвариант AC-3 сохраняется, т.к. `free` выводится вычитанием. Сбой `calculate_daily_balances` **не** глотается: без остатка модели нет.
3. **Границы горизонтов.** `reference_date` = последний день месяца → `payments_end == reference_date`, `payments(D) == 0` для всех дней окна (модель валидна, оранжевая полоса отсутствует — честное «платежей до конца месяца больше нет»). Окно всегда 45 дней, поэтому вырождение графика в 1-7 столбцов из v1 исчезает. `calculate_daily_balances(ref, ref+44)` — `start < end` всегда, `ValueError` (`calendar_service.py:123`) недостижим. Отдельно тестируются февраль, 31-е, переход через год.
4. **Callback'и Dash.** `load_dashboard_data`: `try/except` → `dbc.Alert("Не удалось загрузить данные...")` во все 5 Output'ов; лог заменяется на `logger.opt(exception=True).error(...)` вместо текущего `logger.error(f"...{e}")` (`dashboard.py:1389` — сейчас трейсбека нет, NFR-2). `refresh_dashboard_after_crud` — `PreventUpdate` после лога с трейсбеком.

**Пустое состояние (FR-6, AC-5) — переопределено (закрывает 🟡№6):**

- `is_empty=True` ⟺ «нет данных вообще»: `count(transactions where user_id) == 0` **и** `starting_balance == 0`. Тогда шапка рендерит `_build_verdict_empty_state()` («Пока нечего показать» + «Добавьте первую операцию или сверьте баланс» + кнопка «Сверка»), а график — `_build_chart_empty_state()`: **вместо `dcc.Graph` отдаётся `html.Div`**, Plotly вообще не вызывается → оси −1..1 и «50.001k» физически невозможны (AC-5).
- `window_is_flat=True` (данные есть, в окне ни одной операции) — **график рисуется**: плоская стопка на уровне остатка, шапка показывает реальное «Свободно». Пустое состояние здесь **не** подменяет график — это регрессия класса «Аналитика молча показывает нули», от которой предупредил критик. Отдельный тест `test_window_flat_renders_chart_not_empty_state`.
- Для непустых, но малых данных оси фиксируются: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)` (нет «50.001k»), `xaxis=dict(type="date", tickformat="%-d %b", dtick=_axis_dtick(WINDOW_DAYS), tickangle=0)` (нет склеек на 45 днях).

**Безопасность.** Тултип легенды рендерит пользовательский `description` только через `html.Div`/`html.Span` — Dash экранирует текст. `dangerously_allow_html` и `dcc.Markdown` в новых путях запрещены (зафиксировано как правило реализации).

## План реализации

Оценки — в человеко-часах для одного разработчика, знакомого с проектом (закрывает рекомендацию №13). Итого **≈ 30–36 ч**.

| # | Шаг | Оценка | Зависит от |
|---|---|---|---|
| 1 | `app/schema/money_layers.py` — TypedDict'ы, литералы, константы (`WINDOW_DAYS`, `LAYER_*`, `VERDICT_*`, `DIP_RATIO`, `DIP_FLOOR`) + реэкспорт в `app/schema/__init__.py` | **1.5 ч** | — |
| 2 | `CushionService.get_threshold_amount()` + тесты в `tests/test_cushion_service.py` (порог по проценту, target=0, отсутствующий пользователь, отсутствие вызова `calculate_daily_balances` — monkeypatch-assert) | **1.5 ч** | — |
| 3 | `app/services/money_layers_service.py` — `_horizons`, `_forecast_balances`, `_collect_upcoming_payments`, `_payments_tail_by_day`, `_split_day`, `_detect_empty` (базовый каркас без резерва) + реэкспорт в `app/services/__init__.py` | **4 ч** | 1, 2 |
| 4 | `_reserve_by_day` — режимная логика (`from_balance` / `fixed_date`) + продолжение за границей месяца. Самый тонкий шаг: требует свериться с `budget_reservation_service.py` (:169-222, :466-500, :648-692, :841-926) | **4 ч** | 3 |
| 5 | `_build_verdict` (относительный `dip_threshold`) + `_goal_milestones` (материализация в сессии, ≤3 в окне + одна за краем) | **2 ч** | 3 |
| 6 | `tests/test_money_layers_service.py` — ~22 теста: инвариант AC-3 параметризованно по всем дням; таяние и `payments == 0` за границей месяца; резерв растёт в день резерва след. месяца; `fixed_date` + досрочный взнос (не уходит в «Свободно»); `from_balance` + взнос (не считается дважды); порог подушки вместо target; `min(threshold, balance)` при перенакопленной подушке; три ветки `_split_day` с assert суммы; отрицательный остаток; вердикт на трёх уровнях с проверкой `dip_threshold`; `min_free` ищется по окну, а не по месяцу; `is_empty` (чистая база) vs `window_is_flat` (история есть, окно пустое); граница месяца (последний день, февраль, 31-е, переход через год); ADJUSTMENT с обоими знаками; доступность модели после закрытия сессии (детач); fail-open при падении `BudgetReservationService`. Даты относительные (`date.today()` + хелперы `conftest.py`), без `pytest.skip` | **7 ч** | 3, 4, 5 |
| 7 | `app/assets/panel.css` — `pnl-*` из эскиза v3 на переменных проекта, `tabular-nums`, вертикальный ритм, `@media (prefers-reduced-motion: reduce)` | **2.5 ч** | — |
| 8 | `build_verdict_header()` + `_build_verdict_empty_state()`; кнопка «Сверка» с новым id; шестерёнка `dashboard-settings-cog`; поглощение приветствия | **3 ч** | 1, 7 |
| 9 | `build_layers_chart()` + `_build_layer_legend()` + `_build_payments_tooltip()` + `_build_chart_empty_state()` + `_axis_dtick()`; заметки vision-критика (легенда вне поля, ярлык минимума со сдвигом `yshift`/`ay`) | **4 ч** | 1, 7 |
| 10 | `profile_modal.py` — второй Input и ветка `triggered_id`; ручная проверка: шестерёнка из дашборда и клик по сайдбару оба открывают модал | **0.5 ч** | 8 |
| 11 | Переключение `_load_dashboard_components` и callback'ов: новые Output-ID, 5 значений, снятие `period-switcher` и `update_period_state`, перепривязка `open_create_from_chart` на ISO-дату, clientside «Сверка» на новый id | **3 ч** | 8, 9 |
| 12 | Удаление мёртвого кода в `dashboard.py` (`build_overview_cards`, `_build_kpi_card`, `build_cashflow_chart`, `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`, `build_statistics_card`, `create_ai_assistant_card`, `create_exchange_card`, `build_recent_transactions_card`) + чистка `custom.css` (`#dashboard-overview-cards`, `.db-period-switcher`, `.kpi-*` — grep уже проведён, вне дашборда не используются) | **2 ч** | 11 |
| 13 | Правка `tests/test_dashboard_callbacks.py`: контракт на `dashboard-verdict-header` вместо greeting-Output, 5 значений вместо 7 (переписывание осознанное, см. «судьба dashboard-greeting») | **1 ч** | 11 |
| 14 | Прогон `pytest -q` (565 прежних + новые), `black`, `flake8`; ручная AC-1…AC-6 на наполненной и чистой базе; замер NFR-1 | **2.5 ч** | все |

Порядок сохраняет принцип «тесты модели до UI» (модель здесь — контракт). Шаг 2 вынесен вперёд как независимый: он снимает NFR-риск и нужен шагу 3.

## Зависимости

Новых библиотек нет. `plotly.graph_objs` (`go.Bar` + `barmode="stack"` — базовая возможность, уже в стеке), `dash_bootstrap_components.Tooltip` (dbc уже зависимость), `calendar.monthrange`, `datetime.timedelta` — всё используется в проекте. Обоснование отказа от новых: причина эпика — упрощение; окно 45 дней укладывается в `MAX_FORECAST_DAYS = 366` (`recurring_service.py:25`), внешних календарных библиотек не требует.

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Режимная логика резерва (`fixed_date` vs `from_balance`) реализована с ошибкой — деньги считаются дважды или теряются | Высокая | Шаг 4 отдельно от каркаса; 4 теста на режимы: `fixed_date` + досрочный взнос, `fixed_date` без взносов, `from_balance` + взнос, `from_balance` без бюджета. Инвариант AC-3 держится вычитанием, поэтому ошибка проявится как расхождение слоёв, а не как сломанная сумма — тесты сравнивают `goals_reserve_today` с ожидаемым значением явно, а не только сумму |
| Резерв за границей месяца ведёт себя не так, как ожидает владелец | Средняя | Правило зафиксировано явно с обоснованием через инвариант (резерв виден, т.к. уже в балансе; платежи нет, т.к. неизвестны) и тестом `test_reserve_grows_at_next_month_reserve_date`; совпадает с поведением синей полосы принятого эскиза v3 (22.5px → 34.5px после 5 сентября). Запись в осадок решений |
| `free` уходит в минус при остатке ниже платежей+резерва — отрицательная полоса в стопке | Средняя (снизилась: порог вместо target) | Детерминированный каскад `_split_day`; тест на все три ветки с assert суммы; вердикт «Нужно вмешаться» вместо тихого искажения |
| NFR-1: окно 45 дней вместо ≤31 — на ~45% больше работы `calculate_daily_balances` | Средняя | По-прежнему кратно меньше текущего годового режима (`get_yearly_cashflow` — 12 месяцев). Плюс шаг 2 **убирает** 2 полных обхода recurring-истории (`get_settings` → `get_balance_on_date` → `_calculate_recurring_before_date`, `calendar_service.py:364-407`), который v1 тянул скрыто. Остаётся 1 такой обход внутри `calculate_daily_balances` + 1 в `_build_cushion_card_readonly` (C-1 — карточка подушки не трогается). Замер на шаге 14 на наполненной базе |
| Относительный `dip_threshold` даёт неожиданный вердикт (порог зависит от платежей окна, а те меняются в течение месяца) | Средняя | `dip_threshold` возвращается в `LayersVerdict` и показывается в тултипе вердикта — вердикт объясним, а не магический. `DIP_FLOOR = 1000` не даёт порогу выродиться в 0 при нулевых платежах. Запись в осадок как MVP-эвристика с указанием, что перекалибровка — задача беты |
| Удаление `period-switcher` ломает `Input("period-switcher","value")` в `load_dashboard_data` | Низкая | Input убирается вместе с элементом и callback'ом `update_period_state`; Store `dashboard-period` остаётся с дефолтом `{"period":"month"}` (нужен `open_create_from_chart`). `suppress_callback_exceptions=True` (`main.py:41`) уже стоит — проверено |
| Тултип легенды (FR-4) hover-only — не работает на touch | Низкая (в scope) | `dbc.Tooltip(trigger="hover focus")` + элемент с `tabIndex=0`: доступно с клавиатуры. Полноценный touch — Epic-08 (out of scope) |
| Аватар в шапке дублирует аватар в сайдбаре (C-1 запрещает трогать сайдбар) | Средняя | Осознанная временная цена куска 1, снимается в куске 3 (сайдбар → полоска-меню). Уже в осадке решений |
| Правка `profile_modal.py` ломает вход в профиль из сайдбара | Низкая | Ветка расширяется через `triggered_id in (...)`, существующая логика загрузки профиля не меняется; ручная проверка обоих входов (шаг 10) |
| Латентный дефект `_calculate_recurring_before_date` (учитывает только income/expense, пропускает savings_*, `calendar_service.py:400-407`, тогда как `_get_recurring_daily_changes` :426-437 их учитывает) искажает базу окна | Средняя | Подтверждено проверкой. Инвариант AC-3 не ломает (`free` выводится из того, что вернул `calculate_daily_balances`), но абсолютные величины «Свободно» могут смещаться у пользователей с давним recurring-резервом. Правка — вне scope (C-3 запрещает менять поведение `CalendarService`); фиксируется как кандидат на отдельный протокол в осадке решений |
| Вехи целей загромождают 45-дневную ось | Низкая | ≤3 вехи в окне (ближайшие по `target_date`), остальные — сводкой «и ещё N целей» в тултипе «Резерв»; веха за краем — одна стрелка-аннотация у правого края (эскиз v3). `GoalService.create_goal` требует `target_date >= today + 7` (`goal_service.py:91-98`), поэтому в 45-дневном окне вехи попадают регулярно (в отличие от ≤31 дня из v1) |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|---|---|---|---|
| FR-1.a | «Для каждого дня горизонта (текущий календарный месяц, начиная с сегодня) модель выдаёт декомпозицию прогнозного остатка на три слоя» | FR-1 | **Расхождение зафиксировано осознанно (решение владельца 2026-08-24):** окно оси — 45 дней (`WINDOW_DAYS`), а не календарный месяц; календарным месяцем ограничен только слой «Платежи» (`payments_end`). Спека формулировала горизонт по C-5, но C-5 в design.md:91 ограничивает *слой*, не ось. `MoneyLayersData['days']` — 45 дней | FR |
| FR-1.b | «*Свободно* — реально доступные деньги» | FR-1 | `DayLayers['free']` = `balance − payments − reserve` через `_split_day()`; на числах эскиза `free_today = 2 000 ₽ > 0` (в v1 было 0) | FR |
| FR-1.c | «*Платежи* — деньги ещё на счету, но уйдут на уже запланированные платежи (регулярные + разовые предстоящие) до конца календарного месяца» | FR-1 | `_collect_upcoming_payments(reference_date, payments_end)` (регулярные + разовые из `get_all_transactions_for_period`) + `_payments_tail_by_day()` — суффиксная сумма в `(D, payments_end]`; за `payments_end` слой строго `0` | FR |
| FR-1.d | «слой "тает" по мере исполнения платежей и пересчитывается на границе месяца» | FR-1 | Суффиксная сумма даёт монотонное таяние; `payments(payments_end) == 0`. «Пересчёт на границе месяца» = `payments_end` привязан к месяцу `reference_date`: 1-го числа горизонт платежей скачком становится новым месяцем, слой наполняется заново, при этом **ось не дёргается** (окно скользящее). Тесты «таяние» и «граница месяца» (шаг 6) | FR |
| FR-1.e | «*Резерв* — резерв целей (бюджет накоплений) + подушка» | FR-1 | `_reserve_by_day()`: `min(threshold_amount, max(balance,0))` (порог подушки — решение владельца) + режимно-корректный неизрасходованный `monthly_savings_budget`, ещё лежащий в остатке | FR |
| FR-1.f | «Сумма трёх слоёв на день D равна прогнозному остатку на D (согласована с балансом кассового календаря)» | FR-1 | Конструктивно: `free` выводится вычитанием из `calculate_daily_balances`; `_split_day()` сохраняет сумму во всех трёх ветках. Параметризованный тест по всем 45 дням | FR |
| FR-1.g | «Модель — единый источник для шапки, графика и (в куске 2) карточек щитка» | FR-1 | Один вызов `get_money_layers()` в `_load_dashboard_components()` кормит `build_verdict_header()` и `build_layers_chart()`. Оговорка: контракт куска 1 не претендует на стабильность до куска 2 (зафиксировано в докстринге модуля) | FR |
| FR-2.a | «Вверху дашборда: "Свободно сегодня: N ₽" (N — срез модели FR-1 на сегодня)» | FR-2 | `build_verdict_header()`: метка «Свободно сегодня» + `format_rub(verdict['free_today'])`; `free_today == days[0]['free']`, `days[0]['date'] == reference_date` (тест) | FR |
| FR-2.b | «цветовой вердикт состояния (порядок / впереди просадка / проблема)» | FR-2 | `VerdictLevel = Literal["ok","dip","problem"]`; `VERDICT_TEXTS` = «Всё в порядке» / «Впереди просадка» / «Нужно вмешаться»; `VERDICT_COLORS` = `#2ecc71` / `#f39c12` / `#e74c3c`. Пороги: `problem` при `free_today <= 0` или `min_free < 0`; `dip` при `min_free < max(payments_total × 0.10, 1000)`; иначе `ok`. `min_free` — по **окну 45 дней** | FR |
| FR-2.c | «краткий разбор "баланс − платежи − резерв"» | FR-2 | `pnl-breadcrumb`: «баланс {balance_today} − платежи {payments_today} − резерв {reserve_today}» через `format_rub` (формат эскиза v3) | FR |
| FR-2.d | «Справа — аватар пользователя и служебная иконка настроек» | FR-2 | `get_avatar_emoji(profile['avatar_id'])` + `profile['name']` в `pnl-avatar`; шестерёнка `id="dashboard-settings-cog"` → **новый Input в `profile_modal.py`** (решение владельца), открывает модал профиля. `/settings` вне scope | FR |
| FR-2.e | «Шапка не является дверью-переходом» | FR-2 | На `pnl-breaker` нет `dcc.Link`, `n_clicks`, `cursor:pointer`; кликабельны только кнопка «Сверка» и шестерёнка | FR |
| FR-2.f | «Шапка-вердикт **заменяет текущий ряд 4 KPI-карточек** (два "главных числа" рядом недопустимы)» | FR-2 | Удаляются `build_overview_cards()`, `_build_kpi_card()`, `build_statistics_card()`; `dashboard-overview-cards` и `dashboard-statistics-card` уходят из layout; на их место — `dashboard-verdict-header`. Приветствие тоже поглощается (два «привета» — та же болезнь дублирования) | FR |
| FR-3.a | «Текущий график (grouped bars + линия баланса, протокол 0022) заменяется полностью» | FR-3 | Удаляются `_build_daily_cashflow_chart()`, `_build_yearly_cashflow_chart()`, `build_cashflow_chart()`; `dashboard-cashflow-chart` → `dashboard-layers-chart` | FR |
| FR-3.b | «стопка полос Свободно (зелёный) / Платежи (оранжевый) / Резерв (синий) по дням» | FR-3 | `barmode="stack"`, три `go.Bar` по датам; `LAYER_COLORS`: `#2ecc71` / `#f0b775` / `#3498db`; порядок снизу вверх free → payments → reserve (как в v3) | FR |
| FR-3.c | «вехи целей на оси времени» | FR-3 | `GoalMilestone` + аннотации Plotly (флажок ⚑, название, дата); ≤3 вехи в окне + одна `beyond_window` стрелкой у правого края. При окне 45 дней и `create_goal`-валидации `target_date >= today+7` (`goal_service.py:91-98`) вехи попадают в кадр регулярно — в v1 при ≤31 дне механика была мёртвой | FR |
| FR-3.d | «вертикальная линия "сегодня"» | FR-3 | `fig.add_shape` (`yref="paper"`) на `reference_date`, `dash="dash"`, `#2c3e50`, подпись «сегодня» — как в v3. Линия стоит у левого края окна (это и есть композиция эскиза) | FR |
| FR-3.e | «маркер минимума остатка» | FR-3 | Маркер-кружок на `min_free_date` + аннотация `format_rub(min_free)` со сдвигом (`yshift`), плюс плашка «⚠ Минимум свободного / {дата} — {сумма}» в свободной зоне поля. Минимум ищется по 45 дням — не вырождается в «сегодня», как при ≤31 дне в v1 | FR |
| FR-3.f | «График и шапка — единый визуальный блок: "свободно сегодня" есть срез графика на сегодня» | FR-3 | Одна модель на оба блока; тест `verdict['free_today'] == days[0]['free']`; визуально `pnl-meter` примыкает к `pnl-breaker` (общий gap и палитра) | FR |
| FR-4.a | «У легенды графика — пояснение с конкретикой: для "Платежей" — список предстоящих платежей с датами ("аренда 25 авг, коммуналка 28 авг…")» | FR-4 | `_build_payments_tooltip()`: `dbc.Tooltip` на элементе HTML-легенды «Платежи», строки «{описание} · {format_date_human(date)} · {format_rub(−amount)}» из `upcoming_payments`, до 8 + «и ещё N». Только текстовые компоненты (без `dcc.Markdown`) | FR |
| FR-4.b | «для остальных слоёв — что входит в слой» | FR-4 | «Свободно»: «Остаток минус платежи до конца месяца и резерв». «Резерв целей и подушки»: «Порог подушки {cushion_threshold} + бюджет целей {goals_reserve_today}» — двумя строками, что и требует FR-4.b | FR |
| FR-5.a | «Вход в "Сверку" с дашборда сохраняется (сейчас — кнопка на KPI-карточке баланса)» | FR-5 | Кнопка «Сверка» переезжает в правый блок шапки, id `open-recon-from-dashboard-verdict-btn`, тот же clientside `ClientsideFunction("triggers","timestamp_trigger")` → `open-recon-trigger`. Баннерная кнопка `open-recon-from-dashboard-banner-btn` не трогается | FR |
| FR-5.b | «Судьба показателя "Доходы за месяц" решается проектированием явно: сохранить в новом месте или убрать осознанно (не потерять молча)» | FR-5 | **Решение: убрать с дашборда осознанно.** Основание: не отвечает ни на один вопрос иерархии внимания design.md; его проекция — «цифра месяца» карточки «Аналитика» (кусок 2). Данные сохранны: `CalendarService.get_month_summary`, `DashboardService.get_overview_metrics` (сервис не удаляется — C-3), раздел `/analytics`. Запись в `memory/spec-context/epic-11.md` | FR |
| FR-6.a | «При нулевых данных (новый пользователь, 0 операций) шапка и график показывают спроектированное пустое состояние» | FR-6 | `is_empty` ⟺ `count(transactions) == 0` **и** `starting_balance == 0` («нет данных вообще», не «нули в окне»); `_build_verdict_empty_state()` + `_build_chart_empty_state()`. Отдельно `window_is_flat` — график рисуется, а не подменяется | FR |
| FR-6.b | «без осей −1..1, склеек подписей и прочих артефактов деградации» | FR-6 | При `is_empty` Plotly не вызывается вовсе (`html.Div` вместо `dcc.Graph`) → оси −1..1 невозможны. Для непустых: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)` (нет «50.001k»); `xaxis=dict(type="date", tickformat="%-d %b", dtick=_axis_dtick(45)=4 дня, tickangle=0)` — ~12 подписей на 45 днях, шаг производный от окна | FR |
| NFR-1 | «Загрузка дашборда с новой моделью и графиком — не медленнее текущего дашборда; ориентир < 2 секунд на локальной базе с наполненными данными» | NFR-1 | Окно 45 дней вместо 12 мес./года. Бюджет вызовов на `get_money_layers`: **1** `calculate_daily_balances` (внутри — 1 полный обход recurring-истории через `_calculate_recurring_before_date`) + 1 `get_all_transactions_for_period` + 1 `get_settings`/`get_budget_progress` + 1 `get_threshold_amount` (**без** обхода баланса — снят скрытый пересчёт v1) + 1 `get_all_by_user`. **Честная оговорка:** ещё один полный обход остаётся вне модели — в `_build_cushion_card_readonly` (`dashboard.py:395-398`), который C-1 запрещает трогать. Итого 2 обхода за рендер против ≥3 в v1. Замер на шаге 14 | NFR |
| NFR-2 | «Сбои расчёта модели логируются через loguru с трейсбеком (`logger.opt(exception=True)` — идиома проекта, протокол 0027), не молча» | NFR-2 | `logger.opt(exception=True).warning(...)` в fail-open ветках (бюджет целей, цели, неожиданный сбой порога) и `logger.opt(exception=True).error(...)` в `load_dashboard_data` / `refresh_dashboard_after_crud` вместо `logger.error(f"...{e}")` (`dashboard.py:1389`, :1451). Штатное «нет пользователя / подушка не настроена» — тихий дефолт без трейсбека (сигнал, не шум) | NFR |
| C-1 | «Остальные разделы (календарь, цели, операции, аналитика) и сайдбар в этом куске не трогаются. Таблицы операций, wishlist-виджет и карточка подушки на дашборде остаются как есть» | C-1 | Правки в `dashboard.py`, `profile_modal.py` (решение владельца: C-1 про сайдбар и другие разделы, а не про глобальный модал), `cushion_service.py` (добавление метода), `custom.css`, новых файлах. `sidebar.py`, `calendar.py`, `goals.py`, `transactions.py`, `analytics.py` не меняются. `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `build_wishlist_widget()`, `dashboard-cushion-card` остаются в layout и в tuple | C |
| C-2 | «Decimal для денег, session-контракт flush()/commit(), сервисы не знают о Dash» | C-2 | Все денежные поля TypedDict — `Decimal`; `MoneyLayersService` read-only (не вызывает `flush()`/`commit()` — писать нечего); `get_threshold_amount` тоже read-only; импортов `dash`/`plotly` в сервисах и схеме нет | C |
| C-3 | «Существующее поведение сервисов не меняется — модель FR-1 строится надстройкой/композицией; полный прогон тестов (565 на 2026-08-21) остаётся зелёным» | C-3 | Ни один существующий метод `CalendarService`/`DashboardService`/`CushionService`/`BudgetReservationService`/`GoalService` не редактируется. **Одно явно зафиксированное отступление:** в `CushionService` **добавляется** новый метод `get_threshold_amount()` — поведение существующих не меняется, C-3 запрещает менять поведение, а не расширять API. Фиксируется решением, не молча. `tests/test_dashboard_service.py`, `test_calendar_service.py`, `test_budget_reservation_service.py` не правятся (доказательство C-3); правится только `test_dashboard_callbacks.py` (контракт callback'а) и дополняется `test_cushion_service.py`. Прогон 565 тестов подтверждён локально (`pytest --collect-only` → 565) | C |
| C-4 | «Схема БД не меняется» | C-4 | Проверено по таблице «Модель данных»: `users.starting_balance/cushion_target/cushion_threshold_percent/monthly_savings_budget/reservation_mode/reservation_day/avatar_id/name`, `transactions.*`, `goals.target_date/target_amount/current_amount/status`, `goal_contributions` — всё есть. Отдельно проверено: колонки «ручная сумма порога подушки» в схеме нет (только `cushion_threshold_manual` — булев флаг, `database.py:107`), поэтому `threshold_amount` всегда вычисляется формулой и добавления поля не требует. Миграций нет | C |
| C-5.a | «Горизонт слоя "Платежи" — до конца календарного месяца (принятое решение design.md; платежи начала следующего месяца до зарплаты не видны — осознанное ограничение)» | C-5 | `payments_end = date(y, m, monthrange(y, m)[1])`; `_payments_tail_by_day` не смотрит за `payments_end`, для `D >= payments_end` возвращает `0`. Ось при этом 45 дней (решение владельца), поэтому **ограничение видно честно**: за 31 августа оранжевой полосы просто нет. Ограничение задокументировано в докстринге сервиса и в тултипе легенды «Платежи» | C |
| C-5.b | «Механику "основного дохода" не реализовывать» | C-5 | Нет ни поля, ни ветвления по «основному доходу»; горизонт платежей фиксирован календарным месяцем, окно оси — константой | C |
| AC-1 | «Наполненная база → видна шапка "Свободно сегодня: N ₽" с цветовым вердиктом и разбором, и N совпадает со значением слоя "Свободно" модели на сегодняшнюю дату (срез графика)» | AC-1 | `build_verdict_header()` рендерит `verdict['free_today']`; тест `verdict['free_today'] == days[0]['free']` и `days[0]['date'] == reference_date`; ручная проверка на наполненной базе (шаг 14) | AC |
| AC-2 | «Отображается график стопки трёх полос с легендой "Свободно / Платежи / Резерв", вехами целей, линией "сегодня" и маркером минимума; старый график доходы/расходы+баланс и ряд 4 KPI-карточек отсутствуют» | AC-2 | `build_layers_chart()` + `_build_layer_legend()`; физическое удаление `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`, `build_cashflow_chart`, `build_overview_cards`, `_build_kpi_card`, `build_statistics_card` (шаг 12). Все три полосы фактически ненулевые на типичных данных (порог вместо target — 🔴№1) | AC |
| AC-3 | «Для любого дня D горизонта сумма трёх слоёв модели равна прогнозному остатку на D из кассового календаря (CalendarService) — проверено unit-тестом» | AC-3 | Параметризованный тест: для всех 45 дней `free + payments + reserve == forecast_balance` и `forecast_balance == calculate_daily_balances()[date]`; кейсы: положительный / нулевой / отрицательный остаток, дефицитный каскад, режимы `fixed_date` и `from_balance`, дни до и после границы месяца | AC |
| AC-4 | «Наведение/клик на пояснение легенды "Платежи" показывает список конкретных предстоящих платежей с датами до конца месяца» | AC-4 | `dbc.Tooltip(target="pnl-legend-payments", trigger="hover focus")` со строками из `upcoming_payments`; элемент легенды с `tabIndex=0`. Тултип объясняет и пустой случай («до конца месяца платежей больше нет») | AC |
| AC-5 | «Чистая база (онбординг пропущен, 0 операций) → шапка и график показывают осмысленное пустое состояние без артефактов (осей −1..1, "50.001k", склеек подписей)» | AC-5 | Ветка `is_empty` (Plotly не вызывается) + тесты «чистая база → is_empty=True, слои нулевые, исключений нет» и «онбординг пропущен (`skip()` → `first_launch=False`, `starting_balance=0`) → is_empty=True» (проверено: `first_launch` для критерия не годится, `onboarding_service.py:168-182`). Ручная проверка на чистой базе (шаг 14) | AC |
| AC-6 | «Вход в сверку с дашборда работает: модал сверки открывается и применяется, как до редизайна» | AC-6 | `open-recon-from-dashboard-verdict-btn` → тот же clientside → `open-recon-trigger` → существующий `create_reconciliation_modal()` в `main.py` (не трогается); баннерный вход сохранён; второй потребитель триггера в `calendar.py:1262-1309` не затронут (контракт Store не меняется) | AC |
| AC-7 | «Новая модель покрыта unit-тестами (включая границу месяца и "таяние" платежей); полный прогон pytest зелёный; black + flake8 без новых замечаний» | AC-7 | `tests/test_money_layers_service.py` (~22 теста, шаг 6, явные тесты границы месяца и таяния) + дополнения в `test_cushion_service.py`; шаг 14 — `pytest -q` (565 + новые), `black`, `flake8` | AC |
| Эскиз | «легенду графика вынести из поля» (заметка vision-критика) | memory/spec-context | `showlegend=False` в Plotly; HTML-легенда `_build_layer_legend()` под заголовком блока графика (в эскизе v3 легенда сидит внутри поля на y=47 — заметка исполнена) | Заметка |
| Эскиз | «ярлык минимума ("9 800 ₽") не ставить вплотную к тику даты» | memory/spec-context | Аннотация минимума со сдвигом (`yshift`/`ay`) + развёрнутая плашка «Минимум свободного» в свободной зоне поля, не под тиком | Заметка |
| Эскиз | «выровнять вертикальный ритм карточки "Цели"» | memory/spec-context | Не применимо к куску 1 (карточки-двери — кусок 2). Заметка остаётся в осадке до куска 2 | Заметка |
| Эскиз | Ось «~45 дней» (`v3.html` aria-label: «с 22 августа по 5 октября 2026»; brief.md:45-52) | .visual + осадок | `WINDOW_DAYS = 45`; `_axis_dtick(45)` = 4 дня (~12 подписей, в эскизе — 11); минимум, зарплата и веха за краем попадают в кадр | Эскиз |

## Blast Radius

### Прямые изменения

- `app/schema/money_layers.py` — **НОВЫЙ**: `DayLayers`, `UpcomingPayment`, `GoalMilestone`, `LayersVerdict`, `MoneyLayersData`; `LayerKey`, `VerdictLevel`; `WINDOW_DAYS`, `LAYER_COLORS`, `LAYER_LABELS`, `VERDICT_TEXTS`, `VERDICT_COLORS`, `DIP_RATIO`, `DIP_FLOOR`, `MAX_MILESTONES_IN_WINDOW`.
- `app/services/money_layers_service.py` — **НОВЫЙ**: `MoneyLayersService.get_money_layers()` + `_horizons`, `_forecast_balances`, `_collect_upcoming_payments`, `_payments_tail_by_day`, `_reserve_by_day`, `_split_day`, `_build_verdict`, `_goal_milestones`, `_detect_empty`.
- `app/assets/panel.css` — **НОВЫЙ**: `pnl-*` (шапка-вердикт, блок графика, HTML-легенда).
- `app/services/cushion_service.py` — **ДОБАВЛЕНИЕ** `get_threshold_amount()`; существующие методы не тронуты (явное отступление от буквы C-3, зафиксировано).
- `app/components/dashboard.py` — крупнейший blast: удаление 4 KPI-карточек, `build_statistics_card`, обоих старых графиков и мёртвого кода; добавление `build_verdict_header`, `build_layers_chart`, `_build_layer_legend`, `_build_payments_tooltip`, `_build_verdict_empty_state`, `_build_chart_empty_state`, `_axis_dtick`; перекройка `create_dashboard_layout` (снятие `period-switcher`, `dashboard-greeting`, `dashboard-overview-cards`, `dashboard-statistics-card`), `_load_dashboard_components` (5 значений), `load_dashboard_data` (5 Output'ов, `logger.opt`), `refresh_dashboard_after_crud`, `open_create_from_chart` (новый id + ISO-дата), clientside «Сверка» (новый id); удаление callback'а `update_period_state`.
- `app/components/profile_modal.py` — **прямые изменения** (решение владельца): второй `Input("dashboard-settings-cog", "n_clicks")` и ветка `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")` (сейчас единственный Input :96 и жёсткое сравнение :119).
- `app/schema/__init__.py` — реэкспорт новых типов и констант (+ `__all__`).
- `app/services/__init__.py` — реэкспорт `MoneyLayersService` и типов модели (+ `__all__`).
- `app/assets/custom.css` — удаление `#dashboard-overview-cards .row`, `.db-period-switcher` (все правила), `.kpi-card` / `.kpi-card-icon` / `.kpi-trend*` / `.kpi-number` / `.kpi-title` / `.kpi-subtitle` (:195-268) — **grep проведён, вне `dashboard.py` и `custom.css` не используются; `.an-period-switcher` в analytics — отдельный класс**; правка `.db-page` / `.db-left-col` под новую сетку.
- `tests/test_money_layers_service.py` — **НОВЫЙ**: FR-1 / AC-3 / AC-7.
- `tests/test_dashboard_callbacks.py` — переписывание `test_load_dashboard_data_decorator_declares_greeting_output` (→ `dashboard-verdict-header`) и `test_returns_seven_values_with_greeting_last` (→ 5 значений). `TestBuildGreetingText` и подписки на `profile-updated` не трогаются.
- `tests/test_cushion_service.py` — тесты `get_threshold_amount`.

### Связанные файлы (могут быть затронуты)

- `app/main.py` — `suppress_callback_exceptions=True` (:41) и глобальные Store'ы (`open-recon-trigger` :95, `profile-updated` :91, `balance-toast-dismissed` :93), `create_reconciliation_modal()`, `create_profile_modal()`. Проверить, что снятый `period-switcher` не ломает старт.
- `app/components/calendar.py` — второй потребитель `open-recon-trigger` (:1262-1309): контракт триггера менять нельзя.
- `app/components/sidebar.py` — `sidebar-profile-container` остаётся первым Input'ом модала; C-1 запрещает правки; визуальный дубль аватара — осознанная цена до куска 3.
- `app/config/avatars.py` — `get_avatar_emoji()`, `AVATARS`, `DEFAULT_AVATAR_ID` для шапки.
- `app/components/wishlist.py` — `build_wishlist_widget()` вызывается прямо из `create_dashboard_layout` (:167): при перекройке layout нельзя потерять вызов (C-1).
- `app/components/transaction_modals.py` — `create-modal`, `preselected-date`, `modal-source`: Output'ы `open_create_from_chart`, парсинг клика меняется (день → ISO-дата).
- `app/services/dashboard_service.py` — **НЕ меняется** (C-3), но `get_overview_metrics`, `get_daily_cashflow`, `get_yearly_cashflow`, `get_cashflow_data` теряют вызывающего на дашборде: остаются в публичном API и под тестами, удалять нельзя.
- `app/services/calendar_service.py` — **НЕ меняется**; латентный дефект `_calculate_recurring_before_date` (:400-407 учитывает только income/expense, `_get_recurring_daily_changes` :426-437 учитывает и savings_*) подтверждён проверкой и остаётся вне scope — кандидат на отдельный протокол.
- `app/services/budget_reservation_service.py` — **НЕ меняется**; `_get_reserve_sum_for_month` (:466-500) получает первого вызывающего (сейчас их нет).
- `app/assets/clientside_triggers.js` — namespace `triggers`, `timestamp_trigger` / `open_create_modal`: переиспользуются новыми id, файл не меняется.
- `tests/test_dashboard_service.py`, `tests/test_calendar_service.py`, `tests/test_budget_reservation_service.py`, `tests/test_purchase_recommendation.py` — не должны требовать правок; если потребовали — признак нарушения C-3.
- `tests/test_bootstrap.py`, `tests/test_serializers.py` — smoke-тесты layout/сериализации: могут поймать несериализуемые объекты или отсутствующие id.
- `.obsidian-docs/knowledge-bank/modules/services.md`, `modules/schema.md`, `modules/ui-components.md`, `patterns/plotly-charts.md`, `architecture.md` — обновление KB после реализации (Dual-Y-Axis паттерн перестаёт применяться на дашборде).
- `memory/spec-context/epic-11.md` — записать: судьба «Доходов за месяц» (убрать), достаточность схемы БД, поглощение `dashboard-greeting` шапкой, поведение резерва за границей месяца, `DIP_RATIO`/`DIP_FLOOR` как MVP-эвристика, добавление `get_threshold_amount` как отступление от буквы C-3, латентный дефект `_calculate_recurring_before_date`.

### Проверить после реализации

- [ ] `pytest -q` — 565 прежних зелёные + новые из `test_money_layers_service.py`; в `test_dashboard_service.py`, `test_calendar_service.py`, `test_budget_reservation_service.py` ни одной правки (доказательство C-3).
- [ ] `grep -rn "build_overview_cards\|_build_kpi_card\|_build_daily_cashflow_chart\|_build_yearly_cashflow_chart\|build_cashflow_chart\|build_statistics_card\|dashboard-overview-cards\|dashboard-statistics-card\|dashboard-greeting\|period-switcher\|kpi-" app tests` — по дашборду пусто (остаются только `an-period-switcher` в analytics).
- [ ] Открыть `/` и `/dashboard`: нет ошибок в консоли про nonexistent object `period-switcher`, `dashboard-overview-cards`, `dashboard-statistics-card`, `dashboard-greeting`, `daily-cashflow-chart`.
- [ ] AC-1: число в шапке == высота зелёной полосы «сегодня» (hover) == `days[0]['free']`.
- [ ] AC-3 вручную: на наполненной базе для 3 произвольных дней (один до, один после границы месяца) сумма слоёв из hover == остаток того же дня в `/calendar`.
- [ ] AC-4: hover и Tab-фокус на легенде «Платежи» → список с датами; проверить месяц без платежей (тултип объясняющий, не пустой).
- [ ] AC-5: чистая база — шапка и график в пустом состоянии, в DOM нет `dcc.Graph` от графика слоёв.
- [ ] Отдельно: база с историей и пустым окном → **график рисуется** (плоская стопка), пустое состояние не подменяет его (🟡№6).
- [ ] AC-6: кнопка в шапке и кнопка в баннере обе открывают модал сверки; сверка применяется; вход с `/calendar` не сломан.
- [ ] 🟡№4: шестерёнка в шапке открывает модал профиля; клик по аватару в сайдбаре — тоже (обе ветки живы).
- [ ] Граница месяца: unit-тест с `reference_date` = последний день месяца (окно 45 дней, `payments == 0` всюду) и UI 1-го числа — «пересчёт» слоя платежей корректен, ось не дёргается.
- [ ] 🔴№1 вручную: типичная конфигурация (подушка настроена, бюджет целей есть, платежи есть) → `free_today > 0`, вердикт не «Нужно вмешаться»; `cushion_threshold` в тултипе «Резерв» совпадает с порогом, который использует wishlist «безопасно после…».
- [ ] 🟡№3 вручную: режим `fixed_date`, досрочный взнос в цель → сумма взноса остаётся в синей полосе, не перетекает в «Свободно».
- [ ] Резерв за границей месяца: синяя полоса не обнуляется 1-го числа и подрастает в день следующего резерва (`fixed_date`).
- [ ] NFR-1: замер времени рендера на наполненной базе — < 2 сек и не хуже прежнего; в логах видно ровно один `calculate_daily_balances` от модели.
- [ ] NFR-2: monkeypatch-падение `BudgetReservationService.get_budget_progress` → в логах трейсбек через `logger.opt(exception=True)`, дашборд рендерится с резервом без бюджета целей. Отдельно: чистая база **не** генерирует варнинг-с-трейсбеком (тихий дефолт).
- [ ] `black --check app tests` и `flake8 app tests` — без новых замечаний.
- [ ] Wishlist-виджет, таблицы недавних/предстоящих операций и карточка подушки на месте и живые (C-1).

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|------------------------------|------------|
| 🔴 №1. Полный `cushion_target` в слое «Резерв» обнуляет главное число дашборда (`free = 0` во всех строках собственного примера v1; противоречие с эскизом 84 500 − 37 500 − 15 000 и с `threshold_amount` в `PurchaseRecommendationService`) | Подушка в слое «Резерв» = **`threshold_amount`** (решение владельца) — та же величина, что у `get_safe_dates_map` (`purchase_recommendation_service.py:74`): единая семантика «неприкосновенного» на весь продукт. Сверх того `cushion_part = min(threshold, max(balance, 0))` — защита от кейса аудита «накоплено 922 155 при цели 100 000» и от остатка ниже порога. Берётся новым лёгким `CushionService.get_threshold_amount()`. Пересчёт на числах эскиза дан в «Модели данных»: `free_today = 2 000 ₽ > 0`, все три полосы ненулевые. Тесты: «типичная конфигурация → `free_today > 0`» и «порог совпадает с тем, что использует wishlist» |
| 🔴 №2. Горизонт графика сужен до конца месяца — эскиз (ось 22 авг – 5 окт, минимум 4 сент, зарплата 5 сент, веха 15 окт за краем) становится нереализуемым; ежемесячная деградация до 1-7 столбцов | Разведены два горизонта (решение владельца): ось — `WINDOW_DAYS = 45` дней от `reference_date`; слой «Платежи» — до конца календарного месяца, за границей строго `0`, то есть **C-5 стало видимым ограничением**, а не скрытым. Минимум ищется по всему окну (не вырождается в «сегодня»), вехи попадают в кадр регулярно (`create_goal` требует `target_date >= today+7`, `goal_service.py:91-98`), `beyond_window` обретает смысл, вырождение в 1-7 столбцов исчезло. Поведение резерва за границей месяца решено явно с обоснованием через инвариант и подтверждено эскизом (синяя полоса v3 растёт после 5 сентября). Затронутые формулировки пересмотрены: вердикт по `min_free` окна, FR-1.d «пересчёт на границе» = скачок `payments_end` при неподвижной оси, NFR-1 переписан под 45 дней, тултип платежей объясняет границу месяца |
| 🟡 №3. Двойной/недостающий счёт бюджета целей в режиме `fixed_date` при досрочном взносе (взнос не создаёт транзакцию, `used_budget` вычитается — 15 000 утекают в «Свободно») | `_reserve_by_day` **различает режимы**. `from_balance` → вычитается `used_budget` (взнос создаёт `SAVINGS_CONTRIBUTION`, уже вычтен из остатка — формула v1 корректна). `fixed_date` → вычитается только **материализованный** резерв через `BudgetReservationService._get_reserve_sum_for_month` (:466-500, фильтр `is_recurring.is_(False)` → реальные транзакции и exceptions, не виртуальные инстансы), т.к. `create_contribution_transaction` в этом режиме возвращает `None` (:669-672). Проверка на кейсе критика (взнос 15 000 10-го при резерве 25-го): `goals_part = 15 000` вместо 0 — деньги остаются в синей полосе. Тест «`fixed_date` + досрочный взнос не попадает в Свободно» + парный «`from_balance` + взнос не считается дважды» |
| 🟡 №4. Иконка настроек не может «переиспользовать существующий триггер» — это правка `profile_modal.py` (нарушение C-1) | Решение владельца: `app/components/profile_modal.py` — **файл прямых изменений**, C-1 этого не запрещает (C-1 про сайдбар и другие разделы). Проверено по коду: единственный `Input("sidebar-profile-container","n_clicks")` (:96) и жёсткое `triggered_id == "sidebar-profile-container"` (:119) — добавляется второй Input `dashboard-settings-cog` и ветка `triggered_id in (...)`; `suppress_callback_exceptions=True` (`main.py:41`) снимает риск отсутствия элемента вне дашборда. Куда ведёт шестерёнка сказано явно: **модал профиля**, `title="Профиль и настройки"`; раздел `/settings` (404) вне scope. Файл добавлен в «Прямые изменения» Blast Radius, ручная проверка обеих ветвей в чек-листе |
| 🟡 №5. Сигнатура `_load_dashboard_components` не соответствует фактической; судьба `dashboard-greeting` и состав Output'ов не названы | Сверено с кодом (`dashboard.py:1255-1258` — `(period, period_state)`, оба вызывающих передают два аргумента :1385, :1445). **Решения:** (а) аргумент `period` **остаётся**, Store `dashboard-period` **остаётся** заполненным дефолтом (нужен `open_create_from_chart`), удаление аргумента отложено в кусок 2 явно; (б) `dashboard-greeting` **поглощается шапкой** — элемент и его Output удаляются, приветствие рендерится внутри `build_verdict_header` через сохранённый `_build_greeting_text()`, дух протокола 0026 соблюдён (приветствие по-прежнему обновляется внутри `load_dashboard_data`, а не отдельным callback'ом); (в) точный состав Output'ов обоих callback'ов дан таблицей в «Ключевых интерфейсах» (5 значений вместо 7/6), тесты `test_..._greeting_output` и `test_returns_seven_values_with_greeting_last` (:62-70, :188-210) переписываются осознанно с обоснованием |
| 🟡 №6. Определение `is_empty` противоречиво — «нули в окне» дадут «Добавьте первую операцию» пользователю с полугодовой историей | `is_empty` переопределён через «**нет данных вообще**»: `count(transactions where user_id) == 0` **и** `starting_balance == 0`. `first_launch` для критерия отвергнут с обоснованием — `OnboardingService.skip()` сбрасывает его в `False`, не создавая данных (`onboarding_service.py:168-182`). Введён отдельный флаг `window_is_flat` для кейса «данные есть, окно пустое»: график **рисуется** (плоская стопка), пустое состояние его не подменяет. Тест `test_window_flat_renders_chart_not_empty_state` + пункт в чек-листе |
| 🟡 №7. `CushionService.get_settings` тянет полный пересчёт баланса и бросает `ValidationError` на отсутствующем пользователе (шум вместо сигнала); обещание NFR-1 «один `calculate_daily_balances`» неверно | Добавлен лёгкий `CushionService.get_threshold_amount()` — **без** `_get_current_balance()`. Проверено, что это корректно: `threshold_amount` в `get_settings` (:110-113) не зависит от баланса, а колонки «ручная сумма порога» в схеме нет (`database.py:105-107` — только процент и булев флаг). Возвращает `Decimal("0")` при отсутствии пользователя/подушки — **тихий дефолт без трейсбека**, что снимает шум на чистой базе. C-3 разрешает: запрещено менять *поведение* существующих методов, добавление нового зафиксировано явным решением (строка C-3 в RTM). Формулировка NFR-1 в RTM переписана честно: даётся точный бюджет вызовов и **признаётся** остающийся второй обход в `_build_cushion_card_readonly` (:395-398), который C-1 запрещает трогать; итого 2 обхода против ≥3 в v1 |
| 🟡 №8. `GoalService.get_all_by_user` возвращает ORM-объекты — риск `DetachedInstanceError` (`progress_percentage` — вычисляемое property) | В докстринге `_goal_milestones` и `GoalMilestone` **явно зафиксировано**: материализация полей (включая `progress_percentage`) происходит **внутри** сессии — по образцу `TransactionInfo` (`calendar_service.py:27-33`, заведён ровно для этого). `get_money_layers` в докстринге обещает результат, безопасный после закрытия сессии. Добавлен тест «модель доступна после закрытия сессии» (детач-тест, образец — `tests/test_serializers.py`) |
| 🟡 №9. Ошибочная привязка `DIP_THRESHOLD` к `BALANCE_ATTENTION_THRESHOLD`; абсолютные 5 000 ₽ делают вердикт случайным на краях аудитории | Константа проверена: `BALANCE_ATTENTION_THRESHOLD = Decimal("5000")` действительно существует (`app/schema/dashboard.py:19`), но её семантика — про **остаток**, а не про слой «Свободно», поэтому ссылка на «согласованность» **удалена как ошибочная**. Порог **пересмотрен**: `dip_threshold = max(payments_total × DIP_RATIO(0.10), DIP_FLOOR(1000))` — относительный, от масштаба собственных обязательств пользователя; `DIP_FLOOR` не даёт порогу выродиться в 0 при нулевых платежах. Фактическое значение возвращается в `LayersVerdict['dip_threshold']` — вердикт объясним в тултипе и проверяем в тестах. Эвристика записывается в осадок как MVP-калибровка |
| 🟢 №10. Поле `is_past` в `DayLayers` — мёртвое по собственному признанию | **Удалено** из `DayLayers`. Горизонт всё равно переопределён (окно 45 дней от `reference_date` — прошлых дней в модели нет по построению), поле не понадобится и в куске 2 |
| 🟢 №11. `dtick=86400000*3` — константа, при коротком окне даёт 2-3 подписи | Введён `_axis_dtick(window_days)` — шаг **производный** от длины окна: `max(1, round(window_days / 11))` дней, целевое ~10-12 подписей. Для `WINDOW_DAYS = 45` → 4 дня (12 подписей; в эскизе v3 — 11). Формула, а не магическое число |
| 🟢 №12. Плановая чистка `custom.css` от `.kpi-*` — можно утверждать сразу | Неопределённость **снята**: grep подтверждён самостоятельно — `.kpi-card`, `.kpi-card-icon`, `.kpi-trend*`, `.kpi-number`, `.kpi-title`, `.kpi-subtitle` (`custom.css:195-268`) встречаются только в `dashboard.py` и `custom.css`; `.db-period-switcher` — только `dashboard.py:123` (в analytics отдельный `.an-period-switcher`, `analytics.py:58` + `analytics.css:30-61`). Удаляются на шаге 12 без предварительной проверки, «если не используются» из формулировки убрано |

## Ответы на вопросы критика

**[факт] На чём основано утверждение, что `DIP_THRESHOLD = 5000` «согласован с `BALANCE_ATTENTION_THRESHOLD` (`app/schema/dashboard.py`)» — существует ли константа, каково её значение и семантика?**

Константа **существует**: `app/schema/dashboard.py:19` — `BALANCE_ATTENTION_THRESHOLD = Decimal("5000")`, докстринг: «Баланс < 5000 — требует внимания». Рядом `BALANCE_RISK_THRESHOLD = Decimal("0")` (:16). Реэкспортируется в `app/schema/__init__.py:45` и `app/services/__init__.py:13`. Значение в v1 совпало верно, **но критик прав по существу**: семантика константы — про *прогнозный остаток* (используется для `BalanceStatus` маркера минимума баланса), а `DIP_THRESHOLD` — про *слой «Свободно»* после вычитания платежей и резерва. Это разные величины, «согласованность» была ложной. В v2 ссылка убрана, порог заменён на относительный `max(payments_total × DIP_RATIO, DIP_FLOOR)` с фактическим значением в `LayersVerdict['dip_threshold']`.

**[факт] Как после перекройки layout выживает `dashboard-greeting` и его 7-й Output — поглощается шапкой или сохраняется отдельно?**

**Поглощается шапкой, осознанно.** Факты по коду: элемент `html.H4(..., id="dashboard-greeting")` лежит в `db-glass-header` вместе с `period-switcher` (`dashboard.py:108-127`), который снимается; Output — 7-й в `load_dashboard_data` (:1348); текст даёт хелпер `_build_greeting_text()` (:82-91); контракт закреплён тестом `test_load_dashboard_data_decorator_declares_greeting_output` (`tests/test_dashboard_callbacks.py:62-70`) и `test_returns_seven_values_with_greeting_last` (:188-210, жёсткое `len(result) == 7`). **Решение:** элемент и Output удаляются, приветствие «Привет, {name}» рендерится внутри `build_verdict_header` через сохранённый `_build_greeting_text()`; FR-2 всё равно требует имя пользователя в шапке, а два приветствия рядом — то же дублирование, что и два главных числа. Причина решения 0024/0026 («отдельный Output на элемент только этой страницы → ReferenceError на других») **соблюдена**: приветствие по-прежнему обновляется внутри `load_dashboard_data` (первым Output'ом `dashboard-verdict-header`), а не отдельным callback'ом. Оба теста переписываются на новый id и на 5 значений; `TestBuildGreetingText` не трогается (хелпер живёт).

**[факт] Остаётся ли аргумент `period` в `_load_dashboard_components` и остаётся ли Store `dashboard-period` заполняемым?**

Факты: фактическая сигнатура — `_load_dashboard_components(period: str, period_state: dict | None)` (`dashboard.py:1255-1258`), оба вызывающих передают два аргумента (:1385, :1445); Store `dashboard-period` объявлен в layout с `data={"period": "month"}` (:99-102), заполняется callback'ом `update_period_state` (:1397-1408) и читается `State`'ом в `load_dashboard_data` (:1355), `refresh_dashboard_after_crud` (:1421) и `open_create_from_chart` (:1462). **Решение (оба «да», противоречие v1 устранено):** аргумент `period` **остаётся** в сигнатуре — в куске 1 он больше не влияет на график (режим Year уходит с дашборда), но выкидывать его вместе со Store'ом значило бы одновременно ломать `open_create_from_chart` и трогать три callback'а сверх нужды. Store `dashboard-period` **остаётся** с дефолтом `{"period": "month"}` из layout; callback `update_period_state` **удаляется** вместе с `period-switcher` (единственный его Input), так что Store перестаёт обновляться, но не перестаёт существовать и читаться. `open_create_from_chart` при этом больше не зависит от Store для парсинга даты: X-ось стала датами, дата берётся напрямую из `point["x"]` — guard по `period == "month"` остаётся как страховка. Полная чистка (снятие аргумента и Store) отложена в кусок 2 явно, а не молча.

**[факт] Что именно попадает в слой «Платежи» из операций типа ADJUSTMENT: `get_all_transactions_for_period` возвращает `amount` строкой без знака — как определяется отрицательность корректировки?**

Посылка вопроса неверна — **знак сохраняется**, и вот доказательство по коду. `ReconciliationService.create_adjustment` создаёт транзакцию с `amount=difference`, где `difference = actual_balance - expected_balance`, с явным комментарием «ВАЖНО: amount хранит именно difference (может быть отрицательным)» (`reconciliation_service.py:131-135`). `get_all_transactions_for_period` сериализует поле как `amount=str(txn.amount)` (`calendar_service.py:803` для обычных, `:849` для exceptions, `:831` — `instance["amount"]` из `VirtualTransaction`) — то есть просто `str()` от `Decimal`, знак минус остаётся в строке. Согласованно с этим `CalendarService._get_daily_changes` берёт ADJUSTMENT **как есть** без инверсии (`:266-269`, докстринг :245-247: «положительный amount увеличивает баланс, отрицательный — уменьшает»), а `DashboardService._get_daily_income_expense` ветвит по знаку (`:484-485`, `:513`, `:543`). **Реализация:** `_collect_upcoming_payments` парсит `Decimal(info["amount"])` и при `< 0` кладёт платёж на `abs(...)`, при `>= 0` игнорирует (это доход-корректировка). Отдельный тест на оба знака ADJUSTMENT в списке (шаг 6). Побочно: ADJUSTMENT не может быть recurring (`transaction_service.py:79-80`), так что виртуальных корректировок не бывает.

**[решение] Что считать «неприкосновенной» частью подушки для слоя «Резерв»: порог, накопленное или полную цель?**

**Решение владельца (2026-08-24, зафиксировано в `memory/spec-context/epic-11.md`): порог подушки — `threshold_amount`** = `cushion_target × cushion_threshold_percent / 100` (при дефолтном `DEFAULT_THRESHOLD_PERCENT = Percent(30)`, `cushion_service.py:18`). Та же величина, которую уже использует `PurchaseRecommendationService.get_safe_dates_map` для «безопасных дат» покупок (`purchase_recommendation_service.py:74`) — единая семантика «неприкосновенного» на весь продукт, щиток и wishlist перестают противоречить. Отброшены: полная цель `target` (вечный «Свободно 0 ₽» до накопления подушки), фактически накопленное `min(target, balance)` (расходится с механикой покупок), «не вычитать подушку» (слой её не защищает). Реализация добавляет к решению защитный `min(threshold, max(balance, 0))` — не «политику», а корректность: защищать больше, чем физически есть, невозможно (кейс аудита «накоплено 922 155 при цели 100 000» и кейс остатка ниже порога). Отдельно проверено, что «manual»-ветки в решении владельца нет технического содержания: колонки «ручная сумма порога» в схеме не существует, `cushion_threshold_manual` — булев флаг «процент задан вручную» (`database.py:107`), сама сумма всегда вычисляется формулой.

**[решение] Остаётся ли ось графика в границах календарного месяца или расширяется до окна эскиза?**

**Решение владельца: ось — окно ~45 дней**, как в принятом эскизе `v3.html` (aria-label: «с 22 августа по 5 октября 2026»). C-5 остаётся ограничением **только слоя «Платежи»**: за границей текущего календарного месяца оранжевая полоса нулевая — ограничение видно честно, а не скрыто сужением оси. Отброшено: ось до конца месяца (график вырождается к концу месяца в 1-7 столбцов, вехи целей почти всегда за кадром при `create_goal`-валидации `target_date >= today+7`). Реализовано константой `WINDOW_DAYS = 45` в `app/schema/money_layers.py` (параметризовано, а не вшито в сервис) и двумя горизонтами в `_horizons()`. Следствия пересмотрены явно: вердикт считается по `min_free` **всего окна** (иначе шапка и график рассказывают разные истории про просадку), FR-1.d «пересчёт на границе месяца» = скачок `payments_end` при неподвижной скользящей оси, NFR-1 переоценён под 45 дней (+45% к `calculate_daily_balances`, компенсировано снятием скрытого пересчёта баланса в подушке), тултип «Платежи» объясняет границу месяца текстом, поведение слоя «Резерв» за границей решено отдельным правилом с обоснованием через инвариант AC-3.

**[решение] Куда ведёт шестерёнка в шапке до появления раздела `/settings`?**

**Решение владельца: шестерёнка открывает модал профиля**, а `app/components/profile_modal.py` признаётся файлом **прямых изменений** — добавляется второй Input-источник открытия; C-1 это не нарушает (C-1 про сайдбар и другие разделы). Отброшены: неактивная заглушка (мёртвый элемент на главном экране) и убрать иконку (отступление от принятого эскиза). Реализация: `id="dashboard-settings-cog"` в шапке → новый `Input("dashboard-settings-cog", "n_clicks")` в `handle_profile_modal` и ветка `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")` вместо жёсткого сравнения (:119). Ссылки на несуществующий `/settings` (404, P1 аудита) не создаётся; `title="Профиль и настройки"` честно называет, что откроется. Раздел `/settings` остаётся вне scope до его появления.
