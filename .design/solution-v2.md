# Solution v2: Категоризация и Сверка — Расширенное решение с миграцией и детализацией UI

## Обзор решения
Решение расширяет существующую архитектуру добавлением модели Category как справочника, ЗАМЕНОЙ строкового поля `category` на `category_id` (FK), нового типа ADJUSTMENT и двух новых сервисов (CategoryService, ReconciliationService). Ключевые улучшения v2: явная миграция старого поля category, определение поведения ADJUSTMENT в статистике, детальное описание UI callback-ов при смене типа транзакции.

## Архитектура

### Компоненты

**1. Category (Модель)**
Справочник категорий с системными (is_system=True) и пользовательскими. Системная категория "Коррекция" используется по умолчанию для ADJUSTMENT и не может быть удалена.

**2. CategoryService (Сервис)**
Простой сервис для получения списка категорий с фильтрацией по типу операции и idempotent seed.

**3. ReconciliationService (Сервис)**
Сервис для создания ADJUSTMENT транзакций на основе разницы между расчетным и фактическим балансом. Использует CalendarService для получения expected_balance.

**4. TransactionService (Изменения)**
- Параметр `category` (str) УДАЛЯЕТСЯ
- Параметр `category_id` (int | None) ДОБАВЛЯЕТСЯ
- Обе функции create/update адаптируются

**5. CalendarService (Изменения)**
Добавление обработки TransactionType.ADJUSTMENT во ВСЕХ методах расчета баланса.

**6. DashboardService (Изменения)**
- ADJUSTMENT НЕ входит в total_income/total_expense
- RecentTransaction.category заменяется на category_name (str | None)

**7. RecurringService (Изменения)**
Копирование category_id при генерации exceptions и virtual instances.

**8. UI компоненты**
- Dropdown категории в формах create/edit (transactions.py)
- Callback фильтрации категорий при смене типа операции
- Колонка категории с иконкой в таблице транзакций
- Checkbox "Без категории" для фильтрации
- Модал сверки на календаре (calendar.py)

### Диаграмма взаимодействия

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 UI Layer                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  transactions.py                  calendar.py                                │
│  ┌─────────────────────┐         ┌──────────────────────┐                   │
│  │ Create/Edit Modal   │         │ Reconciliation Modal │                   │
│  │ ┌─────────────────┐ │         │ - expected_balance   │                   │
│  │ │ Type Select     │─┼─[1]──→  │ - actual_input       │                   │
│  │ │ (INCOME/EXPENSE)│ │         │ - difference display │                   │
│  │ └───────┬─────────┘ │         │ - create_adjustment  │                   │
│  │         │[callback] │         └──────────┬───────────┘                   │
│  │         ▼           │                    │                               │
│  │ ┌─────────────────┐ │                    │                               │
│  │ │ Category Dropdown│ │                   │                               │
│  │ │ (filtered)      │ │                    │                               │
│  │ └─────────────────┘ │                    │                               │
│  │                     │                    │                               │
│  │ Table + Filter:     │                    │                               │
│  │ □ Без категории     │                    │                               │
│  │ [icon] Category col │                    │                               │
│  └──────────┬──────────┘                    │                               │
└─────────────┼────────────────────────────────┼───────────────────────────────┘
              │                                │
              ▼                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Service Layer                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TransactionService      CategoryService         ReconciliationService       │
