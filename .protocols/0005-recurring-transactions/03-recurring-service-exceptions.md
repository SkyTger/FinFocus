# Шаг 3: RecurringService — CRUD для exceptions

## Briefing
- **Цель:** Добавить в RecurringService методы для работы с exceptions: create_exception, skip_instance, stop_template, delete_template. Реализовать валидацию, транзакционность (savepoint) и логирование.
- **Ключевые файлы:**
  - `app/services/recurring_service.py` (расширить)
  - `tests/test_recurring_service.py` (расширить)
- **Additional info:**
  - Exception — обычная транзакция с `recurring_parent_id` и `original_date`
  - `stop_template` — soft delete (устанавливает `recurring_end_date`)
  - `delete_template` — hard delete (CASCADE удаляет все exceptions)
  - При изменении периода шаблона — удалять future exceptions (через savepoint)

## Sub-tasks

### 1. Добавить метод get_exceptions_for_template

```python
def get_exceptions_for_template(
    self,
    template_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Transaction]:
    """Получает exceptions для шаблона в заданном периоде.

    Args:
        template_id: ID шаблона.
        start_date: Начало периода (опционально).
        end_date: Конец периода (опционально).

    Returns:
        Список exceptions (транзакции с recurring_parent_id = template_id).
    """
    query = self.session.query(Transaction).filter(
        Transaction.recurring_parent_id == template_id
    )

    if start_date:
        query = query.filter(Transaction.original_date >= start_date)
    if end_date:
        query = query.filter(Transaction.original_date <= end_date)

    exceptions = query.order_by(Transaction.original_date).all()

    logger.debug(
        f"Найдено {len(exceptions)} exceptions для шаблона {template_id}"
    )
    return exceptions
```

### 2. Добавить метод create_exception

```python
def create_exception(
    self,
    template_id: int,
    original_date: date,
    new_amount: Decimal | None = None,
    new_date: date | None = None,
    new_description: str | None = None,
) -> Transaction:
    """Создает exception для конкретного экземпляра recurring операции.

    Args:
        template_id: ID шаблона.
        original_date: Исходная дата экземпляра, который заменяем.
        new_amount: Новая сумма (если None — берем из шаблона).
        new_date: Новая дата (если None — используем original_date).
        new_description: Новое описание (если None — берем из шаблона).

    Returns:
        Созданный exception (Transaction).

    Raises:
        ValidationError: Если шаблон не найден или original_date вне диапазона.
        IntegrityError: Если exception на эту дату уже существует.
    """
    from app.core.exceptions import ValidationError

    # Получаем шаблон
    template = self.session.query(Transaction).get(template_id)
    if not template or not template.is_recurring:
        raise ValidationError(f"Шаблон {template_id} не найден или не является recurring")

    # Валидация: original_date должна быть в диапазоне шаблона
    if original_date < template.transaction_date:
        raise ValidationError(
            f"original_date ({original_date}) раньше начала серии ({template.transaction_date})"
        )

    if template.recurring_end_date and original_date > template.recurring_end_date:
        raise ValidationError(
            f"original_date ({original_date}) позже окончания серии ({template.recurring_end_date})"
        )

    # Проверяем, существует ли уже exception
    existing = (
        self.session.query(Transaction)
        .filter(
            Transaction.recurring_parent_id == template_id,
            Transaction.original_date == original_date,
        )
        .first()
    )

    if existing:
        logger.info(
            f"Exception для шаблона {template_id} на дату {original_date} уже существует"
        )
        # Обновляем существующий
        if new_amount is not None:
            existing.amount = new_amount
        if new_date is not None:
            existing.transaction_date = new_date
        if new_description is not None:
            existing.description = new_description
        existing.is_skipped = False  # Снимаем пропуск если был
        self.session.flush()
        return existing

    # Создаем новый exception
    exception = Transaction(
        user_id=template.user_id,
        amount=new_amount if new_amount is not None else template.amount,
        transaction_type=template.transaction_type,
        transaction_date=new_date if new_date is not None else original_date,
        description=new_description if new_description is not None else template.description,
        is_recurring=False,
        recurring_parent_id=template_id,
        original_date=original_date,
        is_skipped=False,
    )

    self.session.add(exception)
    self.session.flush()

    logger.info(
        f"Создан exception {exception.id} для шаблона {template_id} "
        f"на дату {original_date}"
    )

    return exception
```

