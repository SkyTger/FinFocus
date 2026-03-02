# Шаг 4: Calendar.py обновления

## Briefing

- **Цель:** Рефакторинг format_balance() (возврат С ₽), обновить 4 callsite, заменить 11 inline-форматирований на format_rub()
- **Ключевые файлы:**
  - `app/components/calendar.py` — ~35 строк изменений
- **Доп. информация:** См. `.design/solution-v2.md` секции "format_balance() в calendar.py -- рефакторинг", "calendar.py (12 inline spots)"

## Sub-tasks

1. Добавить import: `from app.utils.formatters import format_rub`

2. Рефакторинг `format_balance()`:
   - Заменить `f"{balance:,.0f}".replace(",", " ")` на `format_rub(balance)` внутри функции
   - Теперь возвращает строку С символом ₽

3. Обновить 4 callsite format_balance():
   - Line 294: `f"+{income_formatted} ₽"` → `format_rub(total_income, show_sign=True)`
   - Line 309: `f"-{expense_formatted} ₽"` → `format_rub(-total_expense)`
   - Line 324: `f"{balance_formatted} ₽"` → просто `balance_formatted`
   - Line 681: `f"{balance_text} ₽"` → просто `balance_text`

4. 11 inline замен по карте из solution-v2.md:
   - Line 95: format_balance() внутри (уже в sub-task 2)
   - Line 419: tooltip balance
   - Lines 465, 468, 471, 475, 478: tooltip transaction amounts
   - Lines 1347, 1385: reconciliation expected
   - Line 1452: reconciliation diff
   - Lines 1525, 1530: reconciliation adjustment

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/calendar.py`
3. Запустить `pytest tests/` — убедиться что нет регрессий
4. Обнови `log.md` — что сделано, неочевидные решения
5. Обнови `context.md` — Current Step + 1, Next Action
6. Коммит: `git add . && git commit -m "feat(calendar): refactor format_balance and replace inline formatting [protocol-0021/04]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
