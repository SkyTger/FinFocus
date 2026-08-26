---
name: architecture
description: Архитектура FinFocus — слои Dash-приложения, сервисы, ORM, редизайн дашборда «щиток» (куски 1-2 и долги куска 1 смержены, кусок 3 не начат)
type: reference
originSessionId: -
---

# Архитектура FinFocus

## Тип архитектуры
**Модульное Dash приложение** с трехслойной архитектурой:
- Frontend (Dash Components) → Business Logic (Services) → Data Access (SQLAlchemy ORM) → Database (SQLite/PostgreSQL)

**Характеристики**:
- Single-page application с URL-based routing
- Server-side rendering через Dash callbacks
- Реактивные компоненты с автообновлением

## Слои приложения

### 1. Presentation Layer (UI)
**Компоненты**: `app/components/`
- **dashboard.py** - главная страница-щиток: шапка «Свободно сегодня»
  + график полос + ряд карточек-дверей (протокол 0030)
- **panel_cards.py** - чистые build-функции пяти карточек-дверей щитка
  (протокол 0030), данные из `DashboardPanelService`
- **sidebar.py** - навигация; чистая функция без БД и колбэков,
  рендерится слотом в `main.py` (протокол 0030, снята с дашборда)
- **transactions.py** - управление операциями (CRUD формы)

**Паттерн**: Stateless functional components, генерирующие Dash layouts

### 2. Application Layer (Business Logic)
**Сервисы**: `app/services/`
- **TransactionService** - CRUD операций, валидация
- **GoalService** - управление целями, расчет взносов, contributions, приоритеты, бюджет
- **CalendarService** - расчет остатков по дням, агрегация за месяц/год
- **RecurringService** - генерация виртуальных экземпляров, управление exceptions
- **DashboardService** - агрегация метрик, cashflow данные (composition)
- **AllocationService** - жадный алгоритм распределения бюджета между целями
- **RedistributionService** - перераспределение бюджета при достижении цели (Temporary Status Pattern)
- **CategoryService** - справочник категорий, seed, get_frequent_for_type
- **ReconciliationService** - сверка баланса, создание ADJUSTMENT транзакций
- **AnalyticsService** - агрегация расходов по категориям, monthly trends, donut/bar charts

- **BudgetReservationService** - управление резервированием бюджета накоплений, два режима (fixed_date/from_balance), adjust_reserve_for_contribution() для досрочных взносов
- **CushionService** - финансовая подушка безопасности, калькулятор сценариев
- **OnboardingService** - onboarding wizard + profile management (complete, update_profile, get_profile)
- **MoneyLayersService** - read-only композиция над Calendar/BudgetReservation/Cushion/Goal, раскладывает прогнозный остаток по дням на три слоя (Свободно/Платежи/Резерв) для щитка (протокол 0028)
- **DashboardPanelService** - read-only композитор карточек-дверей щитка, один сбор `PanelData` за одну сессию БД, поблочная деградация (протокол 0030)

**Паттерн**: Service Layer с изолированной бизнес-логикой, session management через flush()

### 3. Data Access Layer (ORM)
**Модели**: `app/models/database.py`
- **User** - пользователи, starting_balance, monthly_savings_budget, savings_mode
- **Transaction** - операции (income/expense/transfer), recurring поля
- **Goal** - накопительные цели, priority
- **GoalContribution** - взносы в цели

**Паттерн**: Active Record через SQLAlchemy, calculated properties (@property)

### 6. Schema Layer (NEW)
**Модуль**: `app/schema/`
- **goals.py** - TypedDicts для накопительных целей
  - AllocationResult, AllocationSummary
  - GoalDisplayData, GoalsSummary

**Паттерн**: Централизованная типизация для переиспользования между services и UI

### 7. Utils Layer (NEW)
**Модуль**: `app/utils/`
- **formatters.py** - функции форматирования для UI
  - format_amount(), format_date(), format_days_remaining()
  - parse_date_safe()

**Паттерн**: DRY для общих утилит отображения

### 4. Database Layer
**SQLite** (development) / **PostgreSQL** (production)
- Автоинициализация через `init_database()` в `app/core/bootstrap.py` (Протокол 0024)
- Idempotent миграции 001-007 в `app/core/migrations.py` (без Alembic)

