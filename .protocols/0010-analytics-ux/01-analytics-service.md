# Шаг 1: TypedDicts и AnalyticsService

## Briefing
- **Цель:** Создать backend для аналитики: TypedDicts схему и AnalyticsService с методами агрегации расходов по категориям.
- **Ключевые файлы:**
  - `app/schema/analytics.py` (создать) — CategorySummary, MonthlyTrend TypedDicts
  - `app/services/analytics_service.py` (создать) — AnalyticsService class
  - `app/services/__init__.py` (модифицировать) — экспорт новых компонентов
  - `tests/test_analytics_service.py` (создать) — 12+ unit тестов
- **Additional info:**
  - Константа MIN_PERCENTAGE_THRESHOLD = 3.0 для группировки мелких категорий в "Прочее"
  - SQL GROUP BY для эффективной агрегации
  - Фильтровать только EXPENSE транзакции, исключать is_recurring=True (шаблоны)
  - "Без категории" (category_id IS NULL) как отдельная группа

## Sub-tasks

### 1. Создать TypedDicts схему

**Файл:** `app/schema/analytics.py`

```python
"""TypedDicts для аналитического модуля."""
from decimal import Decimal
from typing import TypedDict


class CategorySummary(TypedDict):
    """Агрегация по категории для donut chart."""
    category_id: int | None  # None = "Без категории"
    category_name: str
    category_icon: str | None
    total: Decimal
    percentage: float
    count: int


class MonthlyTrend(TypedDict):
    """Данные за месяц для bar chart."""
    month: str  # "2026-01"
    month_label: str  # "Янв"
    categories: list[CategorySummary]
    total: Decimal
```

### 2. Создать AnalyticsService

**Файл:** `app/services/analytics_service.py`

Реализовать класс с методами:

1. `__init__(self, session: Session)` — инициализация с сессией

2. `get_expenses_by_category(self, user_id: int, start_date: date, end_date: date, group_small: bool = True) -> list[CategorySummary]`:
   - SQL запрос: SELECT category_id, SUM(amount), COUNT(*) FROM transactions WHERE user_id=X AND type=EXPENSE AND is_recurring=False AND date BETWEEN start AND end GROUP BY category_id
   - JOIN с Category для получения name и icon
   - Расчет percentage = (total / grand_total) * 100
   - Если group_small=True: категории с percentage < 3.0 объединить в "Прочее" (category_id=None, icon="📦")
   - Сортировка по total DESC
   - "Без категории" (category_id IS NULL) как отдельная запись

3. `get_monthly_trends(self, user_id: int, months: int = 6, reference_date: date | None = None) -> list[MonthlyTrend]`:
   - Генерация списка месяцев от reference_date (default=today) назад на months месяцев
   - Для каждого месяца: вызов get_expenses_by_category с group_small=True
   - Формирование списка MonthlyTrend с month_label на русском (Янв, Фев, ...)

4. `get_uncategorized_count(self, user_id: int) -> int`:
   - COUNT транзакций WHERE category_id IS NULL AND is_recurring=False AND type IN (INCOME, EXPENSE)

### 3. Обновить экспорты

**Файл:** `app/services/__init__.py`

Добавить:
```python
from app.services.analytics_service import AnalyticsService
```

И в `__all__` добавить `"AnalyticsService"`.

**Файл:** `app/schema/__init__.py`

Добавить:
```python
from app.schema.analytics import CategorySummary, MonthlyTrend
```

### 4. Написать unit тесты

**Файл:** `tests/test_analytics_service.py`

Тесты (минимум 12):

1. `test_get_expenses_by_category_basic` — проверка базовой агрегации с 2-3 категориями
2. `test_get_expenses_includes_uncategorized` — убедиться что category_id=NULL включен как "Без категории"
3. `test_get_expenses_groups_small_categories` — категории < 3% объединены в "Прочее"
4. `test_get_expenses_no_grouping` — с group_small=False все категории сохранены
5. `test_get_expenses_empty_period` — пустой период возвращает []
6. `test_get_expenses_excludes_income` — INCOME транзакции исключены
7. `test_get_expenses_excludes_recurring_templates` — is_recurring=True исключены
8. `test_get_monthly_trends_6_months` — проверка 6 месяцев с корректными month_label
9. `test_get_monthly_trends_12_months` — проверка 12 месяцев
10. `test_get_monthly_trends_empty_month` — месяц без транзакций имеет total=0, categories=[]
11. `test_get_uncategorized_count` — корректный подсчет
12. `test_get_uncategorized_count_excludes_recurring` — is_recurring=True исключены
13. `test_percentage_calculation` — проверка расчета процентов (сумма = 100%)
14. `test_sorting_by_total_desc` — результат отсортирован по убыванию суммы

## Workflow (Порядок работы)

1.  **Выполнение:** Последовательно выполняй подзадачи.

2.  **Базовая проверка:** Убедись что код синтаксически корректен:
    ```bash
    source .venv/bin/activate
    python -m py_compile app/schema/analytics.py app/services/analytics_service.py tests/test_analytics_service.py
    ```

3.  **Фиксация:** После успешной базовой проверки:
    - **Добавь запись в `log.md`**: Опиши реализованные методы и решения.
    - **Обнови `context.md`**: Увеличь `Current Step` на 1.
    - Проверь ветку main в поисках случайно добавленных файлов.

4.  **Сделай коммит:**
    ```bash
    git add app/schema/analytics.py app/services/analytics_service.py app/services/__init__.py app/schema/__init__.py tests/test_analytics_service.py .protocols/
    git commit -m "feat(analytics): add AnalyticsService with category aggregation [protocol-0010/01]"
    git push
    ```

5.  **Отчет пользователю** в установленном формате.
