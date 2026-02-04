# Шаг 5: Wishlist UI (виджет + модал)

## Briefing

- **Цель:** Создать компонент wishlist.py — Dashboard виджет и модал управления с CRUD + "Запланировать" + "Переплан."
- **Ключевые файлы:**
  - `app/components/wishlist.py` — виджет + модал + callbacks (~600 строк)
  - `app/assets/wishlist.css` — стили виджета и модала (~120 строк)
  - `app/components/__init__.py` — экспорт
- **Доп. информация:** solution-v3.md — wishlist.py API, confirm replan modal

## Sub-tasks

1. Создать `app/components/wishlist.py`:
   - **build_wishlist_widget()** — карточка для Dashboard:
     - До 5 фокусных покупок (priority=1), read-only карточки
     - Кнопка "Все покупки" для открытия модала
     - Пустое состояние: "Нет отложенных покупок"
   - **create_wishlist_modal()** — модал управления:
     - Секции: Фокусные (priority=1) / Отложенные (priority=2)
     - Inline-форма добавления (name, amount, category dropdown, priority toggle)
     - Кнопки для каждой хотелки: Редактировать / Удалить / Запланировать (для new) / Переплан. (для planned)
     - Для planned хотелок: disabled amount/category + tooltip "Сначала отмените планирование"
   - **_build_replan_confirm_modal()** — confirm dialog для перепланирования (по образцу goals.py)
   - **dcc.Store**: wishlist-replan-item-id

2. Создать callbacks:
   - **open_wishlist_modal / close_wishlist_modal** — открытие/закрытие
   - **add_wishlist_item** — создание хотелки через inline-форму
   - **edit_wishlist_item** — редактирование (с planned guards в UI)
   - **delete_wishlist_item** — удаление
   - **open_replan_confirm** — открытие confirm dialog, сохранение item_id
   - **cancel_replan** — закрытие confirm dialog
   - **execute_replan** — удаление транзакции → reset_planned → redirect /calendar?wishlist_item=ID
   - **navigate_to_calendar_for_planning** — "Запланировать" для new → redirect /calendar?wishlist_item=ID
   - Все callbacks с ADR-003 guard clauses

3. Создать `app/assets/wishlist.css`:
   - Стили .wishlist-widget, .wishlist-card, .wishlist-modal
   - Priority indicators (focus = green dot, later = gray)
   - Status badges (new, planned with date)
   - Responsive adjustments

4. Обновить `app/components/__init__.py` — экспорт

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/wishlist.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 6, Next Action: Шаг 6
5. Коммит: `git add . && git commit -m "feat(wishlist): UI widget, modal, confirm replan [protocol-0020/05]"`
6. Push
7. Отчёт
