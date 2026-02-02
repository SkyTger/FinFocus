# Solution v2: Budget-Calendar Integration с Transaction-Contribution Link

## Обзор решения

Интеграция реализуется через два новых TransactionType (`SAVINGS_RESERVE` и `SAVINGS_CONTRIBUTION`) с прямой связью между Transaction и GoalContribution через FK. Новый `BudgetReservationService` управляет режимами резервирования, переиспользуя существующий Anchored-алгоритм из `RecurringService`. Решение обеспечивает полную синхронизацию данных при CRUD операциях через каскадные обновления.

## Архитектура

### Компоненты

**1. BudgetReservationService** (новый)
- Управляет режимами резервирования бюджета ("fixed_date" / "from_balance")
- Создает/останавливает recurring шаблон "Резерв на цели"
- Рассчитывает `available_budget` = budget - contributions_this_month
- Создает операции SAVINGS_CONTRIBUTION при взносе в режиме "from_balance"
- Синхронизирует сумму recurring шаблона при изменении бюджета
- Обрабатывает удаление SAVINGS_CONTRIBUTION с каскадным удалением GoalContribution

**2. GoalService** (расширение)
- Метод `add_contribution()` расширяется для создания связанной транзакции
- Добавлена валидация: нельзя вносить взнос в COMPLETED цель

**3. CalendarService** (расширение)
- Добавлена обработка SAVINGS_RESERVE и SAVINGS_CONTRIBUTION в расчетах баланса
- Оба типа уменьшают баланс (как EXPENSE)
- Обновлен TransactionInfo для UI календаря

**4. Goals UI** (расширение)
- Карточка "Бюджет накоплений" над списком целей
- Расширенный модал настройки бюджета с выбором режима

**5. Calendar UI** (расширение)
- Визуализация SAVINGS_RESERVE (иконка 💼, read-only)
- Визуализация SAVINGS_CONTRIBUTION (иконка 🎯, editable)
- Синхронизация при редактировании SAVINGS_CONTRIBUTION

### Диаграмма взаимодействия

```
User -> Goals Page -> Budget Modal (режим + день)
                          |
                          v
              BudgetReservationService.set_mode()
                          |
        +------------------+------------------+
        |                                     |
        v                                     v
 "fixed_date"                           "from_balance"
        |                                     |
        v                                     v
RecurringService.                      (без recurring,
create_template(                       операции при взносах)
  type=SAVINGS_RESERVE,
  anchor_eom=True if day=31)                 |
        |                                     |
        v                                     v
CalendarService.                      GoalService.
calculate_daily_balances()            add_contribution()
(учитывает SAVINGS_RESERVE)                   |
                                              v
                                    Transaction(type=
                                      SAVINGS_CONTRIBUTION)
                                              |
                                              v
                                    GoalContribution(
                                      transaction_id=FK)
```

## Файловая структура

```
app/models/database.py            — добавить SAVINGS_RESERVE, SAVINGS_CONTRIBUTION в TransactionType
                                  — добавить User.reservation_mode, User.reservation_day
                                  — добавить GoalContribution.transaction_id FK
                                  — добавить Index на contribution_date

app/schema/budget_reservation.py  — новый файл с TypedDicts:
                                    ReservationMode, BudgetReservationSettings, BudgetProgress

app/services/budget_reservation_service.py — новый BudgetReservationService

app/services/goal_service.py      — расширить add_contribution() для создания транзакции
                                  — добавить валидацию COMPLETED цели

app/services/calendar_service.py  — добавить SAVINGS_RESERVE и SAVINGS_CONTRIBUTION в расчеты:
                                    _calculate_balance_before_date(), _get_daily_changes(),
                                    _get_recurring_instances_for_period(), _get_recurring_daily_changes()

app/services/__init__.py          — экспорт BudgetReservationService

app/components/goals.py           — карточка бюджета, расширенный модал

app/components/calendar.py        — tooltip для SAVINGS_RESERVE, edit для SAVINGS_CONTRIBUTION

scripts/migrate_004_reservation.py — idempotent migration script

tests/test_budget_reservation_service.py — unit тесты (20+)
tests/test_goal_contribution_sync.py     — integration тесты синхронизации
```

