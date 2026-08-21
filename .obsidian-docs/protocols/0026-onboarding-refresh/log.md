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
