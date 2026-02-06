"""Тесты для DashboardService."""

from datetime import date
from decimal import Decimal

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
        assert result["savings_name"] == "Нет целей"
        assert result["savings_progress"] == 0.0

    def test_savings_multiple_active_goals(self, db_session, test_user):
        """Метрики агрегируют savings по нескольким активным целям."""
        # Arrange - создаем 3 активных цели
        goals = [
            Goal(
                user_id=test_user.id,
                name="Отпуск",
                target_amount=Decimal("100000.00"),
                current_amount=Decimal("25000.00"),
                target_date=date(2026, 12, 31),
                status=GoalStatus.ACTIVE,
                priority=1,
            ),
            Goal(
                user_id=test_user.id,
                name="Автомобиль",
                target_amount=Decimal("500000.00"),
                current_amount=Decimal("150000.00"),
                target_date=date(2027, 6, 30),
                status=GoalStatus.ACTIVE,
                priority=2,
            ),
            Goal(
                user_id=test_user.id,
                name="Ремонт",
                target_amount=Decimal("200000.00"),
                current_amount=Decimal("50000.00"),
                target_date=date(2027, 12, 31),
                status=GoalStatus.ACTIVE,
                priority=3,
            ),
        ]
        for goal in goals:
            db_session.add(goal)
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_overview_metrics(test_user.id, period="month")

        # Assert - должны суммироваться все активные цели
        # total_current = 25000 + 150000 + 50000 = 225000
        # total_target = 100000 + 500000 + 200000 = 800000
        # progress = 225000 / 800000 * 100 = 28.125%
        assert result["savings_current"] == Decimal("225000.00")
        assert result["savings_target"] == Decimal("800000.00")
        assert result["savings_name"] == "3 целей"
        assert result["savings_progress"] == 28.125

    def test_savings_mixed_statuses(self, db_session, test_user):
        """Учитываются только ACTIVE цели, PAUSED и COMPLETED игнорируются."""
        # Arrange
        goals = [
            Goal(
                user_id=test_user.id,
                name="Активная цель",
                target_amount=Decimal("100000.00"),
                current_amount=Decimal("30000.00"),
                target_date=date(2026, 12, 31),
                status=GoalStatus.ACTIVE,
                priority=1,
            ),
            Goal(
                user_id=test_user.id,
                name="Приостановленная",
                target_amount=Decimal("50000.00"),
                current_amount=Decimal("10000.00"),
                target_date=date(2027, 6, 30),
                status=GoalStatus.PAUSED,
                priority=2,
            ),
            Goal(
                user_id=test_user.id,
                name="Завершенная",
                target_amount=Decimal("20000.00"),
                current_amount=Decimal("20000.00"),
                target_date=date(2025, 12, 31),
                status=GoalStatus.COMPLETED,
                priority=3,
            ),
        ]
        for goal in goals:
            db_session.add(goal)
        db_session.commit()

        service = DashboardService(db_session)

        # Act
        result = service.get_overview_metrics(test_user.id, period="month")

        # Assert - только активная цель учитывается
        assert result["savings_current"] == Decimal("30000.00")
        assert result["savings_target"] == Decimal("100000.00")
        assert result["savings_name"] == "Активная цель"
        assert result["savings_progress"] == 30.0

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


