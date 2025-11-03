"""Скрипт для наполнения базы данных тестовыми данными."""

from datetime import date, timedelta
from decimal import Decimal
import sys
import os

# Добавляем корневую директорию проекта в путь импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.database import (
    init_database, get_session,
    User, Transaction, Goal, GoalContribution,
    TransactionType, GoalStatus
)
from app.services.goal_service import GoalService


def seed_database():
    """Наполняет базу данных тестовыми данными для разработки."""
    # Инициализация базы данных
    engine = init_database()
    session = get_session(engine)

    try:
        # Создание тестового пользователя
        user = User(
            name="Тестовый Пользователь",
            email="test@example.com",
            starting_balance=Decimal('50000.00')  # Начальный баланс 50К
        )
        session.add(user)
        session.flush()  # Получаем ID пользователя

        print(f"✅ Создан пользователь: {user.name} (ID: {user.id})")
        print(f"   Начальный баланс: {user.starting_balance} руб.")

        # Создание тестовых транзакций
        transactions = [
            # Доходы
            Transaction(
                user_id=user.id,
                amount=Decimal('80000.00'),
                transaction_type=TransactionType.INCOME,
                transaction_date=date.today() - timedelta(days=30),
                description="Зарплата за прошлый месяц",
                category="Зарплата"
            ),
            Transaction(
                user_id=user.id,
                amount=Decimal('85000.00'),
                transaction_type=TransactionType.INCOME,
                transaction_date=date.today() - timedelta(days=5),
                description="Зарплата текущего месяца",
                category="Зарплата"
            ),
            # Расходы
            Transaction(
                user_id=user.id,
                amount=Decimal('25000.00'),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date.today() - timedelta(days=28),
                description="Аренда квартиры",
                category="Жилье"
            ),
            Transaction(
                user_id=user.id,
                amount=Decimal('8000.00'),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date.today() - timedelta(days=20),
                description="Продукты питания",
                category="Продукты"
            ),
            Transaction(
                user_id=user.id,
                amount=Decimal('15000.00'),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date.today() - timedelta(days=10),
                description="Коммунальные платежи",
                category="ЖКХ"
            ),
        ]

        for transaction in transactions:
            session.add(transaction)

        print(f"✅ Создано транзакций: {len(transactions)}")

        # Создание тестовой накопительной цели
        goal = Goal(
            user_id=user.id,
            name="Отпуск в Турции",
            target_amount=Decimal('150000.00'),
            current_amount=Decimal('0'),  # Начинаем с 0
            target_date=date.today() + timedelta(days=180),  # Через 6 месяцев
            status=GoalStatus.ACTIVE,
            priority=1
        )
        session.add(goal)
        session.flush()

        print(f"✅ Создана цель: {goal.name} (ID: {goal.id})")

        # Используем GoalService для добавления взносов
        goal_service = GoalService(session)
        goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal('15000.00')
        )
        goal_service.add_contribution(
            goal_id=goal.id,
            amount=Decimal('15000.00')
        )
        # Теперь goal.current_amount автоматически = 30000

        # Создаем записи GoalContribution с историческими датами для отображения
        contributions = [
            GoalContribution(
                goal_id=goal.id,
                amount=Decimal('15000.00'),
                contribution_date=date.today() - timedelta(days=60),
                description="Первый взнос"
            ),
            GoalContribution(
                goal_id=goal.id,
                amount=Decimal('15000.00'),
                contribution_date=date.today() - timedelta(days=30),
                description="Второй взнос"
            ),
        ]

        for contribution in contributions:
            session.add(contribution)

        print(f"✅ Создано взносов в цель: {len(contributions)}")
        print(f"   Прогресс: {goal.current_amount}/{goal.target_amount} ({goal.progress_percentage:.1f}%)")

        # Сохранение всех изменений
        session.commit()
        print("\n🎉 База данных успешно наполнена тестовыми данными!")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Ошибка при наполнении базы данных: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()