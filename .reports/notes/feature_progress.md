# FinFocus - Прогресс разработки

## 📊 Общий статус проекта: Батч 4 — Safety Cushion — ✅ ЗАВЕРШЕН

**Последнее обновление**: 2026/01/30
**Текущий этап**: Safety Cushion — MERGED
**Прогресс Epic-04**: 2/6 фичи (Quick-Add Chips + Safety Cushion complete)
**GitHub**: https://github.com/SkyTger/FinFocus

---

## ✅ Батч 12: Safety Cushion (2026-01-30) — MERGED

**Дата**: 2026/01/30
**Протокол**: 0013-safety-cushion
**PR**: https://github.com/SkyTger/FinFocus/pull/13
**Статус**: ✅ Merged в main

### 🎯 Цель батча:
Реализовать финансовую подушку безопасности — резервный фонд для непредвиденных расходов с визуализацией прогресса и порога риска.

### ✅ Выполненные задачи:

1. **Schema + Model** (commit: 12ed5a4)
   - Percent NewType для type safety (0-100)
   - CushionSettings, CushionScenario TypedDicts
   - 3 поля в User: cushion_target, cushion_threshold_percent, cushion_threshold_manual

2. **CushionService** (commit: 560da11)
   - get_settings() — возвращает CushionSettings с вычисляемыми полями
   - update_settings() — обновляет настройки с валидацией
   - reset_settings() — сброс к default (target=0, threshold=30%)
   - calculate_recommendation() — расчёт по сценариям (sum/max_scenario)

3. **Unit Tests** (commit: 38a1817)
   - 20 unit тестов для CushionService
   - Покрытие: _validate_percent, get/update/reset settings, calculate_recommendation

4. **Card UI** (commit: f36e0bb)
   - Карточка подушки на /goals (~180 строк)
   - 4 цветовых статуса: danger/warning/info/success
   - Прогресс-бар с маркером порога

5. **Modal UI** (commit: 6a152ee)
   - Модал настройки (~175 строк)
   - Калькулятор сценариев (sum/max_scenario режимы)
   - Кнопки: Сбросить, Отмена, Сохранить

6. **Callbacks** (commit: a31154c)
   - 12 callbacks с ADR-003 guard clauses (~450 строк)
   - Pattern-Matching для remove_scenario

7. **CSS стили** (commit: 76c8f96)
   - Стили .cushion-* (~200 строк)
   - Responsive breakpoints: 768px, 576px

8. **Финализация** (commit: fd5326f)
   - Black, Flake8, pytest — все прошли
   - 292 теста (было 272, +20 для CushionService)

### 📊 Результат:
- ✅ 292 unit и integration тестов
- ✅ CushionService с Percent NewType для type safety
- ✅ Калькулятор сценариев для расчёта целевого размера
- ✅ Black + Flake8 OK
- ✅ PR #13 Merged

### 💡 Ключевые решения:

1. **Подушка как поля в User** — не Goal, т.к. подушка не участвует в распределении бюджета
2. **Percent NewType** — type safety на уровне IDE/type checker
3. **threshold_manual флаг** — любое изменение порога = manual=True
4. **Калькулятор сценариев** — sum (сумма) или max_scenario (максимум) режимы

---

## ✅ Батч 11: Quick-Add Chips (2026-01-25) — ЗАВЕРШЕН

**Дата**: 2026/01/25
**Протокол**: 0012-quick-add-chips
**PR**: https://github.com/SkyTger/FinFocus/pull/12
**Статус**: ✅ Полностью завершен (Ready for Review)

### 🎯 Цель батча:
Реализовать Quick-add chips для быстрого создания операций — сокращение процесса ввода с 6 шагов до 3-4 через предвыбранные категории.

### ✅ Выполненные задачи:

1. **Schema и константы** (Шаг 1, commit: ffb88d3)
   - TypedDict QuickAddChipData в `app/schema/quick_add.py`
   - DEFAULT_QUICK_ADD_CHIP_NAMES — 7 hardcoded чипов (5 expense + 2 income)
   - _get_quick_add_chips() — lookup по имени с warning при mismatch

2. **UI секция Quick-add** (Шаг 2, commit: 76be290)
   - _build_quick_add_chip() — вертикальный layout (иконка + название)
   - _build_quick_add_section() — группировка expense/income + кнопки "Ещё"
   - Интеграция в transactions.py между header и фильтрами
   - Pattern-Matching IDs: {"type": "qa-chip", ...}, {"type": "qa-more-btn", ...}

3. **Модал "Ещё..."** (Шаг 3, commit: 2fdcaec)
   - _build_category_more_modal() — dbc.Modal с Tabs (expense/income)
   - load_more_modal_categories() callback — динамическая загрузка при открытии
   - Pattern-Matching ID: {"type": "qa-more-category", ...}

