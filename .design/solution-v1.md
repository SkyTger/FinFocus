# Solution v1: Категоризация и Сверка — Расширение моделей и сервисов

## Обзор решения
Решение расширяет существующую архитектуру добавлением модели Category как справочника, nullable связи Transaction.category_id, нового типа ADJUSTMENT и двух новых сервисов (CategoryService, ReconciliationService). UI изменения минимальны — добавление dropdown категории в формы и модал сверки на календарь. Следует существующим паттернам: сервисы принимают Session, используют flush() вместо commit(), UI использует dcc.Store и Pattern-Matching callbacks.

## Архитектура

### Компоненты

**1. Category (Модель)**
Справочник категорий с системными (is_system=True) и пользовательскими. Системные категории ("Коррекция") нельзя удалить.

**2. CategoryService (Сервис)**
Простой сервис для получения списка категорий с фильтрацией и idempotent seed.

**3. ReconciliationService (Сервис)**
Сервис для создания ADJUSTMENT транзакций на основе разницы между расчетным и фактическим балансом.

**4. Изменения в CalendarService**
Добавление обработки TransactionType.ADJUSTMENT в calculate_daily_balances().

**5. Изменения в RecurringService**
Копирование category_id при генерации exceptions.

**6. UI компоненты**
- Dropdown категории в формах create/edit (transactions.py)
- Колонка категории в таблице транзакций
- Модал сверки на календаре (calendar.py)
- Фильтр "Без категории"

### Диаграмма взаимодействия

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  transactions.py          calendar.py                           │
│  ┌─────────────────┐      ┌─────────────────┐                  │
│  │ Create Modal    │      │ Reconciliation  │                  │
│  │ + category      │      │ Modal           │                  │
│  │ dropdown        │      │ - expected bal. │                  │
│  ├─────────────────┤      │ - actual input  │                  │
│  │ Edit Modal      │      │ - create adjust │                  │
│  │ + category      │      └────────┬────────┘                  │
│  │ dropdown        │               │                           │
│  ├─────────────────┤               │                           │
│  │ Table           │               │                           │
│  │ + category col  │               │                           │
│  │ + filter        │               │                           │
│  └────────┬────────┘               │                           │
└───────────┼────────────────────────┼───────────────────────────┘
            │                        │
            ▼                        ▼
┌───────────────────────────────────────────────────────────────┐
│                      Service Layer                            │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  TransactionService    CategoryService    ReconciliationService│
│  (modified:            (NEW)              (NEW)               │
│   +category_id)        ┌──────────────┐   ┌──────────────────┐│
│  ┌──────────────┐      │ get_all()    │   │ get_expected_bal │││
│  │ create()     │      │ get_by_id()  │   │ create_adjustment││ │
│  │ update()     │      │ seed_default │   └──────────────────┘│
│  └──────────────┘      └──────────────┘                       │
│                                                               │
│  CalendarService       RecurringService                       │
│  (modified:            (modified:                             │
│   +ADJUSTMENT)         +category_id copy)                     │
│  ┌──────────────┐      ┌───────────────┐                      │
│  │ calc_daily   │      │ create_except │                      │
│  │ _balances()  │      │ (copy cat_id) │                      │
│  └──────────────┘      └───────────────┘                      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│                       Model Layer                             │
├───────────────────────────────────────────────────────────────┤
│  User           Transaction         Category (NEW)            │
│  ┌─────────┐    ┌──────────────┐   ┌───────────────┐         │
│  │ id      │    │ id           │   │ id            │         │
│  │ ...     │    │ category_id ─┼───│ name          │         │
│  └─────────┘    │ (nullable FK)│   │ icon          │         │
│                 │ trans_type   │   │ type (income/ │         │
│                 │ (+ADJUSTMENT)│   │   expense/both)│         │
│                 └──────────────┘   │ is_system     │         │
│                                    │ sort_order    │         │
│                                    └───────────────┘         │
└───────────────────────────────────────────────────────────────┘
```

## Файловая структура

```
app/models/database.py       — добавить Category, TransactionType.ADJUSTMENT,
                               Transaction.category_id FK

