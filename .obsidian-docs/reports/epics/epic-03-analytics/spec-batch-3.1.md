# Спецификация: Батч 3.1 — Категоризация + Сверка

**Версия**: 1.0
**Дата**: 2026-01-22
**Статус**: Утверждено, готово для /architect

---

## 1. Бизнес-контекст

### Проблема
Пользователь не понимает "куда уходят деньги". Без категоризации невозможна аналитика расходов.

### Решение
Добавить категории операций с "ленивым" подходом — категория опциональна, не блокирует ввод.

### Дополнительная проблема
При неполном учете (особенно наличка) баланс в календаре расходится с реальностью.

### Решение
Механизм "Сверка" — пользователь вводит фактический остаток, система создает корректирующую операцию.

---

## 2. Философия (КРИТИЧНО для архитектуры)

**FinFocus — про будущее (кассовый календарь), не про учет прошлого.**

- Категоризация = "примерная картина" для анализа
- Полный учет каждой копейки НЕ требуется
- "Без категории" — нормальное, валидное состояние
- Сверка = "ремонт модели", не ежедневная рутина

---

## 3. Принятые решения

| ID | Решение | Обоснование |
|----|---------|-------------|
| D012 | Тип ADJUSTMENT (не флаг) | Семантическая чистота, расширяемость |
| D013 | Category как модель | Справочник с метаданными, будущие кастомные категории |
| D014 | category_id nullable | Снижает барьер входа |
| D015 | Recurring → категория из шаблона | Один раз настроил — забыл |
| D016 | Сверка = модал на календаре | Быстрый UX, ясная семантика |

Детали: `decisions.md`

---

## 4. Модель данных

### 4.1 Новая модель: Category

```python
class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)        # "Еда", "Транспорт"
    icon = Column(String(30), default="bi-tag")      # Bootstrap icon
    type = Column(String(10), nullable=False)        # "income" / "expense" / "both"
    is_system = Column(Boolean, default=False)       # Нельзя удалить
    sort_order = Column(Integer, default=0)          # Порядок отображения

    # Relationships
    transactions = relationship("Transaction", back_populates="category")
```

### 4.2 Изменение: Transaction

```python
class Transaction(Base):
    # Существующие поля...

    # НОВОЕ: категория (nullable)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    category = relationship("Category", back_populates="transactions")
```

### 4.3 Изменение: TransactionType

```python
class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"  # НОВЫЙ тип
```

### 4.4 Предзаполненные категории

**Расходы (type="expense")**:
1. Еда и продукты (bi-cart)
2. Транспорт (bi-car-front)
3. Жилье и ЖКХ (bi-house)
4. Связь и интернет (bi-phone)
5. Здоровье (bi-heart-pulse)
6. Одежда (bi-bag)
7. Развлечения (bi-controller)
8. Образование (bi-book)
9. Подарки (bi-gift)
10. Прочие расходы (bi-three-dots)

**Доходы (type="income")**:
1. Зарплата (bi-briefcase)
2. Подработка (bi-laptop)
3. Инвестиции (bi-graph-up)
4. Подарки (bi-gift)
5. Прочие доходы (bi-three-dots)

**Системные (type="both", is_system=True)**:
1. Коррекция (bi-arrow-repeat) — для ADJUSTMENT по умолчанию

---

## 5. Изменения в сервисах

### 5.1 CalendarService

**Изменение в calculate_daily_balances():**
```python
# Текущая логика
if tx.transaction_type == TransactionType.INCOME:
    balance += tx.amount
elif tx.transaction_type == TransactionType.EXPENSE:
    balance -= tx.amount
# TRANSFER игнорируется

# ДОБАВИТЬ
elif tx.transaction_type == TransactionType.ADJUSTMENT:
    balance += tx.amount  # amount может быть отрицательным
```

### 5.2 RecurringService

**Изменение в generate_instances():**
- При создании инстанса копировать `category_id` из шаблона

### 5.3 Новый: CategoryService

```python
class CategoryService:
    def get_all(self, session, type_filter=None) -> list[Category]:
        """Получить все категории, опционально отфильтрованные по типу."""

    def get_by_id(self, session, category_id: int) -> Category | None:
        """Получить категорию по ID."""

    def seed_default_categories(self, session) -> None:
        """Создать предзаполненные категории (idempotent)."""
```

### 5.4 Новый: ReconciliationService

```python
class ReconciliationService:
    def get_expected_balance(self, session, user_id: int, date: date) -> Decimal:
        """Получить расчетный баланс на дату."""

    def create_adjustment(
        self,
        session,
        user_id: int,
        actual_balance: Decimal,
        expected_balance: Decimal,
        category_id: int | None = None  # По умолчанию "Коррекция"
    ) -> Transaction:
        """Создать корректирующую операцию."""
```

