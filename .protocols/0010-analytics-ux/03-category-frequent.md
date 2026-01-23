# Шаг 3: CategoryService extension

## Briefing
- **Цель:** Добавить метод get_frequent_for_type() для получения часто используемых категорий пользователя (для chips UI).
- **Ключевые файлы:**
  - `app/services/category_service.py` (модифицировать) — добавить метод
  - `tests/test_category_service.py` (модифицировать) — добавить 4+ теста
- **Additional info:**
  - Сортировка по частоте использования (COUNT transactions WHERE user_id=X GROUP BY category_id)
  - Fallback на sort_order если у пользователя < 3 транзакций с категориями
  - MIN_TRANSACTIONS_FOR_FREQUENCY = 3

## Sub-tasks

### 1. Добавить константу и метод

**Файл:** `app/services/category_service.py`

```python
from sqlalchemy import func

MIN_TRANSACTIONS_FOR_FREQUENCY: int = 3  # Fallback если < 3 транзакций


class CategoryService:
    # ... existing methods ...

    def get_frequent_for_type(
        self,
        session: Session,
        user_id: int,
        category_type: str,  # "income" | "expense"
        limit: int = 6,
    ) -> list[CategoryOption]:
        """Получить часто используемые категории пользователя.

        Сортировка по частоте использования (COUNT transactions WHERE user_id=X).

        Args:
            session: SQLAlchemy session.
            user_id: ID пользователя.
            category_type: Тип категории для фильтрации ("income" | "expense").
            limit: Максимальное количество (default 6 для chips).

        Returns:
            Список CategoryOption отсортированный по частоте DESC.

        Fallback:
            Если у пользователя < MIN_TRANSACTIONS_FOR_FREQUENCY транзакций
            с категориями данного типа, возвращает top-N по sort_order.
        """
        from app.models.database import Transaction, Category

        # 1. Подсчет транзакций с категориями данного типа у пользователя
        user_tx_count = (
            session.query(func.count(Transaction.id))
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Category.type == category_type,
            )
            .scalar()
        )

        # 2. Fallback если мало данных
        if user_tx_count < MIN_TRANSACTIONS_FOR_FREQUENCY:
            # Вернуть top-N по sort_order
            categories = (
                session.query(Category)
                .filter(Category.type == category_type)
                .order_by(Category.sort_order)
                .limit(limit)
                .all()
            )
            return [
                CategoryOption(
                    id=cat.id,
                    name=cat.name,
                    icon=cat.icon,
                    type=cat.type,
                )
                for cat in categories
            ]

        # 3. Основной запрос: категории отсортированные по частоте
        frequency_query = (
            session.query(
                Category,
                func.count(Transaction.id).label("tx_count"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Category.type == category_type,
            )
            .group_by(Category.id)
            .order_by(func.count(Transaction.id).desc())
            .limit(limit)
        )

        return [
            CategoryOption(
                id=cat.id,
                name=cat.name,
                icon=cat.icon,
                type=cat.type,
            )
            for cat, _ in frequency_query.all()
        ]
```

### 2. Добавить импорт func

В начало файла убедиться что есть:
```python
from sqlalchemy import func
```

### 3. Экспортировать константу

**Файл:** `app/services/__init__.py`

Добавить в импорты:
```python
from app.services.category_service import MIN_TRANSACTIONS_FOR_FREQUENCY
```

И в `__all__` добавить `"MIN_TRANSACTIONS_FOR_FREQUENCY"`.

### 4. Написать unit тесты

**Файл:** `tests/test_category_service.py`

Добавить тесты:

1. `test_get_frequent_returns_top_by_usage` — создать транзакции с разными категориями, проверить сортировку по частоте
2. `test_get_frequent_fallback_to_sort_order` — при < 3 транзакциях возвращает по sort_order
3. `test_get_frequent_filters_by_type` — income категории не попадают в expense запрос
4. `test_get_frequent_respects_limit` — проверка что limit работает корректно

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи.

2.  **Базовая проверка:**
    ```bash
    source .venv/bin/activate
    python -m py_compile app/services/category_service.py tests/test_category_service.py
    ```

3.  **Фиксация:**
    - **Добавь запись в `log.md`**
    - **Обнови `context.md`**: Current Step = 4
    - Проверь ветку main

4.  **Сделай коммит:**
    ```bash
    git add app/services/category_service.py app/services/__init__.py tests/test_category_service.py .protocols/
    git commit -m "feat(categories): add get_frequent_for_type for chips UI [protocol-0010/03]"
    git push
    ```

5.  **Отчет пользователю** в установленном формате.
