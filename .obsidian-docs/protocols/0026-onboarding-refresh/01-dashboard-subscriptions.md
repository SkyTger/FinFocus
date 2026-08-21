# Шаг 1: Подписки дашборда на profile-updated

## Briefing

- **Цель:** Дашборд реагирует на завершение онбординга / смену профиля без
  ручной перезагрузки: обновляются данные (KPI, график, таблицы, подушка),
  скрывается баннер нулевого баланса, обновляется приветствие.
- **Ключевые файлы:**
  - `app/components/dashboard.py` — единственный файл правок:
    - `load_dashboard_data` (декоратор ~строка 1336)
    - `toggle_balance_toast` (декоратор ~строка 1472)
    - `create_dashboard_layout` — greeting H4 (~строки 82-110)
- **Доп. информация:**
  - Эмиттеры пишут `time.time()` в Store `profile-updated`
    (main.py:91 — `data=None` изначально): onboarding_wizard.py:193,
    profile_modal.py:93.
  - Рабочий пример подписчика — sidebar.py:170.
  - Паттерн guard'ов — ADR-003 (patterns/callbacks.md).

## Sub-tasks

1. **`load_dashboard_data`**: добавить `Input("profile-updated", "data")`
   в список Inputs; в сигнатуру функции — параметр `profile_updated`
   (значение не используется, событие — только триггер). Существующий
   guard по pathname уже отсекает срабатывания на других страницах.
   Убедиться, что начальное значение Store (None) не ломает логику
   (Input с None прилетает при initial call — pathname guard покрывает).

2. **`toggle_balance_toast`**: добавить `Input("profile-updated", "data")`
   и параметр `profile_updated`. Логика ветки «При загрузке Dashboard»
   (проверка pathname + запрос OnboardingService.get_status) корректно
   отработает и для этого триггера: после онбординга с балансом
   `needs_balance_alert=False` → баннер скроется. Учесть `is_dismissed`:
   поведение при dismissed не менять.
   Нюанс: triggered_id при событии Store будет `"profile-updated"` —
   проверить, что ветка «закрытие через крестик» не перехватит его.

3. **Приветствие**: в `create_dashboard_layout` дать `html.H4` приветствия
   `id="dashboard-greeting"` (inline-чтение имени оставить как начальное
   значение). Добавить callback `update_dashboard_greeting`:
   - Input: `("profile-updated", "data")`
   - State: `("url", "pathname")`
   - Output: `("dashboard-greeting", "children")`
   - `prevent_initial_call=True`
   - Guard'ы ADR-003: data is None → PreventUpdate; pathname не
     dashboard → PreventUpdate.
   - Тело: get_profile → f-строка приветствия (тот же текст, что в layout);
     ошибка БД → PreventUpdate (не затирать текущее приветствие),
     `logger.warning(..., exc_info=True)`.

4. Ручная проверка через запуск приложения НЕ входит в шаг (нет чистой базы
   под рукой) — поведенческая проверка тестами в шаге 2.

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python3 -m py_compile app/components/dashboard.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "fix(dashboard): подписать дашборд на profile-updated [protocol-0026/01]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
