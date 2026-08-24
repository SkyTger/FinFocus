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
            как достоверные.
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
