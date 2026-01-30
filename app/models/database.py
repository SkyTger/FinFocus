"""
Модели базы данных для FinFocus.
Основные сущности: Пользователи, Операции, Цели накопления, Категории.
"""
# TODO: При переходе в production использовать Alembic миграции
# вместо drop + create_all для изменения схемы БД.
# Текущий подход (пересоздание БД) допустим только для MVP/dev.
from datetime import date
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Numeric,
    Boolean,
    ForeignKey,
    Enum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TransactionType(PyEnum):
    """Типы финансовых операций."""

    INCOME = "income"  # Доход
    EXPENSE = "expense"  # Расход
    TRANSFER = "transfer"  # Перевод
    ADJUSTMENT = "adjustment"  # Корректировка сверки


class GoalStatus(PyEnum):
    """Статусы накопительных целей."""

    ACTIVE = "active"  # Активная
    COMPLETED = "completed"  # Достигнута
    PAUSED = "paused"  # Приостановлена


class Category(Base):
    """Модель категории операций.

    Справочник с предзаполненными категориями расходов и доходов.
    Категории делятся на системные (is_system=True) и пользовательские.

    Attributes:
        name: Название категории (уникальное).
        icon: Bootstrap icon класс (bi-cart, bi-house, etc.).
        type: Тип категории - "income", "expense" или "both".
        is_system: True для системных категорий (Коррекция).
        sort_order: Порядок сортировки в UI.
    """

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(30), default="bi-tag")
    type = Column(String(10), nullable=False)  # "income" | "expense" | "both"
    is_system = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    # Relationships
    transactions = relationship("Transaction", back_populates="category_rel")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', type='{self.type}')>"


class User(Base):
    """Модель пользователя.

    Attributes:
        starting_balance: Начальный баланс для расчета кассового календаря.
            Формула: остаток = starting_balance + SUM(доходы) - SUM(расходы).
            Может быть отрицательным (долг), по умолчанию = 0.
        monthly_savings_budget: Ежемесячный бюджет на накопления.
            Используется AllocationService для расчета рекомендуемых взносов
            в накопительные цели по приоритетам. При = 0 UI показывает подсказку
            настроить бюджет. По умолчанию = 0.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    starting_balance = Column(Numeric(10, 2), default=0, nullable=False)
    monthly_savings_budget = Column(Numeric(10, 2), default=0, nullable=False)
    # Режим накоплений: "free" (100%), "medium" (115%), "strict" (150%)
    # Валидация допустимых значений в GoalService.update_savings_mode()
    savings_mode = Column(String(20), default="free", nullable=False)

    # Финансовая подушка безопасности
    cushion_target = Column(Numeric(12, 2), default=Decimal("0"))
    cushion_threshold_percent = Column(Integer, default=30)
    cushion_threshold_manual = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Связи
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")


class Transaction(Base):
    """Модель финансовой операции (доходы/расходы).

    Поддерживает повторяющиеся операции (recurring) через:
    - is_recurring: флаг шаблона
    - recurring_period: периодичность (monthly, weekly, etc.)
    - recurring_end_date: дата окончания серии (None = бессрочно)
    - recurring_parent_id: FK на шаблон (для exceptions)
    - original_date: исходная дата экземпляра (для exceptions)
    - is_skipped: пропущен ли экземпляр
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transaction_recurring_parent", "recurring_parent_id"),
        Index("ix_transaction_is_recurring", "is_recurring"),
        UniqueConstraint(
            "recurring_parent_id",
            "original_date",
            name="uq_recurring_exception_date",
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Основные поля
    amount = Column(Numeric(10, 2), nullable=False)  # Точность для денег
    transaction_type = Column(Enum(TransactionType), nullable=False)
    transaction_date = Column(Date, nullable=False)  # Дата операции
    description = Column(String(500))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Повторяющиеся операции (Recurring)
    is_recurring = Column(Boolean, default=False)
    recurring_period = Column(String(20))  # monthly, weekly, etc.
    recurring_end_date = Column(Date, nullable=True)  # Дата окончания серии
    recurring_parent_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=True,
    )  # FK на шаблон (для exceptions)
    original_date = Column(Date, nullable=True)  # Исходная дата экземпляра
    is_skipped = Column(Boolean, default=False, nullable=False)  # Пропущен ли экземпляр

    # Метаданные
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Связи
    user = relationship("User", back_populates="transactions")
    category_rel = relationship("Category", back_populates="transactions")
    recurring_parent = relationship(
        "Transaction",
        remote_side="Transaction.id",
        backref="recurring_exceptions",
    )

    @property
    def anchor_day(self) -> int | None:
        """День месяца для Anchored-алгоритма.

        Только для шаблонов (is_recurring=True).
        Возвращает день из transaction_date (start_date серии).

        Returns:
            int | None: День месяца (1-31) или None если не recurring.

        Note:
            GUARD CLAUSE: Если is_recurring=True, но transaction_date=None,
            логируем ошибку и возвращаем None (data integrity issue).
        """
        if not self.is_recurring:
            return None

        # Guard: проверяем transaction_date для recurring шаблона
        if self.transaction_date is None:
            from loguru import logger

            logger.error(
                f"Data integrity issue: Transaction {self.id} имеет "
                f"is_recurring=True, но transaction_date=None. "
                f"Это не должно происходить - проверьте данные."
            )
            return None

        return self.transaction_date.day

    @property
    def is_exception(self) -> bool:
        """Является ли транзакция исключением из recurring серии."""
        return self.recurring_parent_id is not None

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, "
            f"type={self.transaction_type.value}, amount={self.amount})>"
        )


