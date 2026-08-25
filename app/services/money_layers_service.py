"""Сервис модели «свободно / платежи / резерв» по дням (EPIC-11, кусок 1)."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.schema.money_layers import (
    WINDOW_DAYS,
    MAX_MILESTONES_IN_WINDOW,
    DayLayers,
    GoalMilestone,
    Horizons,
    MoneyLayersData,
    TodaySlice,
    UpcomingPayment,
)


# Типы операций, попадающих в слой «Платежи» на полную сумму
_PAYMENT_TYPES = frozenset({"expense", "savings_reserve", "savings_contribution"})

# Типы операций, формирующих слой «Резерв» через бюджет целей
_SAVINGS_TYPES = frozenset({"savings_reserve", "savings_contribution"})


def _month_start(day: date) -> date:
    """Первое число месяца указанной даты.

    Args:
        day: Любая дата.

    Returns:
        date: 1-е число того же месяца.
    """
    return day.replace(day=1)


def _month_end(day: date) -> date:
    """Последний день месяца указанной даты.

    Args:
        day: Любая дата.

    Returns:
        date: Последний календарный день того же месяца.
    """
    return day.replace(day=monthrange(day.year, day.month)[1])


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

    Note:
        ДОПУЩЕНИЯ СОГЛАСОВАННОСТИ ДАННЫХ (critique-v3, №1 и №2).
        Модель читает настройку (monthly_budget, порог подушки) и
        историю (savings-операции) одновременно, поэтому обязана
        сказать, что будет, если они разошлись:

        1. «Бюджет не менялся внутри месяца» — см. _goals_part_by_day.
        2. «Фактическая дата savings-операции совпадает с датой, по
           которой её видит кассовый календарь» — см. _collect_operations.

        Оба допущения верны в норме и нарушаются штатными действиями
        пользователя. Направления ошибки перечислены в докстрингах
        соответствующих методов — необъявленное допущение в финансовой
        модели ведёт себя как дефект, потому что тесты пишут
        по объявленному контракту.
    """

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: SQLAlchemy сессия для работы с БД.
        """
        self.session = session

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
        ref = reference_date or date.today()
        horizons = self._horizons(ref)
        window_dates = [ref + timedelta(days=offset) for offset in range(WINDOW_DAYS)]

        # Прогнозный остаток — единственный источник, сбой не глотаем
        balances = self._forecast_balances(user_id, ref, horizons.window_end)

        payments, savings_by_date = self._collect_operations(
            user_id, horizons.collect_start, horizons.window_end, ref
        )
        payments_tail = self._payments_tail_by_day(
            payments, window_dates, horizons.payments_end
        )

        degraded = False

        # Порог подушки — часть слоя «Резерв», сбой деградирует fail-open
        try:
            from app.services.cushion_service import CushionService

            cushion_threshold = CushionService(self.session).get_threshold_amount(
                user_id
            )
        except Exception:
            logger.opt(exception=True).warning(
                f"Не удалось получить порог подушки для user_id={user_id}, "
                "слой «Резерв» посчитан без него (degraded)"
            )
            cushion_threshold = Decimal("0")
            degraded = True

        # Бюджет накоплений — часть слоя «Резерв», сбой деградирует fail-open
        try:
            from app.services.budget_reservation_service import (
                BudgetReservationService,
            )

            monthly_budget = BudgetReservationService(self.session).get_settings(
                user_id
            )["monthly_budget"]
        except Exception:
            logger.opt(exception=True).warning(
                f"Не удалось получить бюджет накоплений для user_id={user_id}, "
                "слой «Резерв» посчитан без бюджета целей (degraded)"
            )
            monthly_budget = Decimal("0")
            degraded = True

        goals_part = self._goals_part_by_day(
            savings_by_date, window_dates, monthly_budget
        )

        days: list[DayLayers] = []
        for day in window_dates:
            balance = balances.get(day, Decimal("0"))
            day_payments = payments_tail.get(day, Decimal("0"))
            reserve_configured = cushion_threshold + goals_part.get(day, Decimal("0"))
            free, fact_payments, fact_reserve = self._split_day(
                balance, day_payments, reserve_configured
            )
            days.append(
                DayLayers(
                    date=day,
                    free=free,
                    payments=fact_payments,
                    reserve=fact_reserve,
                    reserve_configured=reserve_configured,
                    forecast_balance=balance,
                )
            )

        min_free, min_free_date = self._window_min_free(days)

        # Вехи целей — сбой деградирует fail-open
        try:
            milestones = self._goal_milestones(user_id, ref, horizons.window_end)
        except Exception:
            logger.opt(exception=True).warning(
                f"Не удалось получить вехи целей для user_id={user_id} (degraded)"
            )
            milestones = []
            degraded = True

        starting_balance, has_recurring_templates = self._user_data_markers(user_id)
        is_empty = self._is_empty(
            days, savings_by_date, payments, has_recurring_templates, starting_balance
        )
        window_is_flat = not is_empty and not payments and not savings_by_date

        goals_reserve_today = goals_part.get(ref, Decimal("0"))

        return MoneyLayersData(
            days=days,
            today=self._today_slice(days),
            min_free=min_free,
            min_free_date=min_free_date,
            upcoming_payments=payments,
            milestones=milestones,
            reference_date=ref,
            window_end=horizons.window_end,
            payments_end=horizons.payments_end,
            cushion_threshold=cushion_threshold,
            goals_reserve_today=goals_reserve_today,
            reserve_configured_today=cushion_threshold + goals_reserve_today,
            degraded=degraded,
            is_empty=is_empty,
            window_is_flat=window_is_flat,
        )

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

        Args:
            reference_date: Дата отсчёта.

        Returns:
            Horizons: (collect_start, window_end, payments_end).
        """
        return Horizons(
            collect_start=_month_start(reference_date),
            window_end=reference_date + timedelta(days=WINDOW_DAYS - 1),
            payments_end=_month_end(reference_date),
        )

    def _forecast_balances(
        self, user_id: int, reference_date: date, window_end: date
    ) -> dict[date, Decimal]:
        """Прогнозный остаток по дням окна — делегат в CalendarService.

        Единственный источник остатка: инвариант AC-3
        (free + payments + reserve == balance) держится по построению
        именно потому, что модель не считает баланс сама.

        Args:
            user_id: ID пользователя.
            reference_date: Первый день окна.
            window_end: Последний день окна.

        Returns:
            dict[date, Decimal]: {дата: остаток на конец дня}.
        """
        from app.services.calendar_service import CalendarService

        return CalendarService(self.session).calculate_daily_balances(
            user_id, reference_date, window_end
        )

    def _collect_operations(
        self,
        user_id: int,
        collect_start: date,
        window_end: date,
        reference_date: date,
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

        КЛЮЧЕВАНИЕ savings_by_date — ПО ФАКТИЧЕСКОЙ ДАТЕ ОПЕРАЦИИ
        (critique-v3, №2). Ключ — TransactionInfo['date'], то есть
        Transaction.transaction_date для реальных строк и instance_date
        для виртуальных. НЕ original_date. Словарь НЕ фильтруется
        по границам окна: он может содержать даты за window_end
        (и, теоретически, до collect_start).

        Почему так может получиться. RecurringService
        .get_instances_with_exceptions(user_id, start, end):
          * отбирает exceptions по original_date в [start, end]
            (get_exceptions_for_template, recurring_service.py:390-393),
          * подставляет их вместо виртуального инстанса по ключу
            (template_id, instance_date) (:704-710),
          * а вызывающий раскладывает их по transaction_date
            (calendar_service.py:845).
        У перенесённого exception original_date и transaction_date
        не совпадают, поэтому операция попадает в результат с датой,
        которая может лежать вне запрошенного диапазона.

        ВАЖНО: ту же самую выборку с той же семантикой использует
        расчёт баланса (_get_recurring_daily_changes → тот же
        get_instances_with_exceptions, раскладка по transaction_date).
        С протокола 0029 баланс расширяет диапазоны выборки и фильтрует
        по фактической дате, поэтому перенесённый exception виден
        и нам, и балансу на одной и той же дате — прежнее расхождение
        из-за разных диапазонов вызова снято (см. докстринг
        _goals_part_by_day, Note).

        Достижимость переноса (проверено grep'ом): параметр
        create_exception(new_date=...) (recurring_service.py:405)
        не имеет ни одного вызывающего — все три call-site
        (budget_reservation_service.py:294, :916,
        transaction_modals.py:1163) передают только original_date.
        Расхождение достижимо двухшаговым путём UI: exception
        создаётся с совпадающими датами, затем пользователь меняет
        дату в модале правки операции — TransactionService
        .update_transaction присваивает transaction_date и
        original_date НЕ трогает (transaction_service.py:236-243).

        Args:
            user_id: ID пользователя.
            collect_start: Левая граница сбора (1-е число месяца).
            window_end: Правая граница сбора (последний день окна).
            reference_date: Дата отсчёта — платежи берутся от неё.

        Returns:
            tuple: (payments, savings_by_date), где
                payments — расходные операции с датой >= reference_date
                    (прошедшие дни месяца в слой «Платежи» не входят:
                    они уже вычтены из balance);
                savings_by_date — {ФАКТИЧЕСКАЯ дата: Σ savings_reserve +
                    savings_contribution} по всему собранному материалу,
                    включая прошедшие дни месяца и даты за window_end.
                    Ровно эти суммы CalendarService вычитает из баланса
                    (_get_daily_changes :270-283 для обычных,
                    _get_recurring_daily_changes :426-437 для recurring
                    и exceptions) — потому формула резерва и не двоится.
        """
        from app.services.calendar_service import CalendarService

        by_date = CalendarService(self.session).get_all_transactions_for_period(
            user_id, collect_start, window_end
        )

        payments: list[UpcomingPayment] = []
        savings_by_date: dict[date, Decimal] = {}

        for day, transactions in by_date.items():
            for txn in transactions:
                if txn["is_skipped"]:
                    continue

                txn_type = txn["transaction_type"]
                amount = Decimal(txn["amount"])

                if txn_type in _PAYMENT_TYPES:
                    payment_amount = amount
                elif txn_type == "adjustment" and amount < 0:
                    payment_amount = abs(amount)
                else:
                    payment_amount = Decimal("0")

                if payment_amount > 0 and day >= reference_date:
                    payments.append(
                        UpcomingPayment(
                            date=day,
                            amount=payment_amount,
                            description=txn["description"],
                            category_name=txn["category_name"],
                            is_recurring=txn["is_recurring"],
                        )
                    )

                if txn_type in _SAVINGS_TYPES:
                    savings_by_date[day] = (
                        savings_by_date.get(day, Decimal("0")) + amount
                    )

        payments.sort(key=lambda item: item["date"])
        return payments, savings_by_date

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

        Args:
            payments: Платежи от reference_date и далее.
            window_dates: Дни окна по возрастанию.
            payments_end: Правая граница горизонта платежей.

        Returns:
            dict[date, Decimal]: {день окна: сумма хвоста платежей}.
        """
        # Суммы платежей по дням в пределах горизонта «Платежи»
        by_day: dict[date, Decimal] = {}
        for payment in payments:
            if payment["date"] <= payments_end:
                by_day[payment["date"]] = (
                    by_day.get(payment["date"], Decimal("0")) + payment["amount"]
                )

        result: dict[date, Decimal] = {}
        tail = Decimal("0")
        # Проход справа налево: на дне D в хвосте лежат платежи строго после D
        for day in reversed(window_dates):
            if day >= payments_end:
                result[day] = Decimal("0")
            else:
                result[day] = tail
            tail += by_day.get(day, Decimal("0"))

        return result

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
            Суммирование НЕ ограничено границами окна (critique-v3, №2):
            committed(D) считает до month_end(D) включительно, даже если
            month_end(D) > window_end. Savings-операция, чья фактическая
            дата лежит за правым краем окна, но внутри месяца дня D, —
            это реальное «ещё предстоит уйти в этом месяце», и её учёт
            уменьшает goals_part(D), то есть НЕ завышает «Свободно».
            savings_by_date такие ключи содержит (см. _collect_operations),
            и отбрасывать их нельзя.

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
            ДОПУЩЕНИЕ «БЮДЖЕТ НЕ МЕНЯЛСЯ ВНУТРИ МЕСЯЦА»
            (critique-v3, №1; решение владельца п. 3в).

            monthly_savings_budget — ОДНА настройка на все месяцы
            (users.monthly_savings_budget, database.py:99), месячной
            истории бюджета в схеме нет (C-4). Поэтому budget(D) ==
            monthly_budget для любого D.

            При этом суммы savings-операций месяца зафиксированы
            НА МОМЕНТ ПРОШЛЫХ ОПЕРАЦИЙ и при смене бюджета не
            переписываются: BudgetReservationService
            .sync_template_amount (:808-839) обновляет ТОЛЬКО
            template.amount и существующие exceptions не трогает;
            recalculate_current_month_exception вызывается из путей
            взноса, а не из пути смены бюджета, и содержит guard
            if reserve_date < date.today(): return (:263-265).

            Следствие: формула отражает ТЕКУЩУЮ НАСТРОЙКУ, а не
            историю. Два параметра поведения:

            * бюджет УМЕНЬШЕН после частичного взноса (обещано целям
              больше текущего бюджета): consumed + committed >
              monthly_budget, и max(0, …) обрезает перерасход
              ДО НУЛЯ. Признака «обещано сверх бюджета» в UI НЕТ —
              решение владельца п. 3в: цифры остаются корректными
              (деньги действительно сидят в слое «Платежи» и уйдут),
              теряется только информация о превышении. Различие
              «goals_part = 0, потому что бюджет исчерпан» и
              «= 0, потому что обещано больше бюджета» модель
              сознательно НЕ различает: жизненный цикл целей и
              превышение — отдельный открытый вопрос ROADMAP №9.
            * бюджет УВЕЛИЧЕН после полного взноса: goals_part
              завышается на разницу, «Свободно» ЗАНИЖАЕТСЯ.
              Направление безопасное (показать меньше свободных
              денег, чем есть, не опасно — та же асимметрия, что
              для правого края окна).

            Оба параметра — в блоке A шага 6 с числами по трём слоям.

        Note:
            Ограничение куска 1 «перенесённый exception внутри текущего
            месяца» (critique-v3, №2, случай 3) СНЯТО протоколом 0029:
            _calculate_recurring_before_date и _get_recurring_daily_changes
            (calendar_service.py) теперь учитывают savings-типы и
            раскладывают перенесённые exceptions по фактической дате —
            прогнозный остаток видит такую операцию там же, где её видит
            наш сбор, «Свободно» больше не завышается. Покрыто
            регрессионными тестами (test_calendar_service.py
            ::TestRecurringBeforePeriodSavings,
            test_money_layers_service.py::TestMovedExceptionRegression).
            Остаточная экзотика — exception, перенесённый с исходной
            даты дальше RECURRING_LOOKAHEAD_DAYS (366) от границы
            расчёта, — описана в докстринге
            _calculate_recurring_before_date.

        Args:
            savings_by_date: Savings-операции по фактическим датам
                (может содержать даты за границами окна).
            window_dates: Дни окна по возрастанию.
            monthly_budget: Текущая настройка бюджета накоплений.

        Returns:
            dict[date, Decimal]: {день окна: бюджет целей в остатке}.
        """
        result: dict[date, Decimal] = {}

        for day in window_dates:
            month_start = _month_start(day)
            month_end = _month_end(day)

            consumed = Decimal("0")
            committed = Decimal("0")
            # Границы суммирования — месяц дня D; committed НЕ обрезается
            # правым краем окна (ключи за window_end учитываются)
            for op_date, amount in savings_by_date.items():
                if month_start <= op_date <= day:
                    consumed += amount
                elif day < op_date <= month_end:
                    committed += amount

            goals = monthly_budget - consumed - committed
            result[day] = goals if goals > 0 else Decimal("0")

        return result

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

        Args:
            balance: Прогнозный остаток дня.
            payments: Хвост платежей дня.
            reserve: Настроенный резерв дня (до каскада).

        Returns:
            tuple[Decimal, Decimal, Decimal]: (free, payments, reserve),
                сумма которых равна balance при любом входе.
        """
        if balance < 0:
            return balance, Decimal("0"), Decimal("0")

        free = balance - payments - reserve
        if free >= 0:
            return free, payments, reserve

        # Дефицит гасится сначала из резерва, затем из платежей
        deficit = -free
        reserve_fact = reserve - min(deficit, reserve)
        deficit -= reserve - reserve_fact
        payments_fact = payments - min(deficit, payments)

        return Decimal("0"), payments_fact, reserve_fact

    def _today_slice(self, days: list[DayLayers]) -> TodaySlice:
        """Срез первого дня окна (== reference_date) для шапки.

        Вердикта не считает: уровней состояния в куске 1 нет
        (решение владельца п. 3а). Только четыре числа разбора.

        Args:
            days: Дни окна (первый — reference_date).

        Returns:
            TodaySlice: free / balance / payments / reserve на сегодня.
        """
        if not days:
            return TodaySlice(
                free=Decimal("0"),
                balance=Decimal("0"),
                payments=Decimal("0"),
                reserve=Decimal("0"),
            )

        today = days[0]
        return TodaySlice(
            free=today["free"],
            balance=today["forecast_balance"],
            payments=today["payments"],
            reserve=today["reserve"],
        )

    def _window_min_free(self, days: list[DayLayers]) -> tuple[Decimal, date]:
        """Минимум слоя «Свободно» по ВСЕМУ окну — для маркера (FR-3.e).

        Минимум ищется по всем 45 дням, а не по остатку месяца:
        просадка после зарплаты (эскиз: 4 сентября) обязана попадать
        в кадр. При равенстве берётся первая дата.

        Note:
            Величина используется ТОЛЬКО графиком (маркер минимума).
            Оценочного вывода из неё не делается — вердикт снят
            решением владельца.

        Args:
            days: Дни окна.

        Returns:
            tuple[Decimal, date]: (минимум «Свободно», его дата).
        """
        if not days:
            return Decimal("0"), date.today()

        min_day = days[0]
        for day in days[1:]:
            if day["free"] < min_day["free"]:
                min_day = day

        return min_day["free"], min_day["date"]

    def _goal_milestones(
        self, user_id: int, reference_date: date, window_end: date
    ) -> list[GoalMilestone]:
        """Вехи активных целей: в окне + ближайшая за его краем.

        Материализует поля ORM-объектов Goal (включая вычисляемое
        property progress_percentage) в GoalMilestone ВНУТРИ сессии —
        GoalService.get_all_by_user возвращает list[Goal], и обращение
        к нему после закрытия сессии даст DetachedInstanceError.

        Args:
            user_id: ID пользователя.
            reference_date: Левая граница окна.
            window_end: Правая граница окна.

        Returns:
            list[GoalMilestone]: до MAX_MILESTONES_IN_WINDOW вех внутри
                окна (ближайшие по target_date) + не более одной
                с beyond_window=True (ближайшая после window_end).
        """
        from app.models.database import GoalStatus
        from app.services.goal_service import GoalService

        goals = GoalService(self.session).get_all_by_user(
            user_id, status=GoalStatus.ACTIVE
        )

        in_window: list[GoalMilestone] = []
        beyond: list[GoalMilestone] = []

        for goal in sorted(goals, key=lambda item: item.target_date):
            if goal.target_date < reference_date:
                continue

            beyond_window = goal.target_date > window_end
            milestone = GoalMilestone(
                goal_id=goal.id,
                name=goal.name,
                target_date=goal.target_date,
                target_amount=Decimal(goal.target_amount),
                progress_percent=goal.progress_percentage,
                beyond_window=beyond_window,
            )

            if beyond_window:
                beyond.append(milestone)
            else:
                in_window.append(milestone)

        return in_window[:MAX_MILESTONES_IN_WINDOW] + beyond[:1]

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

        Args:
            days: Дни окна.
            savings_by_date: Собранные savings-операции.
            payments: Собранные платежи.
            has_recurring_templates: Есть ли recurring-шаблоны.
            starting_balance: Начальный баланс пользователя.

        Returns:
            bool: True — данных нет вообще (FR-6).
        """
        if starting_balance != 0:
            return False
        if has_recurring_templates:
            return False
        if payments or savings_by_date:
            return False

        return all(day["forecast_balance"] == 0 for day in days)

    def _user_data_markers(self, user_id: int) -> tuple[Decimal, bool]:
        """Начальный баланс и наличие recurring-шаблонов для _is_empty.

        Два лёгких запроса вместо count(transactions) по всей истории:
        начальный баланс читается из пользователя, наличие шаблонов —
        через RecurringService.get_templates_for_user.

        Args:
            user_id: ID пользователя.

        Returns:
            tuple[Decimal, bool]: (starting_balance, есть ли шаблоны).
                На отсутствующем пользователе — (Decimal("0"), False):
                чистая база штатна, исключения не бросаем (FR-6).
        """
        from app.models.database import User
        from app.services.recurring_service import RecurringService

        user = self.session.get(User, user_id)
        starting_balance = Decimal(user.starting_balance or 0) if user else Decimal("0")
        has_templates = bool(
            RecurringService(self.session).get_templates_for_user(user_id)
        )
        return starting_balance, has_templates
