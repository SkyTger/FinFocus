# Шаг 8: Calendar.py расширение

## Briefing

- **Цель:** Расширить calendar.py для поддержки wishlist-mode: data-date атрибут, dcc.Stores, load_and_navigate расширение
- **Ключевые файлы:**
  - `app/components/calendar.py` — расширение (~50 строк изменений)
  - `app/assets/calendar.css` — +стили overlay, маркеров, hover, past-day блокировка (~100 строк)
- **Доп. информация:** data-date нужен для JS hover. load_and_navigate_calendar() получает State("wishlist-active-item") для пересчета при навигации

## Sub-tasks

1. Обновить `app/components/calendar.py`:
   - Добавить `data-date` атрибут на `.calendar-day-balance` в build_day_cell():
     ```python
     **{"data-date": day_date.isoformat()}
     ```
   - Добавить dcc.Stores в calendar layout:
     - `wishlist-safe-dates` — карта SafeDateInfo по дням
     - `wishlist-hover-data` — HoverBalances для JS hover
   - Добавить `wishlist-overlay` div (пустой, будет заполняться callback'ом)
   - Расширить `load_and_navigate_calendar()`:
     - Добавить State("wishlist-active-item")
     - Если wishlist-active-item != None:
       - Получить WishlistItem из БД
       - Вызвать PurchaseRecommendationService.get_safe_dates_map()
       - Вызвать PurchaseRecommendationService.precalculate_hover_data()
       - Использовать build_wishlist_calendar_grid() вместо стандартного grid
       - Вернуть overlay banner, safe_dates, hover_data
     - Иначе — стандартный рендер, пустые stores
   - Добавить callback для load_wishlist_overlay_data (Input: wishlist-active-item)

2. Обновить `app/assets/calendar.css`:
   - `.wishlist-overlay-banner` — стили баннера
   - `.calendar-day.wishlist-safe` — зелёная рамка/индикатор
   - `.calendar-day.wishlist-unsafe` — красная рамка/индикатор
   - `.past-day-wishlist` — pointer-events: none, opacity: 0.5
   - `.hover-recalculated` — подсветка изменённых балансов
   - `.wishlist-mode .day-tooltip { display: none }` — отключение tooltip
   - `.wishlist-legend` — стили легенды маркеров

3. Базовая проверка: `python -m py_compile app/components/calendar.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/calendar.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 9, Next Action: Шаг 9
5. Коммит: `git add . && git commit -m "feat(wishlist): calendar extension + CSS [protocol-0020/08]"`
6. Push
7. Отчёт
