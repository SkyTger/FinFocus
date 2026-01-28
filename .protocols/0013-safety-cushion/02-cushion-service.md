# Шаг 2: CushionService

## Briefing

- **Цель:** Реализовать CushionService с CRUD методами и калькулятором сценариев
- **Ключевые файлы:**
  - `app/services/cushion_service.py` — NEW
  - `app/services/__init__.py` — MODIFY (экспорт)
- **Доп. информация:** См. solution-v3.md, методы get_settings, update_settings, reset_settings, calculate_recommendation

## Sub-tasks

1. **Создать `app/services/cushion_service.py`:**
   ```python
   from decimal import Decimal
   from loguru import logger
   from sqlalchemy.orm import Session

   from app.core import ValidationError
   from app.schema.cushion import CushionSettings, CushionScenario, Percent

   VALID_CALC_MODES = {"sum", "max_scenario"}

   # 30% от цели — типичный рекомендуемый минимальный остаток.
   # При достижении этого порога баланс считается "в зоне риска".
   # Источник: стандартная практика финансового планирования.
   DEFAULT_THRESHOLD_PERCENT: Percent = Percent(30)

   def _validate_percent(value: int) -> Percent:
       """Валидирует и преобразует int в Percent (0-100)."""
       if not 0 <= value <= 100:
           raise ValidationError("Порог должен быть в диапазоне 0-100%", field="threshold_percent")
       return Percent(value)

   class CushionService:
       def __init__(self, session: Session):
           self.session = session

       def _get_user(self, user_id: int):
           # Импорт внутри метода для избежания circular import
           from app.models.database import User
           user = self.session.query(User).filter_by(id=user_id).first()
           if not user:
               raise ValidationError("Пользователь не найден", field="user_id")
           return user

       def _get_current_balance(self, user_id: int) -> Decimal:
           from app.services.calendar_service import CalendarService
           from datetime import date
           cal_service = CalendarService(self.session)
           return cal_service.get_balance_on_date(user_id, date.today())

       def get_settings(self, user_id: int) -> CushionSettings:
           # См. solution-v3.md для полной реализации
           ...

       def update_settings(self, user_id: int, target: Decimal, threshold_percent: int, threshold_manual: bool) -> None:
           # См. solution-v3.md для полной реализации
           ...

       def reset_settings(self, user_id: int) -> None:
           # См. solution-v3.md для полной реализации
           ...

       def calculate_recommendation(self, scenarios: list[CushionScenario], mode: str) -> Decimal:
           if mode not in VALID_CALC_MODES:
               raise ValidationError(f"Неверный режим расчёта: {mode}", field="mode")
           if mode == "sum":
               return sum(s["max_amount"] for s in scenarios)
           else:  # max_scenario
               return max((s["max_amount"] for s in scenarios), default=Decimal("0"))
   ```

2. **Обновить `app/services/__init__.py`:**
   - Добавить экспорт: `CushionService`

## Workflow

1. Выполни Sub-tasks (полная реализация методов по solution-v3.md)
2. Базовая проверка: `python -m py_compile app/services/cushion_service.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 3
5. Коммит: `git add . && git commit -m "feat(services): add CushionService [protocol-0013/02]"`
6. Push
7. Отчёт
