# Solution v1: MoneyLayersService — композитная модель слоёв + шапка-вердикт + stacked-график

## Обзор решения

Вводим новый сервис-надстройку `MoneyLayersService` (`app/services/money_layers_service.py`), который композицией над `CalendarService` (прогноз остатка + перечень операций по дням), `BudgetReservationService` (бюджет целей и его использование), `CushionService` (порог/цель подушки) и `GoalService` (вехи целей) строит по дням горизонта декомпозицию прогнозного остатка на три слоя. Инвариант `free + payments + reserve == forecast_balance(D)` обеспечивается конструктивно: `reserve` и `payments` считаются независимо, `free` выводится вычитанием, а при нехватке остатка применяется детерминированный каскад сжатия слоёв (`free → 0`, затем `reserve`, затем `payments`) — сумма остаётся точно равна остатку в любом случае.

На стороне UI дашборд получает два новых блока в `app/components/dashboard.py`: `build_verdict_header()` (шапка-вердикт вместо `build_overview_cards`) и `build_layers_chart()` (Plotly `barmode="stack"` вместо `_build_daily_cashflow_chart`/`_build_yearly_cashflow_chart`). Схема данных оформляется TypedDict'ами в новом `app/schema/money_layers.py`; стили — в новом `app/assets/panel.css`, чтобы не разбухала `custom.css` и не задевались классы других страниц.

## Архитектура

### Компоненты

**1. `app/schema/money_layers.py` (новый) — контракт модели**

TypedDict'ы `DayLayers`, `UpcomingPayment`, `GoalMilestone`, `LayersVerdict`, `MoneyLayersData`; литералы `VerdictLevel = Literal["ok", "dip", "problem"]`, `LayerKey = Literal["free", "payments", "reserve"]`; константы цветов слоёв и порогов вердикта. Ноль зависимостей от Dash и от SQLAlchemy — чистые типы (стиль `app/schema/dashboard.py`).

**2. `app/services/money_layers_service.py` (новый) — ядро FR-1**

Единственный публичный метод `get_money_layers(user_id, reference_date=None) -> MoneyLayersData`. Внутри — приватные шаги:

