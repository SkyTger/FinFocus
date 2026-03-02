# Шаг 1: Schema + Model

## Briefing

- **Цель:** Добавить User.first_launch поле и OnboardingStatus TypedDict
- **Ключевые файлы:**
  - `app/models/database.py` — добавить first_launch в User
  - `app/schema/onboarding.py` — NEW: OnboardingStatus TypedDict
  - `app/schema/__init__.py` — экспорт
- **Доп. информация:** first_launch: Boolean, default=True

## Sub-tasks

1. **Добавить поле в User model** (`app/models/database.py`):
   ```python
   first_launch: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
   ```

2. **Создать TypedDict** (`app/schema/onboarding.py`):
   ```python
   from typing import TypedDict
   from decimal import Decimal

   class OnboardingStatus(TypedDict):
       """Статус онбординга пользователя."""
       first_launch: bool
       starting_balance: Decimal
       needs_balance_alert: bool  # True если starting_balance == 0
   ```

3. **Экспортировать** в `app/schema/__init__.py`:
   ```python
   from app.schema.onboarding import OnboardingStatus
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/models/database.py app/schema/onboarding.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Проверь main на случайные файлы
6. Коммит: `git add . && git commit -m "feat(models): add User.first_launch and OnboardingStatus [protocol-0014/01]"`
7. Push
8. Отчёт по формату
