# Шаг 5: Analytics.py обновления

## Briefing

- **Цель:** Заменить 2 inline-форматирования на format_rub() в analytics.py
- **Ключевые файлы:**
  - `app/components/analytics.py` — ~5 строк изменений
- **Доп. информация:** См. `.design/solution-v2.md` секция "analytics.py (4 inline spots, 2 Plotly template)"

## Sub-tasks

1. Добавить import: `from app.utils.formatters import format_rub`

2. 2 inline замены:
   - Line 169: `f"<b>{total:,.0f}</b><br>₽"` → `f"<b>{format_rub(total)}</b>"`
   - Line 286: `f"{total:,.0f} ₽"` → `format_rub(total)`

3. Plotly hovertemplate (lines 160, 244): **оставить как есть** — Plotly template language, не поддерживает Python функции

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/analytics.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Коммит: `git add . && git commit -m "feat(analytics): replace inline formatting with format_rub [protocol-0021/05]"`
6. Push
7. Отчёт по формату из `report-format.md.tpl`