- `_horizon(reference_date)` → `(start=reference_date, end=последний день месяца reference_date)`;
- `_forecast_balances()` → делегат в `CalendarService.calculate_daily_balances(user_id, start, end)` — единственный источник прогнозного остатка (гарантия AC-3 по построению);
- `_collect_upcoming_payments()` → делегат в `CalendarService.get_all_transactions_for_period(user_id, start, end)`, фильтр «расходных» типов (`expense`, `savings_reserve`, `savings_contribution`; `transfer` игнорируется, `adjustment` с отрицательным amount трактуется как платёж — та же классификация, что в `DashboardService._get_daily_income_expense`), отброс `is_skipped`; результат — отсортированный список `UpcomingPayment` (дата, сумма, описание, признак регулярности, категория);
- `_payments_tail_by_day()` → суффиксные суммы: `payments(D) = Σ amount платежей с датой в (D, end]`. Именно суффикс, а не префикс, даёт «таяние» слоя: чем ближе конец месяца, тем меньше платежей впереди; на последнем дне месяца `payments = 0`. Платежи с датой ровно D не считаются «впереди» — они уже вычтены из `balance(D)` кассовым календарём (это ключ к инварианту без двойного счёта);
- `_reserve_by_day()` → `reserve(D) = cushion_target + goals_reserve_in_balance(D)`, где `goals_reserve_in_balance(D)` — часть месячного бюджета целей, которая на день D **ещё физически лежит в остатке**: `max(0, monthly_budget − used_budget − Σ SAVINGS_RESERVE/CONTRIBUTION с датой в (D, end])`. Обоснование: `calculate_daily_balances` уже вычитает `SAVINGS_RESERVE`/`SAVINGS_CONTRIBUTION` из остатка (см. `_get_daily_changes`, `_get_recurring_daily_changes`), поэтому уже перечисленные в цели деньги нельзя резервировать повторно, а будущие резервы этого месяца сидят в слое «Платежи» (они попадают в `_collect_upcoming_payments` как расходные типы) — двойного счёта нет ни там, ни там;
- `_split_day()` → каскад: `free = balance − payments − reserve`; если `free < 0` — `free = 0`, дефицит `d = payments + reserve − balance` гасится сначала из `reserve` (`reserve -= min(reserve, d)`), затем из `payments`; если и после этого `balance < 0` — `free = balance` (отрицательное), `payments = reserve = 0`. В любой ветке `free + payments + reserve == balance` (проверяется assert'ом-инвариантом в тестах для всех веток);
- `_build_verdict()` → `LayersVerdict` из среза «сегодня» и минимума слоя «Свободно» по горизонту;
- `_goal_milestones()` → активные цели с `target_date` в горизонте (+ «за краем окна» — ближайшая цель после `end`, для правого края графика как в эскизе).

Сервис не знает о Dash (C-2), возвращает `Decimal` для денег, ничего не пишет в БД (нет `flush()`/`commit()` вообще — read-only модель), не меняет ни одного существующего метода (C-3).

**3. `app/components/dashboard.py` (изменяется) — FR-2, FR-3, FR-4, FR-5, FR-6**

- `build_verdict_header(data: MoneyLayersData, profile: UserProfile) -> html.Div` — шапка-вердикт. Вытесняет `build_overview_cards()` (удаляется вместе с `_build_kpi_card()` — оба больше нигде не используются).
- `build_layers_chart(data: MoneyLayersData) -> dbc.Card` — stacked-график. Вытесняет `_build_daily_cashflow_chart()` и `_build_yearly_cashflow_chart()` (удаляются).
- `_build_payments_tooltip(data)` / `_build_layer_legend(data)` — внешняя (вне поля графика) HTML-легенда с `dbc.Tooltip` на каждый слой — учитывает не-блокирующую заметку vision-критика «легенду вынести из поля» и решает FR-4 надёжнее, чем hover внутри Plotly-легенды (Plotly не даёт кастомный тултип на элемент легенды).
- `_build_verdict_empty_state()` / `_build_chart_empty_state()` — FR-6.
- `_load_dashboard_components()` — переписывается: вызов `MoneyLayersService.get_money_layers()` вместо `get_overview_metrics` + `get_daily_cashflow`/`get_yearly_cashflow`; возвращаемый tuple меняет состав (см. «Ключевые интерфейсы»).
- Callback'и: `load_dashboard_data` / `refresh_dashboard_after_crud` меняют Output-ID (`dashboard-verdict-header`, `dashboard-layers-chart`); `open_create_from_chart` перепривязывается на новый `id="dashboard-layers-chart-graph"` и берёт дату из `customdata` (в stacked-графике X — даты, не номера дней); clientside-callback «Сверка» перевешивается с `open-recon-from-dashboard-kpi-btn` на `open-recon-from-dashboard-verdict-btn` (FR-5, AC-6).

**4. `app/assets/panel.css` (новый) — стили щитка**

Классы `pnl-*` (`pnl-breaker`, `pnl-amount`, `pnl-chip`, `pnl-breadcrumb`, `pnl-who`, `pnl-meter`, `pnl-legend`) — перенос эскиза `v3.html` на CSS-переменные проекта (`--color-primary`, `--color-secondary`, `--color-warning`, `--color-text-*`). Отдельный файл, а не правка `custom.css`: `custom.css` шарится всеми страницами, а `.kpi-*` правила в ней остаются нужны (используются на других страницах? — проверяется на шаге 8 плана; если нет — удаляются).

### Диаграмма взаимодействия

```
                        ┌────────────────────────────────────────┐
                        │  app/components/dashboard.py           │
                        │  load_dashboard_data (callback)        │
                        │           │                            │
                        │           ▼                            │
                        │  _load_dashboard_components()          │
                        └───────────┬────────────────────────────┘
                                    │ get_money_layers(user_id)
                                    ▼
                 ┌──────────────────────────────────────────────┐
                 │  MoneyLayersService  (НОВЫЙ, read-only)      │
                 │                                              │
                 │  _horizon()      today .. end_of_month       │
                 │  _forecast_balances() ───────────────┐       │
                 │  _collect_upcoming_payments() ───────┼───┐   │
                 │  _reserve_by_day() ──────────┐       │   │   │
                 │  _split_day()  free = bal − pay − res│   │   │
                 │  _build_verdict()            │       │   │   │
                 │  _goal_milestones() ─────┐   │       │   │   │
                 └──────────────────────────┼───┼───────┼───┼───┘
                                            │   │       │   │
        ┌───────────────────┬───────────────┘   │       │   │
        ▼                   ▼                    ▼      ▼   ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│ GoalService  │  │ CushionService   │  │ CalendarService          │
│ get_all_by_  │  │ get_settings()   │  │ calculate_daily_balances │
│ user(ACTIVE) │  │ → cushion target │  │ get_all_transactions_    │
└──────────────┘  └──────────────────┘  │   for_period             │
                  ┌──────────────────┐  └──────────────────────────┘
                  │ BudgetReservation│              │
                  │ Service          │              ▼
                  │ get_settings()   │      RecurringService
                  │ get_budget_prog. │      (виртуальные instances)
                  └──────────────────┘
                     ↑ ни один существующий метод не меняется (C-3)

Возврат:  MoneyLayersData ─┬─► build_verdict_header()  → «Свободно сегодня: N ₽»
                           ├─► build_layers_chart()    → stacked bars + вехи + сегодня + min
                           └─► _build_layer_legend()   → dbc.Tooltip со списком платежей (FR-4)
```

## Файловая структура

```
app/schema/money_layers.py            — НОВЫЙ. TypedDict'ы модели слоёв, литералы вердикта,
                                        константы цветов LAYER_COLORS и порогов вердикта.
app/services/money_layers_service.py  — НОВЫЙ. MoneyLayersService: композиция над Calendar/
                                        Cushion/BudgetReservation/Goal сервисами; FR-1.
app/assets/panel.css                  — НОВЫЙ. Стили шапки-вердикта и блока графика (pnl-*).

app/schema/__init__.py                — реэкспорт новых типов (стиль файла: import + __all__).
app/services/__init__.py              — реэкспорт MoneyLayersService и новых типов.
app/components/dashboard.py           — УДАЛЯЮТСЯ: build_overview_cards, _build_kpi_card,
                                        build_cashflow_chart, _build_daily_cashflow_chart,
                                        _build_yearly_cashflow_chart, build_statistics_card,
                                        create_ai_assistant_card, create_exchange_card,
                                        build_recent_transactions_card (мёртвый код).
                                        ДОБАВЛЯЮТСЯ: build_verdict_header, build_layers_chart,
                                        _build_layer_legend, _build_payments_tooltip,
                                        _build_verdict_empty_state, _build_chart_empty_state.
                                        МЕНЯЮТСЯ: create_dashboard_layout (новые id, снят
                                        period-switcher), _load_dashboard_components,
                                        load_dashboard_data, refresh_dashboard_after_crud,
                                        open_create_from_chart, clientside «Сверка».
app/assets/custom.css                 — чистка: #dashboard-overview-cards, .db-period-switcher,
                                        .kpi-* (если не используются вне дашборда).

tests/test_money_layers_service.py    — НОВЫЙ. Инвариант AC-3, «таяние», граница месяца,
                                        пустая база, каскад дефицита, вердикт, вехи.
tests/test_dashboard_callbacks.py     — обновление контрактных тестов (число Output'ов).
tests/test_dashboard_service.py       — БЕЗ изменений (C-3: DashboardService не тронут).
```

## Ключевые интерфейсы

```python
# app/schema/money_layers.py

from datetime import date
from decimal import Decimal
from typing import Literal, TypedDict

LayerKey = Literal["free", "payments", "reserve"]
"""Ключ слоя декомпозиции остатка."""

VerdictLevel = Literal["ok", "dip", "problem"]
"""Уровень вердикта шапки: порядок / впереди просадка / проблема."""

LAYER_COLORS: dict[LayerKey, str] = {
    "free": "#2ecc71",      # Свободно — зелёный (эскиз v3, --free)
    "payments": "#f0b775",  # Платежи — оранжевый (эскиз v3, --promised)
    "reserve": "#3498db",   # Резерв — синий (эскиз v3, --reserve)
}
"""Цвета слоёв графика. Единственный источник правды (см. STATUS_COLORS-паттерн)."""

LAYER_LABELS: dict[LayerKey, str] = {
    "free": "Свободно",
    "payments": "Платежи",
    "reserve": "Резерв целей и подушки",
}
"""Подписи слоёв в легенде (финальная формулировка design.md)."""

VERDICT_TEXTS: dict[VerdictLevel, str] = {
    "ok": "Всё в порядке",
    "dip": "Впереди просадка",
    "problem": "Проблема",
}
"""Текст цветового вердикта шапки (FR-2)."""

VERDICT_COLORS: dict[VerdictLevel, str] = {
    "ok": "#2ecc71",
    "dip": "#f39c12",
    "problem": "#e74c3c",
}
"""Цвет сигнальной шины и чипа вердикта."""

DIP_THRESHOLD = Decimal("5000")
"""Минимум слоя «Свободно» ниже этого порога — вердикт «впереди просадка».
Согласован с BALANCE_ATTENTION_THRESHOLD (app/schema/dashboard.py)."""


class DayLayers(TypedDict):
    """Декомпозиция прогнозного остатка одного дня на три слоя.

    Инвариант: free + payments + reserve == forecast_balance (AC-3).

    Attributes:
        date: Дата дня горизонта.
        free: Слой «Свободно» — реально доступные деньги.
        payments: Слой «Платежи» — уйдут на запланированные платежи
            в интервале (date, конец месяца].
        reserve: Слой «Резерв» — цель подушки + неизрасходованный
            бюджет целей, ещё лежащий в остатке.
        forecast_balance: Прогнозный остаток из CalendarService.
        is_past: True для дней до reference_date (в горизонте не бывает,
            поле для будущих расширений горизонта в куске 2).
    """

    date: date
    free: Decimal
    payments: Decimal
    reserve: Decimal
    forecast_balance: Decimal
    is_past: bool


class UpcomingPayment(TypedDict):
    """Предстоящий платёж для слоя «Платежи» и тултипа легенды (FR-4).

    Attributes:
        date: Дата платежа.
        amount: Сумма (положительное число).
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

    Attributes:
        goal_id: ID цели.
        name: Название цели.
        target_date: Дата достижения.
        target_amount: Целевая сумма.
        progress_percent: Прогресс, 0..100.
        beyond_horizon: True — цель за правым краем окна
            (рисуется стрелкой у края, как в эскизе v3).
    """

    goal_id: int
    name: str
    target_date: date
    target_amount: Decimal
    progress_percent: float
    beyond_horizon: bool


class LayersVerdict(TypedDict):
    """Вердикт шапки — срез модели на сегодня + минимум по горизонту (FR-2).

    Attributes:
        level: Уровень вердикта (ok / dip / problem).
        text: Готовый текст вердикта («Всё в порядке» и т.п.).
        free_today: Слой «Свободно» на reference_date — главное число шапки.
        balance_today: Прогнозный остаток на reference_date (разбор).
        payments_today: Слой «Платежи» на reference_date (разбор).
        reserve_today: Слой «Резерв» на reference_date (разбор).
        min_free: Минимальное значение слоя «Свободно» по горизонту.
        min_free_date: Дата этого минимума.
    """

    level: VerdictLevel
    text: str
    free_today: Decimal
    balance_today: Decimal
    payments_today: Decimal
    reserve_today: Decimal
    min_free: Decimal
    min_free_date: date


class MoneyLayersData(TypedDict):
    """Полный результат модели FR-1 — единый источник для шапки и графика.

    Attributes:
        days: Декомпозиция по дням горизонта (reference_date..конец месяца).
        verdict: Вердикт и срез «сегодня».
        upcoming_payments: Платежи горизонта для тултипа легенды (FR-4).
        milestones: Вехи целей для оси времени (FR-3).
        reference_date: Дата отсчёта («сегодня»).
        horizon_end: Последний день горизонта (конец календарного месяца).
        cushion_target: Цель подушки — расшифровка слоя «Резерв».
        goals_reserve_today: Часть слоя «Резерв» от бюджета целей на сегодня.
        is_empty: True — данных нет вообще (FR-6: пустое состояние).
    """

    days: list[DayLayers]
    verdict: LayersVerdict
    upcoming_payments: list[UpcomingPayment]
    milestones: list[GoalMilestone]
    reference_date: date
    horizon_end: date
    cushion_target: Decimal
    goals_reserve_today: Decimal
    is_empty: bool
```

```python
# app/services/money_layers_service.py

class MoneyLayersService:
    """Модель «свободно / платежи / резерв» по дням (FR-1).

    Read-only надстройка: композиция над CalendarService (прогнозный
    остаток и перечень операций), BudgetReservationService (бюджет целей),
    CushionService (цель подушки) и GoalService (вехи целей). Ни одного
    существующего метода не меняет, в БД не пишет (C-3, C-4).

    Инвариант декомпозиции: для каждого дня D горизонта
    free(D) + payments(D) + reserve(D) == CalendarService.balance(D) (AC-3).
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
        """Строит модель слоёв на горизонт «сегодня .. конец месяца».

        Args:
            user_id: ID пользователя.
            reference_date: Дата отсчёта (по умолчанию date.today()).

        Returns:
            MoneyLayersData: Дни горизонта, вердикт, платежи, вехи целей.

        Note:
            Никогда не бросает при отсутствии данных — возвращает
            корректную «пустую» модель с is_empty=True (FR-6).
            Сбои частей модели (подушка, бюджет целей) деградируют
            fail-open с логом logger.opt(exception=True) (NFR-2).
        """

    # --- Приватные шаги ---

    def _horizon(self, reference_date: date) -> tuple[date, date]:
        """Границы горизонта: (reference_date, последний день его месяца) (C-5)."""

    def _collect_upcoming_payments(
        self, user_id: int, start: date, end: date
    ) -> list[UpcomingPayment]:
        """Собирает расходные операции горизонта (регулярные + разовые).

        Классификация типов повторяет DashboardService._get_daily_income_expense:
        expense / savings_reserve / savings_contribution → платёж;
        adjustment с amount < 0 → платёж на abs(amount);
        transfer и income → не платежи. Пропущенные (is_skipped) отбрасываются.
        """

    def _payments_tail_by_day(
        self, payments: list[UpcomingPayment], start: date, end: date
    ) -> dict[date, Decimal]:
        """Суффиксные суммы платежей: {D: Σ платежей в (D, end]}.

        Строго «после D» — платежи с датой ровно D уже вычтены из
        forecast_balance(D) кассовым календарём (иначе двойной счёт).
        Даёт «таяние» слоя: payments(end) == 0.
        """

    def _reserve_by_day(
        self,
        user_id: int,
        payments: list[UpcomingPayment],
        start: date,
        end: date,
        cushion_target: Decimal,
        goals_budget_unused: Decimal,
    ) -> dict[date, Decimal]:
        """Слой «Резерв» по дням: подушка + бюджет целей, ещё лежащий в остатке.

        goals_reserve(D) = max(0, goals_budget_unused
                               − Σ savings_* платежей в (D, end])
        — будущие перечисления в цели живут в слое «Платежи», уже
        перечисленные вычтены из остатка кассовым календарём.
        """

    def _split_day(
        self, balance: Decimal, payments: Decimal, reserve: Decimal
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Каскад сжатия слоёв, сохраняющий инвариант суммы (AC-3).

        1. free = balance − payments − reserve; если free >= 0 — готово.
        2. Иначе free = 0, дефицит гасится из reserve, затем из payments.
        3. Если balance < 0 — free = balance, payments = reserve = 0.

        Returns:
            tuple[Decimal, Decimal, Decimal]: (free, payments, reserve),
                сумма которых равна balance при любом входе.
        """

    def _build_verdict(
        self, days: list[DayLayers], reference_date: date
    ) -> LayersVerdict:
        """Вердикт по срезу «сегодня» и минимуму слоя «Свободно».

        Уровни: problem — free_today <= 0 или min_free < 0;
        dip — min_free < DIP_THRESHOLD (5000 ₽);
        ok — иначе.
        """

    def _goal_milestones(
        self, user_id: int, start: date, end: date
    ) -> list[GoalMilestone]:
        """Вехи активных целей: внутри горизонта + ближайшая за его краем."""
```

```python
# app/components/dashboard.py  — новые публичные строители UI

def build_verdict_header(
    data: MoneyLayersData,
    profile: UserProfile,
) -> html.Div:
    """Шапка-вердикт «Свободно сегодня: N ₽» (FR-2).

    Состав: метка «Свободно сегодня», сумма (54px, tabular-nums),
    чип вердикта с точкой, разбор «баланс − платежи − резерв целей»,
    справа — аватар с именем, кнопка «Сверка» (FR-5) и иконка настроек.
    Сигнальная шина слева окрашена по verdict['level'].
    Не дверь-переход: клика по шапке нет (design.md).

    Args:
        data: Модель слоёв из MoneyLayersService.
        profile: Профиль пользователя (имя, avatar_id).

    Returns:
        html.Div с классом pnl-breaker.
    """


def build_layers_chart(data: MoneyLayersData) -> dbc.Card:
    """График полос: стопка Свободно/Платежи/Резерв по дням (FR-3).

    Три go.Bar в barmode="stack" (порядок снизу вверх: free, payments,
    reserve), вертикальная линия «сегодня», маркер минимума слоя
    «Свободно», вехи целей аннотациями на оси времени. Легенда Plotly
    отключена (showlegend=False) — вынесена в HTML-легенду с тултипами
    (заметка vision-критика + FR-4).

    Args:
        data: Модель слоёв из MoneyLayersService.

    Returns:
        dbc.Card с dcc.Graph(id="dashboard-layers-chart-graph") либо
        пустым состоянием при data['is_empty'] (FR-6).
    """


def _build_layer_legend(data: MoneyLayersData) -> html.Div:
    """HTML-легенда графика с тултипами-пояснениями слоёв (FR-4).

    Три элемента (цветной квадрат + подпись) с dbc.Tooltip:
    - «Платежи» → список конкретных платежей с датами
      («Аренда · 25 августа · −30 000 ₽», до 8 строк + «и ещё N»);
    - «Свободно» → «Остаток минус платежи до конца месяца и резерв»;
    - «Резерв целей и подушки» → расшифровка суммами.
    """


def _load_dashboard_components(period_state: dict | None) -> tuple:
    """Единая точка загрузки данных и построения UI дашборда.

    Returns:
        tuple: (verdict_header, layers_chart, recent, upcoming, cushion)
            — вместо прежних (cards, chart, stats, recent, upcoming, cushion).
    """
```

## Модель данных

Схема БД не меняется (C-4) — проверено: всё сырьё уже есть.

| Что нужно модели | Откуда берётся | Достаточность |
|---|---|---|
| Прогнозный остаток по дням | `CalendarService.calculate_daily_balances` (`users.starting_balance` + `transactions`) | достаточно |
| Платежи горизонта (регулярные + разовые) с описаниями | `CalendarService.get_all_transactions_for_period` → `TransactionInfo` (есть `description`, `category_name`, `is_recurring`, `is_skipped`) | достаточно |
| Цель подушки | `users.cushion_target` через `CushionService.get_settings` | достаточно |
| Бюджет целей и его использование | `users.monthly_savings_budget`, `goal_contributions` через `BudgetReservationService.get_settings/get_budget_progress` | достаточно |
| Вехи целей | `goals.target_date`, `target_amount`, `current_amount`, `status` через `GoalService.get_all_by_user(ACTIVE)` | достаточно |
| Аватар и имя для шапки | `users.avatar_id`, `users.name` через `OnboardingService.get_profile` | достаточно |

**Вывод по C-4:** миграции не нужны, отдельного решения об изменении схемы не требуется. Единственная семантическая тонкость, потребовавшая проектного решения (не схемы): `SAVINGS_RESERVE`/`SAVINGS_CONTRIBUTION` уже вычитаются из прогнозного остатка (`CalendarService._get_daily_changes`, `_get_recurring_daily_changes`), поэтому «резерв целей» в слое `reserve` — только *неперечисленная* часть месячного бюджета, а будущие перечисления живут в слое `payments`. Иначе те же деньги были бы посчитаны дважды и инвариант AC-3 сломался бы.

**Пример инварианта** (сегодня 22 авг, конец месяца 31 авг, подушка 50 000, бюджет целей 15 000 не израсходован, платежи: аренда 30 000 (25 авг), коммуналка 6 200 (28 авг)):

| D | balance | payments (в (D, 31 авг]) | reserve | free |
|---|---|---|---|---|
| 22 авг | 101 200 | 36 200 | 65 000 | 0 (каскад: дефицит 0) |
| 25 авг | 71 200 | 6 200 | 65 000 | 0 |
| 28 авг | 65 000 | 0 | 65 000 | 0 |
| 31 авг | 65 000 | 0 | 65 000 | 0 |

Во всех строках сумма слоёв == balance (AC-3), `payments` тает до нуля к концу месяца (FR-1 «слой тает»).

## Обработка ошибок

Три уровня, по образцу существующего `PurchaseRecommendationService.get_safe_dates_map` (fail-open + `logger.opt(exception=True)`):

1. **Внутри сервиса — fail-open по компонентам.** Сбой `CushionService.get_settings` → `cushion_target = Decimal("0")` + `logger.opt(exception=True).warning(...)`; сбой `BudgetReservationService` → `goals_budget_unused = 0`; сбой `GoalService` → `milestones = []`. Модель остаётся консистентной (инвариант AC-3 сохраняется, т.к. `free` выводится вычитанием), пользователь видит рабочий дашборд с усечённым резервом, а не «Ошибка загрузки». Сбой `CalendarService.calculate_daily_balances` — не глотается: без остатка модели нет, исключение всплывает.
2. **На границе горизонта.** `_horizon` для последнего дня месяца даёт горизонт из одного дня — валидный вход для `calculate_daily_balances` (`start == end`, `ValueError` только при `start > end`). Отдельно проверяется февраль/31-е (`monthrange`).
3. **В callback'ах Dash.** `load_dashboard_data` сохраняет текущий контракт: `try/except` → `dbc.Alert("Не удалось загрузить данные...")` во все Output'ы; лог заменяется на `logger.opt(exception=True).error(...)` вместо текущего `logger.error(f"...{e}")` (NFR-2 — сейчас трейсбека нет). `refresh_dashboard_after_crud` — `PreventUpdate` после лога, как сейчас.

**Пустое состояние (FR-6, AC-5):** `is_empty=True`, когда нет ни операций горизонта, ни ненулевого остатка, ни целей, ни подушки. Шапка тогда рендерит `_build_verdict_empty_state()`: «Пока нечего показать» + подсказка «Добавьте первую операцию или сверьте баланс» + кнопка «Сверка». График рендерит `_build_chart_empty_state()` — вместо `dcc.Graph` отдаётся `html.Div` с иконкой и текстом, то есть Plotly вообще не вызывается — артефакты осей −1..1 и «50.001k» физически невозможны (AC-5). Дополнительно, для непустых, но малых данных, оси фиксируются: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)`, `xaxis=dict(tickformat="%-d %b", dtick=86400000*3, tickangle=0)` — против склеек подписей на 31-дневном горизонте.

## План реализации

1. **`app/schema/money_layers.py`** — TypedDict'ы, литералы, константы `LAYER_COLORS`/`LAYER_LABELS`/`VERDICT_TEXTS`/`VERDICT_COLORS`/`DIP_THRESHOLD`. Реэкспорт в `app/schema/__init__.py`.
2. **`app/services/money_layers_service.py`** — `MoneyLayersService` с `get_money_layers()` и приватными шагами. Реэкспорт в `app/services/__init__.py`.
3. **`tests/test_money_layers_service.py`** — тесты до UI (модель — контракт): инвариант AC-3 на всех днях наполненной базы; «таяние» (`payments` монотонно не растёт, `payments(end) == 0`); граница месяца (reference_date = последний день → горизонт 1 день; февраль; 31-е); пустая база (`is_empty=True`, нули, без исключений); каскад дефицита (три ветки `_split_day` с assert суммы); отрицательный остаток; вердикт (три уровня на порогах 0 и 5000); вехи целей (в горизонте / за краем / нет целей); отсутствие двойного счёта `SAVINGS_RESERVE` в режиме `fixed_date`; fail-open при падении `CushionService` (monkeypatch). Даты — относительные (`date.today()` + хелперы `conftest.py`), без `pytest.skip` (KB `testing.md`).
4. **`app/assets/panel.css`** — стили `pnl-*` из эскиза v3 на переменных проекта; вертикальный ритм, `font-variant-numeric: tabular-nums` для сумм, `@media (prefers-reduced-motion: reduce)`.
5. **`build_verdict_header()` + `_build_verdict_empty_state()`** в `dashboard.py`; кнопка «Сверка» с новым id `open-recon-from-dashboard-verdict-btn`; иконка настроек — переиспользует существующий триггер профиля/настроек (проверить id в `profile_modal.py`, не изобретать новый).
6. **`build_layers_chart()` + `_build_layer_legend()` + `_build_payments_tooltip()` + `_build_chart_empty_state()`**; заметки vision-критика: легенда вне поля графика, ярлык минимума через `annotation` со сдвигом (`yshift`), чтобы не липнуть к тику даты.
7. **Переключение `_load_dashboard_components()` и callback'ов** на новую модель: новые Output-ID, снятие `period-switcher` и `dashboard-statistics-card` из layout, перепривязка `open_create_from_chart` и clientside «Сверка».
8. **Удаление мёртвого кода** в `dashboard.py` (список в «Файловой структуре») + чистка `custom.css` от `#dashboard-overview-cards`, `.db-period-switcher`, `.kpi-*` — предварительно `grep` по `app/` и `tests/` на использование вне дашборда.
9. **Обновление `tests/test_dashboard_callbacks.py`** — контрактные тесты числа/имён Output'ов `load_dashboard_data` (сейчас проверяется 7 значений и greeting-Output).
10. **Прогон** `pytest -q` (565+ зелёных), `black`, `flake8`; ручная проверка AC-1…AC-6 на наполненной и на чистой базе; замер времени загрузки дашборда (NFR-1).