## Ключевые интерфейсы

```python
# === app/schema/budget_reservation.py ===

from decimal import Decimal
from typing import TypedDict, Literal

ReservationMode = Literal["fixed_date", "from_balance"]


class BudgetReservationSettings(TypedDict):
    """Настройки режима резервирования бюджета."""
    mode: ReservationMode
    day_of_month: int | None  # 1-31, None для "from_balance"
    monthly_budget: Decimal
    template_id: int | None  # ID recurring шаблона, None если нет


class BudgetProgress(TypedDict):
    """Прогресс использования бюджета за текущий месяц."""
    total_budget: Decimal
    used_budget: Decimal  # сумма взносов в месяце
    available_budget: Decimal  # total - used
    progress_percent: float  # 0-100+
    status: str  # "success" | "warning" | "orange" | "danger"
    mode: ReservationMode
    mode_text: str  # "Распределено" | "Внесено"


# === app/services/budget_reservation_service.py ===

from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.database import (
    User, Transaction, TransactionType, Goal, GoalContribution, GoalStatus
)
from app.schema.budget_reservation import (
    BudgetReservationSettings, BudgetProgress, ReservationMode
)
from app.services.recurring_service import RecurringService


class BudgetReservationService:
    """Сервис управления резервированием бюджета накоплений.

    Поддерживает два режима:
    - "fixed_date": recurring операция "Резерв на цели" на фиксированную дату
    - "from_balance": операции при каждом взносе

    Flush/commit contract: сервис вызывает session.flush(),
    caller управляет commit().
    """

    RESERVE_DESCRIPTION = "Резерв на цели"
    CONTRIBUTION_PREFIX = "Взнос: "

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy session для работы с БД.
        """
        self.session = session
        self.recurring_service = RecurringService(session)

    def get_settings(self, user_id: int) -> BudgetReservationSettings:
        """Получает текущие настройки резервирования.

        Args:
            user_id: ID пользователя.

        Returns:
            BudgetReservationSettings с текущими настройками.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь {user_id} не найден")

        template = self._get_reserve_template(user_id)

        return BudgetReservationSettings(
            mode=user.reservation_mode or "from_balance",
            day_of_month=user.reservation_day,
            monthly_budget=user.monthly_savings_budget,
            template_id=template.id if template else None,
        )

    def set_mode(
        self,
        user_id: int,
        mode: ReservationMode,
        day_of_month: int | None = None,
    ) -> None:
        """Устанавливает режим резервирования бюджета.

        Args:
            user_id: ID пользователя.
            mode: "fixed_date" или "from_balance".
            day_of_month: День месяца (1-31) для режима "fixed_date".

        Raises:
            ValidationError: Если mode невалиден или day_of_month вне диапазона.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь {user_id} не найден")

        if mode not in ("fixed_date", "from_balance"):
            raise ValidationError(
                f"Недопустимый режим: {mode}. "
                f"Допустимые: fixed_date, from_balance"
            )

        if mode == "fixed_date":
            if day_of_month is None:
                raise ValidationError(
                    "Для режима 'fixed_date' необходимо указать день месяца",
                    field="day_of_month"
                )
            if not 1 <= day_of_month <= 31:
                raise ValidationError(
                    f"День месяца должен быть от 1 до 31, получено: {day_of_month}",
                    field="day_of_month"
                )

        old_mode = user.reservation_mode
        old_day = user.reservation_day
        user.reservation_mode = mode
        user.reservation_day = day_of_month if mode == "fixed_date" else None

        # Управление recurring шаблоном
        if mode == "fixed_date" and old_mode != "fixed_date":
            self._create_reserve_template(user_id, day_of_month)
        elif mode == "from_balance" and old_mode == "fixed_date":
            self._stop_reserve_template(user_id)
        elif mode == "fixed_date" and old_mode == "fixed_date" and old_day != day_of_month:
            # Изменился день — пересоздать шаблон
            self._stop_reserve_template(user_id)
            self._create_reserve_template(user_id, day_of_month)

        self.session.flush()
        logger.info(
            f"Режим резервирования для user {user_id} изменен: "
            f"{old_mode} -> {mode}"
        )

    def sync_template_amount(self, user_id: int) -> None:
        """Синхронизирует сумму recurring шаблона с monthly_savings_budget.

        Вызывается после изменения бюджета в режиме "fixed_date".

        Args:
            user_id: ID пользователя.
        """
        user = self.session.get(User, user_id)
        if not user or user.reservation_mode != "fixed_date":
            return

        template = self._get_reserve_template(user_id)
        if template:
            template.amount = user.monthly_savings_budget
            self.session.flush()
            logger.info(
                f"Сумма шаблона SAVINGS_RESERVE для user {user_id} "
                f"обновлена до {user.monthly_savings_budget}"
            )

    def get_budget_progress(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> BudgetProgress:
        """Рассчитывает прогресс использования бюджета за месяц.

        Args:
            user_id: ID пользователя.
            reference_date: Дата для определения месяца (по умолчанию сегодня).

        Returns:
            BudgetProgress с расчетами.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь {user_id} не найден")

        ref_date = reference_date or date.today()
        used = self._get_contributions_sum_for_month(user_id, ref_date)
        total = user.monthly_savings_budget
        available = max(Decimal("0"), total - used)

        # Рассчитать процент
        progress = float(used / total * 100) if total > 0 else 0.0

        # Определить статус (соответствует Brief: 0-70 green, 70-90 yellow, 90-100 orange, >100 red)
        if total == 0:
            status = "success"
        elif progress > 100:
            status = "danger"  # >100% = красный
        elif progress >= 90:
            status = "orange"  # 90-100% = оранжевый
        elif progress >= 70:
            status = "warning"  # 70-90% = жёлтый
        else:
            status = "success"  # 0-70% = зелёный

        mode = user.reservation_mode or "from_balance"
        mode_text = "Распределено" if mode == "fixed_date" else "Внесено"

        return BudgetProgress(
            total_budget=total,
            used_budget=used,
            available_budget=available,
            progress_percent=progress,
            status=status,
            mode=mode,
            mode_text=mode_text,
        )

    def create_contribution_transaction(
        self,
        user_id: int,
        goal_name: str,
        amount: Decimal,
        contribution_date: date,
    ) -> Transaction | None:
        """Создает транзакцию "Взнос: {цель}" для режима "from_balance".

        Args:
            user_id: ID пользователя.
            goal_name: Название цели.
            amount: Сумма взноса.
            contribution_date: Дата взноса.

        Returns:
            Transaction или None если режим "fixed_date".

        Note:
            category_id = NULL является нормой для SAVINGS_CONTRIBUTION
            (аналогично TRANSFER и ADJUSTMENT).
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValidationError(f"Пользователь {user_id} не найден")

        # В режиме "fixed_date" транзакции не создаются
        if user.reservation_mode == "fixed_date":
            return None

        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
            transaction_date=contribution_date,
            description=f"{self.CONTRIBUTION_PREFIX}{goal_name}",
            is_recurring=False,
            category_id=None,  # Явно NULL — это не расход с категорией
        )

        self.session.add(transaction)
        self.session.flush()

        logger.info(
            f"Создана транзакция SAVINGS_CONTRIBUTION для user {user_id}: "
            f"{amount} -> {goal_name}"
        )

        return transaction

    def update_contribution_transaction(
        self,
        transaction_id: int,
        new_amount: Decimal,
    ) -> None:
        """Обновляет сумму SAVINGS_CONTRIBUTION и связанного GoalContribution.

        Вызывается при редактировании транзакции в календаре.

        Args:
            transaction_id: ID транзакции.
            new_amount: Новая сумма.

        Raises:
            ValidationError: Если транзакция не найдена или не SAVINGS_CONTRIBUTION.
        """
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            raise ValidationError(f"Транзакция {transaction_id} не найдена")

        if transaction.transaction_type != TransactionType.SAVINGS_CONTRIBUTION:
            raise ValidationError(
                f"Транзакция {transaction_id} не является SAVINGS_CONTRIBUTION"
            )

        old_amount = transaction.amount
        transaction.amount = new_amount

        # Найти связанный GoalContribution по transaction_id
        contribution = (
            self.session.query(GoalContribution)
            .filter(GoalContribution.transaction_id == transaction_id)
            .first()
        )

        if contribution:
            # Обновить amount в contribution
            contribution.amount = new_amount

            # Обновить current_amount в Goal
            goal = self.session.get(Goal, contribution.goal_id)
            if goal:
                delta = new_amount - old_amount
                goal.current_amount += delta

                # Проверить completion status
                if goal.current_amount >= goal.target_amount:
                    goal.status = GoalStatus.COMPLETED
                elif goal.status == GoalStatus.COMPLETED:
                    # Откат статуса если сумма уменьшилась ниже target
                    goal.status = GoalStatus.ACTIVE

        self.session.flush()
        logger.info(
            f"Обновлена транзакция {transaction_id}: {old_amount} -> {new_amount}"
        )

    def delete_contribution_transaction(self, transaction_id: int) -> None:
        """Удаляет SAVINGS_CONTRIBUTION с каскадным удалением GoalContribution.

        Args:
            transaction_id: ID транзакции.

        Raises:
            ValidationError: Если транзакция не найдена или не SAVINGS_CONTRIBUTION.
        """
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            raise ValidationError(f"Транзакция {transaction_id} не найдена")

        if transaction.transaction_type != TransactionType.SAVINGS_CONTRIBUTION:
            raise ValidationError(
                f"Транзакция {transaction_id} не является SAVINGS_CONTRIBUTION"
            )

        # Найти связанный GoalContribution
        contribution = (
            self.session.query(GoalContribution)
            .filter(GoalContribution.transaction_id == transaction_id)
            .first()
        )

        if contribution:
            # Уменьшить current_amount в Goal
            goal = self.session.get(Goal, contribution.goal_id)
            if goal:
                goal.current_amount -= contribution.amount

                # Откат статуса если был COMPLETED
                if goal.status == GoalStatus.COMPLETED:
                    goal.status = GoalStatus.ACTIVE

            # Удалить contribution
            self.session.delete(contribution)

        # Удалить transaction
        self.session.delete(transaction)
        self.session.flush()

        logger.info(f"Удалена транзакция SAVINGS_CONTRIBUTION {transaction_id}")

    def _get_reserve_template(self, user_id: int) -> Transaction | None:
        """Получает активный шаблон "Резерв на цели"."""
        return (
            self.session.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.SAVINGS_RESERVE,
                Transaction.is_recurring == True,  # noqa: E712
                Transaction.recurring_parent_id == None,  # noqa: E711
            )
            .first()
        )

    def _create_reserve_template(
        self, user_id: int, day_of_month: int
    ) -> Transaction:
        """Создает recurring шаблон "Резерв на цели".

        Переиспользует _get_anchored_date из RecurringService.
        Для 31-го числа использует EOM anchor (recurring_anchor_eom=True).
        """
        user = self.session.get(User, user_id)
        today = date.today()

        # Используем EOM anchor для 31-го числа
        anchor_eom = (day_of_month == 31)

        # Получить дату в текущем месяце через Anchored-алгоритм
        start_date = self.recurring_service._get_anchored_date(
            day_of_month, today.year, today.month, anchor_eom
        )

        # Если дата уже прошла — следующий месяц
        if start_date < today:
            if today.month == 12:
                next_year, next_month = today.year + 1, 1
            else:
                next_year, next_month = today.year, today.month + 1
            start_date = self.recurring_service._get_anchored_date(
                day_of_month, next_year, next_month, anchor_eom
            )

        template = Transaction(
            user_id=user_id,
            amount=user.monthly_savings_budget,
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=start_date,
            description=self.RESERVE_DESCRIPTION,
            is_recurring=True,
            recurring_period="monthly",
            recurring_end_date=None,  # Бессрочно
            recurring_anchor_eom=anchor_eom,
            category_id=None,  # Явно NULL
        )

        self.session.add(template)
        self.session.flush()

        logger.info(
            f"Создан шаблон SAVINGS_RESERVE для user {user_id}: "
            f"day={day_of_month}, amount={user.monthly_savings_budget}, "
            f"anchor_eom={anchor_eom}"
        )

        return template

    def _stop_reserve_template(self, user_id: int) -> None:
        """Останавливает recurring шаблон "Резерв на цели"."""
        template = self._get_reserve_template(user_id)
        if template:
            self.recurring_service.stop_template(
                template.id,
                stop_date=date.today() - timedelta(days=1)
            )
            logger.info(f"Остановлен шаблон SAVINGS_RESERVE для user {user_id}")

    def _get_contributions_sum_for_month(
        self,
        user_id: int,
        reference_date: date,
    ) -> Decimal:
        """Получает сумму всех GoalContribution за месяц."""
        from calendar import monthrange
        from sqlalchemy import func

        first_day = date(reference_date.year, reference_date.month, 1)
        _, last_day_num = monthrange(reference_date.year, reference_date.month)
        last_day = date(reference_date.year, reference_date.month, last_day_num)

        result = (
            self.session.query(func.coalesce(func.sum(GoalContribution.amount), 0))
            .join(Goal, GoalContribution.goal_id == Goal.id)
            .filter(
                Goal.user_id == user_id,
                GoalContribution.contribution_date >= first_day,
                GoalContribution.contribution_date <= last_day,
            )
            .scalar()
        )

        return Decimal(str(result)) if result else Decimal("0")
```