4. **Preselection механизм** (Шаг 4, commit: b500451)
   - dcc.Store: preselected-category, preselected-type в transaction_modals.py
   - set_preselection_on_modal_open() callback — применение при открытии
   - create_transaction обновлен — reset preselection после создания

5. **Callbacks Quick-add** (Шаг 5, commit: 69f7837)
   - open_create_from_quick_add() — клик на chip → модал с preselection
   - open_more_modal() — клик на "Ещё..." → модал категорий
   - select_from_more_modal() — выбор → закрытие + открытие create
   - ADR-003 guard clauses во всех 3 callbacks

6. **CSS стили** (Шаг 6, commit: 0f1b945)
   - Стили .qa-* в transactions.css (~100 строк)
   - Chips: vertical layout, hover transform, ellipsis
   - Responsive: horizontal scroll на 768px, уменьшенные размеры на 576px

7. **Unit тесты** (Шаг 7, commit: b325864)
   - test_quick_add_chips.py — 13 тестов
   - Покрытие: TypedDict, _get_quick_add_chips(), константы, UI функции
   - 272 теста проекта проходят

8. **Финализация** (Шаг 8, commit: 55b334c)
   - Black: 1 файл переформатирован
   - Flake8: 3 unused imports исправлены
   - pytest: 272 tests passed
   - PR #12 Ready for Review

### 📊 Результат:
- ✅ 272 unit и integration тестов (было 246)
- ✅ 7 hardcoded quick-add chips (5 расходов + 2 доходов)
- ✅ Сокращение шагов создания операции: 6 → 3-4
- ✅ Black + Flake8 OK
- ✅ PR #12 Ready for Review

### 💡 Ключевые уроки:

1. **Lookup по имени** — защищает от ID mismatch между dev/prod окружениями
2. **Preselection Store Pattern** — чистая передача состояния между модалами
3. **Hardcoded список** — достаточен для MVP, кастомизация в следующем этапе (Протокол B: Шаблоны операций)
4. **Pattern-Matching для chips** — масштабируемо для будущих кастомных чипов
5. **Вертикальный layout** — иконка над названием экономит горизонтальное пространство

### 🔧 Технические детали:

**Новые файлы:**
- `app/schema/quick_add.py` — QuickAddChipData TypedDict
- `tests/test_quick_add_chips.py` — 13 unit тестов

**Модифицированные файлы:**
- `app/components/transactions.py` — +3 UI функции, +3 callbacks
- `app/components/transaction_modals.py` — +2 Stores, +1 callback, update create_transaction
- `app/assets/transactions.css` — +100 строк стилей .qa-*
- `app/schema/__init__.py` — экспорт QuickAddChipData

### 🚀 Следующие шаги:

**Протокол B: Шаблоны операций** (запланировано):
- Кастомизация quick-add chips пользователем
- Частые операции → автоматическое создание шаблонов
- Редактирование/удаление шаблонов

---

## ✅ Батч 3.2: Analytics & UX Improvements (2026-01-23) — MERGED

**Дата**: 2026/01/23
**Протокол**: 0010-analytics-ux
**PR**: https://github.com/SkyTger/FinFocus/pull/10
**Merge commit**: ed0fc44

### 🎯 Цель:
Улучшение UX категоризации (chips, bulk actions) и страница аналитики с визуализацией расходов.

### ✅ Основные достижения:

1. **AnalyticsService** (~290 строк)
   - get_expenses_by_category() — SQL GROUP BY агрегация
   - get_monthly_trends() — тренды за N месяцев
   - Группировка мелких категорий (<3%) в "Прочее"

2. **TransactionService расширен**
   - bulk_update_category() — массовое назначение категории (max 100)
   - export_to_csv() — CSV с UTF-8 BOM для Excel

3. **CategoryService расширен**
   - get_frequent_for_type() — частые категории пользователя для chips

4. **Chips UI для быстрой категоризации**
   - Pattern-Matching callbacks для кликов
   - 5 частых категорий + кнопка "..." для полного списка

5. **Bulk Actions Panel**
   - Multi-select с лимитом 100 транзакций
   - Sticky bottom panel со счетчиком

6. **Страница /analytics**
   - Donut chart структуры расходов
   - Bar chart динамики (stacked/grouped toggle)
   - Фильтры периода (месяц/квартал/год)

### 📊 Результат:
- ✅ 246 unit тестов (было 213)
- ✅ Black + Flake8 OK
- ✅ Memory Bank обновлен

---

## ✅ Global Transaction Modals (2026-01-23) - ЗАВЕРШЕН

