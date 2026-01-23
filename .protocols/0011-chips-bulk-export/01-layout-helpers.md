# Шаг 1: Layout + Helpers

## Briefing

- **Цель:** Добавить dcc.Store, Export button, Bulk Panel и helper functions в transactions.py
- **Ключевые файлы:**
  - `app/components/transactions.py` — основные изменения
- **Доп. информация:** См. solution-v2.md шаги 1-4

## Sub-tasks

- [ ] 1.1. Добавить imports (dcc.Download, CategoryService)
- [ ] 1.2. Добавить dcc.Store компоненты в layout:
  - `dcc.Store(id="selected-transactions", data=[])`
  - `dcc.Store(id="frequent-categories", data={})`
  - `dcc.Download(id="export-download")`
- [ ] 1.3. Добавить кнопку "Экспорт CSV" в header рядом с "Добавить операцию"
- [ ] 1.4. Добавить helper `_pluralize_operations(count: int) -> str`
  - Склонение: "1 операция выбрана" | "2 операции выбраны" | "5 операций выбрано"
- [ ] 1.5. Добавить helper `_build_bulk_panel() -> html.Div`
  - IDs: `bulk-selected-count`, `bulk-category-dropdown`, `bulk-apply-btn`
  - className: `tx-bulk-panel`, style: `{"display": "none"}`
- [ ] 1.6. Добавить `_build_bulk_panel()` в конец layout

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/transactions.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step = 2, Next Action = Шаг 2
5. Проверь main на случайные файлы
6. Коммит: `git add . && git commit -m "feat(transactions): add layout stores and helpers [protocol-0011/01]"`
7. Push
8. Отчёт по формату
