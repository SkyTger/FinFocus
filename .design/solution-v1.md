# Solution v1: Budget-Calendar Integration с новым TransactionType

## Обзор решения

Интеграция реализуется через добавление нового типа транзакций `TransactionType.SAVINGS_RESERVE` для режима "Фиксированная дата" и `TransactionType.SAVINGS_CONTRIBUTION` для режима "Из остатка". Новый сервис `BudgetReservationService` управляет созданием/остановкой recurring шаблона "Резерв на цели" и расчетом доступного бюджета. Переиспользуется существующий Anchored-алгоритм из RecurringService.

## Архитектура

### Компоненты

**1. BudgetReservationService** (новый)
- Управляет режимами резервирования бюджета
- Создает/останавливает recurring шаблон "Резерв на цели"
- Рассчитывает `available_budget` = budget - contributions_this_month
- Создает операции SAVINGS_CONTRIBUTION при взносе в режиме "Из остатка"

**2. GoalService** (расширение)
- Метод `add_contribution()` расширяется для создания транзакции в режиме "Из остатка"
- Новые поля User: `reservation_mode` ("fixed_date" | "from_balance"), `reservation_day` (1-31)

**3. CalendarService** (расширение)
- Обработка SAVINGS_RESERVE и SAVINGS_CONTRIBUTION в расчетах баланса
- Оба типа уменьшают баланс (как EXPENSE)

**4. Goals UI** (расширение)
- Карточка "Бюджет накоплений" над списком целей
- Расширенный модал настройки бюджета с выбором режима

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
  type=SAVINGS_RESERVE)                       |
        |                                     |
        v                                     v
CalendarService.                      GoalService.
calculate_daily_balances()            add_contribution()
(учитывает SAVINGS_RESERVE)                   |
                                              v
                                    Transaction(type=
                                      SAVINGS_CONTRIBUTION)
```

## Файловая структура

```
app/models/database.py            — добавить SAVINGS_RESERVE, SAVINGS_CONTRIBUTION в TransactionType
                                  — добавить User.reservation_mode, User.reservation_day

app/schema/budget_reservation.py  — новый файл с TypedDicts:
                                    BudgetReservationSettings, BudgetProgress

app/services/budget_reservation_service.py — новый BudgetReservationService

app/services/goal_service.py      — расширить add_contribution() для создания транзакции
                                  — добавить get/set_reservation_mode()

app/services/calendar_service.py  — добавить SAVINGS_RESERVE и SAVINGS_CONTRIBUTION в расчеты

app/services/__init__.py          — экспорт BudgetReservationService

app/components/goals.py           — карточка бюджета, расширенный модал

tests/test_budget_reservation_service.py — unit тесты
tests/test_goal_service_contribution.py  — тесты add_contribution с режимами
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
    status: str  # "ok" | "warning" | "danger" | "over"
    mode: ReservationMode
    mode_text: str  # "Распределено" | "Внесено"


# === app/services/budget_reservation_service.py ===

from datetime import date
from decimal import Decimal
from typing import TypedDict

from sqlalchemy.orm import Session
from loguru import logger