### 5. Core Infrastructure Layer (NEW)
**Модуль**: `app/core/`
- **database.py** - централизованный session management
  - `get_engine()` - singleton engine factory
  - `get_db_session()` - context manager для сессий
  - `init_database()` - инициализация БД
- **bootstrap.py** - инициализация БД (init_database, create tables, run migrations, seed categories)
- **migrations.py** - idempotent миграции 001-007 (column additions, table creation)
- **logging.py** - настройка loguru
  - `setup_logging()` - конфигурация логгера
  - Ротация файлов по дням
  - Цветной вывод в консоль + файл
- **exceptions.py** - единые исключения
  - `ValidationError` - для бизнес-правил

**Паттерн**: Infrastructure Layer с singleton factories и context managers

### 8. Config Layer (NEW, Протокол 0024)
**Модуль**: `app/config/`
- **avatars.py** - справочник emoji-аватаров пользователя
  - `AVATARS` - dict[str, dict] (id → emoji + label), 10 записей
  - `DEFAULT_AVATAR_ID` - "emoji-default"
  - `get_avatar_emoji(avatar_id)` - lookup с fallback

**Паттерн**: Статические справочники конфигурации, используются
`OnboardingService` (валидация avatar_id) и `modules/schema.md`/`database.md`

## Ключевые паттерны

### Dash Callbacks Pattern
```python
@callback(
    Output("component-id", "property"),
    Input("trigger-id", "property"),
    prevent_initial_call=True  # Для модалов
)
def handler(input_value):
    # Guard clauses
    if not input_value:
        raise PreventUpdate

    # Business logic
    # ...

    return result
```

**Критично**: Pattern-Matching Callbacks с `ALL`:
- Проверять `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
- Использовать `ctx.triggered_id["index"]` напрямую, избегать поиска в списках
- **Virtual recurring ops**: при редактировании виртуального экземпляра создавать exception через RecurringService.create_exception() ПЕРЕД загрузкой в edit modal (предотвращает NULL primary key error)

### Service Layer Pattern
```python
class TransactionService:
    def create_transaction(self, session, user_id, data):
        """Создание операции с валидацией."""
        # 1. Валидация
        if not data.get('amount') or data['amount'] <= 0:
            raise ValidationError("Amount must be positive")

        # 2. Создание объекта
        transaction = Transaction(**data)
        session.add(transaction)

        # 3. Flush (не commit!)
        session.flush()  # Caller управляет commit

        return transaction
```

**Принцип**: Сервисы используют `flush()`, caller делает `commit()` для атомарности операций

### Calculated Properties Pattern
```python
class Goal(Base):
    @property
    def monthly_contribution(self) -> Decimal:
        """Guard clauses для edge cases."""
        # Guard: deadline в прошлом
        if self.target_date <= date.today():
            return Decimal('0')

        # Guard: цель достигнута
        if self.current_amount >= self.target_amount:
            return Decimal('0')

        # Расчет
        days_remaining = (self.target_date - date.today()).days
        months_remaining = max(days_remaining / 30, 1)
        return (self.target_amount - self.current_amount) / Decimal(months_remaining)
```

**Принцип**: Guard clauses в начале для предотвращения ошибок (division by zero, negative values)

## Коммуникация между компонентами

### UI → Service → ORM → Database
```
Transactions Component (UI)
    ↓ callback(create_transaction)
TransactionService.create_transaction(session, data)
    ↓ session.add(Transaction)
SQLAlchemy ORM
    ↓ INSERT INTO transactions
SQLite Database
```

### Routing Flow
```
User navigates to /transactions
    ↓
app.layout → dcc.Location(id="url")
    ↓
display_page(pathname="/transactions") callback
    ↓
create_transactions_layout()
    ↓
Render Transactions component with callbacks
```

### Form Submission Flow (Pattern-Matching)
```
User clicks "Create" button
    ↓
toggle_create_modal() - opens modal
    ↓
User fills form → clicks "Submit"
    ↓
create_transaction() callback
    ↓
TransactionService.create_transaction()
    ↓
