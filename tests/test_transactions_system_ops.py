"""Тесты маркировки служебных операций в списке операций (протокол 0032).

Покрывают чистые build-функции app/components/transactions.py:
бейджи всех шести типов транзакций, readonly-рендер служебных строк
(SAVINGS_RESERVE / SAVINGS_CONTRIBUTION — без чекбокса, кнопок и chips,
с подписью «(авто)»), решение Р1 (у ADJUSTMENT скрыт edit, delete
остаётся) и регрессию обычных строк.

БД не используется: функции принимают объекты Transaction в памяти
(по образцу test_dashboard_panel_ui.py), даты — относительные.
"""

from datetime import date, timedelta
from decimal import Decimal

import dash_bootstrap_components as dbc
import pytest
from dash import html

from app.components.transactions import (
    SYSTEM_TRANSACTION_TYPES,
    _build_chips_cell,
    _build_transactions_table,
    _is_system_transaction,
)
from app.models.database import Transaction, TransactionType
from app.services.transaction_service import TYPE_LABELS

# ===========================================================================
# Хелперы: обход дерева Dash-компонентов и фабрика транзакций
# ===========================================================================


def iter_tree(component):
    """Рекурсивный обход дерева Dash-компонентов (включая строки-листья)."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        yield from iter_tree(child)


def all_texts(component) -> list[str]:
    """Все строковые узлы дерева."""
    return [node for node in iter_tree(component) if isinstance(node, str)]


def find_by_id_type(component, id_type: str) -> list:
    """Все узлы с pattern-matching id вида {"type": id_type, ...}."""
    return [
        node
        for node in iter_tree(component)
        if isinstance(getattr(node, "id", None), dict)
        and node.id.get("type") == id_type
    ]


def find_badges(component) -> list:
    """Все dbc.Badge в дереве."""
    return [node for node in iter_tree(component) if isinstance(node, dbc.Badge)]


def make_tx(
    tx_type: TransactionType,
    *,
    tx_id: int = 1,
    amount: str = "1000",
    description: str | None = "Тестовая операция",
) -> Transaction:
    """Транзакция в памяти (без БД), дата — относительная."""
    return Transaction(
        id=tx_id,
        user_id=1,
        amount=Decimal(amount),
        transaction_type=tx_type,
        transaction_date=date.today() - timedelta(days=3),
        description=description,
    )


def build_single_row_table(tx: Transaction):
    """Таблица из одной транзакции → tbody для обхода."""
    thead, tbody = _build_transactions_table([tx])
    return tbody


# ===========================================================================
# Предикат служебности
# ===========================================================================


class TestSystemPredicate:
    """_is_system_transaction — единственный источник правды «служебности»."""

    @pytest.mark.parametrize(
        "tx_type,expected",
        [
            (TransactionType.INCOME, False),
            (TransactionType.EXPENSE, False),
            (TransactionType.TRANSFER, False),
            (TransactionType.ADJUSTMENT, False),
            (TransactionType.SAVINGS_RESERVE, True),
            (TransactionType.SAVINGS_CONTRIBUTION, True),
        ],
    )
    def test_predicate(self, tx_type, expected):
        assert _is_system_transaction(make_tx(tx_type)) is expected

    def test_system_types_set(self):
        """Служебные — строго два savings-типа."""
        assert SYSTEM_TRANSACTION_TYPES == frozenset(
            {TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION}
        )


# ===========================================================================
# Бейджи типов
# ===========================================================================


class TestTypeBadges:
    """Список различает все шесть типов транзакций."""

    @pytest.mark.parametrize(
        "tx_type,label",
        [
            (TransactionType.INCOME, "Доход"),
            (TransactionType.EXPENSE, "Расход"),
            (TransactionType.TRANSFER, "Перевод"),
            (TransactionType.ADJUSTMENT, "Корректировка"),
            (TransactionType.SAVINGS_RESERVE, "Накопления"),
            (TransactionType.SAVINGS_CONTRIBUTION, "Накопления"),
        ],
    )
    def test_badge_label(self, tx_type, label):
        tbody = build_single_row_table(make_tx(tx_type))
        badges = find_badges(tbody)
        assert len(badges) == 1
        assert badges[0].children == label

    def test_labels_source_is_service(self):
        """Подписи бейджей — из TYPE_LABELS сервиса (единый источник с CSV)."""
        assert set(TYPE_LABELS) == set(TransactionType)

    def test_savings_amount_has_minus(self):
        """Savings уменьшают баланс как расход — знак «−»."""
        tbody = build_single_row_table(make_tx(TransactionType.SAVINGS_RESERVE))
        amounts = [t for t in all_texts(tbody) if "₽" in t]
        assert len(amounts) == 1
        assert amounts[0].startswith("-")

    def test_adjustment_sign_follows_value(self):
        """У корректировки знак определяется значением суммы."""
        positive = build_single_row_table(
            make_tx(TransactionType.ADJUSTMENT, amount="500")
        )
        negative = build_single_row_table(
            make_tx(TransactionType.ADJUSTMENT, amount="-500")
        )
        pos_amount = next(t for t in all_texts(positive) if "₽" in t)
        neg_amount = next(t for t in all_texts(negative) if "₽" in t)
        assert pos_amount.startswith("+")
        assert not neg_amount.startswith("+")


# ===========================================================================
# Readonly-рендер служебных строк
# ===========================================================================


class TestSystemRowsReadonly:
    """У savings-строк нет органов управления."""

    @pytest.mark.parametrize(
        "tx_type",
        [TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION],
    )
    def test_no_controls_in_tree(self, tx_type):
        """Нет edit-btn / delete-btn / tx-checkbox в дереве строки."""
        tbody = build_single_row_table(make_tx(tx_type))
        assert find_by_id_type(tbody, "edit-btn") == []
        assert find_by_id_type(tbody, "delete-btn") == []
        assert find_by_id_type(tbody, "tx-checkbox") == []

    @pytest.mark.parametrize(
        "tx_type",
        [TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION],
    )
    def test_description_ends_with_auto(self, tx_type):
        """Описание служебной строки оканчивается «(авто)»."""
        tbody = build_single_row_table(make_tx(tx_type, description="Резерв"))
        descriptions = [t for t in all_texts(tbody) if t.endswith("(авто)")]
        assert descriptions == ["Резерв (авто)"]

    def test_description_fallback_when_empty(self):
        """Пустое описание → подпись типа + «(авто)», не «- (авто)»."""
        tbody = build_single_row_table(
            make_tx(TransactionType.SAVINGS_CONTRIBUTION, description=None)
        )
        descriptions = [t for t in all_texts(tbody) if t.endswith("(авто)")]
        assert descriptions == ["Накопления (авто)"]

    @pytest.mark.parametrize(
        "tx_type,title_fragment",
        [
            (TransactionType.SAVINGS_CONTRIBUTION, "через Цели"),
            (TransactionType.SAVINGS_RESERVE, "через настройку резервирования"),
        ],
    )
    def test_lock_title_explains_where_to_manage(self, tx_type, title_fragment):
        """Замок поясняет, откуда управлять операцией."""
        tbody = build_single_row_table(make_tx(tx_type))
        locks = [
            node
            for node in iter_tree(tbody)
            if getattr(node, "className", None) == "tx-system-lock"
        ]
        assert len(locks) == 1
        assert title_fragment in locks[0].title

    def test_system_row_has_dim_class(self):
        """Строка приглушена классом tx-system-row."""
        tbody = build_single_row_table(make_tx(TransactionType.SAVINGS_RESERVE))
        rows = [n for n in iter_tree(tbody) if isinstance(n, html.Tr)]
        assert len(rows) == 1
        assert rows[0].className == "tx-system-row"

    def test_no_chips_for_uncategorized_savings(self):
        """У savings-строки без категории нет chips — есть «—»."""
        tx = make_tx(TransactionType.SAVINGS_RESERVE)
        tbody = build_single_row_table(tx)
        assert find_by_id_type(tbody, "chip-btn") == []
        assert find_by_id_type(tbody, "chip-dropdown") == []
        assert "—" in all_texts(tbody)


# ===========================================================================
# Chips-guard напрямую
# ===========================================================================


class TestChipsCellGuard:
    """_build_chips_cell не категоризирует служебные и не-категоризируемые."""

    @pytest.mark.parametrize(
        "tx_type",
        [
            TransactionType.TRANSFER,
            TransactionType.ADJUSTMENT,
            TransactionType.SAVINGS_RESERVE,
            TransactionType.SAVINGS_CONTRIBUTION,
        ],
    )
    def test_dash_for_non_categorizable(self, tx_type):
        cell = _build_chips_cell(make_tx(tx_type), {}, [])
        assert isinstance(cell, html.Span)
        assert cell.children == "—"

    def test_expense_gets_chips_cell(self):
        """Регрессия: EXPENSE без категории получает chips-ячейку."""
        cell = _build_chips_cell(make_tx(TransactionType.EXPENSE), {}, [])
        assert not isinstance(cell, html.Span)


# ===========================================================================
# Регрессия обычных строк + решение Р1
# ===========================================================================


class TestUserRowsRegression:
    """У пользовательских строк всё на месте."""

    @pytest.mark.parametrize(
        "tx_type",
        [TransactionType.INCOME, TransactionType.EXPENSE],
    )
    def test_income_expense_full_controls(self, tx_type):
        """INCOME/EXPENSE: чекбокс + edit + delete."""
        tbody = build_single_row_table(make_tx(tx_type, tx_id=42))
        assert [n.id["index"] for n in find_by_id_type(tbody, "tx-checkbox")] == [42]
        assert [n.id["index"] for n in find_by_id_type(tbody, "edit-btn")] == [42]
        assert [n.id["index"] for n in find_by_id_type(tbody, "delete-btn")] == [42]

    def test_adjustment_no_edit_keeps_delete(self):
        """Р1: у ADJUSTMENT нет edit (модал не умеет тип), delete остаётся."""
        tbody = build_single_row_table(make_tx(TransactionType.ADJUSTMENT, tx_id=7))
        assert find_by_id_type(tbody, "edit-btn") == []
        assert [n.id["index"] for n in find_by_id_type(tbody, "delete-btn")] == [7]
        assert [n.id["index"] for n in find_by_id_type(tbody, "tx-checkbox")] == [7]

    def test_transfer_keeps_full_controls(self):
        """TRANSFER — полноценная пользовательская операция (решение плана)."""
        tbody = build_single_row_table(make_tx(TransactionType.TRANSFER, tx_id=9))
        assert len(find_by_id_type(tbody, "edit-btn")) == 1
        assert len(find_by_id_type(tbody, "delete-btn")) == 1
        assert len(find_by_id_type(tbody, "tx-checkbox")) == 1

    def test_user_rows_not_dimmed(self):
        """Обычные строки без класса приглушения."""
        tbody = build_single_row_table(make_tx(TransactionType.EXPENSE))
        rows = [n for n in iter_tree(tbody) if isinstance(n, html.Tr)]
        assert rows[0].className != "tx-system-row"


# ===========================================================================
# Серверные guard'ы (шаг 2 протокола 0032)
# ===========================================================================

from contextlib import contextmanager  # noqa: E402
from datetime import date as date_cls  # noqa: E402,F401
from unittest.mock import MagicMock, patch  # noqa: E402

from dash.exceptions import PreventUpdate  # noqa: E402

from app.components.transaction_modals import handle_delete_click  # noqa: E402
from app.components.transactions import (  # noqa: E402
    _drop_system_ids,
    chip_assign_category,
    chip_dropdown_assign_category,
    open_edit_modal,
    update_selection_state,
)


def _mock_session_cm():
    """Мок контекст-менеджера get_db_session()."""
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    return mock_session


class TestEditGuard:
    """open_edit_modal игнорирует служебные операции и ADJUSTMENT (Р1)."""

    @pytest.mark.parametrize(
        "tx_type",
        [
            TransactionType.SAVINGS_RESERVE,
            TransactionType.SAVINGS_CONTRIBUTION,
            TransactionType.ADJUSTMENT,
        ],
    )
    def test_edit_blocked(self, tx_type):
        tx = make_tx(tx_type, tx_id=5)
        with patch("app.components.transactions.ctx") as mock_ctx, patch(
            "app.components.transactions.get_db_session",
            return_value=_mock_session_cm(),
        ), patch("app.components.transactions.TransactionService") as mock_svc:
            mock_ctx.triggered_id = {"type": "edit-btn", "index": 5}
            mock_ctx.triggered = [{"value": 1}]
            mock_svc.return_value.get_by_id.return_value = tx
            with pytest.raises(PreventUpdate):
                open_edit_modal([1])

    def test_edit_allows_expense_regression(self):
        """Регрессия: EXPENSE редактируется как раньше (модал открыт)."""
        tx = make_tx(TransactionType.EXPENSE, tx_id=6)
        with patch("app.components.transactions.ctx") as mock_ctx, patch(
            "app.components.transactions.get_db_session",
            return_value=_mock_session_cm(),
        ), patch("app.components.transactions.TransactionService") as mock_svc, patch(
            "app.components.transactions.CategoryService"
        ) as mock_cat:
            mock_ctx.triggered_id = {"type": "edit-btn", "index": 6}
            mock_ctx.triggered = [{"value": 1}]
            mock_svc.return_value.get_by_id.return_value = tx
            mock_cat.return_value.get_for_dropdown.return_value = []
            result = open_edit_modal([1])
        assert result[0] is True  # edit-modal is_open


class TestDeleteGuard:
    """handle_delete_click игнорирует служебные операции."""

    @pytest.mark.parametrize(
        "tx_type",
        [TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION],
    )
    def test_delete_blocked(self, tx_type):
        tx = make_tx(tx_type, tx_id=5)
        with patch("app.components.transaction_modals.ctx") as mock_ctx, patch(
            "app.components.transaction_modals.get_db_session",
            return_value=_mock_session_cm(),
        ), patch("app.components.transaction_modals.TransactionService") as mock_svc:
            mock_ctx.triggered_id = {"type": "delete-btn", "index": 5}
            mock_ctx.triggered = [{"value": 1}]
            mock_svc.return_value.get_by_id.return_value = tx
            with pytest.raises(PreventUpdate):
                handle_delete_click([1])
            mock_svc.return_value.delete_transaction.assert_not_called()

    def test_delete_allows_expense_regression(self):
        """Регрессия: EXPENSE удаляется как раньше."""
        tx = make_tx(TransactionType.EXPENSE, tx_id=7)
        with patch("app.components.transaction_modals.ctx") as mock_ctx, patch(
            "app.components.transaction_modals.get_db_session",
            return_value=_mock_session_cm(),
        ), patch("app.components.transaction_modals.TransactionService") as mock_svc:
            mock_ctx.triggered_id = {"type": "delete-btn", "index": 7}
            mock_ctx.triggered = [{"value": 1}]
            mock_svc.return_value.get_by_id.return_value = tx
            mock_svc.return_value.delete_transaction.return_value = True
            modal_open, context, trigger = handle_delete_click([1])
        mock_svc.return_value.delete_transaction.assert_called_once_with(7)
        assert modal_open is False
        assert trigger["action"] == "delete"

    def test_delete_allows_adjustment(self):
        """Р1: корректировку сверки пользователь вправе откатить."""
        tx = make_tx(TransactionType.ADJUSTMENT, tx_id=8)
        with patch("app.components.transaction_modals.ctx") as mock_ctx, patch(
            "app.components.transaction_modals.get_db_session",
            return_value=_mock_session_cm(),
        ), patch("app.components.transaction_modals.TransactionService") as mock_svc:
            mock_ctx.triggered_id = {"type": "delete-btn", "index": 8}
            mock_ctx.triggered = [{"value": 1}]
            mock_svc.return_value.get_by_id.return_value = tx
            mock_svc.return_value.delete_transaction.return_value = True
            handle_delete_click([1])
        mock_svc.return_value.delete_transaction.assert_called_once_with(8)


class TestChipsGuards:
    """Chips-callbacks игнорируют назначение категории служебной операции."""

    @pytest.mark.parametrize(
        "tx_type",
        [TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION],
    )
    def test_chip_btn_blocked(self, tx_type):
        tx = make_tx(tx_type, tx_id=5)
        with patch("app.components.transactions.ctx") as mock_ctx, patch(
            "app.components.transactions.get_db_session",
            return_value=_mock_session_cm(),
        ), patch("app.components.transactions.TransactionService") as mock_svc:
            mock_ctx.triggered_id = {"type": "chip-btn", "tx_id": 5, "cat_id": 2}
            mock_ctx.triggered = [{"value": 1}]
            mock_svc.return_value.get_by_id.return_value = tx
            with pytest.raises(PreventUpdate):
                chip_assign_category([1], False, {})
            mock_svc.return_value.update_transaction.assert_not_called()

    @pytest.mark.parametrize(
        "tx_type",
        [TransactionType.SAVINGS_RESERVE, TransactionType.SAVINGS_CONTRIBUTION],
    )
    def test_chip_dropdown_blocked(self, tx_type):
        tx = make_tx(tx_type, tx_id=5)
        with patch("app.components.transactions.ctx") as mock_ctx, patch(
            "app.components.transactions.get_db_session",
            return_value=_mock_session_cm(),
        ), patch("app.components.transactions.TransactionService") as mock_svc:
            mock_ctx.triggered_id = {"type": "chip-dropdown", "tx_id": 5}
            mock_ctx.triggered = [{"value": 2}]
            mock_svc.return_value.get_by_id.return_value = tx
            with pytest.raises(PreventUpdate):
                chip_dropdown_assign_category([2], False, {})
            mock_svc.return_value.update_transaction.assert_not_called()


class TestSelectionGuard:
    """Служебные id не попадают в bulk-выборку (страховка поверх UI)."""

    @contextmanager
    def _fake_get_db_session(self, session):
        yield session

    def _make_db_pair(self, db_session, test_user):
        """EXPENSE + SAVINGS_RESERVE в БД, возвращает (exp_id, sav_id)."""
        expense = Transaction(
            user_id=test_user.id,
            amount=Decimal("100"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            is_recurring=False,
        )
        savings = Transaction(
            user_id=test_user.id,
            amount=Decimal("200"),
            transaction_type=TransactionType.SAVINGS_RESERVE,
            transaction_date=date.today(),
            is_recurring=False,
        )
        db_session.add_all([expense, savings])
        db_session.flush()
        return expense.id, savings.id

    def test_drop_system_ids(self, db_session, test_user):
        exp_id, sav_id = self._make_db_pair(db_session, test_user)
        with patch(
            "app.components.transactions.get_db_session",
            new=lambda: self._fake_get_db_session(db_session),
        ):
            assert _drop_system_ids([exp_id, sav_id]) == [exp_id]

    def test_drop_system_ids_empty(self):
        """Пустая выборка — без обращения к БД."""
        assert _drop_system_ids([]) == []

    def test_select_all_excludes_system(self, db_session, test_user):
        """Select All с устаревшим DOM не захватывает служебные."""
        exp_id, sav_id = self._make_db_pair(db_session, test_user)
        checkbox_ids = [{"index": exp_id}, {"index": sav_id}]
        with patch("app.components.transactions.ctx") as mock_ctx, patch(
            "app.components.transactions.get_db_session",
            new=lambda: self._fake_get_db_session(db_session),
        ):
            mock_ctx.triggered_id = "select-all-checkbox"
            selected = update_selection_state([True, True], True, checkbox_ids)
        assert selected == [exp_id]

    def test_individual_selection_excludes_system(self, db_session, test_user):
        exp_id, sav_id = self._make_db_pair(db_session, test_user)
        checkbox_ids = [{"index": exp_id}, {"index": sav_id}]
        with patch("app.components.transactions.ctx") as mock_ctx, patch(
            "app.components.transactions.get_db_session",
            new=lambda: self._fake_get_db_session(db_session),
        ):
            mock_ctx.triggered_id = {"type": "tx-checkbox", "index": sav_id}
            selected = update_selection_state([True, True], None, checkbox_ids)
        assert selected == [exp_id]