from app.core.exceptions import ValidationError
from app.models.database import (
    User, Transaction, TransactionType, GoalContribution
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
        """Инициализация сервиса."""
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

        # Найти существующий шаблон "Резерв на цели"
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
        user.reservation_mode = mode
        user.reservation_day = day_of_month if mode == "fixed_date" else None

        # Управление recurring шаблоном
        if mode == "fixed_date" and old_mode != "fixed_date":
            self._create_reserve_template(user_id, day_of_month)
        elif mode == "from_balance" and old_mode == "fixed_date":
            self._stop_reserve_template(user_id)
        elif mode == "fixed_date" and old_mode == "fixed_date":
            # Изменился день — пересоздать шаблон
            self._stop_reserve_template(user_id)
            self._create_reserve_template(user_id, day_of_month)

        self.session.flush()
        logger.info(
            f"Режим резервирования для user {user_id} изменен: "
            f"{old_mode} -> {mode}"
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

        # Получить сумму взносов за текущий месяц
        used = self._get_contributions_sum_for_month(user_id, ref_date)
        total = user.monthly_savings_budget
        available = max(Decimal("0"), total - used)

        # Рассчитать процент
        progress = float(used / total * 100) if total > 0 else 0.0

        # Определить статус
        if total == 0:
            status = "ok"
        elif progress > 100:
            status = "over"
        elif progress >= 90:
            status = "danger"
        elif progress >= 70:
            status = "warning"
        else:
            status = "ok"

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
        )

        self.session.add(transaction)
        self.session.flush()

        logger.info(
            f"Создана транзакция SAVINGS_CONTRIBUTION для user {user_id}: "
            f"{amount} -> {goal_name}"
        )

        return transaction

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

    def _create_reserve_template(self, user_id: int, day_of_month: int) -> Transaction:
        """Создает recurring шаблон "Резерв на цели"."""
        user = self.session.get(User, user_id)

        # Определить первую дату (текущий или следующий месяц)
        today = date.today()
        if today.day <= day_of_month:
            # В этом месяце еще не прошла дата
            from calendar import monthrange
            _, last_day = monthrange(today.year, today.month)
            actual_day = min(day_of_month, last_day)
            start_date = date(today.year, today.month, actual_day)
        else:
            # Уже прошла, начинаем со следующего месяца
            if today.month == 12:
                start_date = date(today.year + 1, 1, day_of_month)
            else:
                from calendar import monthrange
                _, last_day = monthrange(today.year, today.month + 1)
                actual_day = min(day_of_month, last_day)
                start_date = date(today.year, today.month + 1, actual_day)

        template = Transaction(
            user_id=user_id,
            amount=user.monthly_savings_budget,
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=start_date,
            description=self.RESERVE_DESCRIPTION,
            is_recurring=True,
            recurring_period="monthly",
            recurring_end_date=None,  # Бессрочно
        )

        self.session.add(template)
        self.session.flush()

        logger.info(
            f"Создан шаблон SAVINGS_RESERVE для user {user_id}: "
            f"day={day_of_month}, amount={user.monthly_savings_budget}"
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

        first_day = date(reference_date.year, reference_date.month, 1)
        _, last_day_num = monthrange(reference_date.year, reference_date.month)
        last_day = date(reference_date.year, reference_date.month, last_day_num)

        from sqlalchemy import func
        from app.models.database import Goal

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
    """День месяца для режима "fixed_date" (1-31). Null для "from_balance"."""
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

### TypedDicts в app/schema/budget_reservation.py:
```python
ReservationMode = Literal["fixed_date", "from_balance"]

class BudgetReservationSettings(TypedDict):
    mode: ReservationMode
    day_of_month: int | None
    monthly_budget: Decimal
    template_id: int | None

class BudgetProgress(TypedDict):
    total_budget: Decimal
    used_budget: Decimal
    available_budget: Decimal
    progress_percent: float
    status: str  # "ok" | "warning" | "danger" | "over"
    mode: ReservationMode
    mode_text: str
```

## Обработка ошибок

```python
# Использовать существующий ValidationError из app/core/exceptions.py

# В BudgetReservationService:
if mode not in ("fixed_date", "from_balance"):
    raise ValidationError(
        f"Недопустимый режим: {mode}",
        field="mode"
    )

if mode == "fixed_date" and not 1 <= day_of_month <= 31:
    raise ValidationError(
        "День месяца должен быть от 1 до 31",
        field="day_of_month"
    )

# В CalendarService (для read-only операций):
# SAVINGS_RESERVE клик -> tooltip с объяснением
# Не выбрасывать ошибку, просто блокировать редактирование
```

## План реализации

### Фаза 1: Database Schema (1 шаг)
1. Добавить SAVINGS_RESERVE, SAVINGS_CONTRIBUTION в TransactionType
2. Добавить User.reservation_mode, User.reservation_day
3. Создать migration script (scripts/migrate_004_reservation_mode.py)

### Фаза 2: BudgetReservationService (3 шага)
4. Создать app/schema/budget_reservation.py с TypedDicts
5. Создать BudgetReservationService с get_settings, set_mode, get_budget_progress
6. Интегрировать с RecurringService для создания/остановки шаблона

### Фаза 3: GoalService интеграция (2 шага)
7. Расширить add_contribution() для вызова create_contribution_transaction()
8. Добавить get_reservation_mode(), set_reservation_mode() прокси-методы

### Фаза 4: CalendarService интеграция (2 шага)
9. Добавить SAVINGS_RESERVE и SAVINGS_CONTRIBUTION в _calculate_balance_before_date()
10. Добавить в _get_daily_changes() обработку как EXPENSE

### Фаза 5: Goals UI (4 шага)
11. Создать _build_budget_progress_card() для карточки бюджета
12. Расширить _build_budget_modal() для выбора режима и дня
13. Добавить callbacks для режима и обновления карточки
14. Добавить dcc.Store для budget_progress

### Фаза 6: Calendar UI (2 шага)
15. Визуализация SAVINGS_RESERVE в ячейке (иконка 💼, нейтральный цвет)
16. Блокировка редактирования системных операций (tooltip)

### Фаза 7: Тесты и финализация (3 шага)
17. Unit тесты для BudgetReservationService (15+ тестов)
18. Integration тесты для GoalService + BudgetReservationService
19. Black, Flake8, pytest --cov

**Всего**: ~17 шагов, ~4-5 батчей

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
| Сложность UI модала с двумя режимами | Средняя | Пошаговая разработка, сначала логика потом UI |
| Производительность расчета contributions_sum | Низкая | SQL агрегация, индекс на contribution_date |
| Обратная совместимость со старыми взносами | Низкая | Режим "from_balance" по умолчанию, старые взносы не затрагиваются |
