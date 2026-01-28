# Шаг 1: Schema + Model

## Briefing

- **Цель:** Создать TypedDicts для подушки и добавить 3 поля в модель User
- **Ключевые файлы:**
  - `app/schema/cushion.py` — NEW
  - `app/schema/__init__.py` — MODIFY (экспорт)
  - `app/models/database.py` — MODIFY (User)
- **Доп. информация:** См. solution-v3.md, изменение #1

## Sub-tasks

1. **Создать `app/schema/cushion.py`:**
   ```python
   from decimal import Decimal
   from typing import NewType, TypedDict

   Percent = NewType("Percent", int)

   class CushionSettings(TypedDict):
       target: Decimal
       threshold_percent: Percent  # 0-100
       threshold_amount: Decimal   # computed
       threshold_manual: bool
       current_amount: Decimal
       progress: float  # 0-100
       is_configured: bool

   class CushionScenario(TypedDict):
       name: str
       min_amount: Decimal
       max_amount: Decimal
   ```

2. **Обновить `app/schema/__init__.py`:**
   - Добавить экспорт: `Percent, CushionSettings, CushionScenario`

3. **Добавить поля в User (`app/models/database.py`):**
   ```python
   # В классе User, после существующих полей:
   cushion_target = Column(Numeric(12, 2), default=Decimal("0"))
   cushion_threshold_percent = Column(Integer, default=30)
   cushion_threshold_manual = Column(Boolean, default=False)
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/schema/cushion.py app/models/database.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Коммит: `git add . && git commit -m "feat(schema): add cushion TypedDicts and User fields [protocol-0013/01]"`
6. Push
7. Отчёт по формату