class Goal(Base):
    """Модель накопительной цели."""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Основные поля
    name = Column(String(200), nullable=False)
    target_amount = Column(Numeric(10, 2), nullable=False)
    current_amount = Column(Numeric(10, 2), default=0)
    target_date = Column(Date, nullable=False)
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE)

    # Настройки накопления
    priority = Column(Integer, default=1)  # Приоритет (для Батча 2)

    # Метаданные
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Связи
    user = relationship("User", back_populates="goals")
    contributions = relationship(
        "GoalContribution", back_populates="goal", cascade="all, delete-orphan"
    )

    @property
    def progress_percentage(self) -> float:
        """Процент выполнения цели."""
        if self.target_amount == 0:
            return 0
        progress = float(self.current_amount / self.target_amount * 100)
        return min(progress, 100.0)

    @property
    def is_completed(self) -> bool:
        """Достигнута ли цель."""
        return self.current_amount >= self.target_amount

    @property
    def monthly_contribution(self) -> Decimal:
        """Рассчитывает рекомендуемый ежемесячный взнос для достижения цели.

        Формула: (target_amount - current_amount) / months_remaining

        Returns:
            Decimal: Рекомендуемый взнос. Возвращает 0 если:
                - target_date не установлен
                - target_date в прошлом или сегодня
                - цель уже достигнута (current >= target)
        """
        if not self.target_date:
            return Decimal("0")

        # Guard clause: deadline в прошлом или сегодня
        if self.target_date <= date.today():
            return Decimal("0")

        # Guard clause: цель уже достигнута
        if self.current_amount >= self.target_amount:
            return Decimal("0")

        # Рассчитываем months_remaining с минимумом 1 месяц
        days_remaining = (self.target_date - date.today()).days
        months_remaining = max(days_remaining / 30, 1)

        remaining_amount = self.target_amount - self.current_amount
        return remaining_amount / Decimal(months_remaining)

    def __repr__(self) -> str:
        progress = self.progress_percentage
        return f"<Goal(id={self.id}, name='{self.name}', progress={progress:.1f}%)>"


class GoalContribution(Base):
    """Модель взноса в накопительную цель."""

    __tablename__ = "goal_contributions"

    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)

    # Основные поля
    amount = Column(Numeric(10, 2), nullable=False)
    contribution_date = Column(Date, nullable=False)
    description = Column(String(500))

    # Метаданные
    created_at = Column(DateTime, default=func.now())

    # Связи
    goal = relationship("Goal", back_populates="contributions")

    def __repr__(self) -> str:
        return (
            f"<GoalContribution(id={self.id}, "
            f"amount={self.amount}, date={self.contribution_date})>"
        )
