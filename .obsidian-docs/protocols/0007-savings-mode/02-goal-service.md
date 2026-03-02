# Шаг 2: GoalService расширение

## Briefing
- **Цель:** Добавить методы для работы с `savings_mode` пользователя: получение текущего режима и обновление с валидацией.
- **Ключевые файлы:**
  - `app/services/goal_service.py` (модифицировать — добавить методы)
  - `app/services/__init__.py` (модифицировать — экспорт константы)
  - `tests/test_savings_mode.py` (создать — тесты методов)
- **Additional info:**
  - Методы работают с User, но размещаются в GoalService (TODO о переносе в UserService)
  - Валидация через константу `VALID_SAVINGS_MODES = {"free", "medium", "strict"}`
  - Паттерн аналогичен `get_savings_budget()` / `update_savings_budget()`

## Sub-tasks

1. **Добавить константу VALID_SAVINGS_MODES:**
   - В начале `app/services/goal_service.py` после импортов добавить:
     ```python
     VALID_SAVINGS_MODES = {"free", "medium", "strict"}
     ```

2. **Добавить метод get_savings_mode():**
   - Получает `user.savings_mode` по `user_id`
   - Возвращает `str` ("free", "medium", "strict")
   - Raises `ValidationError` если пользователь не найден

3. **Добавить метод update_savings_mode():**
   - Принимает `user_id: int` и `mode: str`
   - Валидирует `mode` через `VALID_SAVINGS_MODES`
   - Raises `ValidationError` если mode невалидный или user не найден
   - Вызывает `session.flush()` (caller управляет commit)

4. **Обновить экспорты:**
   - В `app/services/__init__.py` добавить `VALID_SAVINGS_MODES` в экспорт

5. **Написать unit тесты:**
   - Создать `tests/test_savings_mode.py`
   - `test_get_savings_mode_default` — проверяет что default="free"
   - `test_get_savings_mode_user_not_found` — проверяет ValidationError
   - `test_update_savings_mode_success` — проверяет успешное обновление
   - `test_update_savings_mode_invalid_mode` — проверяет ValidationError для невалидного mode

## Workflow (Порядок работы)

**Твоя задача — выполнить `Sub-tasks` выше, строго следуя этому циклу.**

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:**
   - `python -m py_compile app/services/goal_service.py`
   - `python -m py_compile app/services/__init__.py`
   - `python -m py_compile tests/test_savings_mode.py`

3. **Фиксация:**
   - **Добавь запись в `log.md`**: Опиши добавленные методы и их сигнатуры.
   - **Обнови `context.md`**: `Current Step` на 3, подготовь `Next Action` для Шага 3.
   - Проверь ветку main.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(service): add savings_mode methods to GoalService [protocol-0007/02]"
   ```
   Сделай пуш.

5. **Отчет пользователю.**

## Детали реализации

### Метод get_savings_mode()
```python
def get_savings_mode(self, session: Session, user_id: int) -> str:
    """Получает режим накоплений пользователя.

    Args:
        session: SQLAlchemy session.
        user_id: ID пользователя.

    Returns:
        str: "free", "medium" или "strict"

    Raises:
        ValidationError: Если пользователь не найден.
    """
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValidationError(f"Пользователь с ID {user_id} не найден")
    return user.savings_mode
```

### Метод update_savings_mode()
```python
def update_savings_mode(self, session: Session, user_id: int, mode: str) -> None:
    """Обновляет режим накоплений пользователя.

    Args:
        session: SQLAlchemy session.
        user_id: ID пользователя.
        mode: Новый режим ("free", "medium", "strict").

    Raises:
        ValidationError: Если пользователь не найден или mode невалидный.
    """
    if mode not in VALID_SAVINGS_MODES:
        raise ValidationError(
            f"Недопустимый режим накоплений: {mode}. "
            f"Допустимые значения: {', '.join(sorted(VALID_SAVINGS_MODES))}"
        )

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValidationError(f"Пользователь с ID {user_id} не найден")

    user.savings_mode = mode
    session.flush()
```

### TODO комментарий (добавить перед методами)
```python
# TODO: Перенести методы работы с User (get/update_savings_mode, get/update_savings_budget)
# в отдельный UserService при рефакторинге. Временно размещены здесь для MVP.
```
