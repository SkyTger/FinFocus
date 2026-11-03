"""Контракт модели «свободно / платежи / резерв» по дням (EPIC-11, кусок 1).

Note:
    Контракт спроектирован под кусок 1 (шапка + график полос).
    Стабильность до куска 2 (карточки-двери) не гарантируется —
    осознанное решение, зафиксировано в memory/spec-context/epic-11.md.

Note:
    Цветового вердикта состояния (ok/dip/problem) в контракте НЕТ —
    решение владельца 2026-08-24 (memory/spec-context/epic-11.md, п. 3а).
    Протокол 0033 (2026-11-03) пересмотрел это частично: появился факт
    «не хватает N ₽ до <дата>» (shortfall / shortfall_date) — это знак
    числа, а не порог. Маркер минимума «Свободно» (FR-3.e) заменён
    узким местом (bottleneck_date / bottleneck_available): по новой
    формуле «Свободно» от дня к дню только растёт, его минимум всегда
    сегодня.
"""

from datetime import date
from decimal import Decimal
from typing import Literal, NamedTuple, TypedDict

LayerKey = Literal["free", "payments", "reserve"]
"""Ключ слоя декомпозиции прогнозного остатка."""

WINDOW_DAYS = 45
"""Длина окна оси графика в днях (включая сегодня).

Соответствует принятому эскизу .visual/finfocus-panel-dashboard/v3.html
(22 авг — 5 окт 2026). Горизонт РАСЧЁТА длиннее оси — см. HORIZON_CAP_DAYS
и MoneyLayersService._horizons (C-5 «Платежи до конца месяца» отменён
протоколом 0033).
"""

HORIZON_CAP_DAYS = 90
"""Предел горизонта расчёта H в днях (включая сегодня): H <= ref + 89.

H = дата первого дохода строго после правого края оси, но не дальше
этого предела. Прогноз остатка считается до H, чтобы полосы последних
дней оси видели платежи за краем оси до ближайшего поступления —
иначе обрыв «на границе месяца» переехал бы на правый край графика.
"""

MAX_LIMIT_PERIODS = 3
"""Максимум периодов лимита трат на день (протокол 0033)."""

MAX_MILESTONES_IN_WINDOW = 3
"""Максимум вех целей внутри окна (ближайшие по target_date).

Остальные попадают сводкой «и ещё N целей» в тултип слоя «Резерв»:
45-дневная ось не должна зарастать флажками (заметка vision-критика
про вертикальный ритм). Плюс не более одной вехи beyond_window.
"""

MAX_X_TICKS = 11
"""ПОТОЛОК числа подписей на оси X — не цель, а верхняя граница.

Переименована из TARGET_X_TICKS (critique-v3, замечание №5): прежнее
имя обещало результат, которого функция не давала (round(45/11) = 4 →
12 подписей при заявленных 11). Теперь _axis_tickvals использует
k = ceil(len / MAX_X_TICKS), что гарантирует len(tickvals) <= MAX_X_TICKS.

Почему потолок, а не цель: в эскизе v3 ровно 11 подписей, но с
НЕРАВНОМЕРНЫМ шагом — 22/25/28 авг, 1/5/10/15/20/25/30 сент, 5 окт
(v3.html:575-596), то есть семантически значимые даты, а не сетка.
Равномерная сетка эскиз не воспроизводит в принципе; воспроизводима
только плотность подписей, и её честнее ограничить сверху.
"""

LAYER_COLORS: dict[LayerKey, str] = {
    "free": "#2ecc71",  # Свободно — зелёный (эскиз v3)
    "payments": "#f0b775",  # Платежи — оранжевый приглушённый (эскиз v3)
    "reserve": "#3498db",  # Резерв — синий (эскиз v3)
}
"""Цвета слоёв графика — единственный источник правды (паттерн STATUS_COLORS)."""

LAYER_LABELS: dict[LayerKey, str] = {
    "free": "Свободно",
    "payments": "Платежи",
    "reserve": "Резерв целей",
}
"""Подписи слоёв в HTML-легенде (формулировки эскиза v3)."""


class Horizons(NamedTuple):
    """Границы модели — почему они такие, см. докстринг _horizons.

    Attributes:
        collect_start: Левая граница ЕДИНСТВЕННОГО сбора операций —
            начало календарного месяца reference_date. Нужна потому,
            что consumed(reference_date) требует savings-операций,
            датированных ДО сегодня в пределах текущего месяца.
        window_end: Последний день окна оси (reference_date + 44).
        horizon_end: Последний день горизонта расчёта H — первый доход
            строго после window_end, но не дальше
            reference_date + HORIZON_CAP_DAYS − 1.
        horizon_has_income_after: True — H стоит на доходе; False —
            доходов в (window_end, предел] нет и H упёрся в предел
            (край расчёта может оказаться ложным узким местом).
    """

    collect_start: date
    window_end: date
    horizon_end: date
    horizon_has_income_after: bool


