# Work Log: 0032-system-ops-guard — Служебные операции в списке операций

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-NNNN#ctx-N -->

Restore context: protocol-0032#ctx-1

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 01 — Маркировка и рендер служебных операций
- Словарь подписей типов вынесен в `TYPE_LABELS` (модульная константа
  `transaction_service.py`) — единый источник для CSV-экспорта и бейджей
  списка; расширен savings-типами («Накопления»), CSV-экспорт попутно
  перестал показывать сырое `str(enum)` для savings.
- `transactions.py`: `SYSTEM_TRANSACTION_TYPES` + предикат
  `_is_system_transaction` (единственный источник «служебности» для
  шагов 1-2), карта цветов бейджей `_TYPE_BADGE_COLOR`, тексты замка
  `_SYSTEM_LOCK_TITLES`. Служебные строки: без чекбокса/кнопок, замок
  «авто» с title, «(авто)» в описании, класс `.tx-system-row`
  (opacity 0.75 по образцу `.readonly` календаря, без новых токенов).
- **Решение Р1**: dropdown типов edit-модала содержит только
  INCOME/EXPENSE → у ADJUSTMENT скрыта кнопка редактирования, delete
  оставлен (откат корректировки сверки — право пользователя).
  Замечено попутно: TRANSFER модал тоже не умеет (тот же dropdown),
  но по плану TRANSFER не трогаем — полноценная пользовательская
  операция, пре-существующее ограничение модала вне scope.
- Знак суммы: ADJUSTMENT — по значению (как сверка календаря),
  savings — «-» (уменьшают баланс), TRANSFER — без знака, нейтральный
  класс `text-muted`.
- Chips-guard в `_build_chips_cell` расширен обоими savings-типами.
- Тесты: `tests/test_transactions_system_ops.py`, 35 шт. без БД
  (Transaction в памяти, относительные даты). Mutation smoke: предикат
  → `return False` — 14 падений; откат — зелено.
- flake8: единственное замечание `transaction_service.py:65` — это
  pre-existing E501 (был на строке 54, сдвинут вставкой TYPE_LABELS).
