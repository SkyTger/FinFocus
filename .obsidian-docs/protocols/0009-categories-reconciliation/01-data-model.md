# Шаг 1: Модель данных

## Briefing
- **Цель:** Создать модель Category, добавить TransactionType.ADJUSTMENT, заменить Transaction.category (String) на category_id (FK), создать seed для предзаполненных категорий.
- **Ключевые файлы:**
  - `app/models/database.py` (модифицировать)
  - `scripts/seed_categories.py` (создать)
  - `tests/test_category_model.py` (создать)
- **Additional info:**
  - Category.type: "income" | "expense" | "both" — для фильтрации в dropdown
  - Category.is_system: True для системной категории "Коррекция"
  - ADJUSTMENT влияет на баланс (может быть + или -)
  - Существующие транзакции сохранят category_id = NULL (нормальное состояние)

## Sub-tasks

### 1.1. Добавить TransactionType.ADJUSTMENT

В `app/models/database.py` добавить новое значение в enum:

```python
class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"  # NEW: корректировка сверки
```

### 1.2. Создать модель Category

В `app/models/database.py` добавить новую модель:

```python
class Category(Base):
    """Модель категории операций.

    Справочник с предзаполненными категориями расходов и доходов.
    Категории делятся на системные (is_system=True) и пользовательские.
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
```

### 1.3. Обновить модель Transaction

В `app/models/database.py` модифицировать Transaction:

1. **Удалить** старое поле `category = Column(String(50))` (если существует)
2. **Добавить** новые поля:

```python
# В классе Transaction:
category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

# Relationship
category_rel = relationship("Category", back_populates="transactions")
```

### 1.4. Создать скрипт seed категорий

Создать файл `scripts/seed_categories.py`:

```python
"""Скрипт для заполнения таблицы категорий предустановленными значениями.

Запуск: python scripts/seed_categories.py
Идемпотентный: можно запускать повторно.
"""

from app.core import get_db_session
from app.models.database import Category


DEFAULT_CATEGORIES = [
    # Системная категория для коррекций
    {"name": "Коррекция", "icon": "bi-arrow-repeat", "type": "both", "is_system": True, "sort_order": 0},

    # Расходы
    {"name": "Еда и продукты", "icon": "bi-cart", "type": "expense", "is_system": False, "sort_order": 1},
    {"name": "Транспорт", "icon": "bi-car-front", "type": "expense", "is_system": False, "sort_order": 2},
    {"name": "Жилье и ЖКХ", "icon": "bi-house", "type": "expense", "is_system": False, "sort_order": 3},
    {"name": "Связь и интернет", "icon": "bi-phone", "type": "expense", "is_system": False, "sort_order": 4},
    {"name": "Здоровье", "icon": "bi-heart-pulse", "type": "expense", "is_system": False, "sort_order": 5},
    {"name": "Одежда", "icon": "bi-bag", "type": "expense", "is_system": False, "sort_order": 6},
    {"name": "Развлечения", "icon": "bi-controller", "type": "expense", "is_system": False, "sort_order": 7},
    {"name": "Образование", "icon": "bi-book", "type": "expense", "is_system": False, "sort_order": 8},
    {"name": "Подарки другим", "icon": "bi-gift", "type": "expense", "is_system": False, "sort_order": 9},
    {"name": "Прочие расходы", "icon": "bi-three-dots", "type": "expense", "is_system": False, "sort_order": 10},

    # Доходы
    {"name": "Зарплата", "icon": "bi-briefcase", "type": "income", "is_system": False, "sort_order": 101},
    {"name": "Подработка", "icon": "bi-laptop", "type": "income", "is_system": False, "sort_order": 102},
    {"name": "Инвестиции", "icon": "bi-graph-up", "type": "income", "is_system": False, "sort_order": 103},
    {"name": "Подарки полученные", "icon": "bi-gift", "type": "income", "is_system": False, "sort_order": 104},
    {"name": "Прочие доходы", "icon": "bi-three-dots", "type": "income", "is_system": False, "sort_order": 105},
]


def seed_default_categories() -> int:
    """Заполняет таблицу категорий предустановленными значениями.

    Идемпотентный: пропускает категории, которые уже существуют (по имени).

    Returns:
        Количество добавленных категорий.
    """
    added_count = 0

    with get_db_session() as session:
        existing_names = {c.name for c in session.query(Category).all()}

        for cat_data in DEFAULT_CATEGORIES:
            if cat_data["name"] not in existing_names:
                category = Category(**cat_data)
                session.add(category)
                added_count += 1

        session.commit()

    return added_count


if __name__ == "__main__":
    count = seed_default_categories()
    print(f"Добавлено категорий: {count}")
```

