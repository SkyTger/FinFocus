# Шаг 2: UI секция Quick-add

## Briefing

- **Цель:** Создать UI-функции для Quick-add chips и интегрировать в layout
- **Ключевые файлы:**
  - `app/components/transactions.py`
- **Доп. информация:** Pattern-Matching ID для chips: `{"type": "qa-chip", "category_id": N, "tx_type": str}`

## Sub-tasks

1. Создать `_build_quick_add_chip(chip_data: QuickAddChipData) -> dbc.Button`:
   - Pattern-Matching ID: `{"type": "qa-chip", "category_id": N, "tx_type": "expense"}`
   - Размер 100-120px, vertical layout (icon + name)
   - `aria_label` для accessibility
   - className="qa-chip"

2. Создать `_build_quick_add_section(chips: list[QuickAddChipData]) -> html.Div`:
   - Группировка expense (5 чипов) + income (2 чипа)
   - Заголовки секций: "Расход", "Доход"
   - Кнопки "Ещё..." с ID `{"type": "qa-more-btn", "tx_type": "expense"|"income"}`
   - Обёртка с className="qa-chip-section"

3. Интегрировать в `create_transactions_layout()`:
   - Вызов `_get_quick_add_chips(session)` для получения данных
   - Вызов `_build_quick_add_section(chips)` после header, перед фильтрами
   - Session management через `get_db_session()`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/transactions.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Коммит: `git add . && git commit -m "feat(quick-add): add UI section with chips [protocol-0012/02]"`
6. Push
7. Отчёт
