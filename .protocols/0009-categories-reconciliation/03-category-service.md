# Шаг 3: CategoryService

## Briefing
- **Цель:** Создать сервис для работы с категориями: получение списка, фильтрация по типу, seed предустановленных категорий.
- **Ключевые файлы:**
  - `app/services/category_service.py` (создать)
  - `app/services/__init__.py` (модифицировать — добавить экспорт)
  - `tests/test_category_service.py` (создать)
- **Additional info:**
  - CategoryService следует паттерну других сервисов проекта (session в конструкторе)
  - get_for_dropdown() возвращает список CategoryOption для UI
  - seed_default_categories() идемпотентный — можно вызывать повторно

## Sub-tasks

### 3.1. Создать app/services/category_service.py

```python
"""Сервис для работы с категориями операций.

Предоставляет методы для получения и фильтрации категорий,
а также seed предустановленных категорий.
"""

from sqlalchemy.orm import Session

from app.models.database import Category
from app.schema.categories import CategoryOption


# Предустановленные категории для seed
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


class CategoryService:
    """Сервис для работы с категориями операций."""

    def __init__(self, session: Session):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy session для работы с БД.
        """
        self.session = session

    def get_all(self) -> list[Category]:
        """Получить все категории, отсортированные по sort_order.

        Returns:
            Список всех категорий.
        """
        return (
            self.session.query(Category)
            .order_by(Category.sort_order)
            .all()
        )

    def get_by_id(self, category_id: int) -> Category | None:
        """Получить категорию по ID.

        Args:
            category_id: ID категории.

        Returns:
            Категория или None если не найдена.
        """
        return self.session.query(Category).filter_by(id=category_id).first()

    def get_by_type(self, category_type: str) -> list[Category]:
        """Получить категории по типу.

        Args:
            category_type: Тип категории ("income", "expense", "both").

        Returns:
            Список категорий указанного типа + категории с type="both".
        """
        return (
            self.session.query(Category)
            .filter(
                (Category.type == category_type) | (Category.type == "both")
            )
            .order_by(Category.sort_order)
            .all()
        )

    def get_for_dropdown(
        self,
        category_type: str | None = None,
        include_system: bool = False
    ) -> list[CategoryOption]:
        """Получить категории в формате для dropdown UI.

        Args:
            category_type: Фильтр по типу ("income", "expense") или None для всех.
            include_system: Включать ли системные категории (is_system=True).

        Returns:
            Список CategoryOption для использования в dcc.Dropdown.
        """
        query = self.session.query(Category)

        # Фильтр по типу
        if category_type:
            query = query.filter(
                (Category.type == category_type) | (Category.type == "both")
            )

        # Фильтр системных категорий
        if not include_system:
            query = query.filter(Category.is_system == False)  # noqa: E712

        categories = query.order_by(Category.sort_order).all()

        return [
            CategoryOption(
                label=cat.name,
                value=cat.id,
                icon=cat.icon
            )
            for cat in categories
        ]

    def get_system_category(self, name: str = "Коррекция") -> Category | None:
        """Получить системную категорию по имени.

        Args:
            name: Имя системной категории.

        Returns:
            Системная категория или None.
        """
        return (
            self.session.query(Category)
            .filter_by(name=name, is_system=True)
            .first()
        )

    def seed_default_categories(self) -> int:
        """Заполнить таблицу предустановленными категориями.

        Идемпотентный метод: пропускает категории, которые уже существуют.

        Returns:
            Количество добавленных категорий.
        """
        existing_names = {c.name for c in self.session.query(Category).all()}
        added_count = 0

        for cat_data in DEFAULT_CATEGORIES:
            if cat_data["name"] not in existing_names:
                category = Category(**cat_data)
                self.session.add(category)
                added_count += 1

        self.session.flush()
        return added_count
```

### 3.2. Обновить app/services/__init__.py

Добавить экспорт CategoryService:

```python
from app.services.category_service import CategoryService

# В __all__ добавить:
"CategoryService",
```

### 3.3. Обновить scripts/seed_categories.py

Упростить скрипт, используя CategoryService:

