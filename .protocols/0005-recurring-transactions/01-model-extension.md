# Шаг 1: Расширение модели Transaction

## Briefing
- **Цель:** Добавить в модель Transaction поля для поддержки recurring операций: `recurring_end_date`, `recurring_parent_id`, `original_date`, `is_skipped`. Создать UniqueConstraint для предотвращения дубликатов exceptions. Добавить property `anchor_day` с guard clause.
- **Ключевые файлы:**
  - `app/models/database.py` (изменить)
  - `tests/test_models.py` (создать/расширить)
- **Additional info:**
  - Существующие поля `is_recurring` и `recurring_period` уже есть в модели
  - `recurring_parent_id` — FK на саму таблицу Transaction (self-referential)
  - `anchor_day` — вычисляемое свойство, возвращает день месяца из `transaction_date`

## Sub-tasks

### 1. Добавить новые поля в модель Transaction

В файле `app/models/database.py` добавить следующие поля в класс `Transaction`:

```python
# Recurring fields (дополнительные)
recurring_end_date = Column(Date, nullable=True)  # Дата окончания серии (None = бессрочно)
recurring_parent_id = Column(
    Integer,
    ForeignKey("transactions.id", ondelete="CASCADE"),
    nullable=True
)  # FK на шаблон (для exceptions)
original_date = Column(Date, nullable=True)  # Исходная дата экземпляра (для exceptions)
is_skipped = Column(Boolean, default=False, nullable=False)  # Пропущен ли экземпляр
```

### 2. Добавить relationship для parent/children

```python
# Self-referential relationship
recurring_parent = relationship(
    "Transaction",
    remote_side=[id],
    backref="recurring_exceptions"
)
```

### 3. Добавить UniqueConstraint

В `__table_args__` добавить:

```python
__table_args__ = (
    UniqueConstraint(
        "recurring_parent_id",
        "original_date",
        name="uq_recurring_exception_date"
    ),
)
```

### 4. Добавить property anchor_day с guard clause

```python
@property
def anchor_day(self) -> int | None:
    """День месяца для Anchored-алгоритма.

    Только для шаблонов (is_recurring=True).
    Возвращает день из transaction_date (start_date серии).

    GUARD CLAUSE: Если is_recurring=True, но transaction_date=None,
    логируем ошибку и возвращаем None (data integrity issue).
    """
    if not self.is_recurring:
        return None

    # Guard: проверяем transaction_date для recurring шаблона
    if self.transaction_date is None:
        from loguru import logger
        logger.error(
            f"Data integrity issue: Transaction {self.id} имеет "
            f"is_recurring=True, но transaction_date=None. "
            f"Это не должно происходить - проверьте данные."
        )
        return None

    return self.transaction_date.day
```

### 5. Добавить property is_exception

```python
@property
def is_exception(self) -> bool:
    """Является ли транзакция исключением из recurring серии."""
    return self.recurring_parent_id is not None
```

### 6. Добавить индексы для оптимизации

В `__table_args__`:

```python
Index("ix_transaction_recurring_parent", "recurring_parent_id"),
Index("ix_transaction_is_recurring", "is_recurring"),
```

### 7. Написать unit тесты

Создать/расширить `tests/test_models.py` с тестами:

1. **test_transaction_anchor_day_for_recurring** — проверка anchor_day для recurring=True
2. **test_transaction_anchor_day_for_non_recurring** — проверка anchor_day=None для recurring=False
3. **test_transaction_anchor_day_guard_clause** — проверка guard clause (is_recurring=True, date=None)
4. **test_transaction_is_exception_property** — проверка is_exception
5. **test_transaction_recurring_relationship** — проверка parent/children relationship
6. **test_unique_constraint_exception_date** — проверка UniqueConstraint (IntegrityError при дубликате)

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-7.
2. **Верификация:** После завершения ВСЕХ подзадач запусти:
   - `black app/models/database.py tests/test_models.py`
   - `flake8 app/models/database.py tests/test_models.py`
   - `pytest tests/test_models.py -v`
   - Исправляй все ошибки, пока проверки не станут "зелеными".
3. **Фиксация:** После успешной верификации:
   - **Добавь запись в `log.md`**: Опиши добавленные поля и решения.
   - **Обнови `context.md`**: Увеличь `Current Step` на 1 и подготовь `Next Action` для Шага 2.
   - Проверь ветку main в поисках случайно добавленных файлов.
4. **Сделай коммит**: `git add . && git commit -m "feat(models): add recurring fields to Transaction [protocol-0005/01]"`. Сделай пуш.
5. **Отчет пользователю** по установленному формату.
