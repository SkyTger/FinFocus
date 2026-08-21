# Функциональность FinFocus

## Суть
Краткий обзор реализованных функций приложения с ссылками на детали.

## Core Features (MVP готов)

### 1. Кассовый календарь ✅
**Статус**: Завершен (Протокол 0002, PR #2)

**Возможности**:
- Сетка дней с балансами на каждый день
- Цветовая индикация: зеленый (положительный), красный (отрицательный), желтый (< 5000₽)
- Навигация по месяцам (±12 месяцев)
- Stats карточки: Доходы/Расходы/Баланс за месяц
- Клик на день → открытие модала создания операции
- Автообновление после CRUD операций

**Технические детали**:
- CalendarService: calculate_daily_balances, get_month_summary
- Decimal сериализация для dcc.Store
- TRANSFER транзакции исключены из расчетов баланса
- Pattern-Matching callbacks с ADR-003 guard clauses

**Файлы**:
- `app/components/calendar.py` (~700 строк)
- `app/services/calendar_service.py` (~310 строк)
- `app/assets/calendar.css` (~190 строк)

---

### 2. Управление операциями (CRUD) ✅
**Статус**: Завершен (Фаза 2 Core MVP + Протокол 0011)

**Возможности**:
- Создание операций: income/expense/transfer
- Редактирование и удаление операций
- Выбор категории (опционально)
- Повторяющиеся операции (Протокол 0005):
  - Периоды: weekly, monthly, yearly
  - Anchored-алгоритм (31 янв → 28 фев → 31 мар)
  - Exceptions: skip, edit экземпляр, edit серию
- Быстрая категоризация через chips (Протокол 0011):
  - 5 частых категорий + overflow dropdown
  - Pattern-Matching callbacks
  - Guard для TRANSFER/ADJUSTMENT
- Bulk операции (Протокол 0011):
  - Multi-select до 100 транзакций
  - Массовое назначение категории
  - WYSIWYG behavior (сброс selection при фильтрации)
- CSV экспорт (Протокол 0011):
  - UTF-8 BOM для Excel совместимости
  - Filename: finfocus_transactions_{YYYY-MM-DD}.csv
  - Учет фильтра "Без категории"

**Технические детали**:
- TransactionService: CRUD + bulk_update_category (max 100) + export_to_csv
- RecurringService: Anchored-алгоритм, MAX_INSTANCES_PER_CALL = 1000
- Global Transaction Modals (доступны с любой страницы)
- Refresh Trigger Pattern для синхронизации между страницами

**Файлы**:
- `app/components/transactions.py` (~1800 строк после протокола 0011)
- `app/components/transaction_modals.py` (~600 строк)
- `app/services/transaction_service.py`
- `app/services/recurring_service.py` (~550 строк)

---

### 3. Накопительные цели ✅
**Статус**: Завершен (Протокол 0004, 0006, 0007, 0008)

**Возможности**:
- Множественные цели с приоритетами (1, 2, 3...)
- Автоматическое распределение бюджета (жадный алгоритм)
- Три режима накоплений (Протокол 0007):
  - **Free** (1.0x) — минимальные взносы
  - **Medium** (1.15x) — +15% буфер
  - **Strict** (1.5x) — агрессивные накопления
- Статусы: ACTIVE, PAUSED, COMPLETED
- Управление приоритетами: кнопки ↑↓ (shift-down алгоритм)
- Настройка общего бюджета накоплений
- Перераспределение при достижении цели (Протокол 0008):
  - Temporary Status Pattern
  - Preview с comparison OLD vs NEW allocation
  - Confirm/Decline action

**Технические детали**:
- GoalService: CRUD, приоритеты, бюджет, contributions
- AllocationService: жадный алгоритм распределения
- RedistributionService: Temporary Status Pattern, preview
- Monthly Contribution Formula (с guard clauses для edge cases)
- TypedDicts: AllocationResult, AllocationSummary, GoalDisplayData, RedistributionPreview

**Файлы**:
- `app/components/goals.py` (~1500 строк)
- `app/services/goal_service.py`
- `app/services/allocation_service.py`
- `app/services/redistribution_service.py`
- `app/assets/goals.css` (~270 строк)

---

### 4. Dashboard с метриками ✅
**Статус**: Завершен (Протокол 0003)

**Возможности**:
- 4 metric карточки: Balance, Income, Expense, Goals (с реальными данными)
- Cashflow bar chart (Plotly):
  - Переключатель month/year
  - Последние 12 месяцев или 5 лет
- Recent transactions table (последние 5)
- Savings агрегация по всем ACTIVE целям

**Технические детали**:
- DashboardService: get_overview_metrics, get_cashflow_data, get_recent_transactions
- Composition: использует CalendarService и GoalService
- dcc.Store для хранения периода (month/year)
- TypedDicts: OverviewMetrics, CashflowDataPoint, RecentTransaction

**Файлы**:
- `app/components/dashboard.py` (~685 строк)
- `app/services/dashboard_service.py` (~290 строк)

---

## Analytics & UX (Батч 3)

### 5. Категоризация операций ✅
**Статус**: Завершен (Протокол 0009, 0011)

**Возможности**:
- 16 предустановленных категорий (seed idempotent)
- Категория опциональна ("ленивая категоризация")
- Фильтр "Без категории" в списке транзакций
- Quick chips для быстрого назначения (Протокол 0011):
  - 5 частых категорий пользователя
  - Overflow dropdown с полным списком
  - TRANSFER/ADJUSTMENT не могут иметь категорию
- Recurring шаблоны → категория по умолчанию для экземпляров
- Bulk назначение категории (до 100 транзакций)

**Технические детали**:
- Category модель (name, icon, type, is_system, sort_order)
- Transaction.category_id (nullable FK)
- CategoryService: get_frequent_for_type для chips UI
- TransactionService: bulk_update_category (max 100)
- Pattern-Matching callbacks с 3-уровневыми guard clauses

**Файлы**:
- `app/models/database.py` (Category модель)
- `app/services/category_service.py`
- `scripts/seed_categories.py`

---

### 6. Сверка баланса ✅
**Статус**: Завершен (Протокол 0009)

**Возможности**:
- Модал сверки на странице календаря
- Preview разницы: ожидаемый vs фактический баланс
- Создание ADJUSTMENT транзакции для корректировки
- Цветовая индикация (положительная/отрицательная разница)

**Технические детали**:
- TransactionType.ADJUSTMENT (новый тип)
- ReconciliationService: get_expected_balance, calculate_preview, create_adjustment
- CalendarService обрабатывает ADJUSTMENT в calculate_daily_balances
- ADJUSTMENT не может быть recurring (валидация)

**Файлы**:
- `app/services/reconciliation_service.py`
- `app/components/calendar.py` (модал сверки)

---

### 7. Аналитика расходов ✅
**Статус**: Завершен (Протокол 0010)

**Возможности**:
- Страница /analytics с графиками:
  - Donut chart — структура расходов по категориям
  - Bar chart — динамика расходов по месяцам (stacked/grouped toggle)
- Фильтры периода: месяц/квартал/год
- Группировка мелких категорий (<3%) в "Прочее"

**Технические детали**:
- AnalyticsService (~290 строк):
  - get_expenses_by_category (SQL GROUP BY)
  - get_monthly_trends (тренды за N месяцев)
  - Группировка мелких категорий
- Plotly charts с Plotly Express
- TypedDicts: ExpenseByCategory, MonthlyTrend

**Файлы**:
- `app/services/analytics_service.py`
- `app/components/analytics.py`

---

### 8. CSV экспорт ✅
**Статус**: Завершен (Протокол 0011)

**Возможности**:
- Кнопка "Экспорт CSV" в header Transactions
- Учет фильтра "Без категории"
- UTF-8 BOM для Excel совместимости
- Filename: finfocus_transactions_{YYYY-MM-DD}.csv

**Технические детали**:
- TransactionService.export_to_csv()
- dcc.Download компонент
- CSV format с полями: date, type, amount, category, description

**Файлы**:
- `app/services/transaction_service.py` (export_to_csv метод)
- `app/components/transactions.py` (export_transactions callback)

---

### 9. Quick-Add Chips ✅
**Статус**: Завершен (Протокол 0012, PR #12)

**Возможности**:
- 7 hardcoded chips (5 расходов + 2 доходов):
  - Expense: Продукты, Транспорт, Кафе и рестораны, Развлечения, Здоровье
  - Income: Зарплата, Подработка
- Расположение: страница Transactions, между header и фильтрами
- Клик на chip → модал создания с предвыбранной категорией
- Модал "Ещё..." для выбора из всех категорий (tabs: расходы/доходы)
- Preselection Store Pattern — передача category_id и type в модал
- Сокращение шагов создания операции: 6 → 3-4

**Технические детали**:
- TypedDict QuickAddChipData (category_id, name, icon, type)
- DEFAULT_QUICK_ADD_CHIP_NAMES — константа с 7 названиями
- _get_quick_add_chips() — lookup по имени (защита от ID mismatch)
- Pattern-Matching IDs: {"type": "qa-chip", ...}, {"type": "qa-more-btn", ...}
- Preselection Stores: preselected-category, preselected-type
- ADR-003 guard clauses в 3 callbacks
- Responsive: horizontal scroll на 768px, уменьшенные размеры на 576px

**Файлы**:
- `app/schema/quick_add.py` — QuickAddChipData
- `app/components/transactions.py` — 3 UI функции, 3 callbacks
- `app/components/transaction_modals.py` — 2 Stores, preselection callback
- `app/assets/transactions.css` — стили .qa-* (~100 строк)
- `tests/test_quick_add_chips.py` — 13 unit тестов

**Следующие шаги** (Протокол B):
- Кастомизация chips пользователем
- Частые операции → автоматические шаблоны
- Редактирование/удаление шаблонов

---

## Advanced Features (Батч 4 — в процессе)

### 10. Онбординг новых пользователей ✅
**Статус**: Завершен (Протокол 0014, PR #14)

**Возможности**:
- Blocking modal wizard при первом запуске приложения
- Обязательная настройка starting_balance для корректных расчетов календаря
- Кнопка "Пропустить" для опытных пользователей
- Dashboard toast (мягкое напоминание) при нулевом балансе:
  - Показывается пользователям с starting_balance=0
  - CTA кнопка "Настроить" → переход на Calendar с автооткрытием модала сверки
  - Dismissable (можно закрыть, состояние в session Store)
- Calendar query param ?open_recon=1 для автооткрытия модала сверки
- Fail-closed DB strategy (wizard скрывается при ошибке БД, не блокирует приложение)

**Технические детали**:
- User.first_launch (Boolean, default=True) — флаг первого запуска
- OnboardingService:
  - get_status(user_id) → OnboardingStatus (TypedDict)
  - complete_with_balance(user_id, starting_balance) — завершение onboarding
  - skip(user_id) — пропуск (first_launch=False, balance остается 0)
- Migration script: scripts/migrate_003_first_launch.py (idempotent)
- Blocking modal: backdrop="static", keyboard=False, no close button
- Calendar query param handler с full cleanup (url.search = "")
- ADR-003 guard clauses в callbacks
- Flush/commit contract в сервисе (docstring)

**Файлы**:
- `app/models/database.py` — User.first_launch (+1 поле)
- `app/services/onboarding_service.py` — OnboardingService (~80 строк)
- `app/schema/onboarding.py` — OnboardingStatus TypedDict
- `app/components/onboarding_wizard.py` — Wizard UI + callbacks (~200 строк)
- `app/components/dashboard.py` — Toast UI + callbacks (~100 строк добавлено)
- `app/components/calendar.py` — Query param handler (~30 строк изменено)
- `app/main.py` — Global wizard + Store integration
- `app/assets/onboarding.css` — Стили (~80 строк)
- `tests/test_onboarding_service.py` — 8 unit тестов
- `scripts/migrate_003_first_launch.py` — Migration script

**Ключевые паттерны**:
- Fail-closed DB strategy — wizard скрывается при ошибке, не блокирует UI
- Query param full cleanup — url.search = "" (не оставляем артефактов)
- Flush/commit contract — сервис flush(), caller commit()
- ADR-003 guard clauses — n_clicks проверки для предотвращения автовызовов

---

### 11. Финансовая подушка безопасности ✅
**Статус**: Завершен (Протокол 0013, PR #13)

**Возможности**:
- Настройка целевого размера подушки (произвольная сумма)
- Настройка порога риска:
  - Процент от цели (30% по умолчанию)
  - Или фиксированная сумма
- Карточка подушки на странице /goals:
  - Статус "Не настроена" → кнопка "Настроить"
  - Статус "Настроена" → прогресс-бар с маркером порога
  - 4 цветовых статуса: danger (<порог), warning, info, success (≥100%)
- Модал настройки с калькулятором сценариев:
  - Расчет рекомендации по сценариям (месячные расходы по категориям)
  - Режимы: sum (сумма всех) / max_scenario (максимальный)
  - Применение рекомендации к полю цели
- Интеграция с балансом пользователя (User.current_balance для прогресса)

**Технические детали**:
- CushionService с Percent NewType для type safety
- 3 поля в User модели:
  - cushion_target (Decimal, nullable) — целевая сумма подушки
  - cushion_threshold_percent (Integer, default 30) — порог риска в %
  - cushion_threshold_manual (Decimal, nullable) — фиксированный порог
- 12 callbacks с ADR-003 guard clauses:
  - render_cushion_card, load_cushion_settings, open/close/populate modal
  - mark_threshold_manual, toggle_calculator
  - add/remove_scenario (Pattern-Matching)
  - calculate_recommendation, apply_recommendation
  - save/reset_cushion_settings
- TypedDicts: CushionSettings, CushionScenario (app/schema/cushion.py)
- Калькулятор сценариев: анализ расходов по категориям для рекомендации
- Responsive стили .cushion-* с breakpoints 768px, 576px

**Файлы**:
- `app/services/cushion_service.py` — CushionService (~180 строк)
- `app/schema/cushion.py` — Percent NewType, TypedDicts (~40 строк)
- `app/components/goals.py` — карточка + модал + callbacks (~800 строк добавлено)
- `app/assets/goals.css` — стили .cushion-* (~200 строк добавлено)
- `tests/test_cushion_service.py` — 20 unit тестов

**Следующие шаги** (протокол 0014):
- Календарная визуализация подушки (график пополнения в Calendar)
- Умное распределение неосвоенного бюджета накоплений

---

### 12. Tooltip для дней календаря ✅
**Статус**: Завершен (Протокол 0015, PR #15)

**Возможности**:
- CSS-only hover tooltip (zero server calls) при наведении на день календаря
- Отображение баланса на конец дня (positive/negative классы)
- Список операций дня с категориями и суммами:
  - Emoji категории из category_icon
  - Strikethrough для пропущенных recurring экземпляров (is_skipped)
  - Цветовая индикация: зеленый (доходы), красный (расходы)
- Expand/collapse через CSS checkbox hack:
  - Max 5 операций видимы сразу
  - Кнопка "Показать ещё" для раскрытия полного списка
- Клик по операции в tooltip → open edit modal
- Edge detection для правых 2 колонок (tooltip слева)
- Mobile-friendly: tooltip отключен на ширине < 768px

**Технические детали**:
- Glassmorphism стиль: backdrop-filter blur + rgba background
- Sibling structure в build_day_cell() для hover trigger
- TransactionInfo расширен: is_skipped, category_icon (TypedDict)
- VirtualTransaction расширен: is_skipped, category_icon (TypedDict)
- Pattern-Matching callback: open_edit_from_tooltip() с ADR-003 guard clauses
- ICON_TO_EMOJI mapping из formatters.py
- MAX_VISIBLE_TRANSACTIONS = 5 константа
- Transitions с delay для плавного появления

**Файлы**:
- `app/components/calendar.py` — tooltip builder functions (~150 строк добавлено)
  - _build_day_tooltip() — полный tooltip с expand/collapse
  - _build_tooltip_balance() — header с балансом
  - _build_tooltip_transaction_row() — строка операции
  - open_edit_from_tooltip() — Pattern-Matching callback
- `app/services/calendar_service.py` — TransactionInfo extended (~20 строк изменено)
- `app/schema/recurring.py` — VirtualTransaction extended (~2 поля)
- `app/assets/calendar.css` — glassmorphism стили (~200 строк добавлено)
- `tests/test_calendar_tooltip.py` — 20 unit тестов

**Ключевые паттерны**:
- CSS-only tooltip — zero server calls, instant response
- Sibling structure — clickable_content + tooltip как siblings в wrapper
- Checkbox hack — expand/collapse без JavaScript
- Pattern-Matching ID: {"type": "tooltip-txn", "date": "...", "id": ..., "is_virtual": bool, "template_id": int | -1}
- Placeholder -1 для template_id вместо None (Dash не поддерживает None в PM IDs)

**Ограничения**:
- Tooltip не показывается на mobile (< 768px) из-за отсутствия hover
- Max 5 операций видны без expand (UX решение)
- Tooltip скрывается при клике вне области (CSS behavior)

---

### 13. Интеграция бюджета целей с календарём ✅
**Статус**: Завершена (Протокол 0016, PR #16; улучшения UX — Протокол 0017)

**Возможности**:
- Два режима резервирования бюджета накоплений:
  - **"fixed_date"** — recurring операция "Резервирование бюджета" на указанную дату месяца (1-28 число)
    - Создаётся автоматически при выборе режима
    - Сумма синхронизируется с User.monthly_savings_budget
    - Операция SAVINGS_RESERVE уменьшает баланс в календаре
    - "(авто)" суффикс для readonly операций
  - **"from_balance"** — операции создаются только при взносах в цели
    - При добавлении взноса создаётся SAVINGS_CONTRIBUTION транзакция
    - description = "Взнос: {название цели}"
    - FK связь GoalContribution.transaction_id → Transaction.id
- Сводка по целям (Goals Summary) объединяет два аспекта:
  - "Бюджет накоплений (месяц): X / Y ₽" — используемый / общий бюджет
  - "Сумма активных целей: Z ₽" — агрегация по всем ACTIVE целям
  - Подпись "В текущем месяце" для ясности
- Модал выбора режима резервирования:
  - Переключатель режимов (Radio buttons)
  - Выбор дня месяца (1-28) для fixed_date режима
  - Automatic recurring template creation/stop
- Визуализация SAVINGS операций в календаре:
  - SAVINGS_RESERVE: иконка 💼, суффикс "(авто)", readonly (нельзя редактировать)
  - SAVINGS_CONTRIBUTION: иконка 🎯, кликабельно → edit modal
  - Purple цвет для сумм (.tooltip-txn-amount.savings)
- Динамический расчёт доступного бюджета:
  - `remaining_budget = monthly_savings_budget - SUM(contributions_this_month)`
  - Обновляется при каждом взносе
  - При взносах до даты резерва (fixed_date) — создаётся Exception для recurring с уменьшенной суммой

**Технические детали**:
- BudgetReservationService (~350 строк) с CRUD методами:
  - get_settings(), set_mode(), get_budget_progress()
  - create/update/delete_contribution_transaction()
  - sync_template_amount() для синхронизации recurring шаблона
  - adjust_reserve_for_contribution() — коррекция резерва при досрочных взносах (Протокол 0017)
- TransactionType расширен: SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
- User модель: reservation_mode, reservation_day (1-28)
- GoalContribution.transaction_id FK (SET NULL ondelete)
- CalendarService интеграция: SAVINGS операции учитываются в балансе, но не в расчётах целей
- GoalService интеграция:
  - add_contribution() создаёт транзакцию в режиме from_balance
  - add_contribution() вызывает adjust_reserve_for_contribution() для fixed_date
- TypedDicts: BudgetReservationSettings, BudgetProgress, ContributionRecord
- Migration: scripts/migrate_005_reservation.py (idempotent)
- 32 unit тестов для BudgetReservationService (26 + 6 для adjust_reserve)
- 8 integration тестов для CalendarService с SAVINGS операциями

**Файлы**:
- `app/services/budget_reservation_service.py` — BudgetReservationService (~350 строк)
- `app/schema/budget_reservation.py` — TypedDicts (~60 строк)
- `app/models/database.py` — User (+2 поля), TransactionType (+2 enum), GoalContribution (+1 FK)
- `app/components/goals.py` — сводка целей + модал режима (~250 строк изменено, Протокол 0017)
- `app/components/calendar.py` — визуализация SAVINGS (~50 строк изменено)
- `app/services/calendar_service.py` — SAVINGS_RESERVE/CONTRIBUTION handling (~30 строк изменено)
- `app/services/goal_service.py` — add_contribution интеграция (~20 строк изменено)
- `app/assets/goals.css` — стили goals summary (~80 строк)
- `app/assets/calendar.css` — стили .savings (~20 строк)
- `tests/test_budget_reservation_service.py` — 32 unit тестов
- `scripts/migrate_005_reservation.py` — Migration script

**Ключевые паттерны**:
- **Два режима резервирования** — гибкость для разных стилей планирования
- **FK связь** — GoalContribution.transaction_id обеспечивает целостность данных
- **Динамический бюджет** — прозрачность и контроль расходования бюджета
- **Readonly SAVINGS_RESERVE** — автоматические операции нельзя редактировать напрямую
- **Sync template amount** — автоматическая синхронизация recurring шаблона с бюджетом
- **SET NULL ondelete** — при удалении транзакции contribution остаётся в истории
- **adjust_reserve_for_contribution** — создание Exception для recurring при досрочных взносах (Протокол 0017)

**Философия**:
- Бюджет накоплений — это НЕ расход, а резервирование части денег
- SAVINGS операции уменьшают баланс, но не считаются расходами для целей
- Нет блокировок — только визуализация прогресса и остатка бюджета
- Пользователь видит, как накопления влияют на остаток по дням

**Детали**:
- `.reports/epics/epic-04-advanced/spec-budget-calendar-integration.md`
- `.reports/epics/epic-04-advanced/spec-budget-ui-improvements.md`

---

### 14. Отложенные покупки (Wishlist) ✅
**Статус**: Завершена (Протокол 0020, PR #20)

**Возможности**:
- Управление списком желаемых покупок (Wishlist):
  - CRUD операции (создание, редактирование, удаление хотелок)
  - Два уровня приоритета: 1=фокус (срочные), 2=потом (отложенные)
  - Категория опциональна (наследуется в транзакцию при планировании)
  - Статусы: "new" (новая) / "planned" (запланирована с датой)
- Dashboard виджет "Отложенные покупки":
  - До 5 фокусных хотелок (priority=1)
  - Название, сумма, статус (новая / запланирована + дата)
  - Клик на виджет → открывает модал
- Wishlist модал:
  - Полный список (фокусные + отложенные)
  - Inline-форма добавления
  - Кнопки: Редактировать, Удалить, Запланировать
  - Confirm modal для перепланирования
- Календарь wishlist mode (`/calendar?wishlist_item=ID`):
  - Overlay-баннер: название, сумма, легенда, счетчик дней, кнопка "Отмена"
  - Визуализация safe/unsafe дней:
    - Safe дни: зеленая подсветка (.safe-day)
    - Unsafe дни: оранжевый маркер (подушка), красный минус (касса < 0)
  - JS hover для каскадного пересчета остатков:
    - При наведении на день — все балансы месяца пересчитываются "после покупки в этот день"
    - Каскадный эффект: день покупки + все последующие дни до конца месяца
    - Маркеры safe/unsafe остаются статичными (pre-calculated map)
    - Реализация: wishlist_hover.js (IIFE, MutationObserver, Intl.NumberFormat)
  - Клик по дню → create-modal с предзаполнением:
    - Дата, сумма, описание "Отложенная покупка: {название}"
    - Категория из хотелки (если задана)
    - Risk warning для unsafe дней (не блокирует сохранение)
- Preselection Store Pattern:
  - 4 новых Store: preselected-amount, -date, -description, -risk-warning
  - source="wishlist" для trigger mark_planned
- Mark planned workflow:
  - После создания транзакции → статус хотелки "planned"
  - FK связь: WishlistItem.planned_transaction_id → Transaction.id (ON DELETE SET NULL)
  - Orphan detection: callback detect_orphaned_wishlist() сбрасывает статус при удалении транзакции

**Технические детали**:
- WishlistService (~270 строк):
  - CRUD: create_item, get_all, get_focus, get_by_id, update_item, delete_item
  - Planning: mark_as_planned, reset_planned, check_orphaned_planned
  - Planned guard: статус "planned" → можно менять только name, priority
  - Валидация: name (1-100), amount > 0, priority in {1, 2}
- PurchaseRecommendationService (~160 строк):
  - get_safe_dates_map() — карта безопасности дней (cushion + negative_balance checks)
  - precalculate_hover_data() — предрассчет ~960 балансов для JS hover (~30KB Store)
  - Каскадная проверка: min(balance[d:end_month] - amount) для всех дней от кандидата
  - Два критерия: подушка (CushionService.threshold_amount) + баланс ≥ 0
- Calendar wishlist module (calendar_wishlist.py, ~280 строк):
  - build_wishlist_overlay_banner() — баннер с легендой и счетчиком
  - build_wishlist_day_cell() — ячейка с safe/unsafe маркерами, reasons tooltip
  - build_wishlist_calendar_grid() — полная сетка с .wishlist-mode CSS
  - cancel_wishlist_mode callback
- Wishlist hover JS (app/assets/wishlist_hover.js, ~145 строк):
  - IIFE pattern, MutationObserver для обнаружения .wishlist-mode
  - getHoverData() — JSON.parse из #wishlist-hover-data (dcc.Store DOM)
  - applyHoverBalances() / restoreBaseBalances() — подмена балансов
  - attachHoverListeners() — mouseenter/mouseleave на .calendar-day:not(.past-day-wishlist)
  - data-hover-attached guard против повторного подключения
  - Intl.NumberFormat('ru-RU') для форматирования сумм
- TypedDicts (app/schema/wishlist.py):
  - WishlistItemData — для UI serialization (Decimal → string)
  - SafeDateInfo — {safe: bool, reasons: list[str]}
  - HoverBalances — {base_balances: dict, by_candidate: dict}

**Файлы**:
- `app/models/database.py` — WishlistItem ORM (+7 полей)
- `app/services/wishlist_service.py` — WishlistService (~270 строк)
- `app/services/purchase_recommendation_service.py` — PurchaseRecommendationService (~160 строк)
- `app/schema/wishlist.py` — 3 TypedDicts (~50 строк)
- `app/components/wishlist.py` — Wishlist UI + modal + callbacks (~500 строк)
- `app/components/calendar_wishlist.py` — Calendar wishlist grid + overlay (~280 строк)
- `app/components/dashboard.py` — +wishlist виджет (~70 строк)
- `app/components/calendar.py` — +wishlist mode integration (~100 строк изменено)
- `app/components/transaction_modals.py` — +4 preselection Stores (~40 строк)
- `app/assets/wishlist.css` — стили overlay, markers, safe/unsafe (~130 строк)
- `app/assets/wishlist_hover.js` — JS hover logic (~145 строк)
- `tests/test_wishlist_service.py` — 31 unit тест
- `tests/test_purchase_recommendation.py` — 11 unit тестов
- `scripts/migrate_006_wishlist.py` — idempotent migration

**Ключевые паттерны**:
- **Preselection Store Pattern** — передача данных между модалами (amount, date, description, risk_warning)
- **Orphan Detection** — check_orphaned_planned() для очистки после delete Transaction
- **Clientside JS hover** — zero server calls, предрассчет в Store + MutationObserver
- **Lazy import pattern** — _get_budget_service() для избежания circular dependency (как в 0018)
- **Guard #6 в calendar** — блокировка SAVINGS_CONTRIBUTION в tooltip (аналогично SAVINGS_RESERVE)
- **Calendar query param** — ?wishlist_item=ID для активации wishlist mode (как ?open_recon=1)

**Критичные детали**:
- **Каскадный hover**: пересчет балансов от выбранного дня до конца месяца (не только день покупки)
- **Статическая карта**: маркеры safe/unsafe pre-calculated, не меняются при hover
- **Orphan protection**: ON DELETE SET NULL + callback для автосброса статуса
- **Planned guard**: статус "planned" блокирует изменение суммы и категории (только name, priority)
- **Performance**: предрассчет ~200ms (открытие режима), hover < 1ms (clientside)
- **Tolerance**: покупка "проходит" если min(balance) >= threshold (не строго >)

**Следующие шаги** (B-фазы):
- Проверка бюджета целей (AllocationService) — фиолетовый маркер "бюджет нарушен"
- Планирование нескольких хотелок с учетом взаимного влияния
- Статус "archived" и отдельная страница `/wishlist` с фильтрацией
- Тач/мобильное поведение (тап=preview, повторный тап=select)

---

### 15. Профиль пользователя ✅
**Статус**: Завершен (Протокол 0024, PR #24)

**Возможности**:
- Onboarding wizard расширен: имя + аватарка + стартовый баланс
- 10 emoji аватарок (конфиг в app/config/avatars.py)
- Динамический sidebar с именем и аватаркой (Store-based обновление)
- Profile modal для редактирования имени и аватарки
- Dashboard greeting "Добро пожаловать, {name}!"
- Bootstrap модуль (app/core/bootstrap.py) для инициализации БД
- Idempotent миграции 001-007 (app/core/migrations.py)

**Технические детали**:
- User.avatar_id (String(20), nullable, default via bootstrap)
- OnboardingService расширен: complete(), update_profile(), get_profile(), _validate_profile_fields()
- UserProfile TypedDict в app/schema/onboarding.py
- Store("profile-updated") как event bus для реактивного обновления sidebar
  и дашборда (протокол 0026: load_dashboard_data, toggle_balance_toast,
  update_dashboard_greeting подписаны — онбординг применяется без перезагрузки)
- complete_with_balance() deprecated wrapper
- Миграция 007_avatar_id (idempotent)

**Файлы**:
- `app/config/avatars.py` — конфиг 10 аватарок (~30 строк)
- `app/components/profile_modal.py` — модал редактирования (~150 строк)
- `app/components/onboarding_wizard.py` — расширен (имя + аватарка)
- `app/components/sidebar.py` — динамический профиль
- `app/core/bootstrap.py` — инициализация БД (~45 строк)
- `app/core/migrations.py` — миграции 001-007 (~180 строк)
- `tests/test_avatars.py`, `tests/test_bootstrap.py`, `tests/test_migration_007.py`

---

### 16. Импорт операций 🔄
**Статус**: Планируется

**Планируемые возможности**:
- Загрузка выгрузок из банков (CSV, Excel)
- Импорт из файлов (OFX, QIF)
- Маппинг полей
- Автоматическое определение категорий

---

## Критичные формулы и алгоритмы

### Баланс на дату
```
остаток = starting_balance + SUM(доходы) - SUM(расходы) до даты
TRANSFER транзакции исключаются
```

### Monthly Contribution (Goal)
```python
monthly_contribution = (target_amount - current_amount) / months_remaining

# Guard clauses:
if target_date <= today: return 0
if current_amount >= target_amount: return 0
```

### Allocation Algorithm (AllocationService)
```python
# Жадный алгоритм:
# Цели обрабатываются по priority (1, 2, 3...)
# Цель с priority=1 получает полное финансирование первой
# Остаток бюджета распределяется на следующие цели

# Savings Mode множители:
free: 1.0, medium: 1.15, strict: 1.5
```

### Redistribution Algorithm (RedistributionService)
```python
# Temporary Status Pattern:
# 1. Временно возвращаем COMPLETED → ACTIVE
# 2. Расчет OLD allocation
# 3. Permanent COMPLETED
# 4. Расчет NEW allocation
# 5. Preview с comparison
# 6. Confirm/Decline
```

---

Детали: см. `architecture.md` (Критичные детали), `modules/services.md`, `protocols.md`