│  (MODIFIED)              (NEW)                   (NEW)                       │
│  ┌────────────────┐      ┌─────────────────┐    ┌────────────────────────┐  │
│  │ create()       │      │ get_all()       │    │ get_expected_balance() │  │
│  │ update()       │      │ get_by_id()     │    │ create_adjustment()    │  │
│  │ -category (str)│      │ get_for_type()  │    └────────────────────────┘  │
│  │ +category_id   │      │ seed_default()  │              │                 │
│  └────────────────┘      │ get_correction()│              │ uses            │
│                          └─────────────────┘              ▼                 │
│  CalendarService          DashboardService       ┌────────────────┐         │
│  (MODIFIED)               (MODIFIED)             │ CalendarService│         │
│  ┌────────────────┐      ┌─────────────────┐    │ .get_balance   │         │
│  │+ADJUSTMENT     │      │ ADJUSTMENT NOT  │    │ _on_date()     │         │
│  │ handling in:   │      │ in income/      │    └────────────────┘         │
│  │ -calc_balance  │      │ expense totals  │                                │
│  │ -daily_changes │      │ RecentTx: name  │                                │
│  │ -month_summary │      │ not FK          │                                │
│  │ -year_summary  │      └─────────────────┘                                │
│  └────────────────┘                                                         │
│                                                                              │
│  RecurringService                                                            │
│  (MODIFIED)                                                                  │
│  ┌────────────────────────────────────────┐                                 │
│  │ generate_instances(): copy category_id │                                 │
│  │ create_exception(): copy category_id   │                                 │
│  └────────────────────────────────────────┘                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Model Layer                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  User              Transaction                    Category (NEW)             │
│  ┌──────────┐     ┌─────────────────────┐        ┌───────────────────┐      │
│  │ id       │     │ id                  │        │ id                │      │
│  │ ...      │     │ category_id (FK) ───┼────────│ name              │      │
│  └──────────┘     │ [REMOVED: category] │        │ icon              │      │
│                   │ trans_type          │        │ type (income/     │      │
│                   │ (+ADJUSTMENT)       │        │   expense/both)   │      │
│                   └─────────────────────┘        │ is_system         │      │
│                                                  │ sort_order        │      │
│                                                  └───────────────────┘      │
│                                                                              │
│  TransactionType Enum:                                                       │
│  INCOME | EXPENSE | TRANSFER | ADJUSTMENT (NEW)                             │
└──────────────────────────────────────────────────────────────────────────────┘

[1] Callback flow при смене типа:
    Type changed → filter categories → set category_id = None → update dropdown
```

## Файловая структура

```
app/models/database.py           — Category модель, TransactionType.ADJUSTMENT,
                                   Transaction: -category (String), +category_id (FK)
                                   +ON DELETE SET NULL

app/types/categories.py          — НОВЫЙ: TypedDicts (CategoryOption, ReconciliationPreview)

app/services/category_service.py        — НОВЫЙ: CategoryService
app/services/reconciliation_service.py  — НОВЫЙ: ReconciliationService
app/services/transaction_service.py     — изменить: -category, +category_id
app/services/calendar_service.py        — изменить: +ADJUSTMENT handling (6 мест)
app/services/dashboard_service.py       — изменить: RecentTransaction.category -> name
app/services/recurring_service.py       — изменить: copy category_id
app/services/__init__.py                — экспорт новых сервисов

app/components/transactions.py  — изменить: dropdown категории, callback type->category,
                                  колонка с иконкой, checkbox фильтр
app/components/calendar.py      — изменить: кнопка и модал сверки

tests/test_category_service.py           — НОВЫЙ: 5 тестов
tests/test_reconciliation_service.py     — НОВЫЙ: 5 тестов
tests/test_calendar_service.py           — добавить: 3 теста ADJUSTMENT
tests/test_recurring_service.py          — добавить: 2 теста category inheritance
tests/test_transaction_service.py        — добавить: 2 теста category_id

scripts/seed_categories.py              — НОВЫЙ (вызывается из init_database)
```

## Ключевые интерфейсы

```python
# === app/models/database.py ===

class TransactionType(PyEnum):
    """Типы финансовых операций."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"  # НОВЫЙ: корректировка баланса


class Category(Base):
    """Модель категории операций.

    Справочник категорий для классификации транзакций.
    Поддерживает системные (is_system=True) и пользовательские категории.

    Attributes:
        name: Название категории ("Еда и продукты", "Зарплата")
        icon: Bootstrap icon class ("bi-cart", "bi-briefcase")
        type: Применимость к типам операций:
              - "income" — только для доходов
              - "expense" — только для расходов
              - "both" — для любых (например, "Коррекция")
        is_system: True для предзаполненных категорий, нельзя удалить
        sort_order: Порядок в dropdown (сначала по type, потом по sort_order)
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(30), default="bi-tag")
    type = Column(String(10), nullable=False)  # "income" | "expense" | "both"
    is_system = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    # Relationships
    transactions = relationship("Transaction", back_populates="category_rel")


