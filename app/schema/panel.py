"""Контракты данных карточек-дверей щитка (EPIC-11, кусок 2).

Note:
    Решение владельца 2026-08-26: окошка «вчера» в карточке «Календарь»
    НЕТ — карточка показывает сегодня и завтра. Следствие: контракт
    MoneyLayersData куском 2 не расширяется (поле yesterday не заводится),
    оба дня всегда лежат в days[0]/days[1] окна модели, поэтому механизм
    прочерка (has_data) не нужен.
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal, TypedDict

from app.schema.money_layers import MoneyLayersData

OPERATIONS_PER_GROUP = 3
"""Сколько операций в каждой группе карточки «Операции» (FR-1.c: «2-3»).

Три, не пять: карточка — фрагмент, а не таблица. Прежние split-таблицы
брали limit=5 — их место заняла эта карточка (AC-4).
"""

MINI_STRUCTURE_CATEGORIES = 3
"""Категорий в мини-структуре карточки «Аналитика» (эскиз v3: 3 + «из N ₽»)."""

# Константы DIP_STRONG_THRESHOLD НЕТ (critique-v1, №8): имя содержало
# «THRESHOLD», а решение владельца прямо говорит, что порога здесь нет.
# В коде — прямое `dip_free <= 0` с комментарием, что это факт знака
# числа, как красное «Свободно» в шапке куска 1.

TRANSACTION_KIND_MAP: dict[str, Literal["income", "expense", "other"]] = {
    "income": "income",  # доход
    "expense": "expense",  # расход
    "savings_reserve": "expense",  # деньги уходят из остатка
    "savings_contribution": "expense",  # деньги уходят из остатка
    "transfer": "other",  # знак не определён семантикой типа
    "adjustment": "other",  # знак определяется суммой, не типом
}
"""Сведение шести значений TransactionType к трём kind (critique-v2, №4).

Источник — RecentTransaction["transaction_type"]: строка
t.transaction_type.value (dashboard_service.py), то есть одно из
шести значений TransactionType (app/models/database.py:31-39).
В карточке kind управляет ЦВЕТОМ суммы, поэтому правило нужно явное,
а не «по знаку».

Логика: income/expense — прямо; savings_* — expense, потому что деньги
физически уходят из остатка (та же трактовка, что у слоя «Платежи»
модели: _PAYMENT_TYPES, money_layers_service.py); transfer и
adjustment — other (нейтральный цвет), потому что их направление
определяется не типом, а знаком суммы, а карточка-фрагмент не место
для разбора знака: в разделе «Операции» он виден полностью.

