"""Сервис для управления повторяющимися операциями.

Реализует Anchored-алгоритм генерации виртуальных экземпляров
из шаблонов с поддержкой exceptions.
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from loguru import logger
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.database import Transaction


# === КОНСТАНТЫ ===

MAX_INSTANCES_PER_CALL: int = 1000
"""Максимальное количество экземпляров за один вызов generate_instances().
Защита от DoS при бессрочных шаблонах или некорректных параметрах."""

MAX_FORECAST_DAYS: int = 366
"""Максимальный горизонт прогноза (дней). Соответствует 12 месяцам вперед."""

VALID_RECURRING_PERIODS: frozenset[str] = frozenset(
    {
        "weekly",
        "biweekly",
        "monthly",
        "quarterly",
    }
)
"""Допустимые периоды повторения."""


class VirtualTransaction(TypedDict):
    """Виртуальный экземпляр recurring операции.

    Не хранится в БД, генерируется динамически.
    TypedDict для совместимости с JSON-сериализацией (dcc.Store).
    """

    template_id: int  # ID шаблона
    user_id: int
    instance_date: str  # ISO format (YYYY-MM-DD)
    amount: str  # Decimal as string для JSON
    transaction_type: str  # "income" | "expense" | "transfer"
    description: str | None
    is_virtual: bool  # Всегда True для виртуальных
    category_id: int | None  # ID категории (наследуется из шаблона)
    category_name: str | None  # Название категории для UI


class RecurringService:
    """Сервис для управления повторяющимися операциями."""

    @staticmethod
    def is_end_of_month(d: date) -> bool:
        """Проверяет, является ли дата последним днем месяца.

        Args:
            d: Дата для проверки.

        Returns:
            bool: True если последний день месяца.
        """
        _, last_day = monthrange(d.year, d.month)
        return d.day == last_day

    @staticmethod
    def should_show_eom_checkbox(selected_date: date, period: str) -> bool:
        """Определяет, нужно ли показывать EOM checkbox.

        Условия (все должны быть True):
        1. period = monthly или quarterly
        2. selected_date = последний день текущего месяца
        3. day != 31 (31 уже корректно обрабатывается Anchored)

        Args:
            selected_date: Выбранная дата операции.
            period: Период повторения.

        Returns:
            bool: True если checkbox нужно показать.
        """
        if period not in ("monthly", "quarterly"):
            return False

        _, last_day = monthrange(selected_date.year, selected_date.month)

        # Не последний день месяца — checkbox не нужен
        if selected_date.day != last_day:
            return False

        # 31-е число — Anchored итак корректно, checkbox избыточен
        if selected_date.day == 31:
            return False

        return True

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy session для работы с БД.
        """
        self.session = session

    def get_templates_for_user(self, user_id: int) -> list[Transaction]:
        """Получает все активные recurring шаблоны пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Список шаблонов (is_recurring=True, recurring_parent_id=None).
        """
        logger.debug(f"Получение шаблонов для пользователя {user_id}")

        templates = (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_recurring == True,  # noqa: E712
                Transaction.recurring_parent_id == None,  # noqa: E711
            )
            .order_by(Transaction.transaction_date)
            .all()
        )

        logger.info(f"Найдено {len(templates)} шаблонов для пользователя {user_id}")
        return templates

    def _get_anchored_date(
        self,
        anchor_day: int,
        year: int,
        month: int,
        anchor_eom: bool = False,
    ) -> date:
        """Вычисляет дату по Anchored-алгоритму или EOM.

        Args:
            anchor_day: Исходный день месяца (1-31).
            year: Год.
            month: Месяц (1-12).
            anchor_eom: True = всегда последний день месяца.

        Returns:
            Дата экземпляра:
            - EOM режим: всегда последний день месяца
            - Anchored режим: min(anchor_day, last_day)
        """
        _, last_day = monthrange(year, month)

        if anchor_eom:
            # EOM режим: всегда последний день
            return date(year, month, last_day)

        # Anchored режим: min(anchor_day, last_day)
        actual_day = min(anchor_day, last_day)
        return date(year, month, actual_day)

    def _generate_dates(
        self,
        start_date: date,
        end_date: date,
        period: str,
        anchor_day: int,
        recurring_end_date: date | None,
        anchor_eom: bool = False,
    ) -> list[date]:
        """Генерирует даты экземпляров по Anchored-алгоритму или EOM.

        Args:
            start_date: Начало периода генерации.
            end_date: Конец периода генерации.
            period: Период повторения (weekly, biweekly, monthly, quarterly).
            anchor_day: День месяца для привязки (1-31).
            recurring_end_date: Дата окончания серии (None = бессрочно).
            anchor_eom: True = всегда последний день месяца (для monthly/quarterly).

        Returns:
            Список дат экземпляров в заданном периоде.
        """
        # Guard: валидация периода
        if period not in VALID_RECURRING_PERIODS:
            logger.warning(f"Неизвестный период: {period}")
            return []

        # Guard: end_date серии
        effective_end = (
            min(end_date, recurring_end_date) if recurring_end_date else end_date
        )

        dates: list[date] = []
        current = start_date

        if period == "weekly":
            # Для weekly используем простой шаг в 7 дней
            while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
                dates.append(current)
                current += timedelta(days=7)

        elif period == "biweekly":
            # Для biweekly шаг в 14 дней
            while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
                dates.append(current)
                current += timedelta(days=14)

        elif period == "monthly":
            # Anchored/EOM: каждый месяц возвращаемся к anchor_day или EOM
            while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
                dates.append(current)
                # Переход к следующему месяцу
                if current.month == 12:
                    next_year, next_month = current.year + 1, 1
                else:
                    next_year, next_month = current.year, current.month + 1
                current = self._get_anchored_date(
                    anchor_day, next_year, next_month, anchor_eom
                )

        elif period == "quarterly":
            # Anchored/EOM: каждые 3 месяца
            while current <= effective_end and len(dates) < MAX_INSTANCES_PER_CALL:
                dates.append(current)
                # Переход через 3 месяца
                new_month = current.month + 3
                if new_month > 12:
                    next_year = current.year + 1
                    next_month = new_month - 12
                else:
                    next_year = current.year
                    next_month = new_month
                current = self._get_anchored_date(
                    anchor_day, next_year, next_month, anchor_eom
                )

        return [d for d in dates if start_date <= d <= effective_end]

    def generate_instances(
        self,
        template: Transaction,
        start_date: date,
        end_date: date,
    ) -> list[VirtualTransaction]:
        """Генерирует виртуальные экземпляры шаблона в периоде.

        Использует Anchored-алгоритм или EOM режим (если anchor_eom=True).

        ЗАЩИТА от DoS: генерация ограничена MAX_INSTANCES_PER_CALL.

        Args:
            template: Шаблон (Transaction с is_recurring=True).
            start_date: Начало периода.
            end_date: Конец периода.

        Returns:
            Список виртуальных экземпляров.
        """
        # Guard: валидация шаблона
        if not template.is_recurring:
            logger.warning(
                f"generate_instances вызван для не-recurring транзакции {template.id}"
            )
            return []

        # Guard: anchor_day должен быть валиден
        anchor_day = template.anchor_day
        if anchor_day is None:
            logger.error(
                f"Template {template.id} имеет is_recurring=True, "
                f"но anchor_day=None (transaction_date={template.transaction_date})"
            )
            return []

        # Guard: период должен быть валиден
        if template.recurring_period not in VALID_RECURRING_PERIODS:
            logger.warning(
                f"Template {template.id} имеет невалидный период: "
                f"{template.recurring_period}"
            )
            return []

        # EOM режим: привязка к последнему дню месяца
        anchor_eom = template.recurring_anchor_eom

        # Определяем start_date шаблона
        template_start = template.transaction_date

        # Генерируем даты начиная с первой даты >= start_date
        effective_start = max(template_start, start_date)

        # Для monthly/quarterly нужно найти первую дату в периоде
        if template.recurring_period in ("monthly", "quarterly"):
            # Начинаем с anchor_day в месяце effective_start
            effective_start = self._get_anchored_date(
                anchor_day, effective_start.year, effective_start.month, anchor_eom
            )
            # Если эта дата раньше template_start или start_date,
            # переходим к следующему периоду
            if effective_start < template_start or effective_start < start_date:
                if template.recurring_period == "monthly":
                    months_to_add = 1
                else:  # quarterly
                    months_to_add = 3
                new_month = effective_start.month + months_to_add
                if new_month > 12:
                    effective_start = self._get_anchored_date(
                        anchor_day, effective_start.year + 1, new_month - 12, anchor_eom
                    )
                else:
                    effective_start = self._get_anchored_date(
                        anchor_day, effective_start.year, new_month, anchor_eom
                    )

        dates = self._generate_dates(
            effective_start,
            end_date,
            template.recurring_period,
            anchor_day,
            template.recurring_end_date,
            anchor_eom,
        )

        # Ограничение количества
        if len(dates) >= MAX_INSTANCES_PER_CALL:
            logger.warning(
                f"Достигнут лимит {MAX_INSTANCES_PER_CALL} экземпляров "
                f"для шаблона {template.id}. Генерация прервана."
            )

        results: list[VirtualTransaction] = []
        for instance_date in dates:
            results.append(
                VirtualTransaction(
                    template_id=template.id,
                    user_id=template.user_id,
                    instance_date=instance_date.isoformat(),
                    amount=str(template.amount),
                    transaction_type=template.transaction_type.value,
                    description=template.description,
                    is_virtual=True,
                    category_id=template.category_id,
                    category_name=(
                        template.category_rel.name if template.category_rel else None
                    ),
                )
            )

        logger.debug(
            f"Сгенерировано {len(results)} экземпляров для шаблона {template.id} "
            f"в периоде {start_date} - {end_date}"
        )

        return results

    # === CRUD для exceptions ===

    def get_exceptions_for_template(
        self,
        template_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """Получает exceptions для шаблона в заданном периоде.

        Args:
            template_id: ID шаблона.
            start_date: Начало периода (опционально).
            end_date: Конец периода (опционально).

        Returns:
            Список exceptions (транзакции с recurring_parent_id = template_id).
        """
        query = self.session.query(Transaction).filter(
            Transaction.recurring_parent_id == template_id
        )

        if start_date:
            query = query.filter(Transaction.original_date >= start_date)
        if end_date:
            query = query.filter(Transaction.original_date <= end_date)

        exceptions = query.order_by(Transaction.original_date).all()

        logger.debug(f"Найдено {len(exceptions)} exceptions для шаблона {template_id}")
        return exceptions

    def create_exception(
        self,
        template_id: int,
        original_date: date,
        new_amount: Decimal | None = None,
        new_date: date | None = None,
        new_description: str | None = None,
        category_id: int | None = None,
    ) -> Transaction:
        """Создает exception для конкретного экземпляра recurring операции.

        Args:
            template_id: ID шаблона.
            original_date: Исходная дата экземпляра, который заменяем.
            new_amount: Новая сумма (если None — берем из шаблона).
            new_date: Новая дата (если None — используем original_date).
            new_description: Новое описание (если None — берем из шаблона).
            category_id: ID категории (если None — наследуем из шаблона).

        Returns:
            Созданный exception (Transaction).

        Raises:
            ValidationError: Если шаблон не найден или original_date вне диапазона.
            IntegrityError: Если exception на эту дату уже существует.
        """
        # Получаем шаблон
        template = self.session.get(Transaction, template_id)
        if not template or not template.is_recurring:
            raise ValidationError(
                f"Шаблон {template_id} не найден или не является recurring"
            )

        # Валидация: original_date должна быть в диапазоне шаблона
        if original_date < template.transaction_date:
            raise ValidationError(
                f"original_date ({original_date}) раньше начала серии "
                f"({template.transaction_date})"
            )

        if template.recurring_end_date and original_date > template.recurring_end_date:
            raise ValidationError(
                f"original_date ({original_date}) позже окончания серии "
                f"({template.recurring_end_date})"
            )

        # Проверяем, существует ли уже exception
        existing = (
            self.session.query(Transaction)
            .filter(
                Transaction.recurring_parent_id == template_id,
                Transaction.original_date == original_date,
            )
            .first()
        )

        if existing:
            logger.info(
                f"Exception для шаблона {template_id} на дату {original_date} "
                f"уже существует"
            )
            # Обновляем существующий
            if new_amount is not None:
                existing.amount = new_amount
            if new_date is not None:
                existing.transaction_date = new_date
            if new_description is not None:
                existing.description = new_description
            if category_id is not None:
                existing.category_id = category_id
            existing.is_skipped = False  # Снимаем пропуск если был
            self.session.flush()
            return existing

        # Создаем новый exception
        # category_id: если не указан явно — наследуем из шаблона
        effective_category_id = (
            category_id if category_id is not None else template.category_id
        )

        exception = Transaction(
            user_id=template.user_id,
            amount=new_amount if new_amount is not None else template.amount,
            transaction_type=template.transaction_type,
            transaction_date=new_date if new_date is not None else original_date,
            description=(
                new_description if new_description is not None else template.description
            ),
            category_id=effective_category_id,
            is_recurring=False,
            recurring_parent_id=template_id,
            original_date=original_date,
            is_skipped=False,
        )

        self.session.add(exception)
        self.session.flush()

        logger.info(
            f"Создан exception {exception.id} для шаблона {template_id} "
            f"на дату {original_date}"
        )

        return exception

    def skip_instance(self, template_id: int, original_date: date) -> Transaction:
        """Пропускает конкретный экземпляр recurring операции.

        Args:
            template_id: ID шаблона.
            original_date: Дата экземпляра, который пропускаем.

        Returns:
            Созданный/обновленный exception с is_skipped=True.
        """
        # Получаем шаблон
        template = self.session.get(Transaction, template_id)
        if not template or not template.is_recurring:
            raise ValidationError(
                f"Шаблон {template_id} не найден или не является recurring"
            )

        # Проверяем существующий exception
        existing = (
            self.session.query(Transaction)
            .filter(
                Transaction.recurring_parent_id == template_id,
                Transaction.original_date == original_date,
            )
            .first()
        )

        if existing:
            existing.is_skipped = True
            self.session.flush()
            logger.info(f"Exception {existing.id} помечен как пропущенный")
            return existing

        # Создаем новый exception с is_skipped=True
        exception = Transaction(
            user_id=template.user_id,
            amount=template.amount,
            transaction_type=template.transaction_type,
            transaction_date=original_date,
            description=template.description,
            is_recurring=False,
            recurring_parent_id=template_id,
            original_date=original_date,
            is_skipped=True,
        )

        self.session.add(exception)
        self.session.flush()

        logger.info(
            f"Создан пропущенный exception {exception.id} для шаблона {template_id} "
            f"на дату {original_date}"
        )

        return exception

    def stop_template(
        self,
        template_id: int,
        stop_date: date | None = None,
    ) -> Transaction:
        """Останавливает recurring серию (soft delete).

        Устанавливает recurring_end_date. Не удаляет шаблон или exceptions.

        Args:
            template_id: ID шаблона.
            stop_date: Дата остановки (по умолчанию — вчера).

        Returns:
            Обновленный шаблон.
        """
        template = self.session.get(Transaction, template_id)
        if not template or not template.is_recurring:
            raise ValidationError(
                f"Шаблон {template_id} не найден или не является recurring"
            )

        effective_stop_date = (
            stop_date if stop_date else date.today() - timedelta(days=1)
        )

        template.recurring_end_date = effective_stop_date
        self.session.flush()

        logger.info(f"Шаблон {template_id} остановлен с даты {effective_stop_date}")

        return template

    def delete_template(self, template_id: int) -> bool:
        """Полностью удаляет recurring шаблон и все его exceptions (hard delete).

        Args:
            template_id: ID шаблона.

        Returns:
            True если удаление успешно.

        Raises:
            ValidationError: Если шаблон не найден.
        """
        template = self.session.get(Transaction, template_id)
        if not template or not template.is_recurring:
            raise ValidationError(
                f"Шаблон {template_id} не найден или не является recurring"
            )

        # CASCADE удалит все exceptions автоматически
        self.session.delete(template)
        self.session.flush()

        logger.info(f"Шаблон {template_id} и все его exceptions удалены")

        return True

    def update_template_period(
        self,
        template_id: int,
        new_period: str,
    ) -> Transaction:
        """Изменяет период повторения шаблона.

        При изменении периода удаляются все future exceptions (транзакционно).

        Args:
            template_id: ID шаблона.
            new_period: Новый период (weekly, biweekly, monthly, quarterly).

        Returns:
            Обновленный шаблон.
        """
        if new_period not in VALID_RECURRING_PERIODS:
            raise ValidationError(f"Недопустимый период: {new_period}")

        template = self.session.get(Transaction, template_id)
        if not template or not template.is_recurring:
            raise ValidationError(f"Шаблон {template_id} не найден")

        # Savepoint для атомарности
        with self.session.begin_nested():
            # Удаляем future exceptions
            today = date.today()
            deleted_count = (
                self.session.query(Transaction)
                .filter(
                    Transaction.recurring_parent_id == template_id,
                    Transaction.original_date > today,
                )
                .delete(synchronize_session="fetch")
            )

            template.recurring_period = new_period

            logger.info(
                f"Шаблон {template_id}: период изменен на {new_period}, "
                f"удалено {deleted_count} future exceptions"
            )

        self.session.flush()
        return template

    def get_instances_with_exceptions(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[VirtualTransaction | Transaction]:
        """Получает все экземпляры recurring операций с учетом exceptions.

        Объединяет:
        - Виртуальные экземпляры из шаблонов
        - Заменяет их на exceptions где есть

        Args:
            user_id: ID пользователя.
            start_date: Начало периода.
            end_date: Конец периода.

        Returns:
            Список экземпляров (VirtualTransaction или Transaction).
        """
        templates = self.get_templates_for_user(user_id)

        # Собираем все exceptions в словарь (template_id, original_date) -> exception
        all_exceptions: dict[tuple[int, date], Transaction] = {}
        for template in templates:
            exceptions = self.get_exceptions_for_template(
                template.id, start_date, end_date
            )
            for exc in exceptions:
                all_exceptions[(template.id, exc.original_date)] = exc

        results: list[VirtualTransaction | Transaction] = []

        for template in templates:
            virtual_instances = self.generate_instances(template, start_date, end_date)

            for vi in virtual_instances:
                instance_date = date.fromisoformat(vi["instance_date"])
                key = (template.id, instance_date)

                if key in all_exceptions:
                    exc = all_exceptions[key]
                    if not exc.is_skipped:
                        # Возвращаем exception вместо виртуального
                        results.append(exc)
                    # Если is_skipped=True, не добавляем ничего
                else:
                    # Возвращаем виртуальный экземпляр
                    results.append(vi)

        logger.debug(
            f"get_instances_with_exceptions: {len(results)} экземпляров "
            f"для пользователя {user_id} в периоде {start_date} - {end_date}"
        )

        return results
