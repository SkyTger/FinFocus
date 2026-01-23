# Solution v3: Категоризация и Сверка — Финальная версия

## Обзор решения
Это финальная версия решения, готовая к реализации. Solution v2 получил оценку 5/5, изменения в v3 носят уточняющий характер: исправлено расположение TypedDicts (`app/schema/` вместо `app/types/`), добавлены category fields в TransactionInfo, определена валидация ADJUSTMENT + recurring.

**Статус:** Финальная версия, готова к кодированию.

## Учтённые замечания из критики v2

| Замечание из critique v2 | Как решено |
|--------------------------|------------|
| VirtualTransaction TypedDict не в app/types/ | **Исправлено направление**: проект использует `app/schema/`, а не `app/types/`. VirtualTransaction остаётся в recurring_service.py (локальный TypedDict), новые TypedDicts создаются в `app/schema/categories.py` |
| TransactionInfo не включает category_id | **Добавлено**: `category_id: int \| None` и `category_name: str \| None` в TransactionInfo для отображения категории в UI календаря |

## Ответы на вопросы критика

1. **Вопрос:** Планируется ли показывать категорию в ячейках календаря или только в списке транзакций?
   **Ответ:** Категория будет показываться как в ячейках календаря (при hover/клике на транзакцию), так и в списке транзакций (колонка с иконкой). TransactionInfo расширяется полями `category_id` и `category_name` для поддержки обоих сценариев.

2. **Вопрос:** Нужна ли явная валидация, что ADJUSTMENT не может быть recurring template?
   **Ответ:** **Да**, добавляется явная валидация в TransactionService.create_transaction():
   ```python
   if is_recurring and transaction_type == TransactionType.ADJUSTMENT:
       raise ValidationError("Корректировки не могут быть повторяющимися операциями")
   ```
   ADJUSTMENT — это single-shot операция сверки, повторение не имеет смысла.

## Дополнения к Solution v2

### Исправление: TypedDicts в app/schema/ (не app/types/)

Проект использует `app/schema/` для централизованных TypedDicts. Создаётся новый файл:

```
app/schema/categories.py   — НОВЫЙ: CategoryOption, ReconciliationPreview
```

Обновить `app/schema/__init__.py` для экспорта.

### Новые/обновленные TypedDicts

```python
# === app/schema/categories.py (НОВЫЙ файл) ===

"""TypedDicts для типизации данных категорий и сверки."""

from typing import TypedDict


class CategoryOption(TypedDict):
    """Опция категории для dropdown в UI.

    Используется для передачи данных из CategoryService в callbacks.
    """

    label: str  # "Еда и продукты"
    value: int  # category_id
    icon: str  # "bi-cart"


class ReconciliationPreview(TypedDict):
    """Предпросмотр сверки для модала.

    Все Decimal конвертируются в строки для JSON-совместимости (dcc.Store).
    """

    expected_balance: str  # "15000.00"
    actual_balance: str  # "14200.00" (user input)
    difference: str  # "-800.00"
    is_positive: bool  # False если difference < 0
    target_date: str  # "2026-01-22"
    explanation: str  # "Будет создана корректировка на -800 ₽"


# === app/services/calendar_service.py (ОБНОВЛЕНИЕ TransactionInfo) ===

class TransactionInfo(TypedDict):
    """Информация о транзакции для UI календаря.

    Используется вместо ORM-объекта Transaction для передачи
    данных из CalendarService в UI-компоненты после закрытия сессии БД.
    Поддерживает как обычные транзакции, так и recurring instances.
    """

    id: int | None  # ID транзакции (None для виртуальных recurring)
    template_id: int | None  # ID шаблона для recurring (None для обычных)
    transaction_type: str  # "income" | "expense" | "transfer" | "adjustment"  # +ADJUSTMENT
    amount: str  # Decimal в строковом формате
    description: str | None  # Описание
    date: str  # ISO format (YYYY-MM-DD)
    is_virtual: bool  # True для виртуальных recurring instances
    is_recurring: bool  # True для recurring (виртуальных и exceptions)
    is_exception: bool  # True для exceptions (материализованных recurring)
    category_id: int | None  # NEW: ID категории (None = без категории)
    category_name: str | None  # NEW: Название категории для UI


# === app/services/recurring_service.py (ОБНОВЛЕНИЕ VirtualTransaction) ===

class VirtualTransaction(TypedDict):
    """Виртуальный экземпляр recurring операции.

    Не хранится в БД, генерируется динамически.
    TypedDict для совместимости с JSON-сериализацией (dcc.Store).
    """

    template_id: int  # ID шаблона
    user_id: int
    instance_date: str  # ISO format (YYYY-MM-DD)
    amount: str  # Decimal as string для JSON
    transaction_type: str  # "income" | "expense" | "transfer"
    description: str | None
    is_virtual: bool  # Всегда True для виртуальных
    category_id: int | None  # NEW: копируется из шаблона


# === app/services/dashboard_service.py (ОБНОВЛЕНИЕ RecentTransaction) ===

class RecentTransaction(TypedDict):
    """Данные транзакции для списка на дашборде."""

    id: int
    description: str | None
    category_name: str | None  # ИЗМЕНЕНО: было category (str), теперь category_name
    category_icon: str | None  # NEW: для отображения иконки
    date: str
    amount: Decimal
    transaction_type: str
```