class Transaction(Base):
    # ... существующие поля ...

    # УДАЛЕНО: category = Column(String(100))  # Категория (на будущее)

    # НОВОЕ: категория как FK (nullable, ON DELETE SET NULL)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_rel = relationship("Category", back_populates="transactions")


# === app/types/categories.py ===

from typing import TypedDict


class CategoryOption(TypedDict):
    """Опция категории для dropdown в UI.

    Используется для передачи данных из CategoryService в callbacks.
    """
    label: str   # "Еда и продукты"
    value: int   # category_id
    icon: str    # "bi-cart"


class ReconciliationPreview(TypedDict):
    """Предпросмотр сверки для модала.

    Все Decimal конвертируются в строки для JSON-совместимости (dcc.Store).
    """
    expected_balance: str   # "15000.00"
    actual_balance: str     # "14200.00" (user input)
    difference: str         # "-800.00"
    is_positive: bool       # False если difference < 0
    target_date: str        # "2026-01-22"
    explanation: str        # "Будет создана корректировка на -800 ₽"


# === app/services/category_service.py ===

DEFAULT_CATEGORIES: list[dict] = [
    # === РАСХОДЫ (sort_order 1-100) ===
    {"name": "Еда и продукты", "icon": "bi-cart", "type": "expense", "sort_order": 1},
    {"name": "Транспорт", "icon": "bi-car-front", "type": "expense", "sort_order": 2},
    {"name": "Жилье и ЖКХ", "icon": "bi-house", "type": "expense", "sort_order": 3},
    {"name": "Связь и интернет", "icon": "bi-phone", "type": "expense", "sort_order": 4},
    {"name": "Здоровье", "icon": "bi-heart-pulse", "type": "expense", "sort_order": 5},
    {"name": "Одежда", "icon": "bi-bag", "type": "expense", "sort_order": 6},
    {"name": "Развлечения", "icon": "bi-controller", "type": "expense", "sort_order": 7},
    {"name": "Образование", "icon": "bi-book", "type": "expense", "sort_order": 8},
    {"name": "Подарки другим", "icon": "bi-gift", "type": "expense", "sort_order": 9},
    {"name": "Прочие расходы", "icon": "bi-three-dots", "type": "expense", "sort_order": 10},
    # === ДОХОДЫ (sort_order 101-200) ===
    {"name": "Зарплата", "icon": "bi-briefcase", "type": "income", "sort_order": 101},
    {"name": "Подработка", "icon": "bi-laptop", "type": "income", "sort_order": 102},
    {"name": "Инвестиции", "icon": "bi-graph-up", "type": "income", "sort_order": 103},
    {"name": "Подарки полученные", "icon": "bi-gift", "type": "income", "sort_order": 104},
    {"name": "Прочие доходы", "icon": "bi-three-dots", "type": "income", "sort_order": 105},
    # === СИСТЕМНЫЕ (sort_order 0) ===
    {"name": "Коррекция", "icon": "bi-arrow-repeat", "type": "both", "is_system": True, "sort_order": 0},
]


