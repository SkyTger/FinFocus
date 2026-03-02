# Шаг 2: TransactionService extensions

## Briefing
- **Цель:** Расширить TransactionService методами bulk_update_category() и export_to_csv() для массовых операций и экспорта данных.
- **Ключевые файлы:**
  - `app/services/transaction_service.py` (модифицировать) — добавить 2 метода + константу
  - `tests/test_transaction_service.py` (модифицировать) — добавить 8+ тестов
- **Additional info:**
  - MAX_BULK_UPDATE_SIZE = 100 — лимит для bulk операций (NFR2: <500ms)
  - bulk_update_category ОБЯЗАТЕЛЬНО валидирует user_id (ownership check)
  - export_to_csv возвращает bytes с UTF-8 BOM для Excel совместимости
  - Использовать bulk UPDATE WHERE id IN (...) AND user_id = :user_id

## Sub-tasks

### 1. Добавить константу и метод bulk_update_category

**Файл:** `app/services/transaction_service.py`

```python
MAX_BULK_UPDATE_SIZE: int = 100  # NFR2: <500ms для bulk update


class TransactionService:
    # ... existing methods ...

    def bulk_update_category(
        self,
        session: Session,
        user_id: int,
        transaction_ids: list[int],
        category_id: int | None,
    ) -> int:
        """Массовое обновление категории для списка транзакций.

        Args:
            session: SQLAlchemy session.
            user_id: ID пользователя (для валидации ownership).
            transaction_ids: Список ID транзакций (max 100).
            category_id: ID новой категории (или None для сброса).

        Returns:
            Количество обновленных записей.

        Raises:
            ValidationError:
                - Если len(transaction_ids) > MAX_BULK_UPDATE_SIZE
                - Если не все транзакции принадлежат пользователю
                - Если category_id не существует (при category_id != None)
        """
        # 1. Валидация размера
        if len(transaction_ids) > MAX_BULK_UPDATE_SIZE:
            raise ValidationError(f"Максимум {MAX_BULK_UPDATE_SIZE} операций за раз")

        if not transaction_ids:
            return 0

        # 2. Валидация category_id (если указан)
        if category_id is not None:
            category = session.query(Category).filter_by(id=category_id).first()
            if not category:
                raise ValidationError(f"Категория с ID {category_id} не найдена")

        # 3. Bulk UPDATE с проверкой ownership
        affected = (
            session.query(Transaction)
            .filter(
                Transaction.id.in_(transaction_ids),
                Transaction.user_id == user_id,
                Transaction.is_recurring == False,  # Не обновлять шаблоны
            )
            .update({"category_id": category_id}, synchronize_session=False)
        )

        # 4. Проверка что все транзакции обновлены
        if affected != len(transaction_ids):
            raise ValidationError(
                f"Не все операции принадлежат пользователю или являются шаблонами "
                f"(запрошено: {len(transaction_ids)}, обновлено: {affected})"
            )

        session.flush()
        return affected
```

### 2. Добавить метод export_to_csv

```python
import csv
import io
from datetime import date


class TransactionService:
    # ... existing methods ...

    def export_to_csv(
        self,
        session: Session,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: int | None = None,
        uncategorized_only: bool = False,
    ) -> bytes:
        """Генерирует CSV для экспорта.

        Args:
            session: SQLAlchemy session.
            user_id: ID пользователя.
            start_date: Фильтр начала периода.
            end_date: Фильтр конца периода.
            category_id: Фильтр по категории.
            uncategorized_only: Только без категории.

        Returns:
            CSV как bytes с UTF-8 BOM для Excel.
            Формат: Дата,Тип,Сумма,Описание,Категория
        """
        # 1. Построение запроса
        query = (
            session.query(Transaction, Category)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_recurring == False,  # Исключить шаблоны
            )
        )

        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if uncategorized_only:
            query = query.filter(Transaction.category_id.is_(None))

        query = query.order_by(Transaction.date.desc())

        # 2. Генерация CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Дата", "Тип", "Сумма", "Описание", "Категория"])

        # Data
        type_labels = {
            TransactionType.INCOME: "Доход",
            TransactionType.EXPENSE: "Расход",
            TransactionType.TRANSFER: "Перевод",
            TransactionType.ADJUSTMENT: "Корректировка",
        }

        for tx, category in query.all():
            writer.writerow([
                tx.date.strftime("%Y-%m-%d"),
                type_labels.get(tx.transaction_type, str(tx.transaction_type)),
                str(tx.amount),
                tx.description or "",
                category.name if category else "Без категории",
            ])

        # 3. UTF-8 BOM + encode
        csv_content = output.getvalue()
        return b"\xef\xbb\xbf" + csv_content.encode("utf-8")
```

### 3. Добавить импорты

В начало файла добавить:
```python
import csv
import io
from app.models.database import Category
```

### 4. Написать unit тесты

**Файл:** `tests/test_transaction_service.py`

Добавить тесты:

1. `test_bulk_update_category_success` — успешное обновление 5 транзакций
2. `test_bulk_update_validates_ownership` — проверка что user_id валидируется
3. `test_bulk_update_rejects_foreign_transactions` — ValidationError если транзакция чужая
4. `test_bulk_update_exceeds_limit` — ValidationError при >100 записях
5. `test_bulk_update_invalid_category` — ValidationError при несуществующей категории
6. `test_bulk_update_excludes_recurring_templates` — шаблоны (is_recurring=True) не обновляются
7. `test_export_csv_utf8_bom` — проверка что результат начинается с BOM
8. `test_export_csv_with_filters` — проверка фильтров start_date, end_date
9. `test_export_csv_uncategorized_only` — проверка фильтра uncategorized_only
10. `test_export_csv_correct_format` — проверка формата и заголовков

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи.

2.  **Базовая проверка:**
    ```bash
    source .venv/bin/activate
    python -m py_compile app/services/transaction_service.py tests/test_transaction_service.py
    ```

3.  **Фиксация:**
    - **Добавь запись в `log.md`**
    - **Обнови `context.md`**: Current Step = 3
    - Проверь ветку main

4.  **Сделай коммит:**
    ```bash
    git add app/services/transaction_service.py tests/test_transaction_service.py .protocols/
    git commit -m "feat(transactions): add bulk_update_category and export_to_csv [protocol-0010/02]"
    git push
    ```

5.  **Отчет пользователю** в установленном формате.
