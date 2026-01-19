# Work Log: 0002 — Кассовый календарь

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

**Restore context: protocol-0002#ctx-5** (2026-01-19)

**Restore context: protocol-0002#ctx-4** (2026-01-19)

**Self-Review: protocol-0002#review-1** (2026-01-19)

**Restore context: protocol-0002#ctx-3** (2026-01-19)

**Restore context: protocol-0002#ctx-2** (2026-01-18)

---

## Self-Review: Шаг 4 (2026-01-19)

**Найденные проблемы:**
1. ⚠️ `__init__.py` некомплектный: экспортировался только `create_calendar_layout`, остальные компоненты игнорировались
   - **Исправлено**: Добавлены все 4 компонента в `__all__` для консистентности API
   - Теперь: `create_calendar_layout`, `create_dashboard_layout`, `create_sidebar`, `create_transactions_layout`

**Проверенные аспекты:**
- ✅ Полнота: Все 5 sub-tasks выполнены (sidebar уже содержал /calendar, изменений не требовал)
- ✅ Роутинг: `/calendar` корректно вызывает `create_calendar_layout()`
- ✅ Порядок импортов: transactions → calendar (критично для callbacks)
- ✅ Качество: black + flake8 без ошибок
- ✅ Корректность: pytest 15/15 passed, layout создается без ошибок
- ✅ Консистентность: `__all__` теперь полный для всех компонентов

---

## Шаг 4: Интеграция и функциональное тестирование (2026-01-19)

**Действия:**
- Обновлен `app/components/__init__.py`:
  - Добавлены exports для всех 4 компонентов (консистентность API)
  - `__all__` с полным списком публичных функций
- Обновлен `app/main.py`:
  - Добавлен импорт `create_calendar_layout` после `create_transactions_layout`
  - Заменена заглушка `/calendar` на вызов `create_calendar_layout()`
  - Порядок импортов: transactions → calendar (критично для регистрации callbacks)

**Тестирование:**
- ✅ TC-01: Загрузка календаря — HTTP 200, calendar.css подключен
- ✅ Unit тесты: 15/15 passed (CalendarService)
- ✅ Import check: `create_calendar_layout()` создает layout без ошибок
- ⏳ TC-02..TC-08: Требуют ручной проверки в браузере

**Проверки:**
- black: ✅ (main.py переформатирован)
- flake8: ✅ (без ошибок)
- pytest: ✅ 15/15 passed (0.21s)

**Примечание:**
Seed скрипты (`seed_database.py`, `seed_test_data.py`) устарели после рефакторинга протокола 0001 (используют старые импорты). Не блокирует тестирование — операции можно создать через UI.

---

## Self-Review: Шаги 1-3 (2026-01-19)

**Найденные проблемы:**
1. ⚠️ Type annotation несоответствие: `build_stats_cards()` имела `-> html.Div` вместо `-> dbc.Row`
   - **Исправлено**: Изменена аннотация на `-> dbc.Row` (соответствует реальному return)
   - Amend коммита [protocol-0002/03] (8372401)

2. ⚠️ context.md устарел: Указывал "ожидает коммит", хотя коммит уже сделан
   - **Исправлено**: Обновлен статус Git с хешем коммита

**Проверенные аспекты:**
- ✅ Полнота: Все функции из плана реализованы (12 функций + 3 callbacks)
- ✅ Guard clauses: Корректно применены 3 guard clauses согласно ADR-003
- ✅ CSS классы: Все 13 основных классов на месте
- ✅ Логирование: logger.debug + logger.error корректно
- ✅ allow_duplicate: Используется для всех shared outputs (5 outputs)
- ✅ Валидация: ±12 месяцев корректно проверяется
- ✅ Проверки: black + flake8 пройдены без ошибок
- ✅ Коммиты: 3 коммита протокола с правильными тегами
- ✅ Dependencies: python-dateutil==2.8.2 уже в requirements.txt

**Метрики:**
- calendar.py: 702 строки (UI 440 + callbacks 260)
- calendar.css: 191 строка
- Функций всего: 15 (9 UI + 3 utils + 3 callbacks)
- Guard clauses: 8 (3 в open_create_modal, 3 в refresh_calendar, 2 в load_and_navigate)

---

## Шаг 3: Dash Callbacks — Интерактивность (2026-01-19)

**Действия:**
- Добавлены импорты в `app/components/calendar.py`:
  - `callback, Input, Output, State, ALL, ctx` из dash
  - `PreventUpdate` из dash.exceptions
  - `relativedelta` из dateutil для навигации
  - `logger` из loguru для отладки
  - `get_db_session` и `CalendarService` для работы с данными
- Реализовано 3 callback функции (~260 строк):
  1. `load_and_navigate_calendar()` — загрузка данных и навигация по месяцам
     - Guard: pathname != "/calendar" → PreventUpdate
     - Обработка prev/next/today кнопок через relativedelta
     - Валидация ±12 месяцев от текущего
     - Загрузка balances, transactions_by_date, summary через CalendarService
     - Обработка ошибок с выводом Alert
  2. `open_create_modal_from_calendar()` — открытие модала создания при клике на день
     - 3 Guard clauses согласно ADR-003:
       - Guard #1: triggered_id существует
       - Guard #2: isinstance(dict) and type == "calendar-day"
       - Guard #3: ctx.triggered[0].get("value") is not None
     - Использует allow_duplicate=True для create-modal и create-date-picker
  3. `refresh_calendar_after_transaction()` — обновление после CRUD операций
     - Слушает create-submit-btn, edit-submit-btn, delete-btn
     - Guard clauses для фильтрации автовызовов
     - Пересчитывает grid, stats и state

**Решения:**
- DEFAULT_USER_ID = 1 как временная константа (до реализации авторизации)
- allow_duplicate=True для outputs, используемых в нескольких callbacks
- Логирование через logger.debug для отладки и logger.error для ошибок

**Проверки:**
- black: ✅ (1 файл переформатирован)
- flake8: ✅ (без ошибок)

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
