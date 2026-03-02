# Шаг 4: Unit тесты сервисов

## Briefing

- **Цель:** Написать unit тесты для WishlistService и PurchaseRecommendationService
- **Ключевые файлы:**
  - `tests/test_wishlist_service.py` — ~25 тестов
  - `tests/test_purchase_recommendation.py` — ~15 тестов
- **Доп. информация:** Использовать существующие фикстуры из conftest.py (db_session, user, и т.д.)

## Sub-tasks

1. Создать `tests/test_wishlist_service.py` (~25 тестов):
   - **CRUD**: create_item (happy path), create с валидацией (пустое имя, длинное имя, amount<=0, bad priority)
   - **get_all**: сортировка по priority, created_at
   - **get_focus**: limit работает, только priority=1
   - **get_by_id**: found, not found
   - **update_item**: name/amount для new, planned guard (name/priority OK, amount/category_id → error)
   - **mark_as_planned**: happy path, проверка полей
   - **reset_planned**: happy path, проверка сброса
   - **delete_item**: happy path, not found
   - **check_orphaned_planned**: есть/нет orphans
   - **to_data**: проверка маппинга полей

2. Создать `tests/test_purchase_recommendation.py` (~15 тестов):
   - **get_safe_dates_map**: all safe, mixed, all unsafe
   - **get_safe_dates_map**: past days not included
   - **get_safe_dates_map**: cushion threshold respected
   - **get_safe_dates_map**: negative balance detection
   - **precalculate_hover_data**: base_balances correct
   - **precalculate_hover_data**: by_candidate correct calculation
   - **precalculate_hover_data**: past days not in by_candidate
   - **edge cases**: zero amount, first/last day of month

3. Запустить `pytest tests/test_wishlist_service.py tests/test_purchase_recommendation.py -v`

## Workflow

1. Выполни Sub-tasks последовательно
2. `pytest tests/test_wishlist_service.py tests/test_purchase_recommendation.py -v`
3. Обнови `log.md` — количество тестов, результаты
4. Обнови `context.md` — Current Step: 5, Next Action: Шаг 5
5. Коммит: `git add . && git commit -m "test(wishlist): unit tests for services [protocol-0020/04]"`
6. Push
7. Отчёт
