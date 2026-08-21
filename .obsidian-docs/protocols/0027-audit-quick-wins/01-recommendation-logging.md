# Шаг 1: Логирование fail-open в рекомендациях покупок

> Исполнение: субагент (решение владельца). Главный агент проверяет и коммитит.

## Briefing

- **Цель:** Сбой CushionService при расчёте безопасных дат покупок больше
  не проглатывается молча: warning в лог с трейсбеком; fail-open поведение
  сохраняется и документируется.
- **Ключевые файлы:**
  - `app/services/purchase_recommendation_service.py` — блок try/except
    в `get_safe_dates_map()` (~строки 66-70)
  - `tests/test_purchase_recommendation.py` — существующие 11 тестов + новый
- **Доп. информация:**
  - Решение по fail-closed: ОТКЛОНЕНО (см. plan.md, Alternatives) — критерий
    negative_balance продолжает защищать, сбой настройки подушки не должен
    ронять режим. Менять семантику поведения НЕЛЬЗЯ.
  - Логирование в проекте — loguru: `from loguru import logger`.

## Sub-tasks

1. В except-блоке добавить `logger.warning(..., exc_info=True)` с внятным
   сообщением (сбой получения настроек подушки → критерий подушки отключён
   для расчёта). Проверить, есть ли в этом же файле другие молчаливые
   except той же природы (например, в `precalculate_hover_data`) — если
   есть, залогировать аналогично (семантику не менять).
2. Обновить докстринг `get_safe_dates_map()`: задокументировать fail-open
   (при сбое настроек подушки критерий cushion отключается, negative_balance
   продолжает действовать).
3. Тест: mock `CushionService.get_settings` → raise; проверить, что
   (а) результат по-прежнему рассчитывается, (б) критерий cushion не
   срабатывает, negative_balance работает, (в) warning попадает в лог —
   для loguru перехват через `logger.add(sink)` в тесте или caplog с
   propagation-хендлером; если лог-проверка в тестовой обвязке проекта
   неоправданно сложна — покрыть (а)+(б), лог-проверку отметить в отчёте
   как пропущенную с причиной.
4. Прогнать: `tests/test_purchase_recommendation.py -v` → зелёные.

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python3 -m py_compile app/services/purchase_recommendation_service.py`
3. Обнови `log.md`; обнови `context.md` (Current Step + 1)
4. Проверь `main` на случайные файлы
5. Коммит: `git add . && git commit -m "fix(recommendations): логировать сбой настроек подушки (fail-open задокументирован) [protocol-0027/01]"`
6. Push
7. Отчёт по формату `report-format.md.tpl`
