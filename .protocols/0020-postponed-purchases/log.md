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

### Step 07 — Calendar wishlist module
- Создан `app/components/calendar_wishlist.py` (~280 строк):
  - build_wishlist_overlay_banner() — баннер с названием, суммой, легендой, счетчиком
  - build_wishlist_day_cell() — ячейка с safe/unsafe маркерами, data-date, reasons tooltip
  - build_wishlist_calendar_grid() — полная сетка с .wishlist-mode CSS
  - cancel_wishlist_mode callback
- py_compile OK, pytest 483 passed

### Step 06 — Dashboard + Main интеграция
- `app/components/dashboard.py`: добавлен build_wishlist_widget() в правую колонку
- `app/main.py`:
  - create_wishlist_modal() в layout
  - dcc.Store wishlist-active-item
  - Единый handle_calendar_query_params() для ?open_recon=1 и ?wishlist_item=ID
  - Заменен handle_open_recon_query_param → handle_calendar_query_params
- py_compile OK, pytest 483 passed

### Step 05 — Wishlist UI (виджет + модал)
- Создан `app/components/wishlist.py` (~500 строк):
  - build_wishlist_widget() — Dashboard карточка с 5 фокусными покупками
  - create_wishlist_modal() — модал с inline-формой, секции Focus/Later
  - _build_replan_confirm_modal() — confirm dialog перепланирования
  - 9 callbacks: open/add/delete/edit(priority toggle)/replan flow/plan navigate
  - ADR-003 guard clauses
- Создан `app/assets/wishlist.css` (~75 строк)
- Обновлен `app/components/__init__.py`
- py_compile OK, pytest 483 passed

### Step 04 — Unit тесты сервисов
- Создан `tests/test_wishlist_service.py`: 31 тест (CRUD, validation, guards, to_data)
- Создан `tests/test_purchase_recommendation.py`: 11 тестов (safe dates, hover data, edge cases)
- Итого: 483 теста (было 441, +42)
- Все тесты pass

### Step 02 — WishlistService (inline, see below)

### Step 03 — PurchaseRecommendationService
- Создан `app/services/purchase_recommendation_service.py` (~160 строк):
  - get_safe_dates_map() — карта безопасности дат (negative_balance, cushion reasons)
  - precalculate_hover_data() — base_balances + by_candidate для JS hover
  - Зависимости: CalendarService.calculate_daily_balances(), CushionService.get_settings()
  - Формула: min(balance[d:end] - amount) для проверки safe
- Обновлен `app/services/__init__.py`: экспорт PurchaseRecommendationService
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
