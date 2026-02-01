# Work Log: 0015-calendar-tooltip — Tooltip для дней календаря

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0015#ctx-N -->

- Restore context: protocol-0015#ctx-1 (2026/02/01)

---

## Step Log

### Step 00 — Setup (commit: b3b209a)
- Создана ветка 0015-calendar-tooltip
- Создан worktree в ../worktrees/0015-calendar-tooltip
- Созданы артефакты протокола (plan.md, context.md, log.md, step files)
- Источник: solution-v3.md из .design/

### Step 01 — Extend TransactionInfo (commit: 77db700)
- Добавлены поля `is_skipped: bool` и `category_icon: str | None` в TransactionInfo
- Добавлены поля `is_skipped: bool` и `category_icon: str | None` в VirtualTransaction
- Обновлено заполнение TransactionInfo в get_all_transactions_for_period():
  - regular transactions: is_skipped=False, category_icon из category_rel
  - VirtualTransaction: is_skipped из instance, category_icon из instance
  - exceptions: is_skipped из instance.is_skipped, category_icon из category_rel
- Обновлено создание VirtualTransaction в generate_instances(): is_skipped=False, category_icon из template
- 80 тестов calendar/recurring проходят