```python
"""Скрипт для заполнения таблицы категорий предустановленными значениями.

Запуск: python scripts/seed_categories.py
Идемпотентный: можно запускать повторно.
"""

from app.core import get_db_session
from app.services import CategoryService


def main():
    """Запустить seed категорий."""
    with get_db_session() as session:
        service = CategoryService(session)
        count = service.seed_default_categories()
        session.commit()
        print(f"Добавлено категорий: {count}")


if __name__ == "__main__":
    main()
```

### 3.4. Написать unit тесты

Создать файл `tests/test_category_service.py`:

```python
"""Тесты для CategoryService."""

import pytest
from app.services.category_service import CategoryService
from app.models.database import Category


class TestCategoryServiceGetAll:
    """Тесты метода get_all."""

    def test_get_all_empty(self, db_session):
        """Возвращает пустой список если нет категорий."""
        service = CategoryService(db_session)
        result = service.get_all()
        assert result == []

    def test_get_all_sorted_by_sort_order(self, db_session):
        """Категории отсортированы по sort_order."""
        cat1 = Category(name="Z", type="expense", sort_order=10)
        cat2 = Category(name="A", type="expense", sort_order=1)
        db_session.add_all([cat1, cat2])
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_all()

        assert len(result) == 2
        assert result[0].name == "A"
        assert result[1].name == "Z"


class TestCategoryServiceGetByType:
    """Тесты метода get_by_type."""

    def test_get_by_type_expense(self, db_session):
        """Возвращает категории типа expense и both."""
        cat_expense = Category(name="Еда", type="expense", sort_order=1)
        cat_income = Category(name="Зарплата", type="income", sort_order=2)
        cat_both = Category(name="Коррекция", type="both", sort_order=0)
        db_session.add_all([cat_expense, cat_income, cat_both])
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_by_type("expense")

        names = [c.name for c in result]
        assert "Еда" in names
        assert "Коррекция" in names
        assert "Зарплата" not in names


class TestCategoryServiceGetForDropdown:
    """Тесты метода get_for_dropdown."""

    def test_get_for_dropdown_returns_category_option(self, db_session):
        """Возвращает список CategoryOption."""
        cat = Category(name="Еда", icon="bi-cart", type="expense", sort_order=1)
        db_session.add(cat)
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_for_dropdown()

        assert len(result) == 1
        assert result[0]["label"] == "Еда"
        assert result[0]["value"] == cat.id
        assert result[0]["icon"] == "bi-cart"

    def test_get_for_dropdown_excludes_system_by_default(self, db_session):
        """По умолчанию исключает системные категории."""
        cat_regular = Category(name="Еда", type="expense", is_system=False)
        cat_system = Category(name="Коррекция", type="both", is_system=True)
        db_session.add_all([cat_regular, cat_system])
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_for_dropdown()

        labels = [c["label"] for c in result]
        assert "Еда" in labels
        assert "Коррекция" not in labels

    def test_get_for_dropdown_include_system(self, db_session):
        """С include_system=True включает системные категории."""
        cat_system = Category(name="Коррекция", type="both", is_system=True)
        db_session.add(cat_system)
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_for_dropdown(include_system=True)

        labels = [c["label"] for c in result]
        assert "Коррекция" in labels


class TestCategoryServiceSeed:
    """Тесты метода seed_default_categories."""

    def test_seed_creates_categories(self, db_session):
        """seed_default_categories создает предустановленные категории."""
        service = CategoryService(db_session)
        count = service.seed_default_categories()

        assert count > 0
        all_cats = service.get_all()
        assert len(all_cats) == count

    def test_seed_is_idempotent(self, db_session):
        """Повторный вызов seed не создает дубликаты."""
        service = CategoryService(db_session)
        count1 = service.seed_default_categories()
        db_session.commit()

        count2 = service.seed_default_categories()

        assert count2 == 0
        all_cats = service.get_all()
        assert len(all_cats) == count1
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 3.1-3.4.
2.  **Базовая проверка:**
    - `python -m py_compile app/services/category_service.py`
    - `python -m py_compile scripts/seed_categories.py`
    - `python -m py_compile tests/test_category_service.py`
    - Проверь импорт: `python -c "from app.services import CategoryService; print('OK')"`
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 4
    - Проверь ветку main
    - `git add . && git commit -m "feat(services): add CategoryService [protocol-0009/03]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
