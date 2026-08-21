# Work Log: 0026-onboarding-refresh — Онбординг: мгновенное применение профиля на дашборде

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-NNNN#ctx-N -->

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 01 — Подписки дашборда на profile-updated
- `load_dashboard_data`: добавлен Input("profile-updated","data") + параметр
  `profile_updated` (только триггер, значение не используется). Существующий
  pathname-guard отсекает события на других страницах.
- `toggle_balance_toast`: добавлен тот же Input. Ветка «закрытие через крестик»
  не перехватывает событие (проверяет triggered_id == "balance-alert-toast").
  Докстринг разбит на многострочный — исходный однострочный давал новый E501.
- Приветствие: H4 получил id="dashboard-greeting"; новый callback
  `update_dashboard_greeting` (Input profile-updated, State url.pathname,
  prevent_initial_call=True, guard'ы: data None / чужой pathname → PreventUpdate;
  ошибка БД → PreventUpdate + logger.warning, чтобы не затирать текущее
  приветствие). Inline-чтение имени в layout оставлено как начальное значение.
- Проверки: py_compile OK, black OK, flake8 — новых замечаний нет
  (2 старых E501 в файле сместились 141→142, 147→148 — не наши),
  смоук `import app.main` OK (регистрация колбэков не падает).

### Step 02 — Тесты (выполнен субагентом, проверен главным агентом)
- Новый файл tests/test_dashboard_callbacks.py: 11 тестов, 3 класса
  (контракт подписок / update_dashboard_greeting / toggle_balance_toast
  с триггером profile-updated).
- Контракт подписок зафиксирован через inspect.getsource (анализ блока
  @callback перед функцией) — устойчивая альтернатива из спеки:
  dash.callback_map ключуется по строке Output и хрупок вне запущенного
  приложения.
- Мок ctx.triggered_id — patch("app.components.dashboard.ctx"), по паттерну
  существующих тестов (патчить модуль-импортёр, не место определения).
- Прогон: 75 passed (новые + test_dashboard_service + test_onboarding_service),
  регрессий нет; black/flake8 по новому файлу — чисто.
- Найдено расхождение доков с кодом: KB (modules/ui-components.md,
  services.md) описывает needs_balance_alert как «balance=0 AND
  first_launch=False», в коде (onboarding_service.py:80) — только
  starting_balance == 0. Код прав, поведение не меняли; кандидат
  в /kb-update при финализации.
