# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the application
```bash
python run.py
```
Launches Dash application on http://localhost:8050. Port/debug mode configurable via `PORT` and `DEBUG` environment variables.

### Running tests
```bash
pytest                          # Run all tests
pytest tests/test_models.py     # Run specific test file
pytest -v                       # Verbose output
pytest --cov                    # With coverage report
```

### Code quality
```bash
black app/                      # Format code
flake8 app/                     # Lint code
```

**Flake8 priority**: F-category (errors) → E-category (PEP8) → W-category (warnings)

### Database operations
Database initialization happens automatically on app startup via `init_database()` in `app/models/database.py`.

SQLite database location: `data/finfocus.db` (created automatically)

## Architecture Overview

### Application Structure
**Multi-page Dash application** with modular component architecture:

- **`app/main.py`**: Dash app initialization, URL routing, page layout orchestration
- **`app/models/database.py`**: SQLAlchemy ORM models (User, Transaction, Goal, GoalContribution)
- **`app/components/`**: Reusable UI components (dashboard.py, sidebar.py)
- **`app/services/`**: Business logic and data processing (future)
- **`app/assets/`**: Static files (CSS, images)

### Data Model
Core domain entities with SQLAlchemy ORM:

- **User**: Basic user profile with relationships to transactions and goals
- **Transaction**: Financial operations (income/expense/transfer) with date-based tracking
  - Supports recurring transactions (`is_recurring`, `recurring_period`)
- **Goal**: Savings targets with progress tracking and priority system
  - Calculated properties: `progress_percentage`, `is_completed`
- **GoalContribution**: Individual contributions toward goals

### Routing System
URL-based page routing in `app/main.py`:
- `/` or `/dashboard` → Dashboard overview
- `/calendar` → Cash calendar (stub)
- `/goals` → Savings goals management (stub)
- `/transactions` → Transaction list (stub)

Routing handled by `display_page()` callback responding to URL pathname changes.

### UI Framework
**Dash + Bootstrap** stack:
- Dash Bootstrap Components (dbc) for layout/styling
- Plotly for interactive charts (cashflow bars, donut charts)
- Bootstrap icons for UI elements
- Custom CSS for brand theming (green/white palette)

## Development Workflow

### Batch Process (план → батч)
1. **Plan mode**: Read ROADMAP.md → propose 1-3 file batch → await approval
2. **Batch mode**: Edit approved files → show diffs → run quality checks → update ROADMAP.md + feature_progress.md
3. **Constraint**: Only edit files in current batch scope