class CategoryService:
    """Сервис для работы с категориями операций."""

    def __init__(self, session: Session):
        self.session = session

    def get_all(self, type_filter: str | None = None) -> list[Category]:
        """Получает все категории с опциональной фильтрацией.

        Args:
            type_filter: "income", "expense" или None (все)

        Returns:
            list[Category]: Категории, отсортированные по sort_order.
            При type_filter также включает категории с type="both".
        """
        query = self.session.query(Category)

        if type_filter:
            # Включаем и запрошенный тип, и "both" (например, "Коррекция")
            query = query.filter(
                Category.type.in_([type_filter, "both"])
            )

        return query.order_by(Category.sort_order).all()

    def get_by_id(self, category_id: int) -> Category | None:
        """Получает категорию по ID."""
        return self.session.get(Category, category_id)

    def get_system_correction_category(self) -> Category | None:
        """Получает системную категорию 'Коррекция'.

        Returns:
            Category | None: Категория или None если не найдена
        """
        return (
            self.session.query(Category)
            .filter(Category.is_system == True, Category.name == "Коррекция")  # noqa: E712
            .first()
        )

    def seed_default_categories(self) -> int:
        """Создает предзаполненные категории (idempotent).

        Проверяет существование по name+type, создает только отсутствующие.

        Returns:
            int: Количество созданных категорий
        """
        created_count = 0

        for cat_data in DEFAULT_CATEGORIES:
            exists = (
                self.session.query(Category)
                .filter(
                    Category.name == cat_data["name"],
                    Category.type == cat_data["type"],
                )
                .first()
            )

            if not exists:
                category = Category(**cat_data)
                self.session.add(category)
                created_count += 1

        self.session.flush()
        return created_count

    def get_for_dropdown(self, type_filter: str | None = None) -> list[CategoryOption]:
        """Получает категории в формате для dbc.Select options.

        Args:
            type_filter: "income" или "expense"

        Returns:
            list[CategoryOption]: Список для dropdown
        """
        categories = self.get_all(type_filter)
        return [
            CategoryOption(
                label=cat.name,
                value=cat.id,
                icon=cat.icon,
            )
            for cat in categories
        ]


# === app/services/reconciliation_service.py ===

class ReconciliationService:
    """Сервис для сверки расчетного баланса с фактическим.

    Создает ADJUSTMENT транзакции для синхронизации модели с реальностью.
    """

    def __init__(self, session: Session):
        self.session = session
        self._calendar_service = CalendarService(session)
        self._category_service = CategoryService(session)

    def get_expected_balance(self, user_id: int, target_date: date) -> Decimal:
        """Получает расчетный баланс на дату (делегирует CalendarService)."""
        return self._calendar_service.get_balance_on_date(user_id, target_date)

    def create_adjustment(
        self,
        user_id: int,
        target_date: date,
        actual_balance: Decimal,
        description: str | None = None,
    ) -> Transaction:
        """Создает корректирующую ADJUSTMENT транзакцию.

        Формула: adjustment_amount = actual_balance - expected_balance
        - Если positive — в реальности денег больше (забыли записать доход)
        - Если negative — в реальности денег меньше (забыли записать расход)

        Args:
            user_id: ID пользователя
            target_date: Дата корректировки
            actual_balance: Фактический остаток от пользователя
            description: Описание (по умолчанию "Сверка от DD.MM.YYYY")

        Returns:
            Transaction: Созданная ADJUSTMENT транзакция

        Raises:
            ValidationError: Если actual == expected (разница = 0)
        """
        expected_balance = self.get_expected_balance(user_id, target_date)
        difference = actual_balance - expected_balance

        if difference == 0:
            raise ValidationError(
                "Фактический баланс совпадает с расчетным — корректировка не нужна"
            )

        # Получаем системную категорию "Коррекция"
        correction_category = self._category_service.get_system_correction_category()

        # Формируем описание
        if not description:
            description = f"Сверка от {target_date.strftime('%d.%m.%Y')}"

        adjustment = Transaction(
            user_id=user_id,
            amount=difference,  # Может быть отрицательным
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_date=target_date,
            description=description,
            category_id=correction_category.id if correction_category else None,
            is_recurring=False,
        )

        self.session.add(adjustment)
        self.session.flush()

        logger.info(
            f"Создана корректировка для user {user_id}: "
            f"expected={expected_balance}, actual={actual_balance}, diff={difference}"
        )

        return adjustment

    def get_preview(
        self, user_id: int, target_date: date, actual_balance: Decimal
    ) -> ReconciliationPreview:
        """Формирует превью сверки для UI.

        Args:
            user_id: ID пользователя
            target_date: Дата сверки
            actual_balance: Введенный пользователем фактический баланс

        Returns:
            ReconciliationPreview для отображения в модале
        """
        expected = self.get_expected_balance(user_id, target_date)
        difference = actual_balance - expected

        if difference > 0:
            explanation = f"В реальности на {difference:,.0f} ₽ больше (забыт доход?)"
        elif difference < 0:
            explanation = f"В реальности на {abs(difference):,.0f} ₽ меньше (забыт расход?)"
        else:
            explanation = "Остаток совпадает — корректировка не нужна"

        return ReconciliationPreview(
            expected_balance=str(expected),
            actual_balance=str(actual_balance),
            difference=str(difference),
            is_positive=difference > 0,
            target_date=target_date.isoformat(),
            explanation=explanation,
        )


