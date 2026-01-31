# Шаг 3: OnboardingService

## Briefing

- **Цель:** Создать сервис с методами get_status, complete_with_balance, skip
- **Ключевые файлы:**
  - `app/services/onboarding_service.py` — NEW
  - `app/services/__init__.py` — экспорт
- **Доп. информация:**
  - flush/commit contract: методы делают flush(), caller отвечает за commit()
  - Документировать в class docstring

## Sub-tasks

1. **Создать OnboardingService** (`app/services/onboarding_service.py`):
   ```python
   """Сервис управления онбордингом пользователя."""
   from decimal import Decimal
   from sqlalchemy.orm import Session

   from app.models.database import User
   from app.schema import OnboardingStatus


   class OnboardingService:
       """Сервис управления онбордингом пользователя.

       Предоставляет методы для проверки и завершения процесса онбординга.

       Note:
           Методы модификации (complete_with_balance, skip) делают flush(),
           но НЕ commit. Caller отвечает за вызов session.commit() или
           rollback() для завершения транзакции.

       Example:
           with get_db_session() as session:
               service = OnboardingService(session)
               service.complete_with_balance(user_id=1, starting_balance=Decimal("10000"))
               session.commit()  # Caller делает commit!
       """

       def __init__(self, session: Session) -> None:
           self.session = session

       def get_status(self, user_id: int) -> OnboardingStatus:
           """Получить статус онбординга пользователя."""
           user = self.session.get(User, user_id)
           if not user:
               raise ValueError(f"User {user_id} not found")

           return OnboardingStatus(
               first_launch=user.first_launch,
               starting_balance=user.starting_balance,
               needs_balance_alert=user.starting_balance == Decimal("0"),
           )

       def complete_with_balance(
           self, user_id: int, starting_balance: Decimal
       ) -> None:
           """Завершить онбординг с указанным балансом."""
           user = self.session.get(User, user_id)
           if not user:
               raise ValueError(f"User {user_id} not found")

           user.starting_balance = starting_balance
           user.first_launch = False
           self.session.flush()

       def skip(self, user_id: int) -> None:
           """Пропустить онбординг (баланс остается 0)."""
           user = self.session.get(User, user_id)
           if not user:
               raise ValueError(f"User {user_id} not found")

           user.first_launch = False
           self.session.flush()
   ```

2. **Экспортировать** в `app/services/__init__.py`:
   ```python
   from app.services.onboarding_service import OnboardingService
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/onboarding_service.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Коммит: `git add . && git commit -m "feat(services): add OnboardingService [protocol-0014/03]"`
6. Push
7. Отчёт по формату