## Модель данных

### Изменения в User:
```python
# app/models/database.py

class User(Base):
    # ... существующие поля ...

    # Режим резервирования бюджета
    reservation_mode = Column(String(20), default="from_balance", nullable=False)
    """Режим резервирования: "fixed_date" или "from_balance"."""

    reservation_day = Column(Integer, nullable=True)
    """День месяца для режима "fixed_date" (1-31). NULL для "from_balance"."""
```

### Изменения в TransactionType:
```python
class TransactionType(PyEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    SAVINGS_RESERVE = "savings_reserve"        # NEW: Резерв на цели
    SAVINGS_CONTRIBUTION = "savings_contribution"  # NEW: Взнос в цель
```

### Изменения в GoalContribution:
```python
class GoalContribution(Base):
    __tablename__ = "goal_contributions"
    __table_args__ = (
        Index("ix_contribution_date", "contribution_date"),  # NEW: для производительности
    )

    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)

    # NEW: связь с Transaction для режима "from_balance"
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True  # NULL для режима "fixed_date" и legacy данных
    )

    amount = Column(Numeric(10, 2), nullable=False)
    contribution_date = Column(Date, nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=func.now())

    # Relationships
    goal = relationship("Goal", back_populates="contributions")
    transaction = relationship("Transaction")  # NEW
```