---

## 6. UI требования

### 6.1 Формы создания/редактирования транзакции

**Добавить поле "Категория":**
- Dropdown с категориями (отфильтрованными по типу операции)
- Placeholder: "Без категории"
- Позиция: после поля "Тип"

### 6.2 Модал сверки (на календаре)

**Триггер:** Кнопка "Сверка" рядом с балансом на сегодня

**Содержимое модала:**
```
┌─────────────────────────────────────┐
│ Сверка остатка                    X │
├─────────────────────────────────────┤
│                                     │
│ Расчетный остаток: 15 000 ₽        │
│                                     │
│ Фактический остаток:               │
│ ┌─────────────────────────────┐    │
│ │ 14200                       │    │
│ └─────────────────────────────┘    │
│                                     │
│ Разница: -800 ₽                    │
│                                     │
│ Категория: [Коррекция      ▼]      │
│                                     │
│ ┌─────────────────────────────┐    │
│ │   Создать корректировку     │    │
│ └─────────────────────────────┘    │
│                                     │
└─────────────────────────────────────┘
```

**Поведение:**
- При вводе суммы — показать разницу
- Если разница = 0 — кнопка disabled, текст "Остаток совпадает"
- При клике — создать ADJUSTMENT, закрыть модал, обновить календарь

### 6.3 Список транзакций

**Добавить:**
- Колонка "Категория" в таблице
- Фильтр "Без категории" (checkbox или dropdown)
- Отображение категории с иконкой

### 6.4 Отображение ADJUSTMENT

**В календаре:** Показывать как обычную операцию, но с пометкой (иконка или цвет)
**В списке:** Категория "Коррекция", можно изменить

---

## 7. НЕ в скоупе (Батч 3.2+)

- Account модель (несколько кошельков)
- Быстрые кнопки категорий в списке (chips)
- Режим "разобрать хвост" (bulk edit)
- Графики и диаграммы (отдельный батч)

---

## 8. Тестирование

### Unit тесты

**CategoryService:**
- get_all() возвращает категории
- get_all(type_filter="expense") фильтрует
- seed_default_categories() idempotent

**ReconciliationService:**
- create_adjustment() создает ADJUSTMENT с правильной суммой
- create_adjustment() со знаком (положительная/отрицательная разница)

**CalendarService:**
- calculate_daily_balances() корректно обрабатывает ADJUSTMENT
- ADJUSTMENT с отрицательным amount уменьшает баланс

**RecurringService:**
- generate_instances() копирует category_id

### Integration тесты

- Создание операции с категорией → отображается в списке
- Сверка → создается ADJUSTMENT → баланс обновляется
- Recurring с категорией → инстансы наследуют категорию

---

## 9. Миграция данных

**Существующие транзакции:** `category_id = NULL` (нормально)
**Seed категорий:** При запуске приложения вызвать `seed_default_categories()`

---

## 10. Файлы для изменения

### Модели
- `app/models/database.py` — Category модель, Transaction.category_id, TransactionType.ADJUSTMENT

### Сервисы
- `app/services/category_service.py` — НОВЫЙ
- `app/services/reconciliation_service.py` — НОВЫЙ
- `app/services/calendar_service.py` — обработка ADJUSTMENT
- `app/services/recurring_service.py` — копирование category_id
- `app/services/__init__.py` — экспорт новых сервисов

### UI
- `app/components/transactions.py` — поле категории в формах, колонка в таблице
- `app/components/calendar.py` — кнопка и модал сверки

### Тесты
- `tests/test_category_service.py` — НОВЫЙ
- `tests/test_reconciliation_service.py` — НОВЫЙ
- `tests/test_calendar_service.py` — тесты ADJUSTMENT
- `tests/test_recurring_service.py` — тесты category inheritance

### Скрипты
- `scripts/seed_categories.py` — опционально, или в init_database()

---

## 11. Acceptance Criteria

- [ ] Пользователь может создать операцию с категорией
- [ ] Пользователь может создать операцию БЕЗ категории
- [ ] Категория отображается в списке транзакций
- [ ] Фильтр "Без категории" работает
- [ ] Recurring операции наследуют категорию из шаблона
- [ ] Кнопка "Сверка" на календаре открывает модал
- [ ] Модал показывает расчетный баланс и принимает фактический
- [ ] При создании корректировки баланс в календаре обновляется
- [ ] ADJUSTMENT корректно влияет на баланс (+ и -)
- [ ] Все unit тесты проходят

---

**Готово для передачи в /architect**