### 1.5. Добавить TODO для production миграций

В начало `app/models/database.py` добавить комментарий:

```python
# TODO: При переходе в production использовать Alembic миграции
# вместо drop + create_all для изменения схемы БД.
# Текущий подход (пересоздание БД) допустим только для MVP/dev.
```

### 1.6. Написать unit тесты

Создать файл `tests/test_category_model.py`:

```python
"""Тесты для модели Category и TransactionType.ADJUSTMENT."""

import pytest
from app.models.database import Category, Transaction, TransactionType
from decimal import Decimal
from datetime import date


class TestCategoryModel:
    """Тесты модели Category."""

    def test_create_category(self, db_session):
        """Категория создается с корректными полями."""
        category = Category(
            name="Тестовая",
            icon="bi-test",
            type="expense",
            is_system=False,
            sort_order=999
        )
        db_session.add(category)
        db_session.flush()

        assert category.id is not None
        assert category.name == "Тестовая"
        assert category.icon == "bi-test"
        assert category.type == "expense"
        assert category.is_system is False

    def test_category_default_values(self, db_session):
        """Категория имеет корректные значения по умолчанию."""
        category = Category(name="Минимум", type="income")
        db_session.add(category)
        db_session.flush()

        assert category.icon == "bi-tag"
        assert category.is_system is False
        assert category.sort_order == 0


class TestTransactionCategoryRelation:
    """Тесты связи Transaction -> Category."""

    def test_transaction_with_category(self, db_session, sample_user):
        """Транзакция может иметь категорию."""
        category = Category(name="Еда", type="expense")
        db_session.add(category)
        db_session.flush()

        transaction = Transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id
        )
        db_session.add(transaction)
        db_session.flush()

        assert transaction.category_id == category.id
        assert transaction.category_rel.name == "Еда"

    def test_transaction_without_category(self, db_session, sample_user):
        """Транзакция может быть без категории (nullable)."""
        transaction = Transaction(
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=None
        )
        db_session.add(transaction)
        db_session.flush()

        assert transaction.category_id is None
        assert transaction.category_rel is None


class TestTransactionTypeAdjustment:
    """Тесты TransactionType.ADJUSTMENT."""

    def test_adjustment_type_exists(self):
        """ADJUSTMENT существует в TransactionType."""
        assert hasattr(TransactionType, "ADJUSTMENT")
        assert TransactionType.ADJUSTMENT.value == "adjustment"

    def test_create_adjustment_transaction(self, db_session, sample_user):
        """Можно создать транзакцию типа ADJUSTMENT."""
        transaction = Transaction(
            user_id=sample_user.id,
            amount=Decimal("-500.00"),  # Отрицательная корректировка
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
            description="Сверка баланса"
        )
        db_session.add(transaction)
        db_session.flush()

        assert transaction.transaction_type == TransactionType.ADJUSTMENT
        assert transaction.amount == Decimal("-500.00")
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 1.1-1.6.
2.  **Базовая проверка:** Убедись что код синтаксически корректен:
    - `python -m py_compile app/models/database.py`
    - `python -m py_compile scripts/seed_categories.py`
    - `python -m py_compile tests/test_category_model.py`
3.  **Пересоздание БД:** Для применения изменений схемы:
    - Удалить `data/finfocus.db`
    - Запустить `python -c "from app.core import init_database; init_database()"`
    - Запустить `python scripts/seed_categories.py`
4.  **Фиксация:** После успешной проверки:
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 2
    - Проверь ветку main
    - `git add . && git commit -m "feat(models): add Category model and ADJUSTMENT type [protocol-0009/01]"`
    - `git push`
5.  **Отчет пользователю** в установленном формате.