# === Изменения в app/services/calendar_service.py ===

def _calculate_balance_before_date(self, user_id: int, before_date: date) -> Decimal:
    """Рассчитывает сумму всех изменений баланса до указанной даты.

    ИЗМЕНЕНИЕ v2: Добавлена обработка ADJUSTMENT.
    ADJUSTMENT добавляется к балансу напрямую (amount может быть отрицательным).
    """
    result = (
        self.session.query(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
                        (Transaction.transaction_type == TransactionType.EXPENSE, -Transaction.amount),
                        (Transaction.transaction_type == TransactionType.ADJUSTMENT, Transaction.amount),  # NEW
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            )
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date < before_date,
            Transaction.transaction_type.in_(
                [TransactionType.INCOME, TransactionType.EXPENSE, TransactionType.ADJUSTMENT]  # +ADJUSTMENT
            ),
            Transaction.is_recurring == False,
            Transaction.recurring_parent_id == None,
        )
        .scalar()
    )
    ...


# === Изменения в app/services/transaction_service.py ===

def create_transaction(
    self,
    user_id: int,
    amount: Decimal,
    transaction_type: TransactionType,
    transaction_date: date,
    description: str | None = None,
    category_id: int | None = None,  # ИЗМЕНЕНО: int | None вместо str | None
    is_recurring: bool = False,
    recurring_period: str | None = None,
    recurring_end_date: date | None = None,
) -> Transaction:
    """Создает новую транзакцию или шаблон recurring.

    Args:
        category_id: ID категории (опционально, None = без категории)
    """
    # ... валидация ...

    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        description=description,
        category_id=category_id,  # ИЗМЕНЕНО: category_id вместо category
        is_recurring=is_recurring,
        recurring_period=recurring_period if is_recurring else None,
        recurring_end_date=recurring_end_date if is_recurring else None,
    )
    ...


def update_transaction(
    self,
    transaction_id: int,
    amount: Decimal | None = None,
    transaction_type: TransactionType | None = None,
    transaction_date: date | None = None,
    description: str | None = None,
    category_id: int | None = ...,  # Sentinel для "не менять", None для "очистить"
) -> Transaction:
    """Обновляет существующую транзакцию.

    Args:
        category_id: ID категории. Если не передан — не меняется.
                    Если None — очищается.
    """
    # Используем sentinel для различия "не передан" и "передан None"
    if category_id is not ...:
        transaction.category_id = category_id
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
    """Создает exception для конкретного экземпляра recurring.

    ИЗМЕНЕНИЕ v2: Копирует category_id из шаблона.
    """
    template = self.get_template_by_id(template_id)
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


# VirtualTransaction также включает category_id
class VirtualTransaction(TypedDict):
    template_id: int
    user_id: int
    instance_date: str
    amount: str
    transaction_type: str
    description: str | None
    category_id: int | None  # НОВОЕ
    is_virtual: bool
```

## Модель данных

### Предзаполненные категории (v2 — устранены коллизии)

| Name | Icon | Type | is_system | sort_order |
|------|------|------|-----------|------------|
| Коррекция | bi-arrow-repeat | both | True | 0 |
| Еда и продукты | bi-cart | expense | False | 1 |
| Транспорт | bi-car-front | expense | False | 2 |
| Жилье и ЖКХ | bi-house | expense | False | 3 |
| Связь и интернет | bi-phone | expense | False | 4 |
| Здоровье | bi-heart-pulse | expense | False | 5 |
| Одежда | bi-bag | expense | False | 6 |
| Развлечения | bi-controller | expense | False | 7 |
| Образование | bi-book | expense | False | 8 |
| **Подарки другим** | bi-gift | expense | False | 9 |
| Прочие расходы | bi-three-dots | expense | False | 10 |
| Зарплата | bi-briefcase | income | False | 101 |
| Подработка | bi-laptop | income | False | 102 |
| Инвестиции | bi-graph-up | income | False | 103 |
| **Подарки полученные** | bi-gift | income | False | 104 |
| Прочие доходы | bi-three-dots | income | False | 105 |

**Изменения v2:**
- "Подарки" → "Подарки другим" (expense) и "Подарки полученные" (income)
- sort_order для income начинается с 101 для избежания конфликтов

### TypedDicts (в app/types/categories.py)

```python
class CategoryOption(TypedDict):
    """Для dbc.Select/dbc.RadioItems options."""
    label: str   # Название категории
    value: int   # category_id
    icon: str    # Bootstrap icon class