### Project Context Files
- **@ROADMAP.md**: Single source of truth for tasks/priorities (read at session start)
- **@.reports/notes/feature_progress.md**: Active feature/batch summaries
- **docs/adr/*.md**: Architecture Decision Records for long-term decisions

### ROADMAP Management
Checkbox format:
- `[ ]` Todo → `[-]` In Progress (add date YYYY/MM/DD) → `[x]` Done (add date + commit link)

Sections: High Priority (next 3-5 tasks) | Backlog | Recently Completed

### Code Standards
- **Python 3.12** with type annotations required
- **Docstrings in Russian** for functions/classes
- **No global variables**, no secrets in code
- **Minimal changes**: preserve behavior, review diffs before writing

### Git Workflow
- Branches: `feature/...`, `bugfix/...`, `hotfix/...`
- Commits: `type: short_description` (e.g., `feat: add user resolver`)

## 📚 Что читать при старте

**Обязательно в начале КАЖДОЙ сессии:**
1. `@ROADMAP.md` - единый источник задач и приоритетов
2. `@.reports/notes/feature_progress.md` - последние 5 батчей (краткая история)

**При необходимости:**
3. `@.reports/epics/epic-XX/README.md` - цель текущего эпика
4. `@.reports/epics/epic-XX/decisions.md` - критичные решения (КРИТИЧНО блоки)

**Детали работы с субагентами:**
`@.reports/DELEGATION_GUIDE.md` - полное руководство по делегированию

## 🤖 Работа с субагентами

### Принцип гибридной памяти

**Глобальный контекст** (главный агент читает):
- `CLAUDE.md` - контракт проекта (этот файл)
- `ROADMAP.md` - план и прогресс
- `feature_progress.md` - история последних 5 батчей

**Локальный контекст** (субагенты видят ТОЛЬКО):
- `.protocol.md` - изолированная задача (10-30 строк)
- Удаляется после выполнения

### Workflow делегирования

```
Задача возникает
  ↓
Главный агент создает .protocol.md
  ↓
Технический субагент выполняет
  ↓
Главный агент обновляет глобальную документацию
  ↓
Удаляет .protocol.md
```

### Формат .protocol.md

```markdown
# Задача: [конкретная задача]

## Контекст
[2-3 предложения минимум для понимания]

## Критичные детали
- Терминология: [если есть]
- Формулы: [если есть]
- Ограничения: [если есть]

## Файлы
- `path/to/file.py:45-67` - описание
- `path/to/other.py` - описание
```

### Доступные субагенты

- `@code-search` - поиск в кодовой базе (БЕЗ написания кода)
- `@code-reviewer` - code review Python кода
- `@python-refactor` - рефакторинг и улучшение кода
- `@qa-engineer` - тестирование
- `@doc-manager` - обновление документации

**Детальное руководство**: `@.reports/DELEGATION_GUIDE.md`

---

## 📝 Правила документации

### Синхронизация при изменениях

**При SCOPE CHANGE** - СРАЗУ обновить ROADMAP.md:
```markdown
~~Старая задача (6 карточек)~~ → Новая (5 карточек) (см. D005)
```

**При изменении бизнес-логики** - обновить CLAUDE.md:
- Profit Calculation Logic - если изменились формулы
- Data Architecture - если изменилась терминология
- Code Patterns - если появился новый паттерн

**После каждого батча** - обновить feature_progress.md:
```markdown
## Батч N: Название (YYYY-MM-DD) ✅
[3 строки описания]
Файлы: file.py:123-456
```

### Rolling Window Pattern (feature_progress.md)

- Хранить только **последние 5 батчей**
- Старые батчи → `archive/YYYY-QX-epicNN-batches.md`
- Цель: быстрое чтение AI сессиями (~2-3 минуты)

### Принцип: ROADMAP.md = Single Source of Truth

- **ROADMAP.md** всегда актуален для планирования
- **decisions.md** - история решений и детальный контекст
- **При конфликте**: ROADMAP.md > decisions.md

**Детальные правила**: `@.reports/DELEGATION_GUIDE.md`

---

## 🎯 Процесс работы (план → батч)

### План-режим (БЕЗ правок кода)

1. Прочитать `ROADMAP.md` и `feature_progress.md`
2. Сформировать "План батча" (1-3 файла максимум)
3. Указать действия и ожидаемый эффект
4. Ждать подтверждения пользователя

### Батч-режим (ПОСЛЕ подтверждения)

1. Редактировать только согласованные файлы
2. Показать диффы
3. Выполнить скрипты качества (`scripts/run_lint.sh`, pytest)
4. По завершении - обновить `ROADMAP.md` и `feature_progress.md`

**Ограничения**:
- ❌ НЕ править файлы вне списка текущего батча
- ❌ Длинные списки/логи сохранять в `.reports/notes/*.md`, а не в чат
---

## 🚀 Быстрый старт для новой AI сессии

**3-5 минут чтения:**

1. ✅ Прочитать `ROADMAP.md` - актуальные задачи и приоритеты
2. ✅ Прочитать `feature_progress.md` - последние 5 батчей
3. ✅ Прочитать `epic-XX/README.md` - цель текущего эпика (если в работе)
4. ⏭️ По необходимости: `epic-XX/decisions.md` - критичные решения

**При изменении scope:**

1. Записать решение в `decisions.md` с блоком **КРИТИЧНО**
2. **СРАЗУ** обновить `ROADMAP.md` (не ждать завершения батча)
3. Обновить `feature_progress.md` после батча
4. Если изменились формулы → обновить `CLAUDE.md` (Profit Calculation Logic)

---

## 🔒 Безопасность

**НИКОГДА!** Не публиковать данные содержащие логины, пароли, ключи и токены никуда! Не отправлять в GIT либо любой другой сервер.

**Файлы в .gitignore**:
- `app/.env` - пароли ClickHouse
- `*.log` - логи
- `__pycache__/`, `.pytest_cache/` - временные файлы

---

## Стандарты разработки 
- Ветки: feature/..., bugfix/..., hotfix/...  
- Коммиты: «тип: краткое_описание» (например, feat: add user resolver)  
- Секреты не хранить в коде. Не использовать глобальные переменные.  

---

## 🔧 Дополнительные ресурсы

### Документация проекта

| Файл | Назначение |
|------|-----------|
| `ROADMAP.md` | План развития и прогресс по эпикам |
| `feature_progress.md` | Последние 5 батчей (краткая история) |
| `docs/adr/` | Architecture Decision Records |
| `.reports/epics/epic-XX/` | Детали эпиков (README, decisions, progress, technical) |
| `.reports/DELEGATION_GUIDE.md` | Полное руководство по работе с субагентами |
| `.reports/DOCUMENTATION_PROMPT.md` | Промпт для документации других проектов |
