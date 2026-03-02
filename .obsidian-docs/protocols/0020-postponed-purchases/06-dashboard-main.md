# Шаг 6: Dashboard + Main интеграция

## Briefing

- **Цель:** Интегрировать wishlist виджет в Dashboard и модал в main.py layout
- **Ключевые файлы:**
  - `app/components/dashboard.py` — +wishlist виджет в layout (~30 строк)
  - `app/main.py` — +wishlist модал, dcc.Stores, единый handle_calendar_query_params (~40 строк)
- **Доп. информация:** Существующий handle для ?open_recon=1 в calendar.py нужно объединить с ?wishlist_item=ID в единый callback в main.py

## Sub-tasks

1. Обновить `app/components/dashboard.py`:
   - Импорт build_wishlist_widget из wishlist.py
   - Добавить виджет в layout (после существующих карточек, перед графиками)
   - Refresh callback: слушать global-transaction-trigger для обновления виджета

2. Обновить `app/main.py`:
   - Добавить create_wishlist_modal() в layout (после transaction_modals)
   - Добавить dcc.Stores: wishlist-active-item, wishlist-modal-open
   - Создать/заменить единый handle_calendar_query_params():
     - Input: url.search
     - State: url.pathname
     - Outputs: open-recon-trigger, wishlist-active-item, url.search
     - Обрабатывает ?open_recon=1 И ?wishlist_item=ID
     - Очищает url.search после обработки
   - Если существует отдельный ?open_recon=1 handler в calendar.py — мигрировать логику в main.py

3. Базовая проверка: `python -m py_compile app/main.py app/components/dashboard.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/main.py app/components/dashboard.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 7, Next Action: Шаг 7
5. Коммит: `git add . && git commit -m "feat(wishlist): dashboard widget + main integration [protocol-0020/06]"`
6. Push
7. Отчёт
