# Шаг 7: Calendar wishlist module

## Briefing

- **Цель:** Создать отдельный модуль calendar_wishlist.py с wishlist-специфичной логикой для календаря
- **Ключевые файлы:**
  - `app/components/calendar_wishlist.py` — НОВЫЙ модуль (~350 строк)
- **Доп. информация:** solution-v3.md — calendar_wishlist.py API. Модуль содержит всю wishlist-логику, которая импортируется из calendar.py

## Sub-tasks

1. Создать `app/components/calendar_wishlist.py`:
   - **build_wishlist_overlay_banner(item_name, item_amount, safe_dates_map)** — overlay-баннер:
     - Название и сумма хотелки
     - Кнопка "Отмена" для выхода из wishlist-mode
     - Легенда маркеров: зелёный (безопасно), красный (риск)
     - Счетчик safe дней
   - **build_wishlist_day_cell(day_date, balance, transactions, safe_info, is_today, is_current_month, is_weekend, is_past)** — ячейка дня в wishlist-mode:
     - Маркер safe/unsafe (цвет рамки или точки)
     - Для past days: CSS класс .past-day-wishlist
     - data-date атрибут на balance элементе
     - Reasons tooltip на unsafe днях
   - **build_wishlist_calendar_grid(month, year, balances, transactions, safe_dates_map)** — полная сетка:
     - CSS класс .wishlist-mode на grid
     - Вызов build_wishlist_day_cell для каждого дня
   - **cancel_wishlist_mode callback** — кнопка "Отмена":
     - Очистка wishlist-active-item Store
     - Перерендер календаря без overlay

2. Базовая проверка: `python -m py_compile app/components/calendar_wishlist.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/calendar_wishlist.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 8, Next Action: Шаг 8
5. Коммит: `git add . && git commit -m "feat(wishlist): calendar wishlist module [protocol-0020/07]"`
6. Push
7. Отчёт