Неизвестное значение (если enum расширят) → "other" через
.get(..., "other"): карточка не падает, максимум теряет цвет. Покрыто
тестом на все шесть значений enum — тест покраснеет при добавлении
седьмого.
"""


class CardStatus(str, Enum):
    """Состояние блока карточки — ЕДИНСТВЕННЫЙ источник правды её отрисовки.

    OK      — данные есть, показываем цифры.
    EMPTY   — в ЭТОМ разделе данных нет: пустое состояние БЕЗ числовых
              артефактов, карточка остаётся (FR-2, FR-5, AC-5).
              Определяется ТОЛЬКО по данным собственного блока —
              «каждая карточка честна сама за себя» (решение владельца
              2026-08-25). Сюда же относится «пользователя нет в БД»
              для карточки Цели: это пустота, а не сбой (critique-v2, №6).
    FAILED  — сбор блока упал; сбой залогирован logger.opt(exception=True),
              карточка деградирует с индикацией, дашборд жив (NFR-2).
    """

    OK = "ok"
    EMPTY = "empty"
    FAILED = "failed"


class CalendarDaySlice(TypedDict):
    """Одно окошко дня карточки «Календарь» (FR-1.a).

    Окошек два — сегодня и завтра (решение владельца 2026-08-26,
    «вчера» убрано). Оба дня всегда присутствуют в окне модели
    (days[0]/days[1]), поэтому поля has_data нет: прочерк рисовать
    не из чего.

    Attributes:
        date: Дата дня.
        label: «Сегодня» / «Завтра».
        is_today: True для сегодняшнего окошка (класс .pnl-day-today).
        balance: Прогнозный остаток дня — DayLayers['forecast_balance'].
            Тот же язык, что у раздела «Календарь», и то же число, что
            в модели шапки (AC-3). Источник — days[0]/days[1].
        free: Слой «Свободно» дня — для подписи под остатком.
        operations_note: «2 операции» / «план» / None — подпись эскиза.
        href: /calendar?focus_date=<ISO> — дверь дня (FR-3, AC-2).
    """

    date: date
    label: str
    is_today: bool
    balance: Decimal
    free: Decimal
    operations_note: str | None
    href: str


class CalendarCardData(TypedDict):
    """Карточка «Календарь» (FR-1.a). Считается ИЗ MoneyLayersData, без запросов.

    Attributes:
        status: OK / EMPTY / FAILED — только по собственным данным.
        days: Ровно два окошка: сегодня, завтра (в этом порядке).
        dip_date: День минимума слоя «Свободно» в окне модели —
            layers['min_free_date']; маркер показывается ВСЕГДА при
            status == OK (решение владельца «оба»).
        dip_free: Значение минимума (layers['min_free']).
        dip_is_strong: dip_free <= 0 — маркер визуально усилен (AC-7).
            Факт знака числа, не порог.
        dip_href: /calendar?focus_date=<dip_date ISO>.

    ВАЖНО (critique-v2, №10): при status != OK поля dip_* НЕ рисуются,
    даже если непустые. _window_min_free при пустом days возвращает
    (Decimal("0"), date.today()) — проверено по телу
    (money_layers_service.py), а не None. Без этой оговорки чистая база
    дала бы «Ближайшая просадка: сегодня, 0 ₽» — числовой артефакт,
    запрещённый AC-5.
    """

    status: CardStatus
    days: list[CalendarDaySlice]
    dip_date: date | None
    dip_free: Decimal | None
    dip_is_strong: bool
    dip_href: str | None


class GoalsCardData(TypedDict):
    """Карточка «Цели» (FR-1.b): топ-цель + сводка + подушка одной строкой.

    Все поля материализованы ВНУТРИ сессии из ORM Goal (контракт
    материализации DashboardPanelService): progress_percentage —
    вычисляемое property, обращение к нему после закрытия сессии даёт
    DetachedInstanceError.

    Подушка считается БЕЗ CushionService.get_settings — из
    layers['cushion_threshold'], layers['today']['balance'] и
    User.cushion_target (см. «Стратегия загрузки»): второй расчёт
    баланса ради процента был бы дублем, от которого лечит FR-6.

    Бюджет и режим накоплений читаются из того же User одним
    session.get, а не через GoalService.get_savings_budget /
    get_savings_mode: те бросают ValidationError при отсутствии
    пользователя, а «нет пользователя» здесь — EMPTY (critique-v2, №6).

    Attributes:
        status: OK / EMPTY / FAILED.
        top_goal_id, top_goal_name, top_goal_progress, top_goal_current,
        top_goal_target, top_goal_target_date, top_goal_href: топ-цель
            (приоритет 1 среди активных).
        others_count: Сколько ещё активных целей помимо топовой.
        others_behind_count: Из них отстающих от плана.
        others_summary: «по плану» / «1 отстаёт»; источник — цели
            с shortfall > 0 в AllocationSummary['results'], сводное поле
            сервиса называется total_shortfall (app/schema/goals.py).
        cushion_is_configured, cushion_progress, cushion_label: подушка
            одной строкой.
    """

    status: CardStatus
    top_goal_id: int | None
    top_goal_name: str | None
    top_goal_progress: float
    top_goal_current: Decimal
    top_goal_target: Decimal
    top_goal_target_date: date | None
    top_goal_href: str | None
    others_count: int
    others_behind_count: int
    others_summary: str
    cushion_is_configured: bool
    cushion_progress: float
    cushion_label: str


class OperationRow(TypedDict):
    """Строка операции в карточке «Операции» (FR-1.c).

    КОНТРАКТ НЕ РАВЕН КОНТРАКТУ ИСТОЧНИКА (critique-v2, №4).
    Источник — RecentTransaction (app/schema/dashboard.py),
    заполняемый DashboardService._map_transactions. Различия и
    преобразования — в докстринге _operations_block; здесь важно:
      * date — ЭТО date, а не ISO-строка источника: поле уходит в
        format_date_human (app/utils/formatters.py → date_obj.day),
        и строка дала бы AttributeError внутри try/except блока,
        то есть FAILED на нормальных данных;
      * kind — три значения, сведённые из шести по TRANSACTION_KIND_MAP;
      * is_recurring — переименование is_recurring_instance источника.
    Тип поля date проверяется тестом сервиса на isinstance: тесты
    карточек его не поймают, они кормятся словарями с уже верным типом.
    """

    date: date
    title: str
    amount: Decimal
    kind: Literal["income", "expense", "other"]
    is_recurring: bool


class OperationsCardData(TypedDict):
    """Карточка «Операции» (FR-1.c): 2-3 недавние + 2-3 предстоящие.

    ОГРАНИЧЕНИЕ (решение владельца 2026-08-25, принято осознанно):
    карточка показывает ТОЛЬКО материализованные операции — те, что
    физически лежат в таблице transactions. Виртуальные инстансы
    регулярных платежей (RecurringService), ещё не сохранённые в базу,
    в неё НЕ попадают: get_recent/get_upcoming исключают шаблоны
    условием ~(is_recurring == True & recurring_parent_id IS NULL)
    (dashboard_service.py) и не знают о виртуальных инстансах
    вовсе, а менять поведение сервиса запрещает C-3. Эскиз v3 рисовал
    «Аренда 🔁» — этого не будет.
    Где регулярные видны: в календаре, в графике полос щитка и в
    тултипе легенды слоя «Платежи» (кусок 1). Флаг is_recurring
    остаётся: материализованные recurring-инстансы маркер получают
    (источник — recurring_parent_id is not None).
    Ограничение зафиксировано здесь, в докстринге _operations_block
    и в документации (modules/ui-components.md).

    Attributes:
        status: OK / EMPTY / FAILED.
        recent: До OPERATIONS_PER_GROUP недавних операций.
        upcoming: До OPERATIONS_PER_GROUP предстоящих операций.
        recent_href / upcoming_href: те же диапазоны, по которым
            источник отбирал строки (FR-6): recent — [1-е число, ref],
            upcoming — [ref, конец месяца].
    """

    status: CardStatus
    recent: list[OperationRow]
    upcoming: list[OperationRow]
    recent_href: str
    upcoming_href: str


class AnalyticsCategorySlice(TypedDict):
    """Доля категории в мини-структуре карточки «Аналитика».

    Источник — CategorySummary (app/schema/analytics.py):
    name ← category_name, total ← total, share ← percentage.
    """

    name: str
    total: Decimal
    share: float
    color: str


class AnalyticsCardData(TypedDict):
    """Карточка «Аналитика» (FR-1.d): ТОЛЬКО расходы.

    Показателя «Доходы за месяц» здесь нет и не появится ни в каком
    виде — решение владельца 2026-08-25.

    ОБЪЯВЛЕННОЕ РАСХОЖДЕНИЕ С ГРАФИКОМ ЩИТКА (critique-v2, №5;
    решение владельца по вопросу 5). month_total считается тем же
    AnalyticsService.get_expenses_by_category, что питает раздел
    «Аналитика», — с разделом цифра совпадает по построению, и это
    правильное поведение. Но с МЕСЯЧНЫМ СЛОЕМ «ПЛАТЕЖИ» графика,
    стоящего прямо над карточкой, она НЕ сопоставима, и это названо
    прямо, а не оставлено пользователю на догадки.

    Проверено по телу get_expenses_by_category (analytics_service.py):
    фильтр transaction_type == EXPENSE И is_recurring == False.
    Следствия:
      * виртуальные инстансы регулярных платежей в цифру НЕ входят,
        а в слой «Платежи» входят (модель считает их через
        CalendarService);
      * savings_reserve / savings_contribution и отрицательные
        adjustment в цифру НЕ входят, а в слой «Платежи» входят
        (_PAYMENT_TYPES + ветка adjustment, money_layers_service.py).
    Поэтому «расходы августа» будут заметно меньше месячного слоя
    платежей на графике. Обе цифры корректны в своей семантике;
    необъявленное расхождение и было болезнью (P1-боль аудита, FR-6),
    поэтому семантика объявляется в трёх местах: здесь, в подписи
    карточки («расходы августа · без регулярных и взносов в цели»)
    и в RTM (#87) — симметрично оформлению ограничения карточки
    «Операции». AnalyticsService НЕ правится (C-3); отдельный
    протокол по семантике «расходов месяца» в этом куске
    не заводится (решение владельца).
    """

    status: CardStatus
    month_label: str
    month_total: Decimal
    top_category_name: str | None
    top_category_total: Decimal
    top_category_share: float
    structure: list[AnalyticsCategorySlice]
    href: str


class WishlistCardRow(TypedDict):
    """Одна хотелка в карточке Wishlist — второй уровень двери (AC-8).

    Материализована из WishlistItemData ВНУТРИ сессии: to_data
    (wishlist_service.py) возвращает словарь примитивов, но внутри
    читает связь item.category_rel — то есть сам безопасен только
    внутри сессии.
    """

    item_id: int
    name: str
    amount_label: str
    is_planned: bool
    planned_date_label: str | None
    href: str


class WishlistCardData(TypedDict):
    """Карточка «Wishlist» (FR-1.e) — двухуровневая дверь."""

    status: CardStatus
    items: list[WishlistCardRow]
    total_count: int


class PanelData(TypedDict):
    """Полный набор данных щитка за один сбор (FR-6).

    Все значения — примитивы (Decimal/date/str/bool/int): PanelData
    безопасен ПОСЛЕ закрытия сессии (контракт материализации),
    проверяется целевым тестом.

    Поля is_new_user НЕТ (critique-v1, №7; решение владельца
    2026-08-25): общего признака пустоты, влияющего на отрисовку
    карточек, в контракте не существует — иначе получались бы два
    источника правды для AC-5 и достижимое расхождение «пустой щиток
    с непустыми карточками». Каждая карточка честна сама за себя:
    единственный источник — <slot>["status"].

    Attributes:
        layers: Модель слоёв — источник шапки, графика И карточки
            «Календарь». Один вызов на рендер: расхождение цифр между
            шапкой, графиком и карточкой физически невозможно (AC-3).
        calendar / goals / operations / analytics / wishlist: срезы карточек.
        reference_date: Дата отсчёта сборки.
    """

    layers: MoneyLayersData
    calendar: CalendarCardData
    goals: GoalsCardData
    operations: OperationsCardData
    analytics: AnalyticsCardData
    wishlist: WishlistCardData
    reference_date: date
