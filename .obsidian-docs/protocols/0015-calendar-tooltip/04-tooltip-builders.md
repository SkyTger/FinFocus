# Шаг 4: Tooltip Builder Functions

## Briefing

- **Цель:** Реализовать функции построения tooltip: _build_day_tooltip, _build_tooltip_balance, _build_tooltip_transaction_row
- **Ключевые файлы:**
  - `app/components/calendar.py` — добавить 3 функции
- **Доп. информация:** Полный код в solution-v3.md

## Sub-tasks

1. **Добавить импорт ICON_TO_EMOJI**:
   ```python
   from app.utils.formatters import ICON_TO_EMOJI
   ```

2. **Реализовать _build_tooltip_balance()**:
   ```python
   def _build_tooltip_balance(balance: Decimal) -> html.Div:
       """Строит header tooltip с балансом."""
       balance_text = f"{balance:,.0f}".replace(",", " ") + " ₽"
       return html.Div(
           f"Остаток: {balance_text}",
           className="tooltip-balance",
       )
   ```

3. **Реализовать _build_tooltip_transaction_row()**:
   - Получить emoji через `ICON_TO_EMOJI.get(txn["category_icon"], "📋")`
   - Форматировать сумму с + или -
   - Добавить CSS класс skipped если is_skipped
   - Добавить 🔁 иконку для recurring
   - Pattern-Matching ID: `{"type": "tooltip-txn", "date": ..., "id": ..., "is_virtual": ..., "template_id": ...}`

4. **Реализовать _build_day_tooltip()**:
   - Если нет транзакций → return None
   - Разделить на visible (первые 5) и hidden (остальные)
   - Checkbox ПЕРВЫМ если есть hidden
   - Balance header
   - Visible rows
   - Если есть hidden: label "ещё N..." + контейнер hidden rows
   - ARIA атрибуты: role="tooltip", aria-label

5. **Интегрировать в build_day_cell()**:
   - Заменить `tooltip = None` на вызов `_build_day_tooltip(day_date, balance, transactions)`
   - Передать transactions из параметров build_day_cell

## Workflow

1. Выполни Sub-tasks
2. Проверка: `python -m py_compile app/components/calendar.py`
3. Запустить приложение, проверить tooltip визуально:
   - Hover на день с операциями → tooltip появляется
   - Hover на пустой день → tooltip не появляется
   - Кнопка "ещё N..." раскрывает список (если >5 операций)
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 5
6. Коммит: `git add . && git commit -m "feat(calendar): add tooltip builder functions [protocol-0015/04]"`
7. Push
8. Отчёт
