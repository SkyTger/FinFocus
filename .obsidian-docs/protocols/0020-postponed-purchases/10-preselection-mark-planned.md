# Шаг 10: Preselection + mark_planned + orphan detection

## Briefing

- **Цель:** Расширить transaction_modals.py для source="wishlist", реализовать mark_planned после создания транзакции, orphan detection
- **Ключевые файлы:**
  - `app/components/transaction_modals.py` — расширение preselection (~60 строк)
  - `app/components/wishlist.py` — +mark_planned callback, +orphan detection callback
- **Доп. информация:** Preselection Store Pattern уже реализован (preselected-category, preselected-type). Нужно добавить preselected-amount, -date, -description, -risk-warning.

## Sub-tasks

1. Обновить `app/components/transaction_modals.py`:
   - Добавить dcc.Stores: preselected-amount, preselected-date, preselected-description, preselected-risk-warning
   - Расширить set_preselection_on_modal_open():
     - Если source="wishlist": применить amount, date, description из stores
     - Показать risk warning alert (если preselected-risk-warning не пусто)
   - Расширить create_transaction:
     - После создания: emit global-transaction-trigger с source="wishlist" и item_id
     - Reset всех preselection stores

2. Обновить `app/components/wishlist.py` (или calendar_wishlist.py):
   - **Click callback на день в wishlist-mode**:
     - Получить дату клика из callback context
     - Заполнить preselection stores: amount, date, description="Покупка: {item_name}", category_id, type=EXPENSE
     - Если день unsafe — установить risk-warning с reasons
     - Открыть create-modal с source="wishlist"
   - **mark_wishlist_planned_after_create() callback**:
     - Input: global-transaction-trigger
     - Условие: source="wishlist"
     - Вызвать WishlistService.mark_as_planned(item_id, date, transaction_id)
     - Обновить wishlist-active-item (очистить)
   - **detect_orphaned_wishlist() callback**:
     - Input: global-transaction-trigger (action="delete")
     - Вызвать WishlistService.check_orphaned_planned()
     - Для каждого orphan: reset_planned()

3. Базовая проверка: `python -m py_compile app/components/transaction_modals.py app/components/wishlist.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 11, Next Action: Шаг 11 (финализация)
5. Коммит: `git add . && git commit -m "feat(wishlist): preselection, mark planned, orphan detection [protocol-0020/10]"`
6. Push
7. Отчёт