class DayLayers(TypedDict):
    """Декомпозиция прогнозного остатка одного дня окна на три слоя.

    Инвариант: free + payments + reserve == forecast_balance (AC-3).

    Attributes:
        date: Дата дня окна.
        free: Слой «Свободно» — сколько можно потратить в этот день
            разово и пройти все дни до горизонта H без минуса:
            min по t ∈ [date, H] от available(t) (протокол 0033).
        payments: Слой «Платежи» — сколько из денег этого дня нельзя
            трогать, чтобы пройти до следующих поступлений:
            available(date) − min по t ∈ [date, H] от available(t).
            Доходы, приходящие раньше платежа, учтены сами; обрыва на
            границе месяца нет (C-5 отменён протоколом 0033).
        reserve: Слой «Резерв» — ФАКТ дня после каскада _split_day.
            Может быть меньше reserve_configured, если остатка меньше:
            это и есть сигнал «бюджета целей не хватает».
        reserve_configured: Настроенный резерв дня ДО каскада
            (goals_part; порог подушки в резерв не входит — вопрос №12).
            Нужен тултипу, чтобы
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
        date: Дата платежа (ФАКТИЧЕСКАЯ дата операции).
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
        free: Слой «Свободно» на reference_date — «Свободно сегодня»
            в шапке. Клэмпнут каскадом (≥ 0 при balance ≥ 0): глубину
            нехватки показывает MoneyLayersData.shortfall.
        balance: Прогнозный остаток на reference_date (разбор).
        payments: Слой «Платежи» на reference_date (разбор).
        reserve: Слой «Резерв» на reference_date, ФАКТ дня (разбор).
    """

    free: Decimal
    balance: Decimal
    payments: Decimal
    reserve: Decimal


class LimitPeriod(TypedDict):
    """Период лимита трат на день (протокол 0033).

    Дни считаются ВКЛЮЧИТЕЛЬНО с обоих концов: start..end.

    Attributes:
        start: Первый день периода.
        end: Последний день периода — узкое место периода.
        per_day: Лимит трат в день (Decimal без округления; округление
            до рубля вниз — только при слиянии и в UI).
        reliable: False — период кончается на краю расчёта H (за ним
            данных нет; если H — день дохода, остаток уже включает
            доход); UI его не показывает (кроме первого — предупреждение
            вместо числа).
    """

    start: date
    end: date
    per_day: Decimal
    reliable: bool


class MoneyLayersData(TypedDict):
    """Полный результат модели FR-1 — единый источник шапки и графика.

    Attributes:
        days: Декомпозиция по дням окна (reference_date .. window_end).
        today: Срез «сегодня» для шапки.
        limit_periods: Периоды лимита трат на день (до 3), по порядку.
        bottleneck_date: Узкое место — день, на котором стоит самое
            жёсткое ограничение (конец первого периода); None — ряд пуст.
            Заменило маркер минимума «Свободно» (FR-3.e, протокол 0033).
        bottleneck_available: available(t) в день узкого места.
        shortfall: Нехватка max(0, −min available на [ref, H]) — сколько
            не хватает, чтобы пройти все дни без минуса. Полосы её не
            показывают (клэмп каскадом), показывает шапка.
        shortfall_date: Первый день, где available достигает минимума
            (None при пустом ряде).
        norm_per_day: Норма «по плану» — (доходы − расходы) регулярных
            операций месяца reference_date ÷ дней месяца; None — нет
            регулярных операций.
        upcoming_payments: Платежи от reference_date до horizon_end
            для тултипа (FR-4).
        milestones: Вехи целей для оси времени (FR-3.c).
        reference_date: Дата отсчёта («сегодня»).
        window_end: Последний день окна оси (reference_date + 44).
        horizon_end: Последний день горизонта расчёта H.
        cushion_threshold: Порог подушки — ориентир (линия на графике,
            строка в шапке); в слой «Резерв» не входит (вопрос №12).
        goals_reserve_today: Часть слоя «Резерв» от бюджета целей на сегодня
            (до каскада — настроенная).
        reserve_configured_today: goals_reserve_today (порог подушки не входит).
            Сравнение с today['reserve'] показывает, сжат ли слой —
            тултип обязан говорить факт, а не настройку (п. 3б).
        degraded: True — часть модели посчитана в деградации (fail-open,
            см. «Обработка ошибок»). UI помечает разбор оговоркой
            «часть данных недоступна» и НЕ показывает заниженные числа
            как достоверные.
        is_empty: True — у пользователя нет данных ВООБЩЕ (FR-6);
            НЕ «нули в окне». Считается без отдельного запроса.
        window_is_flat: True — данные есть, но в окне ни одной операции
            (график рисуется плоским, пустое состояние НЕ подменяет его).
    """

    days: list[DayLayers]
    today: TodaySlice
    limit_periods: list[LimitPeriod]
    bottleneck_date: date | None
    bottleneck_available: Decimal
    shortfall: Decimal
    shortfall_date: date | None
    norm_per_day: Decimal | None
    upcoming_payments: list[UpcomingPayment]
    milestones: list[GoalMilestone]
    reference_date: date
    window_end: date
    horizon_end: date
    cushion_threshold: Decimal
    goals_reserve_today: Decimal
    reserve_configured_today: Decimal
    degraded: bool
    is_empty: bool
    window_is_flat: bool