class ReconciliationPreview(TypedDict):
    """Для модала сверки."""
    expected_balance: str
    actual_balance: str
    difference: str
    is_positive: bool
    target_date: str
    explanation: str  # Человеко-понятное объяснение
```

## Обработка ошибок

### Стратегия
Используется существующий паттерн ValidationError из app/core/exceptions.py.

```python
# ReconciliationService
if actual_balance == expected_balance:
    raise ValidationError("Фактический баланс совпадает с расчетным — корректировка не нужна")

# CategoryService.seed_default_categories()
# Не бросает исключений — idempotent, возвращает количество созданных

# TransactionService — валидация category_id
# Если category_id указан но не существует — FK constraint error от SQLite
# Рекомендация: не проверять существование (FK + ON DELETE SET NULL достаточно)
```

### UI обработка
- Модал сверки: если difference == 0, кнопка "Создать корректировку" disabled + текст "Остаток совпадает"
- Формы транзакций: category_id = None (без категории) — валидное состояние, отображается как "Без категории"
- При смене типа операции: category_id сбрасывается в None, dropdown обновляется

## План реализации

### Шаг 1: Модель данных и миграция (1-2 часа)
1.1. Добавить TransactionType.ADJUSTMENT в app/models/database.py
1.2. Создать модель Category
1.3. УДАЛИТЬ поле Transaction.category (String)
1.4. ДОБАВИТЬ Transaction.category_id FK с ON DELETE SET NULL
1.5. Добавить Index на category_id для производительности
1.6. Пересоздать БД (drop + create) — данных мало, миграция не нужна

### Шаг 2: TypedDicts (15 мин)
2.1. Создать app/types/categories.py
2.2. Добавить CategoryOption, ReconciliationPreview
2.3. Обновить app/types/__init__.py (если существует)

### Шаг 3: CategoryService (1 час)
3.1. Создать app/services/category_service.py
3.2. Реализовать get_all(), get_by_id(), get_system_correction_category()
3.3. Реализовать seed_default_categories() (idempotent, проверка по name+type)
3.4. Реализовать get_for_dropdown() для UI
3.5. Написать unit тесты (5+)

### Шаг 4: ReconciliationService (1-2 часа)
4.1. Создать app/services/reconciliation_service.py
4.2. Реализовать get_expected_balance() (делегирует CalendarService)
4.3. Реализовать create_adjustment() с валидацией
4.4. Реализовать get_preview() для UI
4.5. Написать unit тесты (5+)

### Шаг 5: Изменения в CalendarService (1 час)
5.1. Добавить ADJUSTMENT в _calculate_balance_before_date()
5.2. Добавить ADJUSTMENT в _get_daily_changes()
5.3. **НЕ добавлять** ADJUSTMENT в get_month_summary() (total_income/expense)
5.4. **НЕ добавлять** ADJUSTMENT в get_year_summary()
5.5. Написать unit тесты (3+)

### Шаг 6: Изменения в TransactionService (30 мин)
6.1. УДАЛИТЬ параметр category (str)
6.2. ДОБАВИТЬ параметр category_id (int | None) в create_transaction()
6.3. ДОБАВИТЬ параметр category_id в update_transaction() с sentinel
6.4. Написать unit тесты (2+)

### Шаг 7: Изменения в RecurringService (30 мин)
7.1. Добавить category_id в VirtualTransaction TypedDict
7.2. Копировать category_id в create_exception()
7.3. Копировать category_id в generate_instances() (для virtual)
7.4. Написать unit тесты (2+)

### Шаг 8: Изменения в DashboardService (30 мин)
8.1. RecentTransaction.category заменить на получение category_rel.name
8.2. Проверить что ADJUSTMENT не влияет на total_income/expense (уже так)
8.3. Написать unit тесты (1)

### Шаг 9: UI — Формы транзакций (2-3 часа)
9.1. Добавить dropdown категории в create modal (после поля "Тип")
9.2. Добавить callback `update_category_dropdown` при смене типа:
     - Input: create-type-select.value
     - Output: create-category-select.options, create-category-select.value
     - При смене типа: options = CategoryService.get_for_dropdown(type), value = None
9.3. Добавить dropdown категории в edit modal (аналогично)
9.4. Обновить create_transaction callback: использовать category_id
9.5. Обновить update_transaction callback: использовать category_id
9.6. Добавить колонку "Категория" в таблицу (иконка + название)
9.7. Добавить checkbox "Без категории" в header
9.8. Реализовать фильтрацию по checkbox

### Шаг 10: UI — Модал сверки (2-3 часа)
10.1. Добавить кнопку "Сверка" на странице календаря (рядом с текущим балансом)
10.2. Создать reconciliation-modal:
      - dbc.Modal с id="reconciliation-modal"
      - Показывает expected_balance (readonly)
      - Input для actual_balance
      - Показывает difference с объяснением
      - Кнопка "Создать корректировку" (disabled если diff == 0)
10.3. Callback: open_reconciliation_modal
      - Trigger: кнопка "Сверка"
      - Загружает expected_balance
      - Открывает модал
10.4. Callback: update_difference_preview
      - Trigger: actual_balance input
      - Вызывает ReconciliationService.get_preview()
      - Обновляет difference и explanation
10.5. Callback: create_adjustment
      - Trigger: кнопка "Создать корректировку"
      - Вызывает ReconciliationService.create_adjustment()
      - Закрывает модал
      - Обновляет календарь

### Шаг 11: Интеграция и документация (1 час)
11.1. Обновить app/services/__init__.py
11.2. Вызвать seed_default_categories() в init_database()
11.3. Обновить scripts/seed_database.py (использовать category_id вместо category)
11.4. Обновить ROADMAP.md и feature_progress.md
11.5. Интеграционные тесты (3)

## Зависимости
Новые библиотеки не требуются. Все зависимости уже в проекте:
- SQLAlchemy (модели, FK, ON DELETE SET NULL)
- Dash / Dash Bootstrap Components (UI)
- pytest (тесты)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Сложность callback при смене типа транзакции | Средняя | Вынести логику в CategoryService.get_for_dropdown(); использовать dcc.Store для кэширования списка категорий |
| ADJUSTMENT с отрицательным amount может запутать пользователя | Средняя | UI показывает explanation: "в реальности на X ₽ меньше (забыт расход?)"; корректировка сразу видна в календаре |
| seed_default_categories() при каждом запуске | Низкая | Idempotent проверка по name+type выполняется быстро (<10ms для 16 записей) |
| Breaking change: удаление Transaction.category (String) | Средняя | Данных в поле нет (все NULL или "Зарплата"/"Жилье" из seed); seed_database.py обновляется |
| FK constraint violation при удалении Category | Низкая | ON DELETE SET NULL — транзакции не удаляются, category_id становится NULL |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🟡 Коллизия Transaction.category (String) и category_id (FK) | **Удаляем старое поле category (String)**, заменяем на category_id. Поле не использовалось реально (только в seed скрипте). Это breaking change, но данных нет. |
| 🟡 ADJUSTMENT в статистике неопределен | **Явно определено**: ADJUSTMENT НЕ входит в total_income/total_expense (только в баланс). Корректировка — это синхронизация модели, не реальный доход/расход. |
| 🟡 Callback фильтрации категорий не описан | **Описан детально**: при смене типа операции → category_id = None, dropdown.options = CategoryService.get_for_dropdown(new_type). Категории с type="both" всегда включены. |
| 🟡 Формула ADJUSTMENT может быть неочевидна | **Добавлен explanation в ReconciliationPreview**: "В реальности на X ₽ меньше (забыт расход?)" или "...больше (забыт доход?)". UI явно объясняет что происходит. |
| 🟢 TypedDicts в отдельном файле | **Используем app/types/categories.py** для консистентности с будущей структурой (app/types/goals.py, etc.) |
| 🟢 sort_order конфликт income/expense | **Разделены диапазоны**: expense = 1-100, income = 101-200. При смешанном списке (type="both") порядок предсказуем. |
| 🟢 "Подарки" дублируется | **Переименованы**: "Подарки другим" (expense) и "Подарки полученные" (income) |
| 🔹 ON DELETE SET NULL | **Добавлено** в ForeignKey definition |

## Ответы на вопросы критика

1. **Вопрос:** Судьба `Transaction.category` (String): Удалять, переименовать или оставить оба?
   **Ответ:** **Удалять**. Поле было добавлено "на будущее" и реально не использовалось в бизнес-логике. Текущие данные:
   - В БД все значения NULL или тестовые ("Зарплата", "Жилье" из seed)
   - TransactionService принимает category как параметр, но это не связано с аналитикой
   - Dashboard показывает "Uncategorized" если category is None

   Оставлять два поля (category String и category_id FK) создаёт путаницу и требует синхронизации. Чистый breaking change с удалением проще и надёжнее.

2. **Вопрос:** ADJUSTMENT в статистике: влияет на total_income/total_expense или только на баланс?
   **Ответ:** **Только на баланс**. Обоснование:
   - ADJUSTMENT — это "синхронизация модели с реальностью", не настоящий доход или расход
   - Если пользователь забыл записать расход в 800₽, создаётся ADJUSTMENT -800₽
   - Это НЕ расход (он уже произошёл раньше), это корректировка
   - В отчётах "Доходы/Расходы за месяц" ADJUSTMENT не должен появляться
   - В баланс на дату — должен влиять (это его назначение)

3. **Вопрос:** Фильтр "Без категории": checkbox или dropdown?
   **Ответ:** **Checkbox** в header таблицы. Обоснование:
   - Простой бинарный выбор (показать/скрыть)
   - Не конфликтует с будущими фильтрами (по типу, по дате)
   - Легко заметить состояние (checked/unchecked)
   - Dropdown имеет смысл для множественного выбора категорий (Батч 3.2)

4. **Вопрос:** Приоритеты тестов?
   **Ответ:** **Приоритет 1 (критично):**
   - CalendarService: ADJUSTMENT корректно влияет на баланс (+ и -)
   - ReconciliationService: create_adjustment создаёт правильную транзакцию
   - CategoryService: seed_default_categories idempotent

   **Приоритет 2 (важно):**
   - RecurringService: category_id копируется в exceptions
   - TransactionService: create/update с category_id

   **Приоритет 3 (желательно):**
   - CategoryService: фильтрация по типу
   - Integration: E2E сверка

5. **Вопрос:** Порядок категорий: фиксированный или настраиваемый?
   **Ответ:** **Фиксированный** через sort_order. Обоснование:
   - Для MVP достаточно предзаполненных категорий
   - Настройка порядка — feature creep для Батча 3.1
   - Если понадобится: добавить User.category_preferences (JSON) или отдельная таблица UserCategoryOrder
   - sort_order в Category — это базовый порядок, переопределяемый пользователем в будущем

## Critical Files for Implementation

1. `/home/skytiger/PycharmProjects/FinFocus/app/models/database.py` — Core changes: Category model, TransactionType.ADJUSTMENT, Transaction.category_id FK, remove Transaction.category
2. `/home/skytiger/PycharmProjects/FinFocus/app/services/calendar_service.py` — Add ADJUSTMENT handling in 6 calculation methods
3. `/home/skytiger/PycharmProjects/FinFocus/app/components/transactions.py` — Category dropdown, type-change callback, table column, filter checkbox
4. `/home/skytiger/PycharmProjects/FinFocus/app/components/calendar.py` — Reconciliation button and modal
5. `/home/skytiger/PycharmProjects/FinFocus/app/services/transaction_service.py` — Replace category (str) with category_id (int), pattern for existing service changes
