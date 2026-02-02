# FinFocus Memory Bank - Главное оглавление

## Суть проекта
**FinFocus** - веб-приложение для планирования личного и семейного бюджета с фокусом на кассовый календарь и целевые накопления.

**Уникальная ценность**: Кассовое планирование с прогнозом остатков по дням + автоматическое распределение бюджета между множественными накопительными целями с приоритетами.

**Статус**: Батч 4 (Budget-Calendar Integration + UI Improvements) завершен ✅, Epic-04-Advanced Features в процессе (5/6 фичи)

**Последнее обновление**: 2026-02-02 (после bugfix: edit virtual recurring operations, commit cae3575)

## Быстрые ссылки на разделы

### Архитектура и технологии (КРИТИЧНО)
- [architecture.md] - Модульная архитектура Dash приложения, слои системы, паттерны
- [tech-stack.md] - Python 3.12 + Dash 2.17.1 + SQLAlchemy 2.0.23, зависимости, версии

### Стандарты разработки (КРИТИЧНО)
- [code-style.md] - Python docstrings на русском, type annotations, batch workflow, git conventions

### Функциональность и протоколы
- [features.md] - Обзор реализованных функций (кассовый календарь, CRUD, цели, аналитика)
- [protocols.md] - История протоколов разработки (0002-0011) с деталями реализации

### Модули системы (краткие описания)
- [modules/database.md] - SQLAlchemy ORM: User, Transaction, Goal, GoalContribution
- [modules/services.md] - TransactionService, GoalService, CalendarService, RecurringService, DashboardService, AllocationService
- [modules/ui-components.md] - Dashboard, Sidebar, Transactions, Calendar, Goals - Dash компоненты
- [modules/routing.md] - URL-based routing, display_page callback
- [modules/schema.md] - TypedDicts для типизации (app/schema/)
- [modules/utils.md] - Утилиты форматирования и сериализации (app/utils/)

### Процессы и инструменты
- [testing.md] - pytest, coverage, QA workflow
- [deployment.md] - run.py, environment variables, database initialization

## Важные соглашения

**Batch Process (план → батч)**:
1. План-режим: Читать ROADMAP.md → предложить 1-3 файла батча → ждать подтверждения
2. Батч-режим: Редактировать ТОЛЬКО согласованные файлы → показать diffs → quality checks → обновить документацию

**Файлы контекста**:
- `ROADMAP.md` - Single Source of Truth для задач
- `.reports/notes/feature_progress.md` - последние 5 батчей (rolling window)
- `docs/adr/*.md` - Architecture Decision Records

**Git workflow**:
- Branches: `feature/...`, `bugfix/...`, `hotfix/...`
- Commits: `type: short_description` (например, `feat: add transaction service`)

## Инструкция для AI "с чего начать"

**При старте новой сессии (ОБЯЗАТЕЛЬНО, 3-5 минут)**:
1. Прочитать `@ROADMAP.md` - актуальные приоритеты
2. Прочитать `@.reports/notes/feature_progress.md` - история последних 5 батчей
3. Прочитать `@memory-bank/index.md` (этот файл) - понимание проекта

**При работе над задачей**:
1. Определить тип задачи → прочитать соответствующий модуль в `modules/`
2. Если новый паттерн → проверить `code-style.md` для консистентности
3. Если изменение архитектуры → проверить `architecture.md`
4. После батча → обновить `feature_progress.md` + `ROADMAP.md`

**При изменении scope**:
1. Записать решение в `.reports/epics/epic-XX/decisions.md` с блоком **КРИТИЧНО**
2. СРАЗУ обновить `ROADMAP.md`
3. Если изменились формулы/термины → обновить `CLAUDE.md`

## Текущие приоритеты (из ROADMAP.md)

