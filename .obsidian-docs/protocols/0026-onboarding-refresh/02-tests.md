# Шаг 2: Тесты

## Briefing

- **Цель:** Регрессионная защита подписок: колбэчные тесты по образцу
  `tests/test_transactions_callbacks.py` (прямой вызов функций колбэков
  с моком ctx / сессии).
- **Ключевые файлы:**
  - `tests/test_dashboard_callbacks.py` — новый файл
  - `tests/conftest.py` — существующие фикстуры (сессия, хелперы
    относительных дат) — переиспользовать, не дублировать
- **Доп. информация:** Тесты сервисов дашборда живут в
  `test_dashboard_service.py` — их не трогать.

## Sub-tasks

1. **Тест декораторов (подписки существуют)**: интроспекцией Dash callback map
   или чтением сигнатур проверить, что `load_dashboard_data` и
   `toggle_balance_toast` имеют Input `profile-updated` — фиксация контракта,
   чтобы подписку не потеряли при рефакторинге. Если интроспекция callback map
   в тестовой среде нестабильна — допустима проверка через
   `inspect.signature` + анализ зарегистрированных Input'ов колбэка
   (callback_context недоступен вне запроса — НЕ эмулировать полный Dash).

2. **Тест `update_dashboard_greeting`**: прямой вызов функции:
   - с валидным профилем в БД → возвращает приветствие с именем;
   - data=None → PreventUpdate;
   - pathname="/goals" → PreventUpdate.
   Мокать ctx не требуется, если функция не использует ctx.triggered
   (спроектировать её так в шаге 1).

3. **Тест `toggle_balance_toast` с триггером profile-updated**: прямой вызов
   с pathname="/dashboard", is_dismissed=False и балансом > 0 в БД →
   возвращает False (баннер скрыт). Использовать unittest.mock для
   `ctx.triggered_id`, как в существующих колбэчных тестах.

4. Прогнать новый файл + смежные:
   `pytest tests/test_dashboard_callbacks.py tests/test_dashboard_service.py tests/test_onboarding_service.py -v`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python3 -m py_compile tests/test_dashboard_callbacks.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "test(dashboard): колбэчные тесты подписок profile-updated [protocol-0026/02]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