class TestDashboardServiceCategoryFields:
    """Тесты category fields в RecentTransaction."""

    def test_recent_transaction_includes_category(self, db_session, test_user):
        """RecentTransaction включает category_name и category_icon."""
        from app.models.database import Category

        # Создаем категорию
        category = Category(name="Еда", icon="bi-cart", type="expense")
        db_session.add(category)
        db_session.flush()

        # Создаем транзакцию с категорией
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=category.id,
        )
        db_session.add(transaction)
        db_session.commit()

        service = DashboardService(db_session)
        recent = service.get_recent_transactions(test_user.id, limit=5)

        assert len(recent) == 1
        assert recent[0]["category_name"] == "Еда"
        assert recent[0]["category_icon"] == "bi-cart"

    def test_recent_transaction_without_category(self, db_session, test_user):
        """RecentTransaction корректно обрабатывает отсутствие категории."""
        transaction = Transaction(
            user_id=test_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            category_id=None,
        )
        db_session.add(transaction)
        db_session.commit()

        service = DashboardService(db_session)
        recent = service.get_recent_transactions(test_user.id, limit=5)

        assert len(recent) == 1
        assert recent[0]["category_name"] is None
        assert recent[0]["category_icon"] is None

    def test_excludes_recurring_templates(self, db_session, test_user):
        """Recurring шаблоны не попадают в recent transactions."""
        # Создаем обычную транзакцию
        regular = Transaction(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
            description="Обычная",
            is_recurring=False,
        )
        # Создаем recurring шаблон
        template = Transaction(
            user_id=test_user.id,
            amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today(),
            description="Шаблон зарплаты",
            is_recurring=True,
            recurring_period="monthly",
        )
        db_session.add_all([regular, template])
        db_session.commit()

        service = DashboardService(db_session)
        recent = service.get_recent_transactions(test_user.id, limit=10)

        # Должна быть только обычная транзакция
        assert len(recent) == 1
        assert recent[0]["description"] == "Обычная"


class TestDashboardServiceAdjustmentExclusion:
    """Тесты исключения ADJUSTMENT из period_income/period_expense."""

    def test_adjustment_not_in_period_income(self, db_session, test_user):
        """ADJUSTMENT не учитывается в period_income."""
        # Создаем реальный доход
        income = Transaction(
            user_id=test_user.id,
            amount=Decimal("1000.00"),
            transaction_type=TransactionType.INCOME,
            transaction_date=date.today(),
        )
        # Создаем положительную корректировку
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("500.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
        )
        db_session.add_all([income, adjustment])
        db_session.commit()

        service = DashboardService(db_session)
        metrics = service.get_overview_metrics(test_user.id, period="month")

        # ADJUSTMENT не должен увеличивать period_income
        assert metrics["period_income"] == Decimal("1000.00")

    def test_adjustment_not_in_period_expense(self, db_session, test_user):
        """ADJUSTMENT не учитывается в period_expense."""
        # Создаем реальный расход
        expense = Transaction(
            user_id=test_user.id,
            amount=Decimal("300.00"),
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date.today(),
        )
        # Создаем отрицательную корректировку
        adjustment = Transaction(
            user_id=test_user.id,
            amount=Decimal("-200.00"),
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=date.today(),
        )
        db_session.add_all([expense, adjustment])
        db_session.commit()

        service = DashboardService(db_session)
        metrics = service.get_overview_metrics(test_user.id, period="month")

        # ADJUSTMENT не должен влиять на period_expense
        assert metrics["period_expense"] == Decimal("300.00")


