"""Композитор данных щитка — один сбор PanelData за одну сессию (EPIC-11, кусок 2)."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.models.database import GoalStatus, User
from app.schema import (
    AnalyticsCardData,
    AnalyticsCategorySlice,
    CalendarCardData,
    CalendarDaySlice,
    CardStatus,
    GoalsCardData,
    MoneyLayersData,
    OperationRow,
    OperationsCardData,
    PanelData,
    WishlistCardData,
    WishlistCardRow,
    MINI_STRUCTURE_CATEGORIES,
    OPERATIONS_PER_GROUP,
    TRANSACTION_KIND_MAP,
)
from app.services.allocation_service import AllocationService
from app.services.analytics_service import AnalyticsService
from app.services.dashboard_service import DashboardService
from app.services.goal_service import GoalService
from app.services.money_layers_service import MoneyLayersService
from app.services.wishlist_service import WishlistService
from app.utils.formatters import (
    MONTH_NAMES_RU_GENITIVE,
    format_date_human,
    format_rub,
)

_STRUCTURE_COLORS = [
    "#2E7D32",  # green
    "#1565C0",  # blue
    "#EF6C00",  # orange
    "#C62828",  # red
]
"""Цвета долей мини-структуры карточки «Аналитика».

Первые цвета палитры CATEGORY_COLORS раздела «Аналитика»
(app/components/analytics.py) — визуальная согласованность карточки
с donut chart раздела. Локальная копия, а не импорт: сервисный слой
не импортирует из app/components (направление слоёв, C-2).
"""


def _plural_operations(count: int) -> str:
    """Склоняет «операция» по-русски: 1 операция, 2 операции, 5 операций."""
    if count % 10 == 1 and count % 100 != 11:
        word = "операция"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = "операции"
    else:
        word = "операций"
    return f"{count} {word}"


def _empty_calendar() -> CalendarCardData:
    """Пустая карточка «Календарь»: EMPTY + нейтральные значения.

    days=[] — НЕ окошки с нулями: карточка при EMPTY рисует своё
    пустое состояние. dip_* → None; плюс оговорка critique-v2 №10:
    dip_* не рисуются при status != OK, даже если непустые — то есть
    даже если сюда однажды положат значения, UI их не покажет.
    """
    return CalendarCardData(
        status=CardStatus.EMPTY,
        days=[],
        dip_date=None,
        dip_free=None,
        dip_is_strong=False,
        dip_href=None,
    )


def _empty_goals() -> GoalsCardData:
    """Пустая карточка «Цели»: EMPTY + нейтральные значения (critique-v3, №5).

    Два пути сюда (см. _goals_block): пользователя нет в БД;
    пользователь есть, но нет активных целей И cushion_target пуст.

    Не-Optional поля контракта GoalsCardData обязаны быть заполнены:
      top_goal_progress: 0.0    (float, не None по контракту)
      top_goal_current:  Decimal("0")
      top_goal_target:   Decimal("0")
      others_count:      0
      others_behind_count: 0
      others_summary:    ""     ← пустая СТРОКА, не «Нет целей»
      cushion_is_configured: False
      cushion_progress:  0.0
      cushion_label:     ""     ← пустая СТРОКА, не «0%»
    Optional-поля — None: top_goal_id, top_goal_name,
      top_goal_target_date, top_goal_href.

    ПОЧЕМУ "" И НЕ ТЕКСТ: при status == EMPTY build_goals_card рисует
    СВОЙ текст пустого состояния и в others_summary/cushion_label не
    смотрит вовсе (status — единственный источник правды отрисовки,
    RTM #81). Текст в данных завёл бы второй источник формулировки;
    строка «0%» или «0 ₽» в данных при будущей правке build-функции
    протекла бы в дерево как числовой артефакт, запрещённый AC-5.
    """
    return GoalsCardData(
        status=CardStatus.EMPTY,
        top_goal_id=None,
        top_goal_name=None,
        top_goal_progress=0.0,
        top_goal_current=Decimal("0"),
        top_goal_target=Decimal("0"),
        top_goal_target_date=None,
        top_goal_href=None,
        others_count=0,
        others_behind_count=0,
        others_summary="",
        cushion_is_configured=False,
        cushion_progress=0.0,
        cushion_label="",
    )


def _empty_operations(ref: date) -> OperationsCardData:
    """Пустая карточка «Операции»: EMPTY + href'ы заполнены как обычно.

    href — маршрут двери, не число: дверь работает и на пустой
    карточке (FR-2 «находимость разделов» не зависит от данных).
    """
    return OperationsCardData(
        status=CardStatus.EMPTY,
        recent=[],
        upcoming=[],
        recent_href=_recent_href(ref),
        upcoming_href=_upcoming_href(ref),
    )


def _empty_analytics(ref: date) -> AnalyticsCardData:
    """Пустая карточка «Аналитика»: EMPTY + month_label как обычно.

    month_label формируется ИЗ reference_date, а не из результата
    запроса (critique-v4, №4): при EMPTY из-за отсутствующего
    пользователя блок до AnalyticsService может не дойти, поэтому
    подпись периода строится из даты отсчёта и доступна всегда
    («августа» — подпись периода, не цифра, пустому состоянию нужна тоже).
    """
    return AnalyticsCardData(
        status=CardStatus.EMPTY,
        month_label=MONTH_NAMES_RU_GENITIVE[ref.month],
        month_total=Decimal("0"),
        top_category_name=None,
        top_category_total=Decimal("0"),
        top_category_share=0.0,
        structure=[],
        href="/analytics",
    )


def _empty_wishlist() -> WishlistCardData:
    """Пустая карточка «Wishlist»: EMPTY + нейтральные значения."""
    return WishlistCardData(
        status=CardStatus.EMPTY,
        items=[],
        total_count=0,
    )


def _failed(empty_data: dict) -> dict:
    """Срез FAILED: те же нейтральные значения, что у EMPTY, но status=FAILED."""
    return {**empty_data, "status": CardStatus.FAILED}


def _recent_href(ref: date) -> str:
    """Дверь «недавние» — тот же диапазон, по которому источник отбирал строки."""
    month_start = ref.replace(day=1)
    return f"/transactions?start={month_start.isoformat()}&end={ref.isoformat()}"


def _upcoming_href(ref: date) -> str:
    """Дверь «предстоящие» — [ref, конец месяца], как в get_upcoming_transactions."""
    month_end = ref.replace(day=monthrange(ref.year, ref.month)[1])
    return f"/transactions?start={ref.isoformat()}&end={month_end.isoformat()}"


class DashboardPanelService:
    """Read-only композитор данных щитка (EPIC-11, кусок 2, FR-6).

    Собирает ВСЕ данные дашборда за один вызов и одну сессию:
    модель слоёв + пять блоков карточек. Ни один существующий сервис
    не меняется — только композиция (C-3). В БД не пишет, о Dash
    не знает (C-2).

    КОНТРАКТ МАТЕРИАЛИЗАЦИИ (обязателен к соблюдению):
        Каждый блок обязан вернуть ТОЛЬКО примитивы — Decimal / date /
        str / bool / int / их списки и словари. Обращение к
        ORM-атрибутам (включая вычисляемые property вроде
        Goal.progress_percentage и связи вроде WishlistItem.category_rel)
        выполняется ВНУТРИ открытой сессии, внутри тела блока.
        ORM-объект за пределы блока НЕ ВЫХОДИТ никогда.
        Почему правило, а не пожелание: GoalService.get_all_by_user
        возвращает list[Goal], WishlistService.get_focus —
        list[WishlistItem]; WishlistService.to_data внутри читает
        item.category_rel, то есть безопасен только внутри сессии.
        PanelData живёт ДОЛЬШЕ сессии (build_*_card вызываются после
        выхода из with), поэтому любая утечка ORM даёт
        DetachedInstanceError в проде, невидимый в тестах карточек
        (они кормятся словарями). Проверяется тестом, читающим ВСЕ
        поля PanelData после закрытия сессии.

    ЯВНЫЕ ПРЕОБРАЗОВАНИЯ ТИПОВ (critique-v2, №4): контракт карточки
        не равен контракту источника. Список — в докстринге
        _operations_block; проверяется тестом на isinstance.

    СТРАТЕГИЯ ЗАГРУЗКИ (FR-6, NFR-1):
        Сессий на пути сборки щитка: 1 (было 3 — сборка компонентов,
        карточка подушки, wishlist-виджет из layout). Модель слоёв —
        один вызов get_money_layers на рендер; блоки карточек
        добавляют 4-9 коротких запросов, ноль дополнительных расчётов
        баланса, ноль вызовов Plotly.

    ДУБЛИ С МОДЕЛЬЮ СЛОЁВ — названы и решены осознанно:
        * GoalService.get_all_by_user(ACTIVE) вызывается и в
          _goal_milestones модели, и в _goals_block. Дубль ОСТАВЛЕН:
          milestones отфильтрованы по target_date >= ref и обрезаны
          до MAX_MILESTONES_IN_WINDOW + 1 — карточке нужны
          current_amount, полный список активных целей и порядок по
          priority, чего в milestones нет. Второй вызов идёт в ту же
          сессию (identity map). Читать milestones вместо целей =
          молча сузить карточку до целей с будущей датой.
        * CushionService.get_settings НЕ вызывается вовсе: помимо
          _get_user он делает _get_current_balance →
          CalendarService.get_balance_on_date с обходом всей
          recurring-истории. Второй расчёт баланса ради процента
          подушки — ровно тот дубль, от которого лечит FR-6. Вместо
          него _goals_block берёт: target — User.cushion_target;
          threshold — layers["cushion_threshold"]; current —
          layers["today"]["balance"]. Побочный выигрыш: цифра подушки
          приходит из того же источника, что шапка и график —
          расхождение невозможно по построению.
        * GoalService.get_savings_budget / get_savings_mode НЕ
          вызываются (critique-v2, №6): каждый — session.get(User) +
          raise ValidationError если нет + return одного поля. Те же
          поля того же User, который блоку и так нужен для
          cushion_target: три чтения сводятся к одному, а «пользователя
          нет» перестаёт быть исключением.

    КЕША НЕТ намеренно: единственный источник инвалидации —
    global-transaction-trigger, а он уже перерисовывает щиток целиком.
    Кеш добавил бы риск показать устаревшие цифры (P1-боль «цифры
    противоречат друг другу») без выигрыша в бюджете NFR-1.
    """

    def __init__(self, session: Session) -> None:
        """Инициализирует композитор с сессией БД."""
        self.session = session

    def get_panel_data(
        self, user_id: int, reference_date: date | None = None
    ) -> PanelData:
        """Собирает PanelData целиком.

        Raises:
            Любое исключение MoneyLayersService — базовая модель
            остатка НЕ деградирует (правило куска 1, NFR-2).
            Сбои четырёх блоков с запросами ловятся поблочно и
            превращаются в CardStatus.FAILED с логом
            logger.opt(exception=True); _calendar_block — без
            try/except: чистая функция от уже валидной MoneyLayersData.
        """
        ref = reference_date or date.today()

        # Вне try/except: без модели слоёв щитка нет (NFR-2)
        layers = MoneyLayersService(self.session).get_money_layers(user_id, ref)

        # Без try/except: чистая функция от уже валидной модели
        calendar_card = self._calendar_block(layers)

        try:
            goals_card = self._goals_block(user_id, layers)
        except Exception:
            logger.opt(exception=True).warning(
                "Сбор блока «Цели» упал, карточка деградирует"
            )
            goals_card = _failed(_empty_goals())

        try:
            operations_card = self._operations_block(user_id, ref)
        except Exception:
            logger.opt(exception=True).warning(
                "Сбор блока «Операции» упал, карточка деградирует"
            )
            operations_card = _failed(_empty_operations(ref))

        try:
            analytics_card = self._analytics_block(user_id, ref)
        except Exception:
            logger.opt(exception=True).warning(
                "Сбор блока «Аналитика» упал, карточка деградирует"
            )
            analytics_card = _failed(_empty_analytics(ref))

        try:
            wishlist_card = self._wishlist_block(user_id)
        except Exception:
            logger.opt(exception=True).warning(
                "Сбор блока «Wishlist» упал, карточка деградирует"
            )
            wishlist_card = _failed(_empty_wishlist())

        return PanelData(
            layers=layers,
            calendar=calendar_card,
            goals=goals_card,
            operations=operations_card,
            analytics=analytics_card,
            wishlist=wishlist_card,
            reference_date=ref,
        )

    def _calendar_block(self, layers: MoneyLayersData) -> CalendarCardData:
        """Два окошка (сегодня, завтра) + маркер просадки (FR-1.a).

        Чистая функция от MoneyLayersData — ноль запросов: «сегодня»
        из layers["days"][0], «завтра» из [1]. Карточка питается тем же
        источником, что шапка и график, — расхождение цифр невозможно
        по построению (AC-3).

        EMPTY-критерий — layers["is_empty"]: собственные данные этой
        карточки и есть модель слоёв; на чистой базе «Сегодня — 0 ₽»
        было бы числовым артефактом (AC-5).

        operations_note (эскиз v3, RTM #62) — из layers
        ["upcoming_payments"] без запроса: «сегодня» — количество
        платежей дня («2 операции»), «завтра» — «план» при наличии
        платежей; нет платежей → None (подпись не рисуется).

        dip_* — из min_free/min_free_date; при status != OK build-функция
        их игнорирует, даже если непустые (critique-v2, №10):
        _window_min_free на пустом окне возвращает (0, today), а не None.
        """
        if layers["is_empty"]:
            return _empty_calendar()

        today_layers = layers["days"][0]
        tomorrow_layers = layers["days"][1]

        payments_by_day: dict[date, int] = {}
        for payment in layers["upcoming_payments"]:
            payments_by_day[payment["date"]] = (
                payments_by_day.get(payment["date"], 0) + 1
            )

        today_count = payments_by_day.get(today_layers["date"], 0)
        tomorrow_count = payments_by_day.get(tomorrow_layers["date"], 0)

        days = [
            CalendarDaySlice(
                date=today_layers["date"],
                label="Сегодня",
                is_today=True,
                balance=today_layers["forecast_balance"],
                free=today_layers["free"],
                operations_note=(
                    _plural_operations(today_count) if today_count else None
                ),
                href=f"/calendar?focus_date={today_layers['date'].isoformat()}",
            ),
            CalendarDaySlice(
                date=tomorrow_layers["date"],
                label="Завтра",
                is_today=False,
                balance=tomorrow_layers["forecast_balance"],
                free=tomorrow_layers["free"],
                operations_note="план" if tomorrow_count else None,
                href=f"/calendar?focus_date={tomorrow_layers['date'].isoformat()}",
            ),
        ]

        dip_free = layers["min_free"]
        dip_date = layers["min_free_date"]
        return CalendarCardData(
            status=CardStatus.OK,
            days=days,
            dip_date=dip_date,
            dip_free=dip_free,
            dip_is_strong=dip_free <= 0,  # факт знака числа, не порог
            dip_href=f"/calendar?focus_date={dip_date.isoformat()}",
        )

    def _goals_block(self, user_id: int, layers: MoneyLayersData) -> GoalsCardData:
        """Топ-цель + сводка + подушка одной строкой (FR-1.b, AC-4).

        ОТСУТСТВИЕ ПОЛЬЗОВАТЕЛЯ — ЭТО EMPTY, НЕ FAILED (critique-v2, №6).
        Читаем User напрямую вместо GoalService.get_savings_budget /
        get_savings_mode: оба делают session.get(User, uid) и бросают
        ValidationError, если пользователя нет. «Нет пользователя» —
        это пустота, а не сбой: MoneyLayersService для того же случая
        специально не бросает (чистая база штатна).

        Одно чтение User даёт все три нужных поля и убирает два вызова
        из стратегии загрузки.

        ДВА ПУТИ В EMPTY, оба через _empty_goals() (см. её контракт):
        пользователя нет в БД; пользователь есть, но нет ни одной
        активной цели И cushion_target не задан.

        Подушка — БЕЗ CushionService.get_settings (см. докстринг
        класса); формула progress повторяет get_settings: current < 0
        → 0.0, иначе min(current / target * 100, 100.0).
        """
        user = self.session.get(User, user_id)
        if user is None:
            return _empty_goals()

        monthly_budget = user.monthly_savings_budget or Decimal("0")
        savings_mode = user.savings_mode
        cushion_target = user.cushion_target or Decimal("0")

        goals = GoalService(self.session).get_all_by_user(
            user_id, status=GoalStatus.ACTIVE
        )
        if not goals and not cushion_target:
            return _empty_goals()

        # AllocationService — БЕЗ АРГУМЕНТОВ (critique-v3, №1): у класса
        # НЕТ __init__, он stateless и работает на переданном списке ORM
        # Goal — поэтому вызов обязан быть внутри открытой сессии.
        # AllocationService(self.session) дал бы TypeError — внутри
        # блочного except это молча превратило бы карточку в FAILED
        # на ЛЮБОЙ базе с целями.
        top_goal_fields: dict = {
            "top_goal_id": None,
            "top_goal_name": None,
            "top_goal_progress": 0.0,
            "top_goal_current": Decimal("0"),
            "top_goal_target": Decimal("0"),
            "top_goal_target_date": None,
            "top_goal_href": None,
        }
        others_count = 0
        others_behind_count = 0
        others_summary = ""
        if goals:
            allocation = AllocationService().calculate_allocation(
                goals, monthly_budget, savings_mode
            )
            # ORM Goal материализуется ЗДЕСЬ, внутри сессии
            top_goal = goals[0]  # сортировка по priority asc
            top_goal_fields = {
                "top_goal_id": top_goal.id,
                "top_goal_name": top_goal.name,
                "top_goal_progress": float(top_goal.progress_percentage),
                "top_goal_current": top_goal.current_amount,
                "top_goal_target": top_goal.target_amount,
                "top_goal_target_date": top_goal.target_date,
                "top_goal_href": f"/goals?goal={top_goal.id}",
            }
            other_ids = {g.id for g in goals[1:]}
            others_count = len(other_ids)
            # others_behind_count — по shortfall > 0 каждой цели;
            # сводное поле сервиса называется total_shortfall, не shortfall
            others_behind_count = sum(
                1
                for result in allocation["results"]
                if result["goal_id"] in other_ids and result["shortfall"] > 0
            )
            if others_count:
                others_summary = (
                    "по плану"
                    if others_behind_count == 0
                    else f"{others_behind_count} "
                    + ("отстаёт" if others_behind_count == 1 else "отстают")
                )

        cushion_is_configured = cushion_target > 0
        cushion_progress = 0.0
        cushion_label = ""
        if cushion_is_configured:
            current_balance = layers["today"]["balance"]
            if current_balance >= 0:
                cushion_progress = min(
                    float(current_balance / cushion_target * 100), 100.0
                )
            cushion_label = f"{cushion_progress:.0f}% из {format_rub(cushion_target)}"

        return GoalsCardData(
            status=CardStatus.OK,
            others_count=others_count,
            others_behind_count=others_behind_count,
            others_summary=others_summary,
            cushion_is_configured=cushion_is_configured,
            cushion_progress=cushion_progress,
            cushion_label=cushion_label,
            **top_goal_fields,
        )

    def _operations_block(self, user_id: int, ref: date) -> OperationsCardData:
        """2-3 недавние + 2-3 предстоящие (FR-1.c).

        ЯВНЫЕ ПРЕОБРАЗОВАНИЯ (critique-v2, №4). Источник —
        DashboardService.get_recent_transactions / get_upcoming_transactions
        (limit=OPERATIONS_PER_GROUP), которые отдают RecentTransaction.
        Контракт источника НЕ совпадает с OperationRow:

          RecentTransaction["date"]: str  ← t.transaction_date.isoformat()
            → OperationRow["date"]: date = date.fromisoformat(row["date"])
            Обязательно: карточка отдаёт это поле в format_date_human
            (→ date_obj.day), и на строке был бы AttributeError внутри
            try/except блока, то есть карточка деградировала бы в FAILED
            на НОРМАЛЬНЫХ данных. Тестами карточек это не ловится:
            они кормятся словарями с date.

          RecentTransaction["transaction_type"]: str  ← enum .value,
            шесть возможных значений
            → OperationRow["kind"]: Literal["income","expense","other"]
            по TRANSACTION_KIND_MAP (см. app/schema/panel.py),
            неизвестное значение → "other".

          RecentTransaction["is_recurring_instance"]: bool
            → OperationRow["is_recurring"]  ← ПЕРЕИМЕНОВАНИЕ поля,
            в источнике поля is_recurring НЕТ.

          RecentTransaction["description"]: str | None
            → OperationRow["title"]: str  ← description or
            category_name or «Без описания» (в UI пустая строка
            выглядела бы дефектом вёрстки).

        ОГРАНИЧЕНИЕ (решение владельца 2026-08-25): только
        материализованные операции — см. докстринг OperationsCardData.

        Диапазоны href'ов — ТЕ ЖЕ, по которым источник отбирал строки
        (FR-6): recent — [1-е число, ref], upcoming — [ref, конец месяца].
        """
        service = DashboardService(self.session)
        recent_raw = service.get_recent_transactions(
            user_id, limit=OPERATIONS_PER_GROUP, reference_date=ref
        )
        upcoming_raw = service.get_upcoming_transactions(
            user_id, limit=OPERATIONS_PER_GROUP, reference_date=ref
        )
        if not recent_raw and not upcoming_raw:
            return _empty_operations(ref)

        def _to_row(row: dict) -> OperationRow:
            return OperationRow(
                date=date.fromisoformat(row["date"]),
                title=row["description"] or row["category_name"] or "Без описания",
                amount=row["amount"],
                kind=TRANSACTION_KIND_MAP.get(row["transaction_type"], "other"),
                is_recurring=row["is_recurring_instance"],
            )

        return OperationsCardData(
            status=CardStatus.OK,
            recent=[_to_row(r) for r in recent_raw],
            upcoming=[_to_row(r) for r in upcoming_raw],
            recent_href=_recent_href(ref),
            upcoming_href=_upcoming_href(ref),
        )

    def _analytics_block(self, user_id: int, ref: date) -> AnalyticsCardData:
        """Только расходы месяца (FR-1.d).

        Один вызов AnalyticsService.get_expenses_by_category(user_id,
        month_start, month_end); month_total = Σ row["total"].
        Тот же сервис, что питает раздел «Аналитика» — цифра карточки
        и цифра раздела совпадают по построению, и это правильно
        (решение владельца по вопросу 5 критика v2).

        ОБЪЯВЛЕННОЕ РАСХОЖДЕНИЕ С ГРАФИКОМ ЩИТКА — см. докстринг
        AnalyticsCardData. AnalyticsService не правится (C-3).

        month_label — из reference_date, не из результата запроса.

        ГРАНИЦЫ ПЕРИОДА — [1-е число, ref], как у раздела «Аналитика»
        (load_analytics_data: end_date = today), НЕ конец месяца:
        иначе завтрашний расход входил бы в цифру карточки, но не
        раздела, и «совпадение по построению» ломалось бы на любой
        базе с запланированными расходами (дефект пойман ручной
        сверкой карточки с разделом на шаге 9 протокола 0030).
        """
        month_start = ref.replace(day=1)
        categories = AnalyticsService(self.session).get_expenses_by_category(
            user_id, month_start, ref
        )
        if not categories:
            return _empty_analytics(ref)

        month_total = sum((row["total"] for row in categories), Decimal("0"))
        top = categories[0]  # сортировка по total DESC
        structure = [
            AnalyticsCategorySlice(
                name=row["category_name"],
                total=row["total"],
                share=row["percentage"],
                color=_STRUCTURE_COLORS[idx % len(_STRUCTURE_COLORS)],
            )
            for idx, row in enumerate(categories[:MINI_STRUCTURE_CATEGORIES])
        ]

        return AnalyticsCardData(
            status=CardStatus.OK,
            month_label=MONTH_NAMES_RU_GENITIVE[ref.month],
            month_total=month_total,
            top_category_name=top["category_name"],
            top_category_total=top["total"],
            top_category_share=top["percentage"],
            structure=structure,
            href="/analytics",
        )

    def _wishlist_block(self, user_id: int) -> WishlistCardData:
        """Фокусные покупки — двухуровневая дверь (FR-1.e, AC-8).

        get_focus(limit=5) + to_data ВНУТРИ сессии: to_data читает
        связь item.category_rel, то есть безопасен только внутри
        сессии. href строки — /calendar?wishlist_item=<id>: календарь
        в режиме покупок с фокусом на хотелке (механизм протокола 0023).
        """
        service = WishlistService(self.session)
        items = service.get_focus(user_id, limit=5)
        if not items:
            return _empty_wishlist()

        rows = []
        for item in items:
            data = service.to_data(item)  # внутри сессии: читает category_rel
            planned_date_label = None
            if data["planned_date"]:
                planned_date_label = format_date_human(
                    date.fromisoformat(data["planned_date"])
                )
            rows.append(
                WishlistCardRow(
                    item_id=data["id"],
                    name=data["name"],
                    amount_label=data["amount"],
                    is_planned=data["status"] == "planned",
                    planned_date_label=planned_date_label,
                    href=f"/calendar?wishlist_item={data['id']}",
                )
            )

        total_count = len(service.get_all(user_id))
        return WishlistCardData(
            status=CardStatus.OK,
            items=rows,
            total_count=total_count,
        )
