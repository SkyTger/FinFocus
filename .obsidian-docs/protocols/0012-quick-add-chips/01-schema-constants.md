# Шаг 1: Schema и константы

## Briefing

- **Цель:** Создать TypedDict QuickAddChipData и константу DEFAULT_QUICK_ADD_CHIP_NAMES
- **Ключевые файлы:**
  - `app/schema/quick_add.py` (новый)
  - `app/schema/__init__.py` (экспорт)
- **Доп. информация:** Lookup категорий по имени для защиты от ID mismatch

## Sub-tasks

1. Создать `app/schema/quick_add.py`:
   ```python
   from typing import TypedDict

   class QuickAddChipData(TypedDict):
       """Данные для Quick-add chip."""
       category_id: int      # 1, 2, 3...
       name: str             # "Еда и продукты"
       icon: str             # "bi-cart"
       type: str             # "expense" | "income"
   ```

2. Обновить `app/schema/__init__.py` — добавить экспорт QuickAddChipData

3. Добавить в `app/components/transactions.py` (в начало файла):
   ```python
   DEFAULT_QUICK_ADD_CHIP_NAMES: list[tuple[str, str]] = [
       # (name, type) — расход (5)
       ("Еда и продукты", "expense"),
       ("Транспорт", "expense"),
       ("Жилье и ЖКХ", "expense"),
       ("Связь и интернет", "expense"),
       ("Развлечения", "expense"),
       # доход (2)
       ("Зарплата", "income"),
       ("Подработка", "income"),
   ]
   ```

4. Добавить функцию `_get_quick_add_chips()` — lookup по имени с warning для отсутствующих

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/schema/quick_add.py app/components/transactions.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Коммит: `git add . && git commit -m "feat(quick-add): add QuickAddChipData schema and constants [protocol-0012/01]"`
6. Push
7. Отчёт