### Изменения в CalendarService:

```python
# В _calculate_balance_before_date() и _get_daily_changes():
Transaction.transaction_type.in_(
    [
        TransactionType.INCOME,
        TransactionType.EXPENSE,
        TransactionType.ADJUSTMENT,
        TransactionType.SAVINGS_RESERVE,      # NEW
        TransactionType.SAVINGS_CONTRIBUTION, # NEW
    ]
)

# В case выражении:
case(
    (TransactionType.INCOME, Transaction.amount),
    (TransactionType.ADJUSTMENT, Transaction.amount),
    (TransactionType.EXPENSE, -Transaction.amount),
    (TransactionType.SAVINGS_RESERVE, -Transaction.amount),      # NEW
    (TransactionType.SAVINGS_CONTRIBUTION, -Transaction.amount), # NEW
    else_=Decimal("0"),
)

# В _get_recurring_instances_for_period и _get_recurring_daily_changes:
if inst["transaction_type"] == "income":
    total += inst["amount"]
elif inst["transaction_type"] in ("expense", "savings_reserve", "savings_contribution"):
    total -= inst["amount"]
```

## Обработка ошибок

```python
# Валидация при add_contribution (в GoalService):

def add_contribution(
    self,
    goal_id: int,
    amount: Decimal,
    contribution_date: date | None = None,
    description: str | None = None,
) -> Goal:
    """Добавляет взнос в цель с созданием транзакции в режиме "from_balance"."""

    if amount <= 0:
        raise ValidationError("Сумма взноса должна быть больше 0", field="amount")

    goal = self.session.get(Goal, goal_id)
    if not goal:
        raise ValidationError(f"Цель с ID {goal_id} не найдена")

    # NEW: Guard clause — нельзя вносить в COMPLETED цель
    if goal.status == GoalStatus.COMPLETED:
        raise ValidationError(
            f"Невозможно внести взнос в завершенную цель '{goal.name}'",
            field="goal_id"
        )

    # Получаем user для проверки бюджета (без блокировки)
    user = self.session.get(User, goal.user_id)

    # Warning логирование если budget = 0 (но не блокируем)
    if user and user.monthly_savings_budget == 0:
        logger.warning(
            f"Взнос {amount} в цель {goal_id} без настроенного бюджета"
        )

    # Создаем транзакцию в режиме "from_balance"
    from app.services.budget_reservation_service import BudgetReservationService
    budget_service = BudgetReservationService(self.session)

    transaction = budget_service.create_contribution_transaction(
        user_id=goal.user_id,
        goal_name=goal.name,
        amount=amount,
        contribution_date=contribution_date or date.today(),
    )

    # Создаём запись взноса с transaction_id
    contribution = GoalContribution(
        goal_id=goal_id,
        amount=amount,
        contribution_date=contribution_date or date.today(),
        description=description,
        transaction_id=transaction.id if transaction else None,  # NEW
    )
    self.session.add(contribution)

    # Обновляем текущую сумму цели
    goal.current_amount += amount

    # Автоматически завершаем цель если достигнута
    if goal.is_completed:
        goal.status = GoalStatus.COMPLETED
        logger.info(f"Цель {goal_id} '{goal.name}' достигнута!")

    self.session.flush()
    return goal
```

