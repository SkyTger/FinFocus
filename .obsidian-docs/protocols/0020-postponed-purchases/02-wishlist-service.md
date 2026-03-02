# Шаг 2: WishlistService

## Briefing

- **Цель:** Реализовать CRUD сервис для хотелок с бизнес-правилами
- **Ключевые файлы:**
  - `app/services/wishlist_service.py` — WishlistService (~200 строк)
  - `app/services/__init__.py` — экспорт WishlistService
- **Доп. информация:** solution-v3.md секция "Ключевые интерфейсы" — WishlistService API

## Sub-tasks

1. Создать `app/services/wishlist_service.py`:
   - `__init__(self, session)` — паттерн flush/commit contract
   - `create_item(user_id, name, amount, category_id=None, priority=1)` — валидация: name не пуст и <= 100 символов, amount > 0, priority in [1, 2]
   - `get_all(user_id)` — ORDER BY priority ASC, created_at ASC
   - `get_focus(user_id, limit=5)` — priority=1, до limit штук
   - `get_by_id(item_id)` — возвращает WishlistItem | None
   - `update_item(item_id, **updates)` — planned guard: для status="planned" разрешены только name, priority. Для status="new" — name, amount, category_id, priority
   - `mark_as_planned(item_id, planned_date, transaction_id)` — status="planned", planned_date, planned_transaction_id
   - `reset_planned(item_id)` — status="new", planned_date=None, planned_transaction_id=None
   - `delete_item(item_id)` — удаление, НЕ удаляет привязанную транзакцию
   - `check_orphaned_planned(user_id)` — status="planned" AND planned_transaction_id IS NULL
   - `to_data(item)` — конвертация ORM → WishlistItemData TypedDict

2. Добавить `ValidationError` — использовать существующий или создать простой (ValueError с сообщением на русском)

3. Обновить `app/services/__init__.py` — экспорт WishlistService

4. Базовая проверка: `python -m py_compile app/services/wishlist_service.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/wishlist_service.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 3, Next Action: Шаг 3
5. Коммит: `git add . && git commit -m "feat(wishlist): WishlistService CRUD [protocol-0020/02]"`
6. Push
7. Отчёт
