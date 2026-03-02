# Шаг 1: Schema + Model + Migration

## Briefing

- **Цель:** Создать TypedDicts, ORM модель WishlistItem, idempotent миграцию
- **Ключевые файлы:**
  - `app/schema/wishlist.py` — WishlistItemData, SafeDateInfo, HoverBalances TypedDicts
  - `app/schema/__init__.py` — экспорт новых TypedDicts
  - `app/models/database.py` — WishlistItem ORM модель
  - `scripts/migrate_006_wishlist.py` — idempotent миграция
- **Доп. информация:** solution-v3.md секция "Модель данных" и "Ключевые интерфейсы"

## Sub-tasks

1. Создать `app/schema/wishlist.py`:
   - `WishlistItemData(TypedDict)` — id, name, amount (str), category_id/name/icon, priority, status, planned_date, planned_transaction_id
   - `SafeDateInfo(TypedDict)` — safe: bool, reasons: list[str]
   - `HoverBalances(TypedDict)` — base_balances: dict[str, str], by_candidate: dict[str, dict[str, str]]

2. Обновить `app/schema/__init__.py` — экспорт WishlistItemData, SafeDateInfo, HoverBalances

3. Добавить `WishlistItem` в `app/models/database.py`:
   - FK: user_id (users.id), category_id (categories.id, nullable), planned_transaction_id (transactions.id, ON DELETE SET NULL)
   - Поля: name (String 100), amount (Numeric 10,2), priority (Integer, default=1), status (String 20, default="new"), planned_date (Date, nullable), created_at, updated_at
   - Relationships: user, category_rel, planned_transaction
   - Добавить relationship `wishlist_items` в User

4. Создать `scripts/migrate_006_wishlist.py`:
   - PRAGMA table_info check перед CREATE TABLE
   - CREATE TABLE IF NOT EXISTS wishlist_items
   - CREATE INDEX ix_wishlist_user_priority

5. Базовая проверка: `python -m py_compile app/models/database.py app/schema/wishlist.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/models/database.py app/schema/wishlist.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Коммит: `git add . && git commit -m "feat(wishlist): schema, model, migration [protocol-0020/01]"`
6. Push
7. Отчёт