### 3. Добавить метод skip_instance

```python
def skip_instance(self, template_id: int, original_date: date) -> Transaction:
    """Пропускает конкретный экземпляр recurring операции.

    Args:
        template_id: ID шаблона.
        original_date: Дата экземпляра, который пропускаем.

    Returns:
        Созданный/обновленный exception с is_skipped=True.
    """
    from app.core.exceptions import ValidationError

    # Получаем шаблон
    template = self.session.query(Transaction).get(template_id)
    if not template or not template.is_recurring:
        raise ValidationError(f"Шаблон {template_id} не найден или не является recurring")

    # Проверяем существующий exception
    existing = (
        self.session.query(Transaction)
        .filter(
            Transaction.recurring_parent_id == template_id,
            Transaction.original_date == original_date,
        )
        .first()
    )

    if existing:
        existing.is_skipped = True
        self.session.flush()
        logger.info(f"Exception {existing.id} помечен как пропущенный")
        return existing

    # Создаем новый exception с is_skipped=True
    exception = Transaction(
        user_id=template.user_id,
        amount=template.amount,
        transaction_type=template.transaction_type,
        transaction_date=original_date,
        description=template.description,
        is_recurring=False,
        recurring_parent_id=template_id,
        original_date=original_date,
        is_skipped=True,
    )

    self.session.add(exception)
    self.session.flush()

    logger.info(
        f"Создан пропущенный exception {exception.id} для шаблона {template_id} "
        f"на дату {original_date}"
    )

    return exception
```

### 4. Добавить метод stop_template (soft delete)

```python
def stop_template(
    self,
    template_id: int,
    stop_date: date | None = None,
) -> Transaction:
    """Останавливает recurring серию (soft delete).

    Устанавливает recurring_end_date. Не удаляет шаблон или exceptions.

    Args:
        template_id: ID шаблона.
        stop_date: Дата остановки (по умолчанию — вчера).

    Returns:
        Обновленный шаблон.
    """
    from app.core.exceptions import ValidationError

    template = self.session.query(Transaction).get(template_id)
    if not template or not template.is_recurring:
        raise ValidationError(f"Шаблон {template_id} не найден или не является recurring")

    effective_stop_date = stop_date if stop_date else date.today() - timedelta(days=1)

    template.recurring_end_date = effective_stop_date
    self.session.flush()

    logger.info(
        f"Шаблон {template_id} остановлен с даты {effective_stop_date}"
    )

    return template
```

### 5. Добавить метод delete_template (hard delete)

```python
def delete_template(self, template_id: int) -> bool:
    """Полностью удаляет recurring шаблон и все его exceptions (hard delete).

    Args:
        template_id: ID шаблона.

    Returns:
        True если удаление успешно.

    Raises:
        ValidationError: Если шаблон не найден.
    """
    from app.core.exceptions import ValidationError

    template = self.session.query(Transaction).get(template_id)
    if not template or not template.is_recurring:
        raise ValidationError(f"Шаблон {template_id} не найден или не является recurring")

    # CASCADE удалит все exceptions автоматически
    self.session.delete(template)
    self.session.flush()

    logger.info(
        f"Шаблон {template_id} и все его exceptions удалены"
    )

    return True
```

### 6. Добавить метод update_template_period (с savepoint)

