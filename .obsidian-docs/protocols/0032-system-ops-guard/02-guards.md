# Шаг 2: Серверные guard'ы

## Briefing

- **Цель:** Даже если клик по служебной операции дойдёт до сервера
  (устаревший DOM, вторая вкладка, ручной запрос) — он игнорируется.
  Защита в глубину поверх UI шага 1.
- **Ключевые файлы:**
  - `app/components/transactions.py` — `open_edit_modal` (~1006),
    `update_selection_state` (~1291), `bulk_assign_category` (~1566),
    chips-callbacks (~1153, ~1221)
  - `app/components/transaction_modals.py` — delete-callback (~1302)
  - `app/services/transaction_service.py` — `bulk_update_category` (~287)
  - `tests/test_transactions_system_ops.py` (дополнить),
    `tests/test_transaction_service.py` (дополнить)
- **Доп. информация:** Использовать предикат служебности из шага 1.
  Паттерн guard'ов — ADR-003 (`patterns/callbacks.md`): молчаливый
  `no_update`/пропуск, НЕ исключение. Guard'ы касаются ТОЛЬКО
  savings-типов (+ edit для ADJUSTMENT, если Р1 шага 1 так решил).

## Sub-tasks

1. **Edit guard**: `open_edit_modal` — по triggered id загрузить
   транзакцию, служебная → `no_update` (+ debug-лог loguru).
2. **Delete guard**: delete-callback в `transaction_modals.py` — та же
   проверка ДО открытия confirm-модала.
3. **Bulk guards**:
   - `bulk_update_category` (сервис) — savings-типы и ADJUSTMENT/TRANSFER
     исключаются из обновления (не ошибка, а фильтрация; вернуть честный
     счётчик обновлённых);
   - `update_selection_state` — served id в выборку не попадают (UI их
     чекбоксов не рендерит, guard страхует).
4. **Chips guards**: `chip_assign_category` / `chip_dropdown_assign_category`
   — назначение категории служебной операции игнорируется.
5. **Тесты**:
   - сервис: `bulk_update_category` со смешанным списком id обновляет
     только пользовательские, счётчик честный (тут БД-фикстуры уместны —
     по образцу существующих тестов сервиса);
   - callbacks: guard-ветки через прямой вызов функций (паттерн
     существующих тестов callbacks);
   - регрессия: обычные INCOME/EXPENSE редактируются/удаляются как раньше.
6. **Mutation smoke**: закомментировать guard удаления → тест падает; вернуть.

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/transactions.py app/components/transaction_modals.py app/services/transaction_service.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 3, Next Action: Финализация
5. Проверь ветку на случайные файлы
6. Коммит: `git add . && git commit -m "feat(transactions): серверные guard'ы служебных операций [protocol-0032-system-ops-guard/02]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
