# FinFocus Memory Bank - Главное оглавление

## Суть проекта
**FinFocus** - веб-приложение для планирования личного и семейного бюджета с фокусом на кассовый календарь и целевые накопления.

**Уникальная ценность**: Кассовое планирование с прогнозом остатков по дням + автоматическое распределение бюджета между множественными накопительными целями с приоритетами.

**Статус**: Epic-03-Analytics завершен ✅ (Батч 3.1 + 3.2 merged)

**Последнее обновление**: 2026-01-23 (после merge протокола 0010)

## Быстрые ссылки на разделы

### Архитектура и технологии (КРИТИЧНО)
- [architecture.md] - Модульная архитектура Dash приложения, слои системы, паттерны
- [tech-stack.md] - Python 3.12 + Dash 2.17.1 + SQLAlchemy 2.0.23, зависимости, версии

### Стандарты разработки (КРИТИЧНО)
- [code-style.md] - Python docstrings на русском, type annotations, batch workflow, git conventions

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
  - Chips UI для быстрой категоризации
  - Bulk actions для массового назначения категорий
  - CSV экспорт с UTF-8 BOM
  - Страница /analytics с donut и bar charts

**Ближайшие задачи**:
1. Code review и merge PR #10
2. Начать Epic-04: Advanced Features (импорт, подушка безопасности)

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
├── testing.md            # Стратегия тестирования
├── deployment.md         # Запуск и деплоймент
└── modules/              # Модули системы (краткие)
    ├── database.md       # ORM модели
    ├── services.md       # Бизнес-логика
    ├── ui-components.md  # UI компоненты
    ├── routing.md        # Система роутинга
    ├── schema.md         # TypedDicts (NEW)
    └── utils.md          # Утилиты (NEW)
```

---

**Версия Memory Bank**: 3.0
**Дата создания**: 2026-01-17
**Последнее обновление**: 2026-01-23 (после протокола 0009 merge)
**GitHub**: https://github.com/SkyTger/FinFocus