refresh_transactions_table() - updates table
```

## Важные принципы

### 1. Separation of Concerns
- UI компоненты НЕ содержат бизнес-логику
- Сервисы НЕ знают о Dash callbacks
- ORM модели содержат ТОЛЬКО данные и calculated properties

### 2. Session Management
- Caller создает session и управляет commit
- Сервисы используют flush() для валидации без commit
- Exception в сервисе → caller делает rollback

### 3. Validation Strategy
- Frontend: Dash Input validation (type, required)
- Backend: Service layer validation с ValidationError
- Database: SQLAlchemy constraints (nullable, unique)

### 4. Error Handling
- ValidationError → понятное сообщение на русском
- Database errors → rollback + user-friendly message
- Callbacks → PreventUpdate для пропуска обработки
- Error Alert UI → transaction-error-alert для пользовательских уведомлений

## Критичные архитектурные решения

**ADR-001**: Dash вместо Flask + React
- Быстрая разработка, встроенная реактивность
- Trade-off: ограниченная кастомизация

**ADR-002**: SQLite для MVP
- Простота, zero-configuration
- Migration path к PostgreSQL через DATABASE_URL

**ADR-003**: Pattern-Matching Callbacks
- Проблема: автовызовы при DOM updates
- Решение: проверка `ctx.triggered[0].get('value') is None`

**D008**: Guard clauses в calculated properties
- Предотвращение division by zero
- Явная обработка edge cases

**~~D009~~**: ~~Одна активная цель в MVP~~ (УДАЛЕНО в протоколе 0006)

**D010**: Session management через flush()
- Атомарность операций
- Гибкость для caller (commit/rollback)

**Протокол 0006**: Множественные цели с приоритетами
- AllocationService с жадным алгоритмом
- TypedDicts в app/schema/ для DRY

**Протокол 0007**: Режимы накоплений (free/medium/strict)
- Множители к monthly_contribution
- User.savings_mode поле

**Протокол 0008**: Перераспределение средств при достижении цели
- RedistributionService с Temporary Status Pattern
- RedistributionPreview TypedDict
- Redistribution Modal UI с confirm/decline callbacks
- NFR: preview < 100ms, аудит-логирование

**Протокол 0016**: Интеграция бюджета накоплений с календарём
- BudgetReservationService с двумя режимами резервирования
- TransactionType: SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
- GoalContribution.transaction_id FK для связи с календарём
- Динамический бюджет: remaining = total - SUM(contributions_this_month)

**Протокол 0017**: Улучшения UX бюджета накоплений
- adjust_reserve_for_contribution() — создание Exception для recurring при досрочных взносах
- Объединение UI: карточка прогресса удалена, данные в "Сводке по целям"
- RESERVE_DESCRIPTION: "Резерв на цели" → "Резервирование бюджета"
- Exception description "(внесено досрочно)" когда взносы покрыли бюджет

**Протокол 0018**: Исправление багов режима fixed_date
- Переиспользование шаблона при переключении режимов (set_mode logic)
- recalculate_current_month_exception() для пересчёта exceptions при изменениях
- GoalService.delete_contribution() с lazy import для избежания circular dependency
- _cleanup_orphan_exceptions() с логированием удалённых exceptions
- Логика: тот же день → реактивировать шаблон, разные дни → stop + cleanup + create new

## Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────┐
│              app/main.py (Entry)                        │
│  - Dash app initialization                              │
│  - URL routing (display_page callback)                  │
└───────────────────┬─────────────────────────────────────┘
                    │
      ┌─────────────┼─────────────┬─────────────┬─────────────┐
      ▼             ▼             ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────┐ ┌─────────┐
│dashboard │ │calendar  │ │transactions  │ │ goals   │ │sidebar  │
│- Header  │ │- Grid    │ │  - CRUD      │ │- Cards  │ │- Nav    │
│- Chart   │ │- Stats   │ │  - Modals    │ │- Budget │ │(slot,   │
│- Cards   │ │          │ │              │ │         │ │0 калбэков)│
└─────┬────┘ └─────┬────┘ └──────┬───────┘ └────┬────┘ └─────────┘
      │            │              │               │
      └────────────┴──────────────┴───────────────┘
                    │
                    ▼
         ┌──────────────────────────────┐
         │      app/services/           │
         │  - TransactionService        │
         │  - GoalService               │
         │  - CalendarService           │
         │  - RecurringService          │
         │  - DashboardService          │
         │  - AllocationService         │
         │  - RedistributionService     │
         │  - CategoryService           │
         │  - ReconciliationService     │
         │  - AnalyticsService          │
         │  - CushionService            │
         │  - OnboardingService         │
         │  - BudgetReservationService  │
         └──────────────┬───────────────┘
                        │
           ┌────────────┼────────────┬─────────────┐
           ▼            ▼            ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐
    │app/core/ │ │app/models│ │app/schema│  │app/utils │
    │-database │ │-ORM      │ │-TypedDicts│  │-formatters│
    │-exceptions││          │ │          │  │          │
    │-logging  │ │          │ │          │  │          │
    └────┬─────┘ └─────┬────┘ └──────────┘  └──────────┘
         │             │
         └──────┬──────┘
                ▼
    ┌───────────────────────┐
    │  SQLite Database      │
    │  data/finfocus.db     │
    │  + миграции scripts/  │
    └───────────────────────┘
```

