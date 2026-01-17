# Шаг 2: Унификация контрактов — ValidationError + add_contribution

## Briefing
- **Цель:** Создать единый класс ValidationError в app/core/exceptions.py. Исправить GoalService.add_contribution() для создания записей GoalContribution (data integrity). Обновить импорты во всех сервисах.
- **Ключевые файлы:**
  - `app/core/exceptions.py` (создать)
  - `app/core/__init__.py` (обновить)
  - `app/services/transaction_service.py` (модифицировать)
  - `app/services/goal_service.py` (модифицировать)
  - `app/services/__init__.py` (модифицировать)
- **Additional info:**
  - ValidationError получает опциональное поле `field` для указания проблемного поля формы
  - add_contribution() должен создавать GoalContribution + обновлять current_amount
  - Добавить логирование операций через loguru

## Sub-tasks

### 1. Создать app/core/exceptions.py
```python
"""Единые исключения приложения."""


class ValidationError(Exception):
    """Ошибка валидации бизнес-правил.

    Используется для сообщения об ошибках валидации пользователю.

    Attributes:
        message: Текст ошибки на русском языке
        field: Имя поля с ошибкой (опционально)
    """

    def __init__(self, message: str, field: str | None = None):
        """Инициализирует ошибку валидации.

        Args:
            message: Текст ошибки
            field: Имя поля с ошибкой (для подсветки в UI)
        """
        self.message = message
        self.field = field
        super().__init__(message)

    def __str__(self) -> str:
        if self.field:
            return f"[{self.field}] {self.message}"
        return self.message
```

### 2. Обновить app/core/__init__.py
- Добавить импорт и экспорт `ValidationError` из `exceptions`

### 3. Обновить app/services/transaction_service.py
- Удалить локальный класс `ValidationError`
- Добавить импорт: `from app.core import ValidationError`
- Заменить относительный импорт `from models.database` на `from app.models.database`
- Добавить импорт логгера: `from loguru import logger`
- Добавить логирование в методы CRUD:
  - `create_transaction`: `logger.info(f"Создана транзакция {transaction.id} для user {user_id}")`
  - `update_transaction`: `logger.info(f"Обновлена транзакция {transaction_id}")`
  - `delete_transaction`: `logger.info(f"Удалена транзакция {transaction_id}")`
- Обновить type hints: `str = None` → `str | None = None`

### 4. Обновить app/services/goal_service.py
- Удалить локальный класс `ValidationError`
- Добавить импорт: `from app.core import ValidationError`
- Заменить относительный импорт на `from app.models.database`
- Добавить импорт логгера и GoalContribution: `from loguru import logger`, `from app.models.database import GoalContribution`
- **Исправить метод add_contribution():**
```python
def add_contribution(
    self,
    goal_id: int,
    amount: Decimal,
    contribution_date: date | None = None,
    description: str | None = None
) -> Goal:
    """Добавляет взнос в цель с созданием записи GoalContribution.

    Args:
        goal_id: ID цели
        amount: Сумма взноса
        contribution_date: Дата взноса (по умолчанию сегодня)
        description: Описание взноса

    Returns:
        Goal: Обновленная цель

    Raises:
        ValidationError: Если amount <= 0 или цель не найдена
    """
    if amount <= 0:
        raise ValidationError("Сумма взноса должна быть больше 0", field="amount")

    goal = self.session.get(Goal, goal_id)
    if not goal:
        raise ValidationError(f"Цель с ID {goal_id} не найдена")

    # Создаём запись взноса
    contribution = GoalContribution(
        goal_id=goal_id,
        amount=amount,
        contribution_date=contribution_date or date.today(),
        description=description
    )
    self.session.add(contribution)

    # Обновляем текущую сумму цели
    goal.current_amount += amount

    # Автоматически завершаем цель если достигнута
    if goal.is_completed:
        goal.status = GoalStatus.COMPLETED
        logger.info(f"Цель {goal_id} '{goal.name}' достигнута!")

    self.session.flush()
    logger.info(f"Добавлен взнос {amount} в цель {goal_id}, текущая сумма: {goal.current_amount}")
    return goal
```
- Добавить логирование в другие методы CRUD

### 5. Обновить app/services/__init__.py
```python
"""Сервисный слой приложения."""

from app.core import ValidationError
from .goal_service import GoalService
from .transaction_service import TransactionService

__all__ = ['GoalService', 'TransactionService', 'ValidationError']
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 1-5.
2.  **Верификация:**
    - `python -m py_compile app/core/exceptions.py app/services/transaction_service.py app/services/goal_service.py`
    - `python run.py` — приложение запускается
    - В Python REPL проверить:
    ```python
    from app.core import get_db_session, ValidationError
    from app.services import GoalService
    # Проверить что ValidationError один класс
    from app.services.transaction_service import ValidationError as VE1
    from app.services.goal_service import ValidationError as VE2
    assert VE1 is VE2  # Должно быть True (один класс)
    ```
3.  **Фиксация:**
    - Добавь запись в `log.md`
    - Обнови `context.md`: `Current Step` → 3
    - Проверь ветку main
4.  **Коммит**: `git add . && git commit -m "refactor(services): unify ValidationError, fix add_contribution [protocol-0001/02]"`. Push.
5.  **Отчет пользователю** в установленном формате.
