# Шаг 1: Расширение CalendarService

## Briefing
- **Цель:** Добавить в CalendarService публичные методы для DashboardService: `get_balance_on_date()` для расчета баланса на конкретную дату и `get_year_summary()` для годовой сводки.
- **Ключевые файлы:**
  - `app/services/calendar_service.py` (изменить)
  - `app/services/__init__.py` (изменить экспорт YearSummary)
- **Additional info:**
  - `get_balance_on_date()` — wrapper над приватным `_calculate_balance_before_date()`, возвращает баланс на конец указанного дня (включительно)
  - `get_year_summary()` — аналог `get_month_summary()`, но для целого года
  - TRANSFER транзакции НЕ учитываются (как в существующих методах)
  - Формула баланса: `starting_balance + SUM(INCOME) - SUM(EXPENSE)`

## Sub-tasks

1. **Добавить TypedDict `YearSummary`** в начало файла (после MonthSummary):
   ```python
   class YearSummary(TypedDict):
       """Сводка по году для дашборда."""
       total_income: Decimal
       total_expense: Decimal
       year: int
   ```

2. **Добавить метод `get_balance_on_date()`** в класс CalendarService:
   ```python
   def get_balance_on_date(self, user_id: int, target_date: date) -> Decimal:
       """Рассчитывает баланс пользователя на указанную дату (включительно).

       Формула: starting_balance + SUM(INCOME) - SUM(EXPENSE)
       до target_date включительно.

       TRANSFER транзакции не учитываются.

       Args:
           user_id: ID пользователя
           target_date: Дата на которую считается баланс (включительно)

       Returns:
           Decimal: Баланс на конец дня target_date

       Note: Для несуществующего user_id возвращает Decimal('0').
       """
       starting_balance = self._get_starting_balance(user_id)
       # +1 день т.к. _calculate_balance_before_date НЕ включает дату
       changes_up_to_date = self._calculate_balance_before_date(
           user_id, target_date + timedelta(days=1)
       )
       return starting_balance + changes_up_to_date
   ```

3. **Добавить метод `get_year_summary()`** в класс CalendarService:
   ```python
   def get_year_summary(self, user_id: int, year: int) -> YearSummary:
       """Формирует сводку по году.

       Args:
           user_id: ID пользователя
           year: Год (например, 2026)

       Returns:
           YearSummary: Сводка с total_income, total_expense за год
       """
       first_day = date(year, 1, 1)
       last_day = date(year, 12, 31)

       result = (
           self.session.query(
               func.coalesce(
                   func.sum(
                       case(
                           (Transaction.transaction_type == TransactionType.INCOME,
                            Transaction.amount),
                           else_=Decimal("0"),
                       )
                   ),
                   Decimal("0"),
               ).label("total_income"),
               func.coalesce(
                   func.sum(
                       case(
                           (Transaction.transaction_type == TransactionType.EXPENSE,
                            Transaction.amount),
                           else_=Decimal("0"),
                       )
                   ),
                   Decimal("0"),
               ).label("total_expense"),
           )
           .filter(
               Transaction.user_id == user_id,
               Transaction.transaction_date >= first_day,
               Transaction.transaction_date <= last_day,
               Transaction.transaction_type.in_(
                   [TransactionType.INCOME, TransactionType.EXPENSE]
               ),
           )
           .first()
       )

       return YearSummary(
           total_income=Decimal(str(result.total_income)) if result.total_income else Decimal("0"),
           total_expense=Decimal(str(result.total_expense)) if result.total_expense else Decimal("0"),
           year=year,
       )
   ```

4. **Обновить `app/services/__init__.py`**: добавить экспорт YearSummary:
   ```python
   from .calendar_service import CalendarService, MonthSummary, TransactionInfo, YearSummary
   ```

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.
2. **Верификация:** После завершения ВСЕХ подзадач запусти проверки:
   ```bash
   cd /home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration
   black app/services/calendar_service.py
   flake8 app/services/calendar_service.py
   pytest tests/test_calendar_service.py -v
   ```
3. **Фиксация:** После успешной верификации:
   - Добавь запись в `log.md`
   - Обнови `context.md`: `Current Step` = 2
   - Проверь ветку main в поисках случайно добавленных файлов
4. **Коммит**: `git add . && git commit -m "feat(calendar): add get_balance_on_date and get_year_summary [protocol-0003/01]"`. Push.
5. **Отчет пользователю** в установленном формате.