app/services/category_service.py        — НОВЫЙ: CategoryService
app/services/reconciliation_service.py  — НОВЫЙ: ReconciliationService
app/services/calendar_service.py        — изменить: обработка ADJUSTMENT
app/services/recurring_service.py       — изменить: копирование category_id
app/services/__init__.py                — экспорт новых сервисов

app/components/transactions.py — изменить: dropdown категории, колонка, фильтр
app/components/calendar.py     — изменить: кнопка и модал сверки

tests/test_category_service.py           — НОВЫЙ: 5+ тестов
tests/test_reconciliation_service.py     — НОВЫЙ: 5+ тестов
tests/test_calendar_service.py           — добавить: 3+ теста ADJUSTMENT
tests/test_recurring_service.py          — добавить: 2+ теста category inheritance

scripts/seed_categories.py              — НОВЫЙ (опционально, можно в init_database)
```

## Ключевые интерфейсы

```python
# === app/models/database.py ===

class TransactionType(PyEnum):
    """Типы финансовых операций."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"  # НОВЫЙ


class Category(Base):
    """Модель категории операций.

    Attributes:
        name: Название категории ("Еда", "Транспорт")
        icon: Bootstrap icon class ("bi-cart", "bi-car-front")
        type: Применимость ("income" | "expense" | "both")
        is_system: Системная категория (нельзя удалить)
        sort_order: Порядок отображения в dropdown
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(30), default="bi-tag")
    type = Column(String(10), nullable=False)  # "income" | "expense" | "both"
    is_system = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    # ... существующие поля ...

    # НОВОЕ: категория (nullable)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category", back_populates="transactions")


# === app/services/category_service.py ===

DEFAULT_CATEGORIES: list[dict] = [
    # Расходы
    {"name": "Еда и продукты", "icon": "bi-cart", "type": "expense", "sort_order": 1},
    {"name": "Транспорт", "icon": "bi-car-front", "type": "expense", "sort_order": 2},
    {"name": "Жилье и ЖКХ", "icon": "bi-house", "type": "expense", "sort_order": 3},
    {"name": "Связь и интернет", "icon": "bi-phone", "type": "expense", "sort_order": 4},
    {"name": "Здоровье", "icon": "bi-heart-pulse", "type": "expense", "sort_order": 5},
    {"name": "Одежда", "icon": "bi-bag", "type": "expense", "sort_order": 6},
    {"name": "Развлечения", "icon": "bi-controller", "type": "expense", "sort_order": 7},
    {"name": "Образование", "icon": "bi-book", "type": "expense", "sort_order": 8},
    {"name": "Подарки", "icon": "bi-gift", "type": "expense", "sort_order": 9},
    {"name": "Прочие расходы", "icon": "bi-three-dots", "type": "expense", "sort_order": 10},
    # Доходы
    {"name": "Зарплата", "icon": "bi-briefcase", "type": "income", "sort_order": 1},
    {"name": "Подработка", "icon": "bi-laptop", "type": "income", "sort_order": 2},
    {"name": "Инвестиции", "icon": "bi-graph-up", "type": "income", "sort_order": 3},
    {"name": "Подарки", "icon": "bi-gift", "type": "income", "sort_order": 4},
    {"name": "Прочие доходы", "icon": "bi-three-dots", "type": "income", "sort_order": 5},
    # Системные
    {"name": "Коррекция", "icon": "bi-arrow-repeat", "type": "both", "is_system": True, "sort_order": 0},
]


