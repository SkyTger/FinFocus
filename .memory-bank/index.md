# FinFocus Memory Bank - Главное оглавление

## Суть проекта
**FinFocus** - веб-приложение для планирования личного и семейного бюджета с фокусом на кассовый календарь и целевые накопления.

**Уникальная ценность**: Кассовое планирование с прогнозом остатков по дням + автоматический расчет взносов для достижения накопительных целей.

**Статус**: Epic-01-CoreMVP в процессе (40% завершено, Фаза 2 из 5 готова)

## Быстрые ссылки на разделы

### Архитектура и технологии (КРИТИЧНО)
- [architecture.md] - Модульная архитектура Dash приложения, слои системы, паттерны
- [tech-stack.md] - Python 3.12 + Dash 2.17.1 + SQLAlchemy 2.0.23, зависимости, версии

### Стандарты разработки (КРИТИЧНО)
- [code-style.md] - Python docstrings на русском, type annotations, batch workflow, git conventions

### Модули системы (краткие описания)
- [modules/database.md] - SQLAlchemy ORM: User, Transaction, Goal, GoalContribution
- [modules/services.md] - TransactionService, GoalService, CRUD логика, валидация
- [modules/ui-components.md] - Dashboard, Sidebar, Transactions - Dash компоненты
- [modules/routing.md] - URL-based routing, display_page callback

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

**Epic-01-CoreMVP** (Батч 1, 40% завершено):
- ✅ Фаза 1: Database Integration (завершена)
- ✅ Фаза 2: Формы управления операциями (завершена)
- 🔄 Фаза 3: Кассовый календарь с остатками по дням (следующая)
- ⏳ Фаза 4: Простой дашборд (месяц/год)
- ⏳ Фаза 5: Одна накопительная цель с расчётом взносов

**Ближайшие задачи**:
1. Реализовать кассовый календарь с расчетом остатков
2. Добавить валидацию форм операций
3. Интегрировать Dashboard с реальными данными из БД

## Критичные детали

**Starting Balance Formula**:
```
остаток на дату = starting_balance + SUM(доходы) - SUM(расходы) до даты
```

**Monthly Contribution Formula** (Goal):
```python
monthly_contribution = (target_amount - current_amount) / months_remaining
# Guard clauses: target_date в прошлом → 0, цель достигнута → 0
```

**Pattern-Matching Callbacks** (Dash):
- При `ALL` callbacks проверять `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
- Использовать `prevent_initial_call=True` для модалов

## Полезные команды

```bash
# Запуск приложения
python run.py  # http://localhost:8050

# Тесты
pytest -v --cov

# Качество кода
black app/
flake8 app/

# База данных (автоинициализация при запуске)
# SQLite: data/finfocus.db
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
    └── routing.md        # Система роутинга
```

---

**Версия Memory Bank**: 1.0
**Дата создания**: 2026-01-17
**Последнее обновление**: 2026-01-17
**GitHub**: https://github.com/SkyTger/FinFocus
