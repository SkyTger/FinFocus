# Шаг 5: Unit тесты

## Briefing
- **Цель:** Создать unit тесты для DashboardService и новых методов CalendarService (get_balance_on_date, get_year_summary).
- **Ключевые файлы:**
  - `tests/test_dashboard_service.py` (создать)
  - `tests/test_calendar_service.py` (добавить тесты)
- **Additional info:**
  - Использовать существующие fixtures из conftest.py (db_session, test_user)
  - Минимум 9 тестов для DashboardService + 2 теста для CalendarService
  - Покрыть edge cases: пустая БД, нет целей, разные периоды
  - Использовать паттерн из tests/test_calendar_service.py

## Sub-tasks

### 5.1. Создать файл tests/test_dashboard_service.py

```python
"""Тесты для DashboardService."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.database import Goal, GoalStatus, Transaction, TransactionType
from app.services.dashboard_service import DashboardService


class TestGetOverviewMetrics:
    """Тесты для get_overview_metrics."""

    def test_with_transactions_month_period(self, db_session, test_user):
        """Метрики за месяц с транзакциями."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
                description="Зарплата",
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("2000.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 10),
                description="Аренда",
            )
        )
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_overview_metrics(
            test_user.id,
            period="month",
            reference_date=date(2026, 1, 19),
        )

        # Assert
        # Total balance = starting_balance (10000) + 5000 - 2000 = 13000
        assert result["total_balance"] == Decimal("13000.00")
        assert result["period_income"] == Decimal("5000.00")
        assert result["period_expense"] == Decimal("2000.00")

    def test_empty_database(self, db_session, test_user):
        """Пустая БД - нулевые метрики (кроме starting_balance)."""
        service = DashboardService(db_session)

        result = service.get_overview_metrics(
            test_user.id,
            period="month",
            reference_date=date(2026, 1, 19),
        )

        # starting_balance = 10000 (из test_user fixture)
        assert result["total_balance"] == Decimal("10000.00")
        assert result["period_income"] == Decimal("0")
        assert result["period_expense"] == Decimal("0")

    def test_year_period(self, db_session, test_user):
        """Метрики за год агрегируют транзакции из разных месяцев."""
        # Arrange - транзакции в разных месяцах
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("10000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("20000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 6, 15),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_overview_metrics(
            test_user.id,
            period="year",
            reference_date=date(2026, 6, 30),
        )

        # Assert - должны суммироваться оба дохода
        assert result["period_income"] == Decimal("30000.00")

    def test_savings_with_active_goal(self, db_session, test_user):
        """Savings отображает данные активной цели."""
        # Arrange
        goal = Goal(
            user_id=test_user.id,
            name="Отпуск",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("25000.00"),
            target_date=date(2026, 12, 31),
            status=GoalStatus.ACTIVE,
        )
        db_session.add(goal)
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_overview_metrics(test_user.id, period="month")

        # Assert
        assert result["savings_current"] == Decimal("25000.00")
        assert result["savings_target"] == Decimal("100000.00")
        assert result["savings_name"] == "Отпуск"
        assert result["savings_progress"] == 25.0

    def test_savings_no_goals(self, db_session, test_user):
        """Нет активных целей - нулевые savings."""
        service = DashboardService(db_session)

        result = service.get_overview_metrics(test_user.id, period="month")

        assert result["savings_current"] == Decimal("0")
        assert result["savings_target"] == Decimal("0")
        assert result["savings_name"] is None
        assert result["savings_progress"] == 0.0

    def test_transfer_excluded_from_balance(self, db_session, test_user):
        """TRANSFER транзакции не влияют на баланс."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.TRANSFER,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_overview_metrics(
            test_user.id,
            period="month",
            reference_date=date(2026, 1, 19),
        )

        # Assert - баланс не изменился от transfer
        assert result["total_balance"] == Decimal("10000.00")
        assert result["period_income"] == Decimal("0")
        assert result["period_expense"] == Decimal("0")


class TestGetCashflowData:
    """Тесты для get_cashflow_data."""

    def test_returns_12_months(self, db_session, test_user):
        """Возвращает данные за 12 месяцев."""
        service = DashboardService(db_session)

        result = service.get_cashflow_data(
            test_user.id,
            period="month",
            reference_date=date(2026, 1, 19),
        )

        assert len(result) == 12

    def test_returns_5_years(self, db_session, test_user):
        """Возвращает данные за 5 лет."""
        service = DashboardService(db_session)

        result = service.get_cashflow_data(
            test_user.id,
            period="year",
            reference_date=date(2026, 1, 19),
        )

        assert len(result) == 5
        assert result[0]["label"] == "2022"
        assert result[4]["label"] == "2026"

    def test_aggregates_by_month(self, db_session, test_user):
        """Данные агрегируются по месяцам."""
        # Arrange - несколько транзакций в одном месяце
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("1000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 5),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("2000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_cashflow_data(
            test_user.id,
            period="month",
            reference_date=date(2026, 1, 19),
        )

        # Assert - январь должен иметь сумму 3000
        january = next(d for d in result if d["label"] == "Янв")
        assert january["income"] == Decimal("3000.00")


class TestGetRecentTransactions:
    """Тесты для get_recent_transactions."""

    def test_sorting_desc(self, db_session, test_user):
        """Сортировка по дате DESC, id DESC."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("100.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 10),
                description="Первая",
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("200.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 15),
                description="Вторая",
            )
        )
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_recent_transactions(test_user.id, limit=5)

        # Assert - более поздняя дата первой
        assert len(result) == 2
        assert result[0]["description"] == "Вторая"
        assert result[1]["description"] == "Первая"

    def test_respects_limit(self, db_session, test_user):
        """Ограничение количества работает."""
        # Arrange - создаем 10 транзакций
        for i in range(10):
            db_session.add(
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("100.00"),
                    transaction_type=TransactionType.INCOME,
                    transaction_date=date(2026, 1, i + 1),
                )
            )
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_recent_transactions(test_user.id, limit=5)

        # Assert
        assert len(result) == 5

    def test_empty_list_when_no_transactions(self, db_session, test_user):
        """Возвращает пустой список если нет транзакций."""
        service = DashboardService(db_session)

        result = service.get_recent_transactions(test_user.id, limit=5)

        assert result == []
```

