# Шаг 3: Dashboard.py переработка

## Briefing

- **Цель:** Переработать KPI-карточки, заменить inline-форматирование на format_rub(), скрыть AI/Exchange, перевести label на русский
- **Ключевые файлы:**
  - `app/components/dashboard.py` — ~180 строк изменений
- **Доп. информация:** См. `.design/solution-v2.md` секции "dashboard.py (12 inline spots)", "KPI-карточки переработка", "Python hardcoded colors"

## Sub-tasks

1. Добавить import: `from app.utils.formatters import format_rub`

2. Удалить `create_metric_card()` (lines 134-198), создать `_build_kpi_card()`:
   - Сигнатура: title, value, subtitle, icon, icon_color, status_border_color, action_button
   - Белый фон, border `1px solid var(--color-border)`, radius 10px, padding 20px
   - Title: className="kpi-title"
   - Value: className="kpi-number"
   - Subtitle: className="kpi-subtitle"

3. 12 inline замен на format_rub() по карте из solution-v2.md:
   - Lines 290-301: метрики KPI (total_balance, income, expense, savings)
   - Lines 476, 494: cashflow bars text
   - Lines 552, 555, 558: transaction amounts

4. Кнопка "Сверка" на Total Balance:
   - `dcc.Link("Сверка", href="/calendar?open_recon=1")` как action_button

5. Русские label:
   - "Overview" → "Обзор"
   - "Month"/"Year" → "Месяц"/"Год"
   - "This Month"/"This Year" → "За месяц"/"За год"
   - "Income"/"Expense" → "Доходы"/"Расходы"
   - "Cashflow" → "Денежный поток"
   - "Statistic" → "Статистика"
   - "Recent Transactions" → "Недавние операции"
   - "No transactions yet" → "Нет операций"

6. Скрыть AI Assistant и Exchange:
   - Закомментировать вызовы в layout
   - Добавить `# TODO: Epic-08 — реализовать AI Assistant и Exchange`

7. Python hardcoded colors (5 замен, 2 в скрытых карточках не менять):
   - line 369: `"#28a745"` → `"#27ae60"`
   - line 378: `"#17a2b8"` → `"#e74c3c"`
   - line 433: `["#28a745", "#17a2b8"]` → `["#27ae60", "#e74c3c"]`
   - line 471: `"#28a745"` → `"#27ae60"`
   - line 489: `"#17a2b8"` → `"#e74c3c"`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/dashboard.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Коммит: `git add . && git commit -m "feat(dashboard): redesign KPI cards, format_rub, Russian labels [protocol-0021/03]"`
6. Push
7. Отчёт по формату из `report-format.md.tpl`
