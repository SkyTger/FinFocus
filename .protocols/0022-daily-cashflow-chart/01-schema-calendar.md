# Шаг 1: Schema TypedDicts + CalendarService Public Method

## Briefing

- **Цель:** Создать TypedDicts для daily/yearly cashflow данных, константы порогов баланса, и новый публичный метод CalendarService для recurring income/expense агрегации.
- **Ключевые файлы:**
  - `app/schema/dashboard.py` — NEW (~60 строк)
  - `app/schema/__init__.py` — MOD (экспорт)
  - `app/services/calendar_service.py` — MOD (+35 строк)
  - `app/services/__init__.py` — MOD (экспорт)
- **Доп. информация:** Решение из solution-v2.md. Публичный метод CalendarService заменяет protected access (blocker из critique-v1).

## Sub-tasks

1. **Создать `app/schema/dashboard.py`:**
   - `BalanceStatus = Literal["ok", "attention", "risk"]`
   - `BALANCE_RISK_THRESHOLD = Decimal("0")`
   - `BALANCE_ATTENTION_THRESHOLD = Decimal("5000")`
   - `DailyCashflow(TypedDict)`: date, income, expense, balance
   - `DailyBalancePoint(TypedDict)`: date, balance, status
   - `MonthlyCashflowData(TypedDict)`: daily, min_balance_point, current_date
   - `MonthlyCashflow(TypedDict)`: month, label, income, expense, end_balance
   - `YearlyCashflowData(TypedDict)`: monthly, min_balance_point, current_date, year

2. **Обновить `app/schema/__init__.py`:**
   - Импорт и экспорт всех новых TypedDicts + констант

3. **Добавить `CalendarService.get_recurring_income_expense_by_day()`:**
   - Public метод-обёртка над `_get_recurring_instances_for_period()`
   - Возвращает `dict[date, tuple[Decimal, Decimal]]` (income, expense)
   - Классификация: income → income, expense/savings_reserve/savings_contribution → expense, transfer → игнорируется
   - Guard comment: "ADJUSTMENT recurring практически невозможен"
   - Использовать `defaultdict(lambda: (Decimal("0"), Decimal("0")))`

4. **Обновить `app/services/__init__.py`:**
   - Экспорт новых TypedDicts

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/schema/dashboard.py app/services/calendar_service.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Коммит: `git add . && git commit -m "feat(schema+calendar): add cashflow TypedDicts and recurring public API [protocol-0022/01]"`
6. Push