**Дата**: 2026/01/23
**Тип**: Рефакторинг UX
**Статус**: ✅ Полностью завершен

### 🎯 Цель:
Вынести модалы создания/редактирования транзакций из transactions.py в глобальный layout для доступности CRUD операций на всех страницах (Dashboard, Calendar, Transactions).

### ✅ Выполненные задачи:

1. **transaction_modals.py создан** (~600 строк)
   - create-modal, edit-modal, recurring-scope-modal
   - dcc.Store: modal-source, global-transaction-trigger, edit-transaction-id, recurring-edit-context
   - Submit callbacks: create_transaction, update_transaction, skip_recurring_instance
   - Category dropdown callbacks с ICON_TO_EMOJI

2. **main.py обновлен**
   - Добавлен create_transaction_modals() в layout
   - Глобальный transaction-error-alert

3. **transactions.py упрощен**
   - Удалены UI модалов (перенесены в transaction_modals.py)
   - Добавлен Output modal-source в toggle_create_modal, open_edit_modal
   - Добавлен refresh_table_after_crud() — слушает global-transaction-trigger

4. **calendar.py обновлен**
   - open_create_modal_from_calendar() добавляет modal-source="calendar"
   - refresh_calendar_after_transaction() слушает global-transaction-trigger

5. **dashboard.py обновлен**
   - Добавлен refresh_dashboard_after_crud() — слушает global-transaction-trigger

6. **utils/formatters.py расширен**
   - ICON_TO_EMOJI dict вынесен для переиспользования

7. **Исправлены баги** (2026/01/23)
   - Duplicate Output: allow_duplicate=True в update_edit_category_options
   - Cancel button: глобальные close_create_modal(), close_edit_modal() в transaction_modals.py
   - Calendar modal auto-open: Guard #4 в open_create_modal_from_calendar (проверка all clicks None)

### 📊 Результат:
- ✅ 213 unit и integration тестов проходят
- ✅ Black + Flake8 без ошибок
- ✅ CRUD операции доступны с любой страницы
- ✅ Refresh Trigger Pattern обеспечивает синхронизацию
- ✅ Cancel button работает глобально
- ✅ Modal не открывается автоматически на календаре

### 💡 Ключевые паттерны:

1. **Refresh Trigger Pattern** — global-transaction-trigger Store emit/listen для обновления страниц
2. **modal-source Store** — отслеживание источника открытия модала
3. **Selective Refresh** — страницы обновляются только если source != own page

### 🔧 Технические детали:

**Новые файлы:**
- `app/components/transaction_modals.py`

**Модифицированные файлы:**
- `app/main.py` — +global modals, +error alert
- `app/components/transactions.py` — -modals, +refresh callback
- `app/components/calendar.py` — +modal-source, +trigger listener
- `app/components/dashboard.py` — +refresh callback
- `app/utils/formatters.py` — +ICON_TO_EMOJI
- `app/components/__init__.py` — +export

---

## ✅ Батч 10: Категоризация + Сверка (2026-01-23) - ЗАВЕРШЕН

**Дата**: 2026/01/23
**Протокол**: 0009-categories-reconciliation
**PR**: https://github.com/SkyTger/FinFocus/pull/9
**Статус**: ✅ Полностью завершен (Ready for Review)

### 🎯 Цель батча:
Добавить категоризацию операций с "ленивым" подходом (категория опциональна) и механизм сверки баланса для синхронизации модели с реальностью.

### ✅ Выполненные задачи:

1. **Модель данных** (Шаг 1)
   - TransactionType.ADJUSTMENT — новый тип для корректировок
   - Модель Category (name, icon, type, is_system, sort_order)
   - Transaction.category_id (nullable FK)
   - 16 предзаполненных категорий через seed

2. **TypedDicts** (Шаг 2)
   - CategoryOption для UI dropdown
   - ReconciliationPreview для модала сверки

3. **CategoryService** (Шаг 3)
   - get_all(), get_by_id(), get_by_type()
   - get_for_dropdown() — для UI
   - seed_default_categories() — идемпотентный seed

4. **ReconciliationService** (Шаг 4)
   - get_expected_balance() — расчетный баланс на дату
   - calculate_preview() — preview для модала
   - create_adjustment() — создание ADJUSTMENT транзакции

5. **CalendarService расширен** (Шаг 5)
   - ADJUSTMENT обрабатывается в calculate_daily_balances()
   - Добавлены category_id и category_name в TransactionInfo

6. **TransactionService обновлен** (Шаг 6)
   - Заменен category (str) на category_id (int)
   - Валидация: ADJUSTMENT не может быть recurring

7. **RecurringService обновлен** (Шаг 7)
   - Виртуальные экземпляры наследуют category_id из шаблона
   - Exceptions могут переопределять категорию

