"""
Скрипт для создания тестовых данных в БД.
Добавляет пользователя и несколько транзакций для демонстрации.
"""
import sys
import os
from datetime import date, timedelta
from decimal import Decimal

# Добавляем путь к app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from models.database import create_database_engine, get_session, User, TransactionType
from services import TransactionService


def seed_test_data():
    """Создает тестовые данные в БД."""
    print("🌱 Seeding test data...")

    # Создаем engine и session
    engine = create_database_engine()
    session = get_session(engine)

    try:
        # Проверяем есть ли уже пользователь с id=1
        user = session.query(User).filter_by(id=1).first()

        if not user:
            # Создаем тестового пользователя
            user = User(
                id=1,
                email="ivan@example.com",
                name="Иван Иванов",
                starting_balance=Decimal("50000.00")
            )
            session.add(user)
            session.commit()
            print("✅ Создан пользователь: Иван Иванов")
        else:
            print("ℹ️  Пользователь уже существует")

        # Создаем сервис транзакций
        service = TransactionService(session)

        # Проверяем есть ли уже транзакции
        existing_txs = service.get_all_by_user(user_id=1)
        if len(existing_txs) > 0:
            print(f"ℹ️  Уже есть {len(existing_txs)} транзакций, пропускаем создание")
            return

        # Создаем тестовые транзакции
        test_transactions = [
            {
                "amount": Decimal("75000.00"),
                "transaction_type": TransactionType.INCOME,
                "transaction_date": date.today() - timedelta(days=5),
                "description": "Зарплата за январь"
            },
            {
                "amount": Decimal("3500.50"),
                "transaction_type": TransactionType.EXPENSE,
                "transaction_date": date.today() - timedelta(days=4),
                "description": "Продукты в супермаркете"
            },
            {
                "amount": Decimal("15000.00"),
                "transaction_type": TransactionType.EXPENSE,
                "transaction_date": date.today() - timedelta(days=3),
                "description": "Оплата аренды квартиры"
            },
            {
                "amount": Decimal("5000.00"),
                "transaction_type": TransactionType.INCOME,
                "transaction_date": date.today() - timedelta(days=2),
                "description": "Фриланс проект"
            },
            {
                "amount": Decimal("1200.00"),
                "transaction_type": TransactionType.EXPENSE,
                "transaction_date": date.today() - timedelta(days=1),
                "description": "Коммунальные услуги"
            },
            {
                "amount": Decimal("850.00"),
                "transaction_type": TransactionType.EXPENSE,
                "transaction_date": date.today(),
                "description": "Ресторан с друзьями"
            }
        ]

        created_count = 0
        for tx_data in test_transactions:
            service.create_transaction(
                user_id=1,
                **tx_data
            )
            created_count += 1

        session.commit()
        print(f"✅ Создано {created_count} тестовых транзакций")
        print("✨ Seeding завершен успешно!")

    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка: {e}")
        raise

    finally:
        session.close()


if __name__ == "__main__":
    seed_test_data()