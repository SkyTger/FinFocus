# Work Log: 0021-dashboard-foundation — Dashboard UI Foundation

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

Restore context: protocol-0021#ctx-1

<!-- Записи вида: Restore context: protocol-NNNN#ctx-N -->

---

## Step Log

### Step 01 — format_rub() + тесты
- format_rub() реализован по спецификации (Decimal/float/int/None, show_sign, U+2212 минус)
- format_amount() переопределён как alias → 28 callsites покрыты без изменений
- MINUS_SIGN константа для типографского минуса
- .00 копейки скрываются (15000 → "15 000 ₽", не "15 000.00 ₽")
- 10 unit тестов PASS, 492 total PASS (1 pre-existing failure в allocation precision)
- format_rub добавлен в __init__.py экспорт

### Step 02 — CSS-переменные + типографика
- 15 новых CSS-переменных (палитра #2ecc71, текст, фон, границы)
- Deprecated aliases --primary-green, --light-green для обратной совместимости
- 9 типографических классов (kpi-number/title/subtitle, table-amount, link-show-all, kpi-card)
- custom.css: 7 замен hardcoded цветов
- calendar.css: 6 замен (#28a745 → var(--color-primary/-dark), #17a2b8 → var(--color-secondary))
- transactions.css: 2 замены
- onboarding.css: 3 замены

### Step 03 — Dashboard.py переработка
- create_metric_card() → _build_kpi_card() (белый фон, border, kpi-number/title/subtitle классы)
- 12 inline замен на format_rub() (KPI values, cashflow text, transaction amounts)
- Кнопка "Сверка" на карточку Total Balance → /calendar?open_recon=1
- Русские label: Overview→Обзор, Income→Доходы, Expense→Расходы, etc.
- AI Assistant и Exchange скрыты (TODO Epic-08)
- Python hardcoded colors: #28a745→#27ae60, #17a2b8→#e74c3c
- table-amount.positive/.negative классы для транзакций
