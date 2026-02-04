# Work Log: 0020-postponed-purchases — Отложенные покупки

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0020#ctx-N -->

### Restore context: protocol-0020#ctx-1
- **Время**: 2026-02-04
- **Диагноз**: B — Прервано (незакоммиченный context.md)
- **Действие**: Закоммитил context.md → Step 1
- **Последний коммит**: 80d1ad2 chore(context): update to step 1

---

## Step Log

### Step 00 — Setup
- Создан протокол 0020-postponed-purchases
- Worktree: /home/skytiger/PycharmProjects/worktrees/0020-postponed-purchases
- План: 11 шагов (0-11), основан на solution-v3.md
- Источники: brief.md, solution-v3.md (учтены critique v1-v3)

### Step 01 — Schema + Model + Migration
- Создан `app/schema/wishlist.py`: WishlistItemData, SafeDateInfo, HoverBalances TypedDicts
- Обновлен `app/schema/__init__.py`: экспорт 3 новых TypedDicts
- Добавлен WishlistItem ORM в `app/models/database.py`:
  - FK: user_id, category_id (nullable), planned_transaction_id (ON DELETE SET NULL)
  - Поля: name, amount, priority (1=фокус), status ("new"|"planned"), planned_date
  - Relationships: user, category_rel, planned_transaction
  - Добавлен `wishlist_items` relationship в User
- Создан `scripts/migrate_006_wishlist.py`: idempotent CREATE TABLE + index
- py_compile OK, pytest 441 passed

### Step 02 — WishlistService
- Создан `app/services/wishlist_service.py` (~270 строк):
  - CRUD: create_item, get_all, get_focus, get_by_id, update_item, delete_item
  - Planning: mark_as_planned, reset_planned
  - Utility: check_orphaned_planned, to_data
  - Валидация: name (1-100), amount > 0, priority in {1,2}
  - Planned guard: status="planned" → только name, priority
- Обновлен `app/services/__init__.py`: экспорт WishlistService
- Использован существующий `app.core.ValidationError`
- py_compile OK, pytest 441 passed