## План реализации

### Фаза 1: Database Schema (2 шага)
1. Добавить SAVINGS_RESERVE, SAVINGS_CONTRIBUTION в TransactionType
2. Добавить User.reservation_mode, User.reservation_day
3. Добавить GoalContribution.transaction_id FK и Index на contribution_date
4. Создать scripts/migrate_004_reservation.py (idempotent)

### Фаза 2: BudgetReservationService (3 шага)
5. Создать app/schema/budget_reservation.py с TypedDicts
6. Создать BudgetReservationService с get_settings, set_mode, get_budget_progress
7. Добавить sync_template_amount, update/delete_contribution_transaction

### Фаза 3: CalendarService интеграция (2 шага)
8. Добавить SAVINGS_RESERVE/CONTRIBUTION в _calculate_balance_before_date(), _get_daily_changes()
9. Добавить в _get_recurring_instances_for_period(), _get_recurring_daily_changes()

### Фаза 4: GoalService интеграция (2 шага)
10. Расширить add_contribution() для создания транзакции и GoalContribution.transaction_id
11. Добавить валидацию COMPLETED и sync с BudgetReservationService

### Фаза 5: Goals UI (4 шага)
12. Создать _build_budget_progress_card() для карточки бюджета
13. Расширить _build_budget_modal() для выбора режима и дня
14. Добавить callbacks для режима и обновления карточки
15. Обновить update_savings_budget() для вызова sync_template_amount()