### Добавление: Валидация ADJUSTMENT + recurring

```python
# === app/services/transaction_service.py (ДОБАВЛЕНИЕ в create_transaction) ===

def create_transaction(
    self,
    user_id: int,
    amount: Decimal,
    transaction_type: TransactionType,
    transaction_date: date,
    description: str | None = None,
    category_id: int | None = None,
    is_recurring: bool = False,
    recurring_period: str | None = None,
    recurring_end_date: date | None = None,
) -> Transaction:
    """Создает новую транзакцию или шаблон recurring.

    Raises:
        ValidationError: Если is_recurring=True и transaction_type=ADJUSTMENT
    """
    # НОВАЯ валидация: ADJUSTMENT не может быть recurring
    if is_recurring and transaction_type == TransactionType.ADJUSTMENT:
        raise ValidationError(
            "Корректировки не могут быть повторяющимися операциями"
        )

    # ... остальная логика из solution-v2 ...
```

### Обновленная файловая структура

```
app/models/database.py           — Category модель, TransactionType.ADJUSTMENT,
                                   Transaction: -category (String), +category_id (FK)

app/schema/categories.py         — НОВЫЙ: CategoryOption, ReconciliationPreview
app/schema/__init__.py           — обновить экспорт

app/services/category_service.py        — НОВЫЙ: CategoryService
app/services/reconciliation_service.py  — НОВЫЙ: ReconciliationService
app/services/transaction_service.py     — изменить: -category, +category_id, +ADJUSTMENT валидация
app/services/calendar_service.py        — изменить: +ADJUSTMENT handling, +TransactionInfo fields
app/services/dashboard_service.py       — изменить: RecentTransaction.category_name/icon
app/services/recurring_service.py       — изменить: +VirtualTransaction.category_id

app/components/transactions.py  — изменить: dropdown категории, колонка с иконкой, фильтр
app/components/calendar.py      — изменить: кнопка и модал сверки, отображение категории

tests/test_category_service.py           — НОВЫЙ: 5 тестов
tests/test_reconciliation_service.py     — НОВЫЙ: 5 тестов
tests/test_calendar_service.py           — добавить: 3 теста ADJUSTMENT
tests/test_recurring_service.py          — добавить: 2 теста category inheritance
tests/test_transaction_service.py        — добавить: 3 теста (category_id + ADJUSTMENT validation)
```

### Обновленный план реализации (дельта к v2)

