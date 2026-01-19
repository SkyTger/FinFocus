# Work Log: 0003 — Dashboard Data Integration

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

---

## Restore context: protocol-0003#ctx-1

---

## [2026-01-19] Шаг 0: Подготовка протокола ✅

**Commit**: 0882ab2
**PR**: https://github.com/SkyTger/FinFocus/pull/3

**Выполнено**:
- Создана ветка `0003-dashboard-integration` из origin/main
- Создан worktree в `../worktrees/0003-dashboard-integration`
- Сгенерированы артефакты протокола:
  - `plan.md` - главный план с 6 шагами
  - `context.md` - текущее состояние
  - `log.md` - журнал работы
  - `00-setup.md` - шаг 0 (этот шаг)
  - `01-calendar-service.md` - расширение CalendarService
  - `02-dashboard-service.md` - создание DashboardService
  - `03-services-init.md` - обновление exports
  - `04-dashboard-ui.md` - рефакторинг dashboard.py
  - `05-tests.md` - unit тесты
  - `06-finalize.md` - финализация
- Создан Draft PR #3

**Решения**:
- Архитектура: DashboardService как агрегатор (composition, не inheritance)
- Переключатель периода через dcc.Store и RadioItems
- Cashflow данные одним SQL-запросом с GROUP BY (оптимизация)

**Следующий шаг**: Шаг 1 - расширение CalendarService

---

## [2026-01-19] Шаг 1: Расширение CalendarService ✅

**Commit**: 4e898f7

**Выполнено**:
- Добавлен TypedDict `YearSummary` для годовой сводки
- Реализован метод `get_balance_on_date(user_id, target_date)`:
  - Wrapper над `_calculate_balance_before_date()` с учетом starting_balance
  - Возвращает баланс на конец указанного дня (включительно)
- Реализован метод `get_year_summary(user_id, year)`:
  - SQL-запрос с агрегацией INCOME/EXPENSE за год
  - TRANSFER транзакции исключены из расчетов
- Обновлен экспорт в `app/services/__init__.py` (добавлен YearSummary)

**Технические детали**:
- `get_balance_on_date`: использует `timedelta(days=1)` для включения целевой даты
- `get_year_summary`: аналогичная SQL-структура как `get_month_summary`, но с границами года (01.01 - 31.12)
- Все существующие тесты CalendarService (17/17) прошли успешно

**Следующий шаг**: Шаг 2 - создание DashboardService