class CategoryService:
    """Сервис для работы с категориями операций."""

    def __init__(self, session: Session):
        """Инициализирует сервис категорий.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def get_all(self, type_filter: str | None = None) -> list[Category]:
        """Получает все категории с опциональной фильтрацией по типу.

        Args:
            type_filter: "income" | "expense" | None (все)

        Returns:
            list[Category]: Отсортированный список категорий
        """
        ...

    def get_by_id(self, category_id: int) -> Category | None:
        """Получает категорию по ID.

        Args:
            category_id: ID категории

        Returns:
            Category | None: Категория или None
        """
        ...

    def get_system_correction_category(self) -> Category | None:
        """Получает системную категорию 'Коррекция'.

        Returns:
            Category | None: Категория или None если не найдена
        """
        ...

    def seed_default_categories(self) -> int:
        """Создает предзаполненные категории (idempotent).

        Проверяет существование по name+type, создает только отсутствующие.

        Returns:
            int: Количество созданных категорий
        """
        ...


# === app/services/reconciliation_service.py ===

class ReconciliationService:
    """Сервис для сверки расчетного баланса с фактическим."""

    def __init__(self, session: Session):
        """Инициализирует сервис сверки.

        Args:
            session: SQLAlchemy сессия для работы с БД
        """
        self.session = session

    def get_expected_balance(self, user_id: int, target_date: date) -> Decimal:
        """Получает расчетный баланс на дату.

        Args:
            user_id: ID пользователя
            target_date: Дата для расчета баланса

        Returns:
            Decimal: Расчетный баланс
        """
        ...

    def create_adjustment(
        self,
        user_id: int,
        target_date: date,
        actual_balance: Decimal,
        expected_balance: Decimal,
        category_id: int | None = None,
        description: str | None = None,
    ) -> Transaction:
        """Создает корректирующую ADJUSTMENT транзакцию.

        Формула: adjustment_amount = actual_balance - expected_balance
        Если positive — добавляем "недостающие" деньги
        Если negative — убираем "лишние" деньги

        Args:
            user_id: ID пользователя
            target_date: Дата корректировки
            actual_balance: Фактический остаток
            expected_balance: Расчетный остаток
            category_id: ID категории (по умолчанию "Коррекция")
            description: Описание (опционально)

        Returns:
            Transaction: Созданная ADJUSTMENT транзакция

        Raises:
            ValidationError: Если actual == expected (разница = 0)
        """
        ...


# === Изменения в app/services/calendar_service.py ===

def _calculate_balance_before_date(self, user_id: int, before_date: date) -> Decimal:
    """Рассчитывает сумму всех изменений баланса до указанной даты.

    ИЗМЕНЕНИЕ: Добавлена обработка ADJUSTMENT.
    ADJUSTMENT добавляется к балансу напрямую (amount может быть отрицательным).
    """
    result = (
        self.session.query(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
                        (Transaction.transaction_type == TransactionType.EXPENSE, -Transaction.amount),
                        (Transaction.transaction_type == TransactionType.ADJUSTMENT, Transaction.amount),  # НОВОЕ
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            )
        )
        .filter(...)
        .scalar()
    )
    ...


# === Изменения в app/services/recurring_service.py ===

def create_exception(
    self,
    template_id: int,
    original_date: date,
    new_amount: Decimal | None = None,
    new_date: date | None = None,
    new_description: str | None = None,
) -> Transaction:
    """Создает exception для конкретного экземпляра recurring операции.

    ИЗМЕНЕНИЕ: Копирует category_id из шаблона.
    """
    ...
    exception = Transaction(
        user_id=template.user_id,
        amount=new_amount if new_amount is not None else template.amount,
        transaction_type=template.transaction_type,
        transaction_date=new_date if new_date is not None else original_date,
        description=...,
        category_id=template.category_id,  # НОВОЕ: копируем из шаблона
        is_recurring=False,
        recurring_parent_id=template_id,
        original_date=original_date,
        is_skipped=False,
    )
    ...
```

## Модель данных

### TypedDicts для UI

```python
# app/schema/reconciliation.py (опционально, можно в reconciliation_service.py)

class ReconciliationPreview(TypedDict):
    """Предпросмотр сверки для UI."""
    expected_balance: str  # Decimal as string
    actual_balance: str  # Decimal as string
    difference: str  # Decimal as string (может быть отрицательным)
    is_positive: bool  # True если difference > 0
    target_date: str  # ISO format


class CategoryOption(TypedDict):
    """Опция категории для dropdown."""
    label: str  # "Еда и продукты"
    value: int  # category_id
    icon: str  # "bi-cart"
```

### Предзаполненные категории

| Name | Icon | Type | is_system | sort_order |
|------|------|------|-----------|------------|
| Коррекция | bi-arrow-repeat | both | True | 0 |
| Еда и продукты | bi-cart | expense | False | 1 |
| Транспорт | bi-car-front | expense | False | 2 |
| ... | ... | ... | ... | ... |
| Зарплата | bi-briefcase | income | False | 1 |
| Подработка | bi-laptop | income | False | 2 |
| ... | ... | ... | ... | ... |

## Обработка ошибок

### Стратегия
Используется существующий паттерн ValidationError из app/core/exceptions.py.

```python
# ReconciliationService
if actual_balance == expected_balance:
    raise ValidationError("Фактический баланс совпадает с расчетным — корректировка не нужна")

# CategoryService.seed_default_categories()
# Не бросает исключений — idempotent, логирует количество созданных
```

### UI обработка
- Модал сверки: если difference == 0, кнопка "Создать корректировку" disabled
- Формы транзакций: category_id = None (без категории) — валидное состояние

## План реализации

### Шаг 1: Модель данных (1-2 часа)
1.1. Добавить TransactionType.ADJUSTMENT в app/models/database.py
1.2. Создать модель Category с полями name, icon, type, is_system, sort_order
1.3. Добавить Transaction.category_id FK (nullable) и relationship
1.4. Пересоздать БД (drop + create) или написать миграцию

### Шаг 2: CategoryService (1 час)
2.1. Создать app/services/category_service.py
2.2. Реализовать get_all(), get_by_id(), get_system_correction_category()
2.3. Реализовать seed_default_categories() (idempotent)
2.4. Написать unit тесты (5+)

### Шаг 3: ReconciliationService (1-2 часа)
3.1. Создать app/services/reconciliation_service.py
3.2. Реализовать get_expected_balance() (использует CalendarService)
3.3. Реализовать create_adjustment()
3.4. Написать unit тесты (5+)

### Шаг 4: Изменения в CalendarService (1 час)
4.1. Добавить обработку ADJUSTMENT в _calculate_balance_before_date()
4.2. Добавить обработку ADJUSTMENT в _get_daily_changes()
4.3. Обновить get_month_summary() и get_year_summary()
4.4. Написать unit тесты (3+)

### Шаг 5: Изменения в RecurringService (30 мин)
5.1. Добавить копирование category_id в create_exception()
5.2. Добавить копирование в skip_instance() (если применимо)
5.3. Написать unit тесты (2+)

### Шаг 6: UI — Формы транзакций (2-3 часа)
6.1. Добавить dropdown категории в create modal (после поля "Тип")
6.2. Добавить callback для фильтрации категорий по типу операции
6.3. Добавить dropdown категории в edit modal
6.4. Обновить create_transaction() и update_transaction() callbacks
6.5. Добавить колонку "Категория" в таблицу
6.6. Добавить фильтр "Без категории"

### Шаг 7: UI — Модал сверки (2-3 часа)
7.1. Добавить кнопку "Сверка" рядом с балансом на сегодня в календаре
7.2. Создать модал reconciliation-modal с полями
7.3. Реализовать callback загрузки expected_balance
7.4. Реализовать callback расчета difference при вводе actual
7.5. Реализовать callback создания ADJUSTMENT
7.6. Обновить календарь после создания корректировки

### Шаг 8: Экспорт и документация (30 мин)
8.1. Обновить app/services/__init__.py
8.2. Вызвать seed_default_categories() в init_database() или run.py
8.3. Обновить ROADMAP.md и feature_progress.md

## Зависимости
Новые библиотеки не требуются. Все зависимости уже в проекте:
- SQLAlchemy (модели, FK)
- Dash / Dash Bootstrap Components (UI)
- pytest (тесты)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Сложность фильтрации категорий по типу операции в UI | Средняя | Использовать callback с Output на options dropdown; загружать категории один раз в dcc.Store |
| ADJUSTMENT с отрицательным amount может запутать пользователя | Средняя | UI показывает "Разница: -800 ₽" явно; корректировка сразу отображается в календаре |
| seed_default_categories() при каждом запуске замедляет старт | Низкая | Idempotent проверка по name+type выполняется быстро; кэширование не требуется |
| Конфликт recurring + category при сложных сценариях | Низкая | category_id копируется только при создании exception; виртуальные экземпляры наследуют из шаблона напрямую |
