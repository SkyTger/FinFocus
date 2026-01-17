"""
Модели базы данных для FinFocus.
Основные сущности: Пользователи, Операции, Цели накопления.
"""
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
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TransactionType(PyEnum):
    """Типы финансовых операций."""

    INCOME = "income"  # Доход
    EXPENSE = "expense"  # Расход
    TRANSFER = "transfer"  # Перевод


class GoalStatus(PyEnum):
    """Статусы накопительных целей."""

    ACTIVE = "active"  # Активная
    COMPLETED = "completed"  # Достигнута
    PAUSED = "paused"  # Приостановлена


class User(Base):
    """Модель пользователя.

    Attributes:
        starting_balance: Начальный баланс пользователя для расчета кассового календаря.
            Используется как базовая точка для расчета остатков по формуле:
            остаток = starting_balance + SUM(доходы) - SUM(расходы) до даты.
            Может быть отрицательным (долг), по умолчанию = 0.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    starting_balance = Column(Numeric(10, 2), default=0, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Связи
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")


class Transaction(Base):
    """Модель финансовой операции (доходы/расходы)."""

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Основные поля
    amount = Column(Numeric(10, 2), nullable=False)  # Точность для денег
    transaction_type = Column(Enum(TransactionType), nullable=False)
    transaction_date = Column(Date, nullable=False)  # Дата операции
    description = Column(String(500))
    category = Column(String(100))  # Категория (на будущее)

    # Повторяющиеся операции (на Батч 2)
    is_recurring = Column(Boolean, default=False)
    recurring_period = Column(String(20))  # monthly, weekly, etc.

    # Метаданные
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Связи
    user = relationship("User", back_populates="transactions")

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
        return f"<Goal(id={self.id}, name='{self.name}', progress={self.progress_percentage:.1f}%)>"


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