**Epic-02-EnhancedPlanning** (Батч 2, 100% завершено):
- ✅ Повторяющиеся операции (завершена, PR #5)
- ✅ Множественные цели с приоритетами (завершена, PR #6)
- ✅ Три режима накоплений (завершена, PR #7)
- ✅ Перераспределение средств между целями (завершена, PR #8)

**Epic-03-Analytics** (Батч 3, 100% завершено):
- ✅ Категоризация + Сверка (завершена, PR #9)
- ✅ UX улучшения + Аналитика (завершена, PR #10)
  - Chips UI для быстрой категоризации некатегоризированных операций
  - Bulk actions для массового назначения категорий
  - CSV экспорт с UTF-8 BOM
  - Страница /analytics с donut и bar charts
- ✅ Восстановление UI компонентов (протокол 0011, PR #11)
  - Chips UI восстановлен после merge conflict
  - Bulk selection с multi-select checkboxes
  - CSV export с UTF-8 BOM для Excel
  - 13 новых тестов для _pluralize_operations helper

**Epic-04-Advanced Features** (Батч 4, 67% завершено):
- ✅ Quick-Add Chips для быстрого создания операций (завершена, PR #12, протокол 0012)
  - 7 hardcoded chips с предвыбранными категориями
  - Сокращение шагов создания: 6 → 3-4
  - Preselection Store Pattern
  - Модал "Ещё..." для выбора из всех категорий
- ✅ Финансовая подушка безопасности (завершена, PR #13, протокол 0013)
  - 3 поля в User: cushion_target, cushion_threshold_percent, cushion_threshold_manual
  - CushionService с Percent NewType для type safety
  - Карточка и модал настройки на /goals
  - Калькулятор сценариев (sum/max_scenario режимы)
  - 12 callbacks с ADR-003 guard clauses
- ✅ Онбординг новых пользователей (завершена, PR #14, протокол 0014)
  - User.first_launch для отслеживания первичных пользователей
  - OnboardingService (get_status, complete_with_balance, skip)
  - Blocking modal wizard с backdrop="static"
  - Dashboard toast для напоминания о нулевом балансе
  - Calendar query param ?open_recon=1 для автооткрытия модала сверки
  - 8 новых unit тестов (всего 300)
- ✅ Tooltip для дней календаря (завершена, PR #15, протокол 0015)
  - CSS-only hover tooltip с glassmorphism стилем
  - Отображение баланса и списка операций дня
  - Expand/collapse через CSS checkbox hack (max 5 visible)
  - Клик по операции в tooltip → edit modal
  - is_skipped и category_icon в TransactionInfo
  - 43 новых unit тестов (всего 343)
- ✅ Интеграция бюджета целей с календарём (завершена, PR #16-18, протокол 0016-0018)
  - BudgetReservationService с двумя режимами резервирования
  - "fixed_date" — recurring операция "Резервирование бюджета" на указанную дату
  - "from_balance" — операции "Взнос: цель" при каждом взносе
  - Сводка по целям объединяет бюджет и активные цели (протокол 0017)
  - Визуализация SAVINGS операций в календаре
  - adjust_reserve_for_contribution() для досрочных взносов (протокол 0017)
  - Переиспользование шаблонов при переключении режимов (протокол 0018)
  - recalculate_current_month_exception() для пересчёта при изменениях (протокол 0018)
  - 72 новых unit тестов (всего 418)
- Импорт операций из банков (планируется)
- Уведомления и напоминания (планируется)

**Ближайшие задачи**:
1. Продолжить Epic-04: Импорт операций из банков
2. Уведомления и напоминания

## Критичные детали

**Starting Balance Formula**:
```
остаток на дату = starting_balance + SUM(доходы) - SUM(расходы) до даты
TRANSFER транзакции исключаются из расчетов баланса
```

**Monthly Contribution Formula** (Goal):
```python
monthly_contribution = (target_amount - current_amount) / months_remaining
# Guard clauses: target_date в прошлом → 0, цель достигнута → 0
```

**Allocation Algorithm** (AllocationService):
```python
# Жадный алгоритм: цели обрабатываются по priority (1, 2, 3...)
# Цель с priority=1 получает полное финансирование первой
# Остаток бюджета распределяется на следующие цели

# Savings Mode множители:
# free: 1.0 (минимальные взносы)
# medium: 1.15 (+15% буфер)
# strict: 1.5 (агрессивные накопления)
```

**Redistribution Algorithm** (RedistributionService):
```python
# При достижении цели:
# 1. Temporary Status Pattern: временно возвращаем статус ACTIVE для расчета OLD allocation
# 2. Расчет freed_budget через старый allocation
# 3. NEW allocation без достигнутой цели
# 4. Preview с comparison OLD vs NEW
# 5. Confirm/Decline action → аудит-логирование
```

**Pattern-Matching Callbacks** (Dash):
- При `ALL` callbacks проверять `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
- Использовать `prevent_initial_call=True` для модалов

**Recurring Transactions**:
- Anchored-алгоритм: 31 янв → 28 фев → 31 мар (сохраняет исходный день месяца)
- Шаблоны (is_recurring=True) + exceptions (recurring_parent_id)
- Виртуальные экземпляры генерируются RecurringService

## Полезные команды

```bash
# Запуск приложения
python run.py  # http://localhost:8050

# Тесты
pytest -v --cov

# Качество кода
black app/
flake8 app/

# База данных
# SQLite: data/finfocus.db (автоинициализация при запуске)
# Миграции: scripts/migrate_*.py
```

## Структура Memory Bank

```
memory-bank/
├── index.md              # Этот файл - главное оглавление
├── architecture.md       # Архитектура системы (КРИТИЧНО)
├── tech-stack.md         # Технологический стек (КРИТИЧНО)
├── code-style.md         # Стандарты кода (КРИТИЧНО)
├── features.md           # Обзор функциональности (NEW)
├── protocols.md          # История протоколов 0002-0011 (NEW)
├── testing.md            # Стратегия тестирования
├── deployment.md         # Запуск и деплоймент
└── modules/              # Модули системы (краткие)
    ├── database.md       # ORM модели
    ├── services.md       # Бизнес-логика
    ├── ui-components.md  # UI компоненты
    ├── routing.md        # Система роутинга
    ├── schema.md         # TypedDicts
    └── utils.md          # Утилиты
```

---

**Версия Memory Bank**: 3.7
**Дата создания**: 2026-01-17
**Последнее обновление**: 2026-02-02 (после bugfix: edit virtual recurring operations, commit cae3575)
**GitHub**: https://github.com/SkyTger/FinFocus
