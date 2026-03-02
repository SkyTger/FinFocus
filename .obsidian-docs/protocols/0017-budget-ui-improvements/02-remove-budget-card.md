# Шаг 2: Remove Budget Card

## Briefing

- **Цель:** Удалить верхнюю карточку "Бюджет накоплений (месяц)" с прогресс-баром
- **Ключевые файлы:**
  - `app/components/goals.py`
- **Доп. информация:** Карточка дублирует информацию, которая будет в "Сводке по целям"

## Sub-tasks

1. Найти и удалить функцию `_build_budget_progress_card()` (примерно строки 390-460)

2. Найти и удалить `budget-progress-card-container` из layout:
   - Поиск: `id="budget-progress-card-container"`
   - Удалить html.Div с этим id

3. Найти и удалить callback `load_budget_progress_card` (примерно строки 3741-3784):
   - Поиск: `def load_budget_progress_card`
   - Удалить весь callback с декоратором @callback

4. Проверить что нет других ссылок на удалённые элементы:
   ```bash
   grep -n "budget_progress_card\|budget-progress-card" app/components/goals.py
   ```

5. Базовая проверка: `python -m py_compile app/components/goals.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/goals.py`
3. Обнови `log.md` — что удалено, сколько строк
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Коммит: `git add . && git commit -m "refactor(goals): remove duplicate budget progress card [protocol-0017/02]"`
6. Push
7. Отчёт
