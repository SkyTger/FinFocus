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

### 10. Финансовая подушка безопасности ✅
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

### 11. Импорт операций 🔄
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
