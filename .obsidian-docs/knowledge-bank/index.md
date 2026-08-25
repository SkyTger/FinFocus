# FinFocus Memory Bank - Главное оглавление

## Суть проекта
**FinFocus** - веб-приложение для планирования личного и семейного бюджета с фокусом на кассовый календарь и целевые накопления.

**Уникальная ценность**: Кассовое планирование с прогнозом остатков по дням + автоматическое распределение бюджета между множественными накопительными целями с приоритетами.

**Статус**: Epic-06 (User Profile + Avatar, протокол 0024) и Epic-09 фазы 1-3
(delivery/setup, протоколы 0025-0027) завершены и смержены. Два способа
доставки сосуществуют — setup-скрипты `start.sh`/`start.bat` (протокол 0025)
и PyInstaller-сборка в CI (незапротоколированная работа, коммиты
`d9e93c6`/`3b6a8e0`); какой основной — открытый вопрос №1 ROADMAP, решение
не принято. Выпущен релиз `v0.9.0-beta.1`. 639 unit-тестов, все зелёные
(протокол 0028, на ревью).

**Epic-11 «щиток», кусок 1 из 3 — РЕАЛИЗОВАН, на ревью** (протокол 0028,
PR #28, мерж предстоит): дашборд переделан на модель «свободно/платежи/
резерв» — новый read-only сервис `MoneyLayersService` раскладывает
прогнозный остаток каждого дня на три слоя единой формулой; UI дашборда
заменён целиком — шапка «Свободно сегодня» + график полос вместо
прежнего ряда 4 KPI-карточек и графика доходы/расходы+баланс.
Куски 2 (карточки-двери) и 3 (полоска-меню вместо сайдбара) ещё не
начаты. Источник решений: `../discussions/_archive/dashboard-as-menu-2026-08-23/design.md`,
детали реализации: `modules/services.md` (MoneyLayersService),
`modules/ui-components.md` (Dashboard-щиток), `protocols.md` (0028).
Секвенирование: редизайн — до следующего бета-цикла (фаза 4 Epic-09,
сбор фидбека, откладывается до завершения всего эпика-11).
См. также `architecture.md` → «Планируемые изменения».

**Последнее обновление**: 2026-08-25 (протокол 0028 на ревью — Epic-11
кусок 1 реализован: MoneyLayersService, дашборд-щиток, 639 тестов)

## Быстрые ссылки на разделы

### Архитектура и технологии (КРИТИЧНО)
- [architecture.md] - Модульная архитектура Dash приложения, слои системы, паттерны
- [tech-stack.md] - Python 3.10-3.12 (поддерживаемый диапазон) + Dash 2.17.1 + SQLAlchemy 2.0.23, зависимости, версии

### Стандарты разработки (КРИТИЧНО)
- [code-style.md] - Python docstrings на русском, type annotations, batch workflow, git conventions

### Функциональность и протоколы
- [features.md] - Обзор реализованных функций (кассовый календарь, CRUD, цели, аналитика)
- [protocols.md] - История протоколов разработки (0002-0028) с деталями реализации; 0028 на ревью (Epic-11 кусок 1); включая packaging-врезку и открытый вопрос №1 (способ доставки)

### Модули системы (краткие описания)
- [modules/database.md] - SQLAlchemy ORM: User (+ avatar_id), Transaction, Goal, GoalContribution
- [modules/services.md] - TransactionService, GoalService, CalendarService, RecurringService, DashboardService, AllocationService, OnboardingService, MoneyLayersService (на ревью)
- [modules/ui-components.md] - Dashboard-щиток (шапка «Свободно сегодня» + график полос, протокол 0028), Sidebar (динамический профиль), ProfileModal (глобальный, 2 входа), Onboarding Wizard
- [modules/routing.md] - URL-based routing, display_page callback
- [modules/schema.md] - TypedDicts для типизации (app/schema/), UserProfile, OnboardingStatus, MoneyLayersData (на ревью)
- [modules/utils.md] - Утилиты форматирования и сериализации (app/utils/)

### Паттерны разработки (NEW, протокол 0022)
- [patterns/plotly-charts.md] - Plotly chart patterns: dual Y-axis, unified hover, markers, clickable bars, status colors
- [patterns/callbacks.md] - Dash callback patterns: helper functions, ADR-003 guards, stores, preselection, selective refresh

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

**Epic-04-Advanced Features** (Батч 4, ✅ 100% завершено):
- ✅ Quick-Add Chips для быстрого создания операций (PR #12, протокол 0012)
- ✅ Финансовая подушка безопасности (PR #13, протокол 0013)
- ✅ Онбординг новых пользователей (PR #14, протокол 0014)
- ✅ Tooltip для дней календаря (PR #15, протокол 0015)
- ✅ Интеграция бюджета целей с календарём (PR #16-18, протокол 0016-0018)
- ✅ Редактирование и удаление взносов в целях (PR #19, протокол 0019)
- ✅ Отложенные покупки (Wishlist) (PR #20, протокол 0020)

**Epic-05-UI** (Dashboard UI Redesign, ✅ ЗАВЕРШЕН):
- [x] ✅ Батч 5.1: Фундамент — цвета + формат ₽ + KPI-карточки (протокол 0021, 2026-02-06)
  - ✅ Новые CSS-переменные (#2ecc71 палитра) с deprecated aliases
  - ✅ Глобальный форматтер format_rub() (замена $X,XXX.XX → X XXX ₽)
  - ✅ Переделка 4 KPI-карточек (без градиентов, кнопка "Сверка")
  - ✅ Скрыты AI Assistant и Exchange (TODO для Epic-08)
  - ✅ Типографика по спецификации (9 новых классов)
  - ✅ 10 unit тестов formatters + 2 обновленных calendar
  - ✅ 492 теста pass (1 pre-existing failure в allocation precision)
- [x] ✅ Батч 5.2: Дневной график (ядро) (протокол 0022, 2026-02-06)
  - ✅ DashboardService.get_daily_cashflow() + get_yearly_cashflow() — дневные/годовые данные
  - ✅ CalendarService.get_recurring_income_expense_by_day() — публичный API
  - ✅ Plotly: grouped bars + линия баланса + diamond маркер минимума + today line + current month highlight
  - ✅ Hover tooltip (hovermode="x unified"), клик по bar → модал (только Month mode)
  - ✅ Переключатель Month/Year через Period Store Pattern
  - ✅ _load_dashboard_components() helper для устранения дублирования
  - ✅ 16 unit тестов (12 daily + 4 yearly), 508 тестов pass
  - ✅ Patterns documentation: plotly-charts.md, callbacks.md
- [x] ✅ Батч 5.3: Layout — операции + правая колонна + sidebar (протокол 0023, 2026-02-06)
  - ✅ format_date_human() форматтер — "5 февраля" для операций
  - ✅ DashboardService.get_upcoming_transactions() — операции после reference_date
  - ✅ Рефакторинг get_recent_transactions() — month range filter (1-го числа..reference_date)
  - ✅ Глобализация reconciliation modal — Calendar + Dashboard доступ
  - ✅ Dashboard layout 8/4 — split таблицы 50/50, cushion card, wishlist, empty states
  - ✅ Sidebar card — активный highlight callback, новый sidebar.css
  - ✅ Transactions URL query params — ?start=&end= для date filter
  - ✅ 28 unit тестов (3 formatters + 9 dashboard_service + 16 старых), 520 тестов pass

**Epic-06 (протокол 0024)**: User Profile + Avatar
- [x] ✅ Поле User.avatar_id (миграция 007)
- [x] ✅ app/config/avatars.py — 10 emoji аватаров, DEFAULT_AVATAR_ID, get_avatar_emoji()
- [x] ✅ app/components/profile_modal.py — глобальный модал редактирования профиля
- [x] ✅ app/core/bootstrap.py — выделен из main.py, idempotent миграции 001-007
- [x] ✅ app/core/migrations.py — 7 идемпотентных миграций
- [x] ✅ OnboardingService.update_profile(), get_profile() — профиль API
- [x] ✅ Sidebar — динамический блок профиля (Store-based)
- [x] ✅ Dashboard greeting — "Добрый день, {name}!"
- [x] ✅ Onboarding Wizard перестроен (name + avatar + balance шаги)
- [x] ✅ dcc.Store("profile-updated") — event bus реактивных обновлений

**Epic-09 (Delivery & Setup for Beta Testers)**, фазы 1-3 завершены:
- [x] ✅ Фаза 1-2 (протокол 0025): setup-скрипты start.sh/start.bat,
  разделение requirements.txt/requirements-dev.txt, BETA_README.md,
  docs/RELEASE_GUIDE.md
- [x] ✅ Packaging (незапротоколировано, коммиты d9e93c6/3b6a8e0):
  PyInstaller-бандл (`finfocus.spec`), сборка Windows/macOS в
  `.github/workflows/build.yml` по тегу `v*` — см. открытый вопрос №1
  ROADMAP (какой способ доставки основной, решение не принято)
- [x] ✅ Релиз v0.9.0-beta.1
- [x] ✅ Протокол 0026: онбординг — дашборд подписан на `profile-updated`,
  приветствие обновляется без перезагрузки страницы
- [x] ✅ Протокол 0027: quick wins аудита — fail-open подушки в
  рекомендациях покупок, `logger.opt(exception=True)` вместо пустого
  `exc_info`, удалён мёртвый код в AnalyticsService
- [ ] Фаза 4 (сбор фидбека беты) — **отложена** до завершения редизайна
  дашборда «щиток» (решение владельца 2026-08-23, см. «Статус» выше)

**Epic-11 «щиток» — редизайн дашборда, кусок 1 из 3 на ревью**:
- [x] 🔶 Кусок 1 (протокол 0028, на ревью, PR #28): модель
  «свободно/платежи/резерв» (`MoneyLayersService`) + шапка «Свободно
  сегодня» + график полос. Заменяет прежний ряд KPI-карточек и график
  доходы/расходы+баланс
- [ ] Кусок 2: карточки-двери (навигация по разделам, пустые состояния)
- [ ] Кусок 3: полоска-меню вместо сайдбара

Подробности в `architecture.md` → «Планируемые изменения»,
`modules/services.md` (MoneyLayersService), `modules/ui-components.md`
(Dashboard-щиток), `protocols.md` (0028) и в
`../discussions/_archive/dashboard-as-menu-2026-08-23/design.md`.

**Прочий бэклог** (не секвенирован):
1. Dark Theme — тёмная тема
2. Mobile Responsive (Epic-08) — адаптивность < 576px
3. Импорт операций из банков
4. Уведомления и напоминания

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
├── features.md           # Обзор функциональности
├── protocols.md          # История протоколов 0002-0027
├── testing.md            # Стратегия тестирования
├── deployment.md         # Запуск и деплоймент
├── modules/              # Модули системы (краткие)
│   ├── database.md       # ORM модели
│   ├── services.md       # Бизнес-логика
│   ├── ui-components.md  # UI компоненты
│   ├── routing.md        # Система роутинга
│   ├── schema.md         # TypedDicts
│   └── utils.md          # Утилиты
└── patterns/             # Паттерны разработки (NEW, протокол 0022)
    ├── plotly-charts.md  # Plotly chart patterns
    └── callbacks.md      # Dash callback patterns
```

---

**Версия Memory Bank**: 4.3
**Дата создания**: 2026-01-17
**Последнее обновление**: 2026-08-25 (протокол 0028 на ревью: Epic-11
«щиток» кусок 1 реализован — MoneyLayersService, дашборд-щиток,
639 тестов)
**GitHub**: https://github.com/SkyTger/FinFocus