### 5.2. Добавить тесты в tests/test_calendar_service.py

Добавить в конец файла:

```python
class TestGetBalanceOnDate:
    """Тесты для get_balance_on_date."""

    def test_balance_includes_target_date(self, db_session, test_user):
        """Баланс включает транзакции на указанную дату."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)

        # Act
        result = service.get_balance_on_date(test_user.id, date(2026, 1, 15))

        # Assert - starting_balance (10000) + 5000 = 15000
        assert result == Decimal("15000.00")

    def test_balance_excludes_future_transactions(self, db_session, test_user):
        """Баланс не включает транзакции после указанной даты."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 20),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)

        # Act
        result = service.get_balance_on_date(test_user.id, date(2026, 1, 15))

        # Assert - только starting_balance, транзакция в будущем
        assert result == Decimal("10000.00")


class TestGetYearSummary:
    """Тесты для get_year_summary."""

    def test_aggregates_full_year(self, db_session, test_user):
        """Агрегирует транзакции за весь год."""
        # Arrange
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("10000.00"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000.00"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 6, 15),
            )
        )
        db_session.commit()

        service = CalendarService(db_session)

        # Act
        result = service.get_year_summary(test_user.id, 2026)

        # Assert
        assert result["total_income"] == Decimal("10000.00")
        assert result["total_expense"] == Decimal("5000.00")
        assert result["year"] == 2026

    def test_empty_year_returns_zeros(self, db_session, test_user):
        """Пустой год возвращает нули."""
        service = CalendarService(db_session)

        result = service.get_year_summary(test_user.id, 2025)

        assert result["total_income"] == Decimal("0")
        assert result["total_expense"] == Decimal("0")
```

## Workflow (Порядок работы)

1. **Выполнение:** Создай файл тестов и добавь тесты в существующий файл.
2. **Верификация:** После завершения запусти тесты:
   ```bash
   cd /home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration
   pytest tests/test_dashboard_service.py -v
   pytest tests/test_calendar_service.py -v -k "balance_on_date or year_summary"
   black tests/
   flake8 tests/
   ```
3. **Фиксация:** После успешной верификации:
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 6
   - Проверь ветку main
4. **Коммит**: `git add . && git commit -m "test(dashboard): add unit tests for DashboardService [protocol-0003/05]"`. Push.
5. **Отчет пользователю** в установленном формате.
