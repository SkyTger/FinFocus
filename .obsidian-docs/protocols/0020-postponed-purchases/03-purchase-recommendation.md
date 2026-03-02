# Шаг 3: PurchaseRecommendationService

## Briefing

- **Цель:** Реализовать сервис расчета безопасных дат для покупки на основе CalendarService + CushionService
- **Ключевые файлы:**
  - `app/services/purchase_recommendation_service.py` — PurchaseRecommendationService (~160 строк)
  - `app/services/__init__.py` — экспорт
- **Доп. информация:** solution-v3.md — PurchaseRecommendationService API. Зависимости: CalendarService.calculate_daily_balances(), CushionService.get_settings().threshold_amount

## Sub-tasks

1. Создать `app/services/purchase_recommendation_service.py`:
   - `__init__(self, session)`
   - `get_safe_dates_map(user_id, amount, year, month)` → dict[str, SafeDateInfo]:
     - Получить daily_balances через CalendarService
     - Получить threshold через CushionService.get_settings()
     - Для каждого дня-кандидата (>= today):
       - Вычислить min(balance[d:end] - amount) для всех дней от d до конца месяца
       - safe = True если min >= 0 AND min >= threshold
       - reasons: "negative_balance" если min < 0, "cushion" если min < threshold
     - Прошлые дни (< today) НЕ включаются в результат
   - `precalculate_hover_data(user_id, amount, year, month)` → HoverBalances:
     - base_balances: все дни месяца (date_iso → balance_str)
     - by_candidate: для каждого candidate_date >= today → {day_iso: balance_str} — балансы с учетом покупки в этот день
     - Формула: для candidate day d, balance[i] = base_balance[i] - amount для i >= d

2. Обновить `app/services/__init__.py` — экспорт PurchaseRecommendationService

3. Базовая проверка: `python -m py_compile app/services/purchase_recommendation_service.py`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/purchase_recommendation_service.py`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Коммит: `git add . && git commit -m "feat(wishlist): PurchaseRecommendationService [protocol-0020/03]"`
6. Push
7. Отчёт