**Шаг 2 (исправлен): TypedDicts в app/schema/**

2.1. Создать `app/schema/categories.py` (не `app/types/`!)
2.2. Добавить CategoryOption, ReconciliationPreview
2.3. Обновить `app/schema/__init__.py` для экспорта

**Шаг 5 (дополнен): CalendarService**

5.1. Добавить ADJUSTMENT в _calculate_balance_before_date()
5.2. Добавить ADJUSTMENT в _get_daily_changes()
5.3. **НЕ добавлять** ADJUSTMENT в get_month_summary() (total_income/expense)
5.4. **НЕ добавлять** ADJUSTMENT в get_year_summary()
5.5. **Добавить** `category_id`, `category_name` в TransactionInfo
5.6. Обновить get_transactions_by_date() для заполнения category fields
5.7. Обновить get_all_transactions_for_period() для заполнения category fields
5.8. Написать unit тесты (3+ для ADJUSTMENT, 2 для category fields)

**Шаг 6 (дополнен): TransactionService**

6.1. УДАЛИТЬ параметр category (str)
6.2. ДОБАВИТЬ параметр category_id (int | None)
6.3. **ДОБАВИТЬ валидацию**: ADJUSTMENT + is_recurring = ValidationError
6.4. Написать unit тесты (3: category_id, ADJUSTMENT validation)

**Шаг 7 (уточнен): RecurringService**

7.1. Добавить category_id в VirtualTransaction TypedDict (в этом же файле)
7.2. Копировать category_id в create_exception()
7.3. Копировать category_id в generate_instances() (для virtual)
7.4. Написать unit тесты (2+)

**Шаг 8 (уточнен): DashboardService**

8.1. RecentTransaction: `category` -> `category_name`, добавить `category_icon`
8.2. Обновить get_recent_transactions() для JOIN с Category
8.3. Проверить что ADJUSTMENT не влияет на total_income/expense (уже так)
8.4. Написать unit тесты (2: category fields, ADJUSTMENT exclusion)

### TODO для production (документация)

Добавить комментарий в `app/models/database.py`:

```python
# TODO: При переходе в production использовать Alembic миграции
# вместо drop + create_all для изменения схемы БД.
# Текущий подход (пересоздание БД) допустим только для MVP/dev.
```

## Готовность к реализации

**Чеклист:**

- [x] Все замечания из critique-v2 учтены
- [x] Вопросы критика получили ответы
- [x] TypedDicts в правильном месте (`app/schema/`, не `app/types/`)
- [x] TransactionInfo включает category_id и category_name
- [x] VirtualTransaction включает category_id
- [x] RecentTransaction обновлен (category_name, category_icon)
- [x] ADJUSTMENT + recurring валидация определена
- [x] План реализации обновлен с учётом изменений
- [x] TODO для Alembic миграций добавлен

**Оценка времени:** 10-12 часов (без изменений от v2)

**Риски:** Низкие — все решения апробированы, паттерны соответствуют проекту

## Critical Files for Implementation

1. `/home/skytiger/PycharmProjects/FinFocus/app/models/database.py` — Core changes: Category model, TransactionType.ADJUSTMENT, Transaction.category_id FK, remove Transaction.category (String)

2. `/home/skytiger/PycharmProjects/FinFocus/app/services/calendar_service.py` — Add ADJUSTMENT handling in balance calculations, extend TransactionInfo TypedDict with category_id/category_name

3. `/home/skytiger/PycharmProjects/FinFocus/app/schema/goals.py` — Pattern to follow for TypedDicts structure (project uses app/schema/, not app/types/)

4. `/home/skytiger/PycharmProjects/FinFocus/app/components/transactions.py` — Category dropdown, type-change callback, table column with icon, filter checkbox

5. `/home/skytiger/PycharmProjects/FinFocus/app/services/transaction_service.py` — Replace category (str) with category_id (int), add ADJUSTMENT + recurring validation

---

## Полная архитектура (консолидация v2 + v3)

Для удобства реализации — полное описание решения включено ниже.

### Модель Category

```python
class Category(Base):
    """Модель категории операций."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(30), default="bi-tag")
    type = Column(String(10), nullable=False)  # "income" | "expense" | "both"
    is_system = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    transactions = relationship("Transaction", back_populates="category_rel")
```

### Предзаполненные категории

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
| Подарки другим | bi-gift | expense | False | 9 |
| Прочие расходы | bi-three-dots | expense | False | 10 |
| Зарплата | bi-briefcase | income | False | 101 |
| Подработка | bi-laptop | income | False | 102 |
| Инвестиции | bi-graph-up | income | False | 103 |
| Подарки полученные | bi-gift | income | False | 104 |
| Прочие доходы | bi-three-dots | income | False | 105 |

### План реализации (11 шагов)

1. **Модель данных** — Category, TransactionType.ADJUSTMENT, Transaction.category_id
2. **TypedDicts** — app/schema/categories.py
3. **CategoryService** — get_all, get_by_id, seed_default, get_for_dropdown
4. **ReconciliationService** — get_expected_balance, create_adjustment, get_preview
5. **CalendarService** — ADJUSTMENT handling, TransactionInfo category fields
6. **TransactionService** — category_id, ADJUSTMENT validation
7. **RecurringService** — VirtualTransaction.category_id, copy in exceptions
8. **DashboardService** — RecentTransaction.category_name/icon
9. **UI Transactions** — dropdown, callback, table column, filter
10. **UI Calendar** — reconciliation modal
11. **Integration** — exports, seed, tests, documentation