## Зависимости

Новых библиотек нет. Всё делается на `plotly.graph_objs` (`go.Bar` + `barmode="stack"` — уже в стеке), `dash_bootstrap_components.Tooltip` (входит в dbc 1.x, уже зависимость), `calendar.monthrange` и `dateutil` (уже используются). Обоснование отказа от новых зависимостей: сама причина эпика — упрощение, а stacked bars — базовая возможность Plotly.

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Инвариант AC-3 расходится из-за двойного счёта `SAVINGS_RESERVE`/`SAVINGS_CONTRIBUTION` (они уже вычтены из остатка) | Высокая | Слой `reserve` считает только *неперечисленную* часть бюджета целей; будущие перечисления живут в `payments`. Тест «нет двойного счёта в режиме fixed_date» + параметризованный тест инварианта по всем дням |
| `free` уходит в минус при остатке ниже платежей+резерва — «сумма слоёв ≠ остаток» либо отрицательная полоса в стопке | Высокая | Детерминированный каскад `_split_day` (free→0, гасим reserve, затем payments); тест на все три ветки с assert суммы; вердикт «проблема» вместо тихого искажения |
| NFR-1: `get_all_transactions_for_period` тянет recurring-инстансы, а `calculate_daily_balances` внутри дважды ходит в `RecurringService` — деградация < 2 сек | Средняя | Горизонт сузился с 12 мес./года до ≤31 дня — работы меньше, чем у текущего `get_yearly_cashflow`. Один вызов `calculate_daily_balances` и один `get_all_transactions_for_period` на загрузку. Замер на шаге 10; при провале — общий кэш инстансов внутри одного `get_money_layers` (передавать список платежей в `_reserve_by_day`, что уже заложено в сигнатуре) |
| Удаление `period-switcher` ломает `dashboard-period` Store и `update_period_state`, а `Input("period-switcher","value")` в `load_dashboard_data` даст «nonexistent object» | Средняя | Убрать Input и callback `update_period_state` вместе с элементом; Store `dashboard-period` оставить (нужен `open_create_from_chart` для year/month), но заполнять из `load_dashboard_data`. Проверить `dash.Dash(suppress_callback_exceptions=...)` в `main.py` перед удалением |
| Тултип легенды (FR-4) hover-only — не работает на мобильных | Низкая (в scope) | `dbc.Tooltip` с `trigger="hover focus"` + элемент с `tabIndex=0`: доступно с клавиатуры. Полноценный touch — Epic-08 (out of scope, зафиксировано в design.md) |
| Аватар в шапке дублирует аватар в сайдбаре (C-1 запрещает трогать сайдбар) | Средняя | В куске 1 шапка рисует аватар как заявлено FR-2; дубль — осознанная временная цена, снимается в куске 3 (сайдбар → полоска-меню). Зафиксировать в осадке решений |
| «Доходы за месяц» молча теряется (FR-5) | Средняя | Решение принято явно: показатель **убирается** с дашборда — он не отвечает ни на один вопрос иерархии внимания и по design.md его проекция — карточка «Аналитика» (кусок 2, «цифра месяца»). Данные не пропадают: `CalendarService.get_month_summary` и раздел /analytics остаются. Записать в осадок решений эпика |
| Вехи целей загромождают 31-дневную ось | Средняя | Не более 3 вех внутри горизонта (ближайшие по `target_date`), остальные — сводкой «и ещё N целей» в тултипе «Резерв»; веха за краем — стрелка у правого края (эскиз v3) |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|---|---|---|---|
| FR-1.a | «Для каждого дня горизонта (текущий календарный месяц, начиная с сегодня) модель выдаёт декомпозицию прогнозного остатка на три слоя» | FR-1 | `MoneyLayersService.get_money_layers()` → `MoneyLayersData['days']: list[DayLayers]`; горизонт `_horizon()` = `(reference_date, monthrange-последний день)` | FR |
| FR-1.b | «*Свободно* — реально доступные деньги» | FR-1 | `DayLayers['free']` = `balance − payments − reserve` через `_split_day()` | FR |
| FR-1.c | «*Платежи* — деньги ещё на счету, но уйдут на уже запланированные платежи (регулярные + разовые предстоящие) до конца календарного месяца» | FR-1 | `_collect_upcoming_payments()` (регулярные + разовые из `CalendarService.get_all_transactions_for_period`) + `_payments_tail_by_day()` (суффиксная сумма в интервале (D, end]) | FR |
| FR-1.d | «слой "тает" по мере исполнения платежей и пересчитывается на границе месяца» | FR-1 | Суффиксная сумма даёт монотонное таяние, `payments(horizon_end) == 0`; `_horizon()` привязан к месяцу `reference_date` → пересчёт на границе. Тесты «таяние» и «граница месяца» (шаг 3) | FR |
| FR-1.e | «*Резерв* — резерв целей (бюджет накоплений) + подушка» | FR-1 | `_reserve_by_day()` = `cushion_target` (CushionService) + неизрасходованный `monthly_savings_budget` (BudgetReservationService), ещё лежащий в остатке | FR |
| FR-1.f | «Сумма трёх слоёв на день D равна прогнозному остатку на D (согласована с балансом кассового календаря)» | FR-1 | Конструктивно: `free` выводится вычитанием из `CalendarService.calculate_daily_balances`; `_split_day()` сохраняет сумму во всех трёх ветках | FR |
| FR-1.g | «Модель — единый источник для шапки, графика и (в куске 2) карточек щитка» | FR-1 | Один вызов `get_money_layers()` в `_load_dashboard_components()` кормит и `build_verdict_header()`, и `build_layers_chart()` | FR |
| FR-2.a | «Вверху дашборда: "Свободно сегодня: N ₽" (N — срез модели FR-1 на сегодня)» | FR-2 | `build_verdict_header()`: метка «Свободно сегодня» + `format_rub(verdict['free_today'])`; `free_today` = `days[0]['free']` | FR |
| FR-2.b | «цветовой вердикт состояния (порядок / впереди просадка / проблема)» | FR-2 | `VerdictLevel = Literal["ok","dip","problem"]`; `VERDICT_TEXTS` = «Всё в порядке» / «Впереди просадка» / «Проблема»; `VERDICT_COLORS` = `#2ecc71` / `#f39c12` / `#e74c3c`; пороги: `problem` при `free_today <= 0` или `min_free < 0`, `dip` при `min_free < 5000` (`DIP_THRESHOLD`), иначе `ok` | FR |
| FR-2.c | «краткий разбор "баланс − платежи − резерв"» | FR-2 | `pnl-breadcrumb`: «баланс {balance_today} − платежи {payments_today} − резерв целей {reserve_today}» (формат эскиза v3, `format_rub`) | FR |
| FR-2.d | «Справа — аватар пользователя и служебная иконка настроек» | FR-2 | `build_verdict_header(profile=...)`: `get_avatar_emoji(profile['avatar_id'])` + `profile['name']` в `pnl-avatar`; иконка-шестерёнка `pnl-cog` (bi-gear), привязана к существующему триггеру профиля | FR |
| FR-2.e | «Шапка не является дверью-переходом» | FR-2 | На контейнере `pnl-breaker` нет `dcc.Link`, `n_clicks`, `cursor: pointer`; кликабельны только кнопка «Сверка» и иконка настроек | FR |
| FR-2.f | «Шапка-вердикт **заменяет текущий ряд 4 KPI-карточек** (два "главных числа" рядом недопустимы)» | FR-2 | Удаляются `build_overview_cards()`, `_build_kpi_card()`, `build_statistics_card()`; `dashboard-overview-cards` и `dashboard-statistics-card` уходят из layout; на их место — `dashboard-verdict-header` | FR |
| FR-3.a | «Текущий график (grouped bars + линия баланса, протокол 0022) заменяется полностью» | FR-3 | Удаляются `_build_daily_cashflow_chart()`, `_build_yearly_cashflow_chart()`, `build_cashflow_chart()`; `dashboard-cashflow-chart` → `dashboard-layers-chart` | FR |
| FR-3.b | «стопка полос Свободно (зелёный) / Платежи (оранжевый) / Резерв (синий) по дням» | FR-3 | `barmode="stack"`, три `go.Bar`; `LAYER_COLORS`: free `#2ecc71` (зелёный), payments `#f0b775` (оранжевый, эскиз v3), reserve `#3498db` (синий); порядок снизу вверх free → payments → reserve (как в v3) | FR |
| FR-3.c | «вехи целей на оси времени» | FR-3 | `GoalMilestone` + аннотации Plotly (флажок ⚑, название, дата); ≤3 вехи в горизонте + стрелка «за краем окна» синим `#3498db` | FR |
| FR-3.d | «вертикальная линия "сегодня"» | FR-3 | `fig.add_vline` (или `add_shape` `yref="paper"`) на `reference_date`, `dash="dash"`, цвет `#2c3e50`, подпись «сегодня» — как в v3 | FR |
| FR-3.e | «маркер минимума остатка» | FR-3 | Маркер-кружок на `min_free_date` + аннотация `format_rub(min_free)`; плашка «⚠ Минимум свободного / {дата} — {сумма}» в свободной зоне | FR |
| FR-3.f | «График и шапка — единый визуальный блок: "свободно сегодня" есть срез графика на сегодня» | FR-3 | Одна модель на оба блока; `verdict['free_today'] == days[0]['free']` (тест); визуально `pnl-meter` примыкает к `pnl-breaker` (gap 16px, общая палитра) | FR |
| FR-4.a | «У легенды графика — пояснение с конкретикой: для "Платежей" — список предстоящих платежей с датами ("аренда 25 авг, коммуналка 28 авг…")» | FR-4 | `_build_payments_tooltip()`: `dbc.Tooltip` на элементе легенды «Платежи», строки «{описание} · {format_date_human(date)} · {format_rub(−amount)}», до 8 + «и ещё N» | FR |
| FR-4.b | «для остальных слоёв — что входит в слой» | FR-4 | Тултип «Свободно»: «Остаток минус платежи до конца месяца и резерв целей с подушкой». Тултип «Резерв целей и подушки»: «Подушка {cushion_target} + бюджет целей {goals_reserve_today}» | FR |
| FR-5.a | «Вход в "Сверку" с дашборда сохраняется (сейчас — кнопка на KPI-карточке баланса)» | FR-5 | Кнопка «Сверка» переезжает в правый блок шапки, новый id `open-recon-from-dashboard-verdict-btn`, тот же clientside `ClientsideFunction("triggers","timestamp_trigger")` → `open-recon-trigger`. Баннерная кнопка `open-recon-from-dashboard-banner-btn` не трогается | FR |
| FR-5.b | «Судьба показателя "Доходы за месяц" решается проектированием явно: сохранить в новом месте или убрать осознанно (не потерять молча)» | FR-5 | **Решение: убрать с дашборда осознанно.** Основание: не отвечает ни на один вопрос иерархии внимания design.md; его проекция — «цифра месяца» карточки «Аналитика» (кусок 2). Данные сохранны: `CalendarService.get_month_summary`, `DashboardService.get_overview_metrics` (сервис не удаляется — C-3), раздел /analytics. Запись в `memory/spec-context/epic-11.md` | FR |
| FR-6.a | «При нулевых данных (новый пользователь, 0 операций) шапка и график показывают спроектированное пустое состояние» | FR-6 | `MoneyLayersData['is_empty']`; `_build_verdict_empty_state()` («Пока нечего показать» + «Добавьте первую операцию или сверьте баланс» + кнопка «Сверка»), `_build_chart_empty_state()` | FR |
| FR-6.b | «без осей −1..1, склеек подписей и прочих артефактов деградации» | FR-6 | При `is_empty` Plotly не вызывается вовсе (`html.Div` вместо `dcc.Graph`) → оси −1..1 невозможны. Для непустых: `yaxis=dict(rangemode="tozero", tickformat=",.0f", separatethousands=True)` (нет «50.001k»), `xaxis=dict(tickformat="%-d %b", dtick=3 дня, tickangle=0)` (нет склеек на 31 дне) | FR |
| NFR-1 | «Загрузка дашборда с новой моделью и графиком — не медленнее текущего дашборда; ориентир < 2 секунд на локальной базе с наполненными данными» | NFR-1 | Горизонт ≤31 день вместо 12 мес./5 лет; один `calculate_daily_balances` + один `get_all_transactions_for_period` за загрузку; список платежей переиспользуется `_reserve_by_day()` (передаётся параметром, не запрашивается снова). Замер на шаге 10 плана | NFR |
| NFR-2 | «Сбои расчёта модели логируются через loguru с трейсбеком (`logger.opt(exception=True)` — идиома проекта, протокол 0027), не молча» | NFR-2 | `logger.opt(exception=True).warning(...)` в fail-open ветках сервиса (подушка, бюджет целей, цели) и `logger.opt(exception=True).error(...)` в `load_dashboard_data` / `refresh_dashboard_after_crud` вместо текущего `logger.error(f"...{e}")` | NFR |
| C-1 | «Остальные разделы (календарь, цели, операции, аналитика) и сайдбар в этом куске не трогаются. Таблицы операций, wishlist-виджет и карточка подушки на дашборде остаются как есть» | C-1 | Правки только в `dashboard.py`, `custom.css`, новых файлах. `dashboard-recent-transactions`, `dashboard-upcoming-transactions`, `build_wishlist_widget()`, `dashboard-cushion-card` остаются в layout и в возвращаемом tuple. `sidebar.py`, `calendar.py`, `goals.py`, `transactions.py`, `analytics.py` не меняются | C |
| C-2 | «Decimal для денег, session-контракт flush()/commit(), сервисы не знают о Dash» | C-2 | Все денежные поля TypedDict — `Decimal`; `MoneyLayersService` read-only (не вызывает `flush()`/`commit()` — писать нечего); импортов `dash`/`plotly` в сервисе и схеме нет | C |
| C-3 | «Существующее поведение сервисов не меняется — модель FR-1 строится надстройкой/композицией; полный прогон тестов (565 на 2026-08-21) остаётся зелёным» | C-3 | Ни один метод `CalendarService`/`DashboardService`/`CushionService`/`BudgetReservationService`/`GoalService` не редактируется — только вызывается. `test_dashboard_service.py` остаётся без правок. Правится только `test_dashboard_callbacks.py` (контракт callback'а, а не сервиса) | C |
| C-4 | «Схема БД не меняется» | C-4 | Проверено по таблице «Модель данных»: `users.starting_balance/cushion_target/monthly_savings_budget/avatar_id/name`, `transactions.*`, `goals.target_date/target_amount/current_amount/status`, `goal_contributions` — всё, что нужно, есть. Миграций нет, отдельного решения об изменении схемы не требуется | C |
| C-5.a | «Горизонт слоя "Платежи" — до конца календарного месяца» | C-5 | `_horizon()` → `end = date(y, m, monthrange(y, m)[1])`; `_payments_tail_by_day` не смотрит за `end`. Ограничение задокументировано в докстринге сервиса | C |
| C-5.b | «Механику "основного дохода" не реализовывать» | C-5 | Нет ни поля, ни ветвления по «основному доходу»; горизонт фиксирован календарным месяцем | C |
| AC-1 | «Наполненная база → видна шапка "Свободно сегодня: N ₽" с цветовым вердиктом и разбором, и N совпадает со значением слоя "Свободно" модели на сегодняшнюю дату (срез графика)» | AC-1 | `build_verdict_header()` рендерит `verdict['free_today']`; тест `verdict['free_today'] == days[0]['free']` и `days[0]['date'] == reference_date`; ручная проверка на наполненной базе (шаг 10) | AC |
| AC-2 | «Отображается график стопки трёх полос с легендой "Свободно / Платежи / Резерв", вехами целей, линией "сегодня" и маркером минимума; старый график доходы/расходы+баланс и ряд 4 KPI-карточек отсутствуют» | AC-2 | `build_layers_chart()` + `_build_layer_legend()`; физическое удаление `_build_daily_cashflow_chart`, `_build_yearly_cashflow_chart`, `build_cashflow_chart`, `build_overview_cards`, `_build_kpi_card`, `build_statistics_card` (шаг 8) | AC |
| AC-3 | «Для любого дня D горизонта сумма трёх слоёв модели равна прогнозному остатку на D из кассового календаря (CalendarService) — проверено unit-тестом» | AC-3 | Тест-инвариант в `tests/test_money_layers_service.py`: для всех `days` — `free + payments + reserve == forecast_balance`, и `forecast_balance == calculate_daily_balances()[date]`; отдельные кейсы: положительный/нулевой/отрицательный остаток, дефицитный каскад, режимы `fixed_date`/`from_balance` | AC |
| AC-4 | «Наведение/клик на пояснение легенды "Платежи" показывает список конкретных предстоящих платежей с датами до конца месяца» | AC-4 | `dbc.Tooltip(target="pnl-legend-payments", trigger="hover focus")` со строками из `upcoming_payments`; элемент легенды имеет `tabIndex=0` | AC |
| AC-5 | «Чистая база (онбординг пропущен, 0 операций) → шапка и график показывают осмысленное пустое состояние без артефактов (осей −1..1, "50.001k", склеек подписей)» | AC-5 | Ветка `is_empty` (Plotly не вызывается) + тест «пустая база → is_empty=True, все слои 0, исключений нет»; ручная проверка на чистой базе (шаг 10) | AC |
| AC-6 | «Вход в сверку с дашборда работает: модал сверки открывается и применяется, как до редизайна» | AC-6 | Кнопка `open-recon-from-dashboard-verdict-btn` → тот же clientside → `open-recon-trigger` → существующий `create_reconciliation_modal()` в `main.py` (не трогается); баннерный вход сохранён | AC |
| AC-7 | «Новая модель покрыта unit-тестами (включая границу месяца и "таяние" платежей); полный прогон pytest зелёный; black + flake8 без новых замечаний» | AC-7 | `tests/test_money_layers_service.py` (шаг 3, явные тесты границы месяца и таяния); шаг 10 — `pytest -q`, `black`, `flake8` | AC |
| Эскиз | «легенду графика вынести из поля» (заметка vision-критика) | memory/spec-context | `showlegend=False` в Plotly; HTML-легенда `_build_layer_legend()` под заголовком блока графика | Заметка |
| Эскиз | «ярлык минимума ("9 800 ₽") не ставить вплотную к тику даты» | memory/spec-context | Аннотация минимума со сдвигом (`yshift`/`ay`) и плашка «Минимум свободного» в свободной зоне поля, не под тиком | Заметка |
| Эскиз | «выровнять вертикальный ритм карточки "Цели"» | memory/spec-context | Не применимо к куску 1 (карточки-двери — кусок 2). Заметку оставить в осадке до куска 2 | Заметка |

## Blast Radius

### Прямые изменения (файлы которые будут изменены)

- `app/schema/money_layers.py` — НОВЫЙ: TypedDict'ы `DayLayers`/`UpcomingPayment`/`GoalMilestone`/`LayersVerdict`/`MoneyLayersData`, литералы `LayerKey`/`VerdictLevel`, константы `LAYER_COLORS`/`LAYER_LABELS`/`VERDICT_TEXTS`/`VERDICT_COLORS`/`DIP_THRESHOLD`.
- `app/services/money_layers_service.py` — НОВЫЙ: `MoneyLayersService.get_money_layers()` + приватные шаги (`_horizon`, `_collect_upcoming_payments`, `_payments_tail_by_day`, `_reserve_by_day`, `_split_day`, `_build_verdict`, `_goal_milestones`).
- `app/assets/panel.css` — НОВЫЙ: классы `pnl-*` (шапка-вердикт, блок графика, HTML-легенда).
- `app/schema/__init__.py` — реэкспорт новых типов и констант (+ `__all__`).
- `app/services/__init__.py` — реэкспорт `MoneyLayersService` и типов модели (+ `__all__`).
- `app/components/dashboard.py` — самый крупный blast: удаление 4 KPI-карточек и обоих старых графиков, добавление шапки-вердикта и stacked-графика, перекройка `create_dashboard_layout`, `_load_dashboard_components`, `load_dashboard_data`, `refresh_dashboard_after_crud`, `open_create_from_chart`, clientside «Сверка»; снятие `period-switcher` и `update_period_state`; удаление мёртвого кода (`create_ai_assistant_card`, `create_exchange_card`, `build_recent_transactions_card`, `build_cashflow_chart`).
- `app/assets/custom.css` — удаление `#dashboard-overview-cards .row`, `.db-period-switcher` (все 6 правил), `.kpi-card`/`.kpi-number`/`.kpi-title`/`.kpi-subtitle`/`.kpi-card-icon` — только после grep-проверки, что они не используются вне дашборда; правка `.db-page`/`.db-left-col` под новую сетку.
- `tests/test_money_layers_service.py` — НОВЫЙ: тесты FR-1/AC-3/AC-7.
- `tests/test_dashboard_callbacks.py` — обновление контрактных тестов: `TestCallbackContracts` парсит декоратор `load_dashboard_data` (проверяет `profile-updated` Input и greeting Output), `TestLoadDashboardDataGreeting.test_returns_seven_values_with_greeting_last` жёстко ждёт 7 значений — при новом составе tuple тест падает.

### Связанные файлы (могут быть затронуты)

- `app/main.py` — глобальные Store'ы (`open-recon-trigger`, `profile-updated`, `balance-toast-dismissed`) и `create_reconciliation_modal()`, от которых зависят шапка и баннер; проверить флаг `suppress_callback_exceptions` перед удалением `period-switcher` (иначе снятый Input даст ошибку на старте).
- `app/components/calendar.py` — второй потребитель `open-recon-trigger` (строки 1262–1309): контракт триггера менять нельзя, иначе сломается вход в сверку с календаря.
- `app/components/sidebar.py` — аватар и имя в сайдбаре: источник `OnboardingService.get_profile` и `get_avatar_emoji` тот же, что у шапки; C-1 запрещает правки, но визуальный дубль аватара нужно зафиксировать как осознанный.
- `app/components/profile_modal.py` — иконка настроек в шапке должна вести на существующий триггер профиля/настроек; проверить фактические id триггеров.
- `app/config/avatars.py` — `get_avatar_emoji()` для аватара в шапке.
- `app/components/wishlist.py` — `build_wishlist_widget()` вызывается прямо из `create_dashboard_layout`; при перекройке layout нельзя потерять этот вызов (C-1).
- `app/components/transaction_modals.py` — `create-modal`, `preselected-date`, `modal-source`: Output'ы `open_create_from_chart`, который перепривязывается на новый id графика; при смене X-оси на даты меняется парсинг клика.
- `app/services/dashboard_service.py` — НЕ меняется (C-3), но `get_overview_metrics`, `get_daily_cashflow`, `get_yearly_cashflow`, `get_cashflow_data` теряют вызывающего на дашборде: остаются в публичном API и под тестами, удалять нельзя.
- `app/assets/clientside_triggers.js` — namespace `triggers`, функции `timestamp_trigger` и `open_create_modal`: переиспользуются новыми id, сам файл не меняется.
- `tests/test_dashboard_service.py` — не должен требовать правок; если потребовал — признак нарушения C-3.
- `tests/test_bootstrap.py`, `tests/test_serializers.py` — smoke-тесты сборки layout/сериализации: могут поймать несериализуемые объекты или отсутствующие id в новом layout.
- `.obsidian-docs/knowledge-bank/modules/services.md`, `modules/schema.md`, `modules/ui-components.md`, `patterns/plotly-charts.md`, `architecture.md` — карта сервисов, схем, UI и Dual-Y-Axis паттерн (который перестаёт применяться на дашборде): обновление KB после реализации.
- `memory/spec-context/epic-11.md` — записать принятые в этом решении решения: судьба «Доходов за месяц» (убрать), достаточность схемы БД (миграции не нужны), дубль аватара до куска 3, семантика «резерв только неперечисленный».

### Проверить после реализации

- [ ] `pytest -q` — 565 прежних тестов зелёные + новые из `test_money_layers_service.py`; ни одного правленого теста в `test_dashboard_service.py` (доказательство C-3).
- [ ] `grep -rn "build_overview_cards\|_build_kpi_card\|_build_daily_cashflow_chart\|_build_yearly_cashflow_chart\|build_cashflow_chart\|build_statistics_card\|dashboard-overview-cards\|dashboard-statistics-card\|period-switcher" app tests` — по дашборду пусто (остаются только `analytics-period-switcher` и `an-period-switcher` в analytics).
- [ ] Открыть `/` и `/dashboard` в браузере: нет ошибок в консоли Dash про nonexistent object `period-switcher`, `dashboard-overview-cards`, `dashboard-statistics-card`, `daily-cashflow-chart`.
- [ ] AC-1 вручную: число в шапке == высота зелёной полосы «сегодня» на графике (hover) и == `days[0]['free']` в python-консоли.
- [ ] AC-3 вручную (сверх теста): на наполненной базе для 3 произвольных дней сумма слоёв из hover == остаток того же дня в кассовом календаре `/calendar`.
- [ ] AC-4: hover и Tab-фокус на элементе легенды «Платежи» → список платежей с датами; проверить месяц без платежей (тултип не пустой, а объясняющий).
- [ ] AC-5: чистая база (новый профиль, 0 операций) — шапка и график в пустом состоянии, в DOM нет `dcc.Graph` от графика слоёв, нет осей −1..1.
- [ ] AC-6: кнопка «Сверка» в шапке и кнопка в баннере нулевого баланса обе открывают модал сверки; сверка применяется; вход с `/calendar` не сломан.
- [ ] Граница месяца: запустить с `reference_date` = последний день месяца (через unit-тест) и в UI 1-го числа — горизонт и «таяние» корректны, ошибок `start_date > end_date` нет.
- [ ] NFR-1: замер времени рендера дашборда на наполненной базе (лог/DevTools) — < 2 сек и не хуже прежнего.
- [ ] NFR-2: искусственно уронить `CushionService.get_settings` (monkeypatch) — в логах трейсбек через `logger.opt(exception=True)`, дашборд рендерится с `reserve` без подушки.
- [ ] `black --check app tests` и `flake8 app tests` — без новых замечаний.
- [ ] Wishlist-виджет, таблицы недавних/предстоящих операций и карточка подушки на месте и живые (C-1).