8. **DashboardService обновлен** (Шаг 8)
   - category_name и category_icon в RecentTransaction
   - Фильтрация recurring шаблонов

9. **UI Transactions** (Шаг 9)
   - Dropdown категорий в формах create/edit
   - Колонка "Категория" в таблице
   - Фильтр "Без категории"

10. **UI Calendar** (Шаг 10)
    - Кнопка "Сверка" в header
    - Модал сверки с preview разницы
    - Создание ADJUSTMENT и обновление календаря

11. **Финализация** (Шаг 11)
    - Black: 5 файлов переформатировано
    - Flake8: 2 проблемы исправлены
    - Pytest: 213 тестов passed

### 📊 Результат:
- ✅ 213 unit и integration тестов
- ✅ 16 предустановленных категорий (seed idempotent)
- ✅ PR #9 Ready for Review
- ✅ Протокол 0009 завершен (11 шагов)

### 💡 Ключевые уроки:

1. **Ленивая категоризация** — category_id nullable снижает барьер входа
2. **ADJUSTMENT type** — семантически чище чем флаг is_adjustment
3. **Seed idempotency** — критично проверять перед merge
4. **Модал сверки** — быстрый UX через preview с цветовой индикацией

### 🔧 Технические детали:

**Новые файлы:**
- `app/services/category_service.py` — CategoryService
- `app/services/reconciliation_service.py` — ReconciliationService
- `app/schema/categories.py` — TypedDicts
- `scripts/seed_categories.py` — seed скрипт
- `tests/test_category_*.py` — тесты категорий
- `tests/test_reconciliation_service.py` — тесты сверки

**Модифицированные файлы:**
- `app/models/database.py` — Category, ADJUSTMENT, category_id
- `app/services/*.py` — все сервисы обновлены
- `app/components/transactions.py` — dropdown и фильтр
- `app/components/calendar.py` — модал сверки

---

## ✅ Bugfix: Schema Mismatch - Пересоздание БД (2026-01-21) - ЗАВЕРШЕН

**Дата**: 2026/01/21
**Тип**: Critical Bugfix
**Статус**: ✅ Полностью завершен

### 🎯 Проблема:
SQLite БД не имела колонки `users.monthly_savings_budget`, что вызывало `OperationalError` при запуске приложения. Корневая причина: БД была создана до добавления поля в модель, `create_all()` не обновляет существующие таблицы.

### ✅ Выполненные задачи:

1. **Удалена старая БД** (data/finfocus.db)
   - 0 пользователей, orphan транзакции - данные не ценные

2. **Исправлены импорты в скриптах**
   - `scripts/seed_database.py` — обновлены на `app.core.database`
   - `scripts/seed_test_data.py` — обновлены на `app.core.database`
   - Использование `get_db_session()` context manager

3. **Создана новая БД с актуальной схемой**
   - Запущена `init_database()` — создана БД с `monthly_savings_budget`
   - Наполнена тестовыми данными через `seed_database.py`

4. **Обновлена документация**
   - `.reports/epics/epic-01-coreMVP/technical.md` — обновлены примеры API
   - `.memory-bank/testing.md` — обновлены примеры фикстур

### 📊 Результат:
- ✅ БД создана с полной схемой (включая monthly_savings_budget)
- ✅ 98 unit тестов проходят
- ✅ Все скрипты используют актуальный API
- ✅ Документация синхронизирована с кодом

### 💡 Ключевые уроки:

1. **SQLite limitations** — `create_all()` не обновляет схему, для production нужны Alembic миграции
2. **Documentation drift** — примеры в документации могут устаревать, нужна периодическая синхронизация
3. **Grep-audit** — полезен для поиска устаревших паттернов после рефакторинга

---

## 📦 Архивные батчи

Старые батчи перемещены в архив для соблюдения Rolling Window Pattern (последние 5 батчей).

**Архив**: `.reports/archive/2026-Q1-batches.md`

**Архивированные батчи**:
- Батч 9: Multiple Goals with Priorities (2026-01-21)
- Батч 8: Recurring Transactions (2026-01-20)
- Батч 7: Goals UI (2026-01-19)
- Батч 6: Dashboard Integration (2026-01-19)
- Батч 5: Кассовый календарь (2026-01-19)
- Батч 4: Исправление Pattern-Matching Callbacks (2025-12-22)
- Батч 3: Диагностика регрессии (2025-11-16)
- Батч 2: Исправление автоудаления операций (2025-11-03)
- Фаза 1: Database Integration (2025-01-27)
- Батч 0: Discovery & Foundation (2025-01-27)

---

*Последнее обновление: 2026/01/25*
*Формат: Rolling Window (последние 5 батчей)*