```python
def update_template_period(
    self,
    template_id: int,
    new_period: str,
) -> Transaction:
    """Изменяет период повторения шаблона.

    При изменении периода удаляются все future exceptions (транзакционно).

    Args:
        template_id: ID шаблона.
        new_period: Новый период (weekly, biweekly, monthly, quarterly).

    Returns:
        Обновленный шаблон.
    """
    from app.core.exceptions import ValidationError

    if new_period not in VALID_RECURRING_PERIODS:
        raise ValidationError(f"Недопустимый период: {new_period}")

    template = self.session.query(Transaction).get(template_id)
    if not template or not template.is_recurring:
        raise ValidationError(f"Шаблон {template_id} не найден")

    # Savepoint для атомарности
    with self.session.begin_nested():
        # Удаляем future exceptions
        today = date.today()
        deleted_count = (
            self.session.query(Transaction)
            .filter(
                Transaction.recurring_parent_id == template_id,
                Transaction.original_date > today,
            )
            .delete(synchronize_session="fetch")
        )

        template.recurring_period = new_period

        logger.info(
            f"Шаблон {template_id}: период изменен на {new_period}, "
            f"удалено {deleted_count} future exceptions"
        )

    self.session.flush()
    return template
```

### 7. Добавить метод get_instances_with_exceptions

```python
def get_instances_with_exceptions(
    self,
    user_id: int,
    start_date: date,
    end_date: date,
) -> list[VirtualTransaction | Transaction]:
    """Получает все экземпляры recurring операций с учетом exceptions.

    Объединяет:
    - Виртуальные экземпляры из шаблонов
    - Заменяет их на exceptions где есть

    Args:
        user_id: ID пользователя.
        start_date: Начало периода.
        end_date: Конец периода.

    Returns:
        Список экземпляров (VirtualTransaction или Transaction).
    """
    templates = self.get_templates_for_user(user_id)

    # Собираем все exceptions в словарь (template_id, original_date) -> exception
    all_exceptions: dict[tuple[int, date], Transaction] = {}
    for template in templates:
        exceptions = self.get_exceptions_for_template(
            template.id, start_date, end_date
        )
        for exc in exceptions:
            all_exceptions[(template.id, exc.original_date)] = exc

    results: list[VirtualTransaction | Transaction] = []

    for template in templates:
        virtual_instances = self.generate_instances(template, start_date, end_date)

        for vi in virtual_instances:
            instance_date = date.fromisoformat(vi["instance_date"])
            key = (template.id, instance_date)

            if key in all_exceptions:
                exc = all_exceptions[key]
                if not exc.is_skipped:
                    # Возвращаем exception вместо виртуального
                    results.append(exc)
                # Если is_skipped=True, не добавляем ничего
            else:
                # Возвращаем виртуальный экземпляр
                results.append(vi)

    logger.debug(
        f"get_instances_with_exceptions: {len(results)} экземпляров "
        f"для пользователя {user_id} в периоде {start_date} - {end_date}"
    )

    return results
```

### 8. Расширить unit тесты

Добавить в `tests/test_recurring_service.py`:

1. **test_create_exception_new** — создание нового exception
2. **test_create_exception_update_existing** — обновление существующего
3. **test_create_exception_invalid_date** — original_date вне диапазона
4. **test_skip_instance_new** — пропуск нового экземпляра
5. **test_skip_instance_existing** — пропуск существующего exception
6. **test_stop_template** — soft delete
7. **test_delete_template_cascades** — hard delete с CASCADE
8. **test_update_template_period_deletes_future** — удаление future exceptions
9. **test_get_instances_with_exceptions_replaces** — замена виртуальных на exceptions
10. **test_get_instances_with_exceptions_skips** — пропуск is_skipped

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-8.
2. **Верификация:** После завершения ВСЕХ подзадач запусти:
   - `black app/services/recurring_service.py tests/test_recurring_service.py`
   - `flake8 app/services/recurring_service.py tests/test_recurring_service.py`
   - `pytest tests/test_recurring_service.py -v`
3. **Фиксация:** После успешной верификации:
   - **Добавь запись в `log.md`**: Опиши CRUD методы и транзакционность.
   - **Обнови `context.md`**: Увеличь `Current Step` на 1.
   - Проверь ветку main.
4. **Сделай коммит**: `git add . && git commit -m "feat(services): add exceptions CRUD to RecurringService [protocol-0005/03]"`. Сделай пуш.
5. **Отчет пользователю** по установленному формату.
