"""Тесты для CategoryService."""

from app.models.database import Category
from app.services.category_service import CategoryService


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


class TestCategoryServiceGetById:
    """Тесты метода get_by_id."""

    def test_get_by_id_found(self, db_session):
        """Возвращает категорию по ID."""
        cat = Category(name="Тест", type="expense")
        db_session.add(cat)
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_by_id(cat.id)

        assert result is not None
        assert result.name == "Тест"

    def test_get_by_id_not_found(self, db_session):
        """Возвращает None если категория не найдена."""
        service = CategoryService(db_session)
        result = service.get_by_id(999)
        assert result is None


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

    def test_get_by_type_income(self, db_session):
        """Возвращает категории типа income и both."""
        cat_expense = Category(name="Еда", type="expense", sort_order=1)
        cat_income = Category(name="Зарплата", type="income", sort_order=2)
        cat_both = Category(name="Коррекция", type="both", sort_order=0)
        db_session.add_all([cat_expense, cat_income, cat_both])
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_by_type("income")

        names = [c.name for c in result]
        assert "Зарплата" in names
        assert "Коррекция" in names
        assert "Еда" not in names


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

    def test_get_for_dropdown_filter_by_type(self, db_session):
        """Фильтрация по типу работает."""
        cat_expense = Category(name="Еда", type="expense")
        cat_income = Category(name="Зарплата", type="income")
        db_session.add_all([cat_expense, cat_income])
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_for_dropdown(category_type="expense")

        labels = [c["label"] for c in result]
        assert "Еда" in labels
        assert "Зарплата" not in labels


class TestCategoryServiceGetSystemCategory:
    """Тесты метода get_system_category."""

    def test_get_system_category_found(self, db_session):
        """Возвращает системную категорию по имени."""
        cat = Category(name="Коррекция", type="both", is_system=True)
        db_session.add(cat)
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_system_category("Коррекция")

        assert result is not None
        assert result.name == "Коррекция"
        assert result.is_system is True

    def test_get_system_category_not_system(self, db_session):
        """Не возвращает обычную категорию с таким же именем."""
        cat = Category(name="Коррекция", type="both", is_system=False)
        db_session.add(cat)
        db_session.flush()

        service = CategoryService(db_session)
        result = service.get_system_category("Коррекция")

        assert result is None


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

    def test_seed_creates_system_category(self, db_session):
        """seed создает системную категорию 'Коррекция'."""
        service = CategoryService(db_session)
        service.seed_default_categories()

        correction = service.get_system_category("Коррекция")
        assert correction is not None
        assert correction.is_system is True
        assert correction.type == "both"
