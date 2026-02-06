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
