# Work Log: 0002 — Кассовый календарь

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

**Restore context: protocol-0002#ctx-3** (2026-01-19)

**Restore context: protocol-0002#ctx-2** (2026-01-18)

---

## Шаг 2: Calendar UI — Компоненты и стили (2026-01-19)

**Действия:**
- Создан `app/components/calendar.py` (~420 строк) с полным набором UI компонентов:
  - Константы: MONTH_NAMES_RU, WEEKDAY_NAMES_RU, WARNING_BALANCE_THRESHOLD, MAX_MONTHS_OFFSET
  - Утилиты сериализации: serialize_balances(), deserialize_balances() — для Decimal в dcc.Store
  - Функции форматирования: format_balance(), format_month_header()
  - Layout: create_calendar_layout() — главный layout страницы
  - Компоненты:
    - build_calendar_header() — заголовок с навигацией (prev/next/today кнопки)
    - build_stats_cards() — карточки статистики (Доходы/Расходы/Баланс)
    - build_calendar_grid() — сетка календаря с использованием модуля calendar
    - build_day_cell() — ячейка дня с Pattern-Matching ID для callbacks
- Создан `app/assets/calendar.css` (~160 строк) со стилями:
  - Сетка календаря с flexbox
  - Цветовая схема для балансов (positive/negative/warning)
  - Подсветка сегодняшнего дня, выходных, дней другого месяца
  - Адаптивность для мобильных устройств (768px, 576px breakpoints)

**Решения:**
- Использован `calendar.Calendar(firstweekday=0)` для генерации матрицы дней месяца
- Pattern-Matching ID для ячеек: `{"type": "calendar-day", "date": "YYYY-MM-DD"}`
- Порог предупреждения `WARNING_BALANCE_THRESHOLD = Decimal("5000")` — желтый цвет для баланса < 5000
- Иконки транзакций: ↓ (доход, зеленый), ↑ (расход, красный)
- Навигация ограничена ±12 месяцев от текущего

**Проверки:**
- black: ✅ (1 файл переформатирован)
- flake8: ✅ (без ошибок)

---

## Шаг 0: Подготовка (2026-01-18)

**Действия:**
- Создана ветка `0002-cash-calendar` с worktree
- Сгенерированы артефакты протокола: plan.md, context.md, log.md, 00-05 step files
- Открыт Draft PR

**Решения:**
- Разбиение на 5 шагов (кроме setup): CalendarService → UI → Callbacks → Integration → Finalize
- Использование существующего `create-modal` из transactions.py вместо создания дублирующего
- TRANSFER транзакции исключаются из расчетов баланса

**Детали:**
- Дизайн-документ: `.design/solution-v2.md`
- Критика v1 учтена: Decimal сериализация, guard clauses, fallback для starting_balance

---

## Шаг 1: CalendarService — Backend Logic (2026-01-19)

**Действия:**
- Создан `app/services/calendar_service.py` (~310 строк)
- Реализован класс `CalendarService` с методами:
  - `_get_starting_balance()` — получение начального баланса пользователя
  - `calculate_daily_balances()` — расчет балансов по дням через SQL агрегацию
  - `_calculate_balance_before_date()` — расчет баланса до указанной даты
  - `_get_daily_changes()` — получение дневных изменений
  - `get_transactions_by_date()` — группировка транзакций по датам
  - `get_month_summary()` — сводка по месяцу (income/expense/balances)
- Создан `MonthSummary` TypedDict для типизации
- Обновлен `app/services/__init__.py` — экспорт CalendarService и MonthSummary
- Создана инфраструктура тестов: `tests/`, `conftest.py`, `__init__.py`
- Написаны 15 unit тестов в `tests/test_calendar_service.py`
- Добавлен `setup.cfg` для конфигурации flake8 (88 chars) и pytest

**Решения:**
- SQL агрегация через SQLAlchemy `case()` и `func.sum()` для производительности
- TRANSFER транзакции исключаются из расчетов баланса (критичный тест подтверждает)
- Fallback на `Decimal('0')` если пользователь не найден или starting_balance=None
- Guard clauses для валидации входных данных

**Проверки:**
- black: ✅ (1 файл переформатирован)
- flake8: ✅ (после добавления setup.cfg)
- pytest: ✅ 15/15 passed (0.28s)
