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

### Step 02 — Серверные guard'ы
- **Edit guard** (`open_edit_modal`): после загрузки транзакции —
  служебная или ADJUSTMENT (по Р1) → debug-лог + PreventUpdate
  (молчаливый пропуск в стиле соседних ADR-003 guard'ов).
- **Delete guard** (`handle_delete_click` в transaction_modals.py):
  служебная → PreventUpdate ДО ветвления recurring/обычная. Импорт
  предиката из transactions.py — цикла нет (transactions.py модалы
  не импортирует).
- **Bulk в сервисе** (`bulk_update_category`): переработан на выборку
  кандидатов (id, тип) → прежняя проверка ownership СОХРАНЕНА (считается
  до фильтрации по типу, существующий тест ownership зелёный) → типы вне
  `CATEGORIZABLE_TRANSACTION_TYPES` (INCOME/EXPENSE) исключаются молча,
  счётчик честный, пустой остаток → 0 без исключения.
- **Selection guard** (`_drop_system_ids` + `update_selection_state`):
  страховка bulk-выборки фильтром по типам из БД (один запрос, только
  при непустой выборке); порядок id сохраняется.
- **Chips guards**: оба chips-callbacks загружают транзакцию до
  update — служебная (или не найдена) → PreventUpdate.
- Тесты: +16 guard'ов в test_transactions_system_ops.py (моки ctx +
  get_db_session по образцу test_profile_modal_callbacks; selection-guard
  на реальной db_session фикстуре) и +2 сервисных в
  test_transaction_service.py (смешанный список — обновлён только
  EXPENSE; список из одних служебных — 0 без исключения).
- Mutation smoke: delete-guard → `if False` — 2 падения; откат — зелено.
- Полный прогон: 898 passed (было 845, +53 за протокол).