## Планируемые изменения (Roadmap)

**~~Фаза 3~~ Кассовый календарь**: ✅ ЗАВЕРШЕНА (PR #2)

**~~Фаза 4~~ Dashboard integration**: ✅ ЗАВЕРШЕНА (PR #3)

**~~Фаза 5~~ Goals UI**: ✅ ЗАВЕРШЕНА (PR #4)

**~~Батч 2~~ Enhanced Planning**: ✅ ЗАВЕРШЕН (75% → 100%)
- ✅ Повторяющиеся операции (PR #5)
- ✅ Множественные цели с приоритетами (PR #6)
- ✅ Три режима накоплений (PR #7)
- ✅ Перераспределение средств между целями (PR #8)

**~~Батч 3~~ Analytics & UX**: ✅ ЗАВЕРШЕН (100%)
- ✅ Категоризация операций (PR #9)
  - Category модель, TransactionType.ADJUSTMENT
  - CategoryService, ReconciliationService
  - Сверка баланса через модал
- ✅ UX улучшения + Аналитика (PR #10)
  - AnalyticsService (donut/bar charts)
  - Страница /analytics с графиками
- ✅ Восстановление UI компонентов (протокол 0011, PR #11)
  - Chips UI для быстрой категоризации (восстановлен после merge)
  - Bulk actions (multi-select, max 100 транзакций)
  - CSV экспорт с UTF-8 BOM для Excel
  - 13 новых тестов для _pluralize_operations
  - Pattern-Matching callbacks с 3-уровневыми guard clauses (ADR-003)

**~~Батч 4~~ Advanced Features**: ✅ ЗАВЕРШЁН (100%, протоколы 0012-0020)
- ✅ Quick-Add Chips, финансовая подушка безопасности (CushionService),
  онбординг (OnboardingService), tooltip календаря, интеграция бюджета
  целей с календарём (BudgetReservationService), edit/delete взносов,
  отложенные покупки (Wishlist)
- Импорт операций из банков, уведомления и напоминания — остались
  в Backlog, не начаты

**~~Epic-05-UI~~ Dashboard UI Redesign**: ✅ ЗАВЕРШЁН (протоколы 0021-0023)
- ✅ Цветовая палитра, форматтер ₽, KPI-карточки без градиентов
- ✅ Дневной/годовой график cashflow (bar + линия баланса, Plotly)
- ✅ Layout 8/4 (график+таблицы / wishlist+подушка), sidebar с профилем
- Этот график и layout **заменяются полностью** в редизайне «щиток»
  (см. ниже) — не развивать дальше в текущем виде

**~~Epic-06~~ User Profile + Avatar**: ✅ ЗАВЕРШЁН (протокол 0024)
- ✅ User.avatar_id, `app/config/avatars.py`, profile_modal, bootstrap/
  migrations вынесены в `app/core/`, Store-based event bus (`profile-updated`)

**Epic-09 (Delivery & Setup for Beta Testers), фазы 1-3**: ✅ ЗАВЕРШЕНЫ
- ✅ Фаза 1-2 (протокол 0025): setup-скрипты start.sh/start.bat
- ✅ Packaging (незапротоколировано): PyInstaller-бандл в CI — второй,
  параллельный способ доставки; какой основной — открытый вопрос №1
  ROADMAP, решение не принято (см. `protocols.md`, `deployment.md`)
- ✅ Релиз v0.9.0-beta.1
- ✅ Протокол 0026: реактивное обновление приветствия на дашборде
  (подписка на `profile-updated`)
- ✅ Протокол 0027: quick wins аудита (fail-open подушки в
  рекомендациях покупок, логирование трейсбеков)
- ⏸️ Фаза 4 (сбор фидбека беты) — **отложена** до завершения редизайна
  дашборда «щиток» ниже (решение владельца, 2026-08-23)

**Редизайн дашборда «щиток» (Epic-11)** — 3 куска, куски 1-2 и долги
куска 1 СМЕРЖЕНЫ (протокол 0028 PR #28, протокол 0029 PR #29,
протокол 0030 PR #30 — 2026-08-26, `33c8a11`):
- Источник решений: `../discussions/_archive/dashboard-as-menu-2026-08-23/design.md`

**~~Кусок 1~~ Модель данных + шапка + график полос**: ✅ СМЕРЖЕНО
- ✅ Новая модель «свободно/платежи/резерв» по дням —
  `MoneyLayersService` (`app/services/money_layers_service.py`),
  read-only композиция над CalendarService/BudgetReservationService/
  CushionService/GoalService, единая формула от даты D без ветвления
  по режиму резервирования (см. `modules/services.md`)
- ✅ Текущий график cashflow (Батч 5.2, bar+линия) **заменён**
  графиком полос Свободно/Платежи/Резерв целей и подушки, с вехами
  целей на оси времени (см. `modules/ui-components.md`,
  `patterns/plotly-charts.md`)
- ✅ Шапка «Свободно сегодня: N ₽» + разбор баланс/платежи/резерв.
  **Без цветового вердикта/светофора** — снят решением владельца
  (любой порог просадки произволен, проблемные дни видны на самом
  графике); в этом редизайн отличается от первоначального замысла
  «шапка-вердикт» из design.md
- Контракт `app/schema/money_layers.py` спроектирован ПОД КУСОК 1;
  стабильность до куска 2 не гарантировалась — кусок 2 (протокол 0030)
  контракт `MoneyLayersData` НЕ тронул (решение владельца про «вчера»)
- ✅ Известное ограничение (перенесённый savings-exception завышал
  «Свободно») **снято протоколом 0029** — багфикс `CalendarService`

**~~Кусок 2~~ Карточки-двери**: ✅ СМЕРЖЕНО (протокол 0030, 2026-08-26)
- ✅ Пять карточек-дверей (`app/components/panel_cards.py`) под
  графиком — единственная точка входа в разделы на главном экране,
  заменяют прежнюю раскладку 8/4 (split-таблицы «Недавние»/
  «Предстоящие», readonly-подушка, wishlist-виджет — все удалены)
- ✅ `DashboardPanelService` — read-only композитор, один сбор
  `PanelData` за одну сессию БД (было 3 сессии на пути прежнего
  layout), пять блоков (calendar/goals/operations/analytics/wishlist)
  с поблочной деградацией
- ✅ Переходы с сохранением контекста: клик по «завтра» → `/calendar
  ?focus_date=`, клик по цели → `/goals?goal=`, клик по хотелке →
  `/calendar?wishlist_item=`; явный контракт владения `url.search`
  по pathname (`_OWNED_SEARCH_PATHS`)
- ✅ Sidebar снят с дашборда, переведён на ноль колбэков (Подход B —
  чистая функция `create_sidebar` + один колбэк-слот `render_sidebar_slot`
  в `main.py`); механики-сироты (сверка, онбординг-тост) — не тронуты
  (вне scope куска 2)
- Окошко «вчера» в карточке «Календарь» убрано решением владельца
  2026-08-26 — карточка показывает сегодня/завтра (отступление от
  FR-1.a спеки), `MoneyLayersService` кусок 2 не затрагивает
- Дефект AC-8 (двухуровневая дверь Wishlist — клик по хотелке всплывал
  в контейнер и открывал модал поверх календаря), найденный
  fidelity-гейтом ревью, исправлен слоем-подложкой до мержа

**Кусок 3** (не начат): текущий Sidebar (`app/components/sidebar.py`)
заменяется компактной полоской иконок на остальных экранах —
затрагивает каркас навигации всех страниц, не только дашборд

- Секвенирование: весь эпик — до следующего бета-цикла (см. Epic-09
  фаза 4 выше), не только кусок 1

---

Референсы:
- Детали Pattern-Matching Callbacks: `docs/adr/ADR-003-pattern-matching-callbacks-issue.md`
- История архитектурных решений: `.reports/epics/epic-01-coreMVP/decisions.md`, `.reports/epics/epic-02-enhancedPlanning/decisions.md`