class TestGetDailyCashflow:
    """Тесты для get_daily_cashflow()."""

    def test_basic_income_expense(self, db_session, test_user):
        """Базовый тест: income + expense отображаются в daily list."""
        db_session.add_all(
            [
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("5000"),
                    transaction_type=TransactionType.INCOME,
                    transaction_date=date(2026, 1, 10),
                ),
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("2000"),
                    transaction_type=TransactionType.EXPENSE,
                    transaction_date=date(2026, 1, 15),
                ),
            ]
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        assert len(result["daily"]) == 31  # Январь = 31 день
        day_10 = result["daily"][9]  # index 9 = 10 января
        assert day_10["income"] == Decimal("5000")
        assert day_10["expense"] == Decimal("0")
        day_15 = result["daily"][14]
        assert day_15["income"] == Decimal("0")
        assert day_15["expense"] == Decimal("2000")
        # Balance: starting 10000 + 5000 = 15000 на 10-е; 15000 - 2000 = 13000 на 15-е
        assert day_10["balance"] == Decimal("15000")
        assert day_15["balance"] == Decimal("13000")

    def test_no_transactions(self, db_session, test_user):
        """Пустой месяц: balance == starting_balance для всех дней."""
        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 2)

        assert len(result["daily"]) == 28  # Февраль 2026 = 28 дней
        for day in result["daily"]:
            assert day["balance"] == Decimal("10000")
            assert day["income"] == Decimal("0")
            assert day["expense"] == Decimal("0")

    def test_negative_balance_risk_status(self, db_session, test_user):
        """Баланс < 0 → min_balance_point.status == 'risk'."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("15000"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 5),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        # Balance = 10000 - 15000 = -5000
        assert result["min_balance_point"]["status"] == "risk"
        assert result["min_balance_point"]["balance"] == Decimal("-5000")

    def test_attention_balance_status(self, db_session, test_user):
        """0 < balance < 5000 → status == 'attention'."""
        # starting_balance = 10000, расход 7000 → balance = 3000
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("7000"),
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date(2026, 1, 5),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        assert result["min_balance_point"]["status"] == "attention"
        assert result["min_balance_point"]["balance"] == Decimal("3000")

    def test_ok_balance_status(self, db_session, test_user):
        """balance >= 5000 → status == 'ok'."""
        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        # starting_balance = 10000 > 5000
        assert result["min_balance_point"]["status"] == "ok"

    def test_min_balance_in_middle(self, db_session, test_user):
        """Минимум в середине месяца (не в конце)."""
        db_session.add_all(
            [
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("9000"),
                    transaction_type=TransactionType.EXPENSE,
                    transaction_date=date(2026, 1, 15),
                ),
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("20000"),
                    transaction_type=TransactionType.INCOME,
                    transaction_date=date(2026, 1, 20),
                ),
            ]
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        # Минимум на 15-19 января: 10000 - 9000 = 1000
        # После 20-го: 1000 + 20000 = 21000
        assert result["min_balance_point"]["date"] == date(2026, 1, 15)
        assert result["min_balance_point"]["balance"] == Decimal("1000")

    def test_running_balance_cumulative(self, db_session, test_user):
        """Кумулятивность: balance дня = balance предыдущего + change."""
        db_session.add_all(
            [
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("1000"),
                    transaction_type=TransactionType.INCOME,
                    transaction_date=date(2026, 1, 1),
                ),
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("500"),
                    transaction_type=TransactionType.EXPENSE,
                    transaction_date=date(2026, 1, 2),
                ),
            ]
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        day1 = result["daily"][0]  # 1 янв
        day2 = result["daily"][1]  # 2 янв
        # day1: 10000 + 1000 = 11000
        assert day1["balance"] == Decimal("11000")
        # day2: 11000 - 500 = 10500
        assert day2["balance"] == Decimal("10500")

    def test_adjustment_positive_as_income(self, db_session, test_user):
        """ADJUSTMENT amount > 0 → income bar."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("800"),
                transaction_type=TransactionType.ADJUSTMENT,
                transaction_date=date(2026, 1, 10),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        day_10 = result["daily"][9]
        assert day_10["income"] == Decimal("800")
        assert day_10["expense"] == Decimal("0")

    def test_adjustment_negative_as_expense(self, db_session, test_user):
        """ADJUSTMENT amount < 0 → expense bar (abs)."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("-600"),
                transaction_type=TransactionType.ADJUSTMENT,
                transaction_date=date(2026, 1, 10),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        day_10 = result["daily"][9]
        assert day_10["income"] == Decimal("0")
        assert day_10["expense"] == Decimal("600")

    def test_transfer_not_counted(self, db_session, test_user):
        """TRANSFER не появляется ни в income, ни в expense."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("3000"),
                transaction_type=TransactionType.TRANSFER,
                transaction_date=date(2026, 1, 10),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        day_10 = result["daily"][9]
        assert day_10["income"] == Decimal("0")
        assert day_10["expense"] == Decimal("0")

    def test_savings_reserve_as_expense(self, db_session, test_user):
        """SAVINGS_RESERVE → expense."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000"),
                transaction_type=TransactionType.SAVINGS_RESERVE,
                transaction_date=date(2026, 1, 10),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        day_10 = result["daily"][9]
        assert day_10["expense"] == Decimal("5000")
        assert day_10["income"] == Decimal("0")

    def test_savings_contribution_as_expense(self, db_session, test_user):
        """SAVINGS_CONTRIBUTION → expense."""
        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("2000"),
                transaction_type=TransactionType.SAVINGS_CONTRIBUTION,
                transaction_date=date(2026, 1, 10),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_daily_cashflow(test_user.id, 2026, 1)

        day_10 = result["daily"][9]
        assert day_10["expense"] == Decimal("2000")
        assert day_10["income"] == Decimal("0")


class TestGetYearlyCashflow:
    """Тесты для get_yearly_cashflow()."""

    def test_returns_12_months(self, db_session, test_user):
        """Возвращает 12 месяцев с номерами 1-12."""
        service = DashboardService(db_session)
        result = service.get_yearly_cashflow(test_user.id, 2026)

        assert len(result["monthly"]) == 12
        months = [m["month"] for m in result["monthly"]]
        assert months == list(range(1, 13))

    def test_monthly_income_expense(self, db_session, test_user):
        """Корректная агрегация income/expense за месяц."""
        db_session.add_all(
            [
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("10000"),
                    transaction_type=TransactionType.INCOME,
                    transaction_date=date(2026, 3, 5),
                ),
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("5000"),
                    transaction_type=TransactionType.INCOME,
                    transaction_date=date(2026, 3, 20),
                ),
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("3000"),
                    transaction_type=TransactionType.EXPENSE,
                    transaction_date=date(2026, 3, 15),
                ),
            ]
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_yearly_cashflow(test_user.id, 2026)

        march = result["monthly"][2]  # index 2 = март
        assert march["income"] == Decimal("15000")
        assert march["expense"] == Decimal("3000")
        assert march["label"] == "Мар"

    def test_end_balance_correct(self, db_session, test_user):
        """end_balance совпадает с CalendarService balance на конец месяца."""
        from app.services.calendar_service import CalendarService

        db_session.add(
            Transaction(
                user_id=test_user.id,
                amount=Decimal("5000"),
                transaction_type=TransactionType.INCOME,
                transaction_date=date(2026, 1, 15),
            )
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_yearly_cashflow(test_user.id, 2026)

        # Проверяем через CalendarService
        cal = CalendarService(db_session)
        expected_jan = cal.get_balance_on_date(test_user.id, date(2026, 1, 31))
        assert result["monthly"][0]["end_balance"] == expected_jan

    def test_min_balance_year(self, db_session, test_user):
        """Минимум года определяется правильно."""
        # Большой расход в марте → минимум end_balance
        db_session.add_all(
            [
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("8000"),
                    transaction_type=TransactionType.EXPENSE,
                    transaction_date=date(2026, 3, 10),
                ),
                # Восстановление в апреле
                Transaction(
                    user_id=test_user.id,
                    amount=Decimal("30000"),
                    transaction_type=TransactionType.INCOME,
                    transaction_date=date(2026, 4, 1),
                ),
            ]
        )
        db_session.commit()

        service = DashboardService(db_session)
        result = service.get_yearly_cashflow(test_user.id, 2026)

        # Март end_balance = 10000 - 8000 = 2000 (минимум)
        # Апрель end_balance = 2000 + 30000 = 32000
        assert result["min_balance_point"]["balance"] == Decimal("2000")
        assert result["min_balance_point"]["date"] == date(2026, 3, 31)