### Фаза 6: Calendar UI (4 шага)
16. Визуализация SAVINGS_RESERVE (иконка 💼, read-only tooltip)
17. Визуализация SAVINGS_CONTRIBUTION (иконка 🎯, editable)
18. Callback для редактирования SAVINGS_CONTRIBUTION (sync с GoalContribution)
19. Callback для удаления SAVINGS_CONTRIBUTION (cascade)

### Фаза 7: Тесты и финализация (3 шага)
20. Unit тесты для BudgetReservationService (20+ тестов)
21. Integration тесты для GoalService + BudgetReservationService + Calendar sync
22. Black, Flake8, pytest --cov

**Всего**: ~22 шагов, ~5-6 батчей

## Зависимости

Новые библиотеки не требуются. Все зависимости уже присутствуют:
- SQLAlchemy 2.0.23 (ORM)
- Dash 2.x + dash-bootstrap-components (UI)
- loguru (logging)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Конфликт при одновременном изменении режима и взносе | Низкая | flush/commit contract + session isolation |
| Некорректный расчет баланса с новыми типами | Средняя | Extensive unit tests для CalendarService |
| Синхронизация Transaction-GoalContribution при edit | Средняя | Транзакционность через flush + update_contribution_transaction |
| Каскадное удаление нарушает данные | Низкая | SET NULL FK + явный rollback в delete_contribution_transaction |
| Производительность расчета contributions_sum | Низкая | SQL агрегация + Index на contribution_date |
| EOM anchor для 31-го числа | Низкая | Переиспользование existing RecurringService._get_anchored_date() |
| Обратная совместимость со старыми взносами | Низкая | transaction_id nullable, legacy данные не затрагиваются |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 Import timedelta | Добавлен `from datetime import date, timedelta` в импорты BudgetReservationService |
| 🔴 CalendarService не обрабатывает новые типы | Добавлено детальное описание изменений во всех 4 методах: _calculate_balance_before_date(), _get_daily_changes(), _get_recurring_instances_for_period(), _get_recurring_daily_changes() |
| 🔴 Нет связи GoalContribution-Transaction | Добавлен GoalContribution.transaction_id FK с ondelete="SET NULL" |
| 🟡 Budget change | Добавлен метод sync_template_amount() в BudgetReservationService, вызывается из GoalService.update_savings_budget() |
| 🟡 SAVINGS_CONTRIBUTION в UI календаря | Добавлена Фаза 6 с 4 шагами: визуализация, tooltip, edit callback, delete callback |
| 🟡 Дублирование Anchored-алгоритма | _create_reserve_template() теперь вызывает self.recurring_service._get_anchored_date() |
| 🟡 Нет валидации при add_contribution | Добавлена валидация GoalStatus.COMPLETED и warning logging для budget=0 |
| 🟡 Нет индекса на contribution_date | Добавлен Index("ix_contribution_date", "contribution_date") в GoalContribution |
| 🟢 Status naming | Исправлено: 0-70%="success", 70-90%="warning", 90-100%="orange", >100%="danger" |
| 🟢 Docstrings на английском | Docstrings переведены на русский для consistency с CLAUDE.md |
| 🟢 Нет fallback для category_id | Добавлен комментарий в create_contribution_transaction: "category_id = NULL является нормой" |

