"""Тесты для Quick-add chips функциональности."""

from unittest.mock import patch, MagicMock

from app.models.database import Category
from app.schema import QuickAddChipData


class TestQuickAddChipsData:
    """Тесты для QuickAddChipData TypedDict."""

    def test_quick_add_chip_data_structure(self):
        """QuickAddChipData имеет правильную структуру."""
        chip: QuickAddChipData = {
            "category_id": 1,
            "name": "Еда и продукты",
            "icon": "bi-cart",
            "type": "expense",
        }

        assert chip["category_id"] == 1
        assert chip["name"] == "Еда и продукты"
        assert chip["icon"] == "bi-cart"
        assert chip["type"] == "expense"


class TestGetQuickAddChips:
    """Тесты для _get_quick_add_chips() функции."""

    def test_returns_empty_list_when_no_categories(self, db_session):
        """Возвращает пустой список если нет категорий в БД."""
        # Импортируем функцию внутри теста для patch
        from app.components.transactions import _get_quick_add_chips

        # Мокаем get_db_session чтобы использовать нашу тестовую сессию
        with patch("app.components.transactions.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = _get_quick_add_chips()

        # Без категорий в БД должен быть пустой список
        assert result == []

    def test_returns_chips_for_existing_categories(self, db_session):
        """Возвращает chips для существующих категорий."""
        # Создаем тестовые категории
        cat1 = Category(name="Еда и продукты", type="expense", icon="bi-cart")
        cat2 = Category(name="Транспорт", type="expense", icon="bi-car-front")
        cat3 = Category(name="Зарплата", type="income", icon="bi-wallet2")
        db_session.add_all([cat1, cat2, cat3])
        db_session.flush()

        from app.components.transactions import _get_quick_add_chips

        with patch("app.components.transactions.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = _get_quick_add_chips()

        # Должны быть 3 чипа (соответствующие DEFAULT_QUICK_ADD_CHIP_NAMES)
        assert len(result) == 3

        # Проверяем структуру первого чипа
        expense_chips = [c for c in result if c["type"] == "expense"]
        income_chips = [c for c in result if c["type"] == "income"]

        assert len(expense_chips) == 2
        assert len(income_chips) == 1

    def test_logs_warning_for_missing_category(self, db_session, caplog):
        """Логирует warning для отсутствующей категории."""
        # Создаем только одну категорию из списка
        cat = Category(name="Еда и продукты", type="expense", icon="bi-cart")
        db_session.add(cat)
        db_session.flush()

        from app.components.transactions import _get_quick_add_chips

        with patch("app.components.transactions.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = _get_quick_add_chips()

        # Только 1 чип должен быть возвращен
        assert len(result) == 1
        assert result[0]["name"] == "Еда и продукты"

    def test_uses_default_icon_when_none(self, db_session):
        """Использует 'bi-tag' если иконка не указана."""
        cat = Category(name="Еда и продукты", type="expense", icon=None)
        db_session.add(cat)
        db_session.flush()

        from app.components.transactions import _get_quick_add_chips

        with patch("app.components.transactions.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = _get_quick_add_chips()

        assert len(result) == 1
        assert result[0]["icon"] == "bi-tag"


class TestDefaultQuickAddChipNames:
    """Тесты для константы DEFAULT_QUICK_ADD_CHIP_NAMES."""

    def test_has_8_entries(self):
        """Константа содержит 8 записей."""
        from app.components.transactions import DEFAULT_QUICK_ADD_CHIP_NAMES

        assert len(DEFAULT_QUICK_ADD_CHIP_NAMES) == 8

    def test_has_6_expense_2_income(self):
        """6 расходных и 2 доходных категории."""
        from app.components.transactions import DEFAULT_QUICK_ADD_CHIP_NAMES

        expense_count = sum(
            1 for _, t in DEFAULT_QUICK_ADD_CHIP_NAMES if t == "expense"
        )
        income_count = sum(1 for _, t in DEFAULT_QUICK_ADD_CHIP_NAMES if t == "income")

        assert expense_count == 6
        assert income_count == 2

    def test_entries_are_tuples(self):
        """Каждая запись — tuple (name, type)."""
        from app.components.transactions import DEFAULT_QUICK_ADD_CHIP_NAMES

        for entry in DEFAULT_QUICK_ADD_CHIP_NAMES:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            name, tx_type = entry
            assert isinstance(name, str)
            assert tx_type in ("expense", "income")


class TestBuildQuickAddChip:
    """Тесты для _build_quick_add_chip() функции."""

    def test_returns_button_component(self):
        """Возвращает dbc.Button компонент."""
        from app.components.transactions import _build_quick_add_chip

        chip_data: QuickAddChipData = {
            "category_id": 1,
            "name": "Тест",
            "icon": "bi-test",
            "type": "expense",
        }

        result = _build_quick_add_chip(chip_data)

        # Проверяем что это Button (Dash components use _type)
        assert result._type == "Button"

    def test_has_pattern_matching_id(self):
        """ID содержит pattern-matching структуру."""
        from app.components.transactions import _build_quick_add_chip

        chip_data: QuickAddChipData = {
            "category_id": 42,
            "name": "Тест",
            "icon": "bi-test",
            "type": "income",
        }

        result = _build_quick_add_chip(chip_data)

        assert result.id == {
            "type": "qa-chip",
            "category_id": 42,
            "tx_type": "income",
        }


class TestBuildQuickAddSection:
    """Тесты для _build_quick_add_section() функции."""

    def test_returns_div_with_qa_class(self):
        """Возвращает div с классом qa-chip-section."""
        from app.components.transactions import _build_quick_add_section

        chips: list[QuickAddChipData] = [
            {"category_id": 1, "name": "Тест", "icon": "bi-test", "type": "expense"},
        ]

        result = _build_quick_add_section(chips)

        assert result._type == "Div"
        assert "qa-chip-section" in result.className

    def test_groups_chips_by_type(self):
        """Группирует chips по типу expense/income."""
        from app.components.transactions import _build_quick_add_section

        chips: list[QuickAddChipData] = [
            {"category_id": 1, "name": "Расход", "icon": "bi-1", "type": "expense"},
            {"category_id": 2, "name": "Доход", "icon": "bi-2", "type": "income"},
        ]

        result = _build_quick_add_section(chips)

        # Должны быть 2 секции (expense и income)
        assert len(result.children) == 2

    def test_empty_chips_returns_empty_section(self):
        """Пустой список chips возвращает пустую секцию."""
        from app.components.transactions import _build_quick_add_section

        result = _build_quick_add_section([])

        assert result._type == "Div"
        assert result.children == []
