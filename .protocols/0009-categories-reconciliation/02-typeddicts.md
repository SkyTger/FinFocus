# Шаг 2: TypedDicts

## Briefing
- **Цель:** Создать централизованные TypedDicts для категорий и сверки в app/schema/categories.py по паттерну проекта.
- **Ключевые файлы:**
  - `app/schema/categories.py` (создать)
  - `app/schema/__init__.py` (модифицировать — добавить экспорт)
- **Additional info:**
  - Проект использует `app/schema/` для TypedDicts, НЕ `app/types/`
  - Все Decimal конвертируются в строки для JSON-совместимости (dcc.Store)
  - Следовать паттерну из `app/schema/goals.py`

## Sub-tasks

### 2.1. Создать app/schema/categories.py

Создать файл `app/schema/categories.py`:

```python
"""TypedDicts для типизации данных категорий и сверки.

Централизованные типы для переиспользования между services и UI.
Все Decimal-значения представлены как строки для JSON-совместимости (dcc.Store).
"""

from typing import TypedDict


class CategoryOption(TypedDict):
    """Опция категории для dropdown в UI.

    Используется для передачи данных из CategoryService в callbacks.
    """

    label: str  # "Еда и продукты"
    value: int  # category_id
    icon: str   # "bi-cart"


class ReconciliationPreview(TypedDict):
    """Предпросмотр сверки для модала.

    Все Decimal конвертируются в строки для JSON-совместимости (dcc.Store).
    """

    expected_balance: str  # "15000.00" — расчетный баланс из CalendarService
    actual_balance: str    # "14200.00" — фактический баланс (user input)
    difference: str        # "-800.00" — разница (actual - expected)
    is_positive: bool      # False если difference < 0
    target_date: str       # "2026-01-22" — дата сверки (ISO format)
    explanation: str       # "Будет создана корректировка на -800 ₽"
```

### 2.2. Обновить app/schema/__init__.py

Добавить экспорт новых TypedDicts в `app/schema/__init__.py`:

```python
# Добавить в существующие импорты:
from app.schema.categories import CategoryOption, ReconciliationPreview

# Добавить в __all__ (если есть):
__all__ = [
    # ... существующие экспорты ...
    "CategoryOption",
    "ReconciliationPreview",
]
```

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи 2.1-2.2.
2.  **Базовая проверка:** Убедись что код синтаксически корректен:
    - `python -m py_compile app/schema/categories.py`
    - `python -m py_compile app/schema/__init__.py`
    - Проверь импорт: `python -c "from app.schema import CategoryOption, ReconciliationPreview; print('OK')"`
3.  **Фиксация:** После успешной проверки:
    - Добавь запись в `log.md`
    - Обнови `context.md`: Current Step = 3
    - Проверь ветку main
    - `git add . && git commit -m "feat(schema): add CategoryOption and ReconciliationPreview TypedDicts [protocol-0009/02]"`
    - `git push`
4.  **Отчет пользователю** в установленном формате.