## Ответы на вопросы критика

1. **Вопрос:** Связь Transaction-GoalContribution при edit
   **Ответ:** При изменении суммы SAVINGS_CONTRIBUTION в календаре вызывается `update_contribution_transaction()`, который АВТОМАТИЧЕСКИ:
   - Обновляет Transaction.amount
   - Находит связанный GoalContribution по transaction_id
   - Обновляет GoalContribution.amount
   - Пересчитывает Goal.current_amount (delta = new - old)
   - Проверяет/обновляет GoalStatus.COMPLETED

2. **Вопрос:** Изменение бюджета
   **Ответ:** При изменении monthly_savings_budget через GoalService.update_savings_budget() АВТОМАТИЧЕСКИ вызывается BudgetReservationService.sync_template_amount(), который обновляет amount существующего recurring шаблона "Резерв на цели". Новый шаблон НЕ создается.

3. **Вопрос:** Delete SAVINGS_CONTRIBUTION
   **Ответ:** КАСКАДНОЕ УДАЛЕНИЕ через delete_contribution_transaction():
   - Удаляет Transaction
   - Находит и удаляет связанный GoalContribution
   - Уменьшает Goal.current_amount на сумму взноса
   - Откатывает GoalStatus.COMPLETED → ACTIVE если была завершена

4. **Вопрос:** Режим по умолчанию
   **Ответ:** "from_balance" (из остатка) по умолчанию для новых пользователей. Это более гибкий режим, не требующий предварительного планирования. Brief не противоречит этому выбору (см. NFR-2: "режим 'Из остатка' по умолчанию").

5. **Вопрос:** EOM anchor для 31-го числа
   **Ответ:** Используется существующий паттерн recurring_anchor_eom из RecurringService:
   - day_of_month == 31 → anchor_eom = True в _create_reserve_template()
   - RecurringService._get_anchored_date() с anchor_eom=True возвращает последний день месяца
   - Это обеспечивает генерацию на 28 фев, 31 мар, 30 апр, 31 май и т.д.
