# Шаг 5: Стили щитка и шапка «Свободно сегодня»

## Briefing

- **Цель:** Собрать шапку — главное число, разбор, аватар с именем, кнопку «Сверка», шестерёнку; завести стили щитка; открыть модал профиля из шапки.
- **Ключевые файлы:**
  - `app/assets/panel.css` — НОВЫЙ
  - `app/components/dashboard.py` — `build_free_header()`, `_build_header_empty_state()`
  - `app/components/profile_modal.py` — второй Input (прямые изменения, решение владельца п. 5)
  - Эскиз: `.visual/finfocus-panel-dashboard/v3.html` — правый блок шапки на строках 415-418
- **Источник правды:** solution-v4.md — докстринг `build_free_header`, компонент 5 (profile_modal), компонент 6 (panel.css).
- **Соответствует шагам 7, 8, 10 плана решения** (оценка 4.5 ч).

## Sub-tasks

1. **`app/assets/panel.css`** — классы `pnl-*` из эскиза v3 на CSS-переменных проекта:
   - `pnl-breaker` (контейнер шапки), `pnl-amount` (сумма, `font-variant-numeric: tabular-nums`), `pnl-breakdown` (разбор), `pnl-avatar`, `pnl-cog`, `pnl-legend`, `pnl-meter`
   - Вертикальный ритм, `@media (prefers-reduced-motion: reduce)`
   - **НЕ заводить:** классы сигнальной шины, чипа вердикта (п. 3а), приветствия (п. 3г)

2. **`build_free_header(data, profile) -> html.Div`:**
   - Слева: метка «Свободно сегодня», сумма через `format_rub(data['today']['free'])`, разбор «баланс {balance} − платежи {payments} − резерв {reserve}»
   - Справа: `get_avatar_emoji(profile['avatar_id'])` + `profile['name']`, кнопка «Сверка» (`id="open-recon-from-dashboard-header-btn"`), шестерёнка (`id="dashboard-settings-cog"`, `title="Профиль и настройки"`)
   - **Приветствия нет** (п. 3г). **Вердикта нет** (п. 3а): ни чипа, ни шины, ни окраски суммы по уровню. Единственное исключение — отрицательная сумма в цвете риска (факт знака, не оценка)
   - При `data['degraded']` — нейтральная сноска под разбором «часть данных недоступна, показано без бюджета целей»
   - Не дверь-переход: на контейнере нет `dcc.Link`, `n_clicks`, `cursor: pointer` (FR-2.e)
   - `profile` — единственный источник имени и аватара; **`_build_greeting_text()` не вызывать** (удаляется на шаге 7)

3. **`_build_header_empty_state()`** — при `data['is_empty']`: «Пока нечего показать» + «Добавьте первую операцию или сверьте баланс» + кнопка «Сверка».

4. **`profile_modal.py`** — второй источник открытия:
   - Добавить `Input("dashboard-settings-cog", "n_clicks")` рядом с существующим `Input("sidebar-profile-container", "n_clicks")` (:96)
   - Заменить жёсткое `ctx.triggered_id == "sidebar-profile-container"` (:119) на `triggered_id in ("sidebar-profile-container", "dashboard-settings-cog")`
   - Логику загрузки профиля **не менять**
   - `suppress_callback_exceptions=True` (`main.py:41`) снимает риск отсутствия элемента вне дашборда

5. **Кнопка «Сверка»** — clientside-триггер тот же (`ClientsideFunction("triggers", "timestamp_trigger")` → `open-recon-trigger`), только новый id. Баннерную кнопку `open-recon-from-dashboard-banner-btn` не трогать.

## Проверки шага

- `python -m py_compile app/components/dashboard.py app/components/profile_modal.py`
- Приложение запускается, `/dashboard` открывается без ошибок в консоли Dash
- **Шестерёнка открывает модал профиля; клик по аватару в сайдбаре — тоже** (обе ветки живы)
- После правки имени/аватара в модале шапка обновляется без перезагрузки страницы (подписка `profile-updated` жива)
- `.venv/bin/pytest -q` — прежние зелёные
- `.venv/bin/black` + `.venv/bin/flake8 --select=F` — чисто

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile {FILES}`
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 6, Next Action: Шаг 6
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(dashboard): шапка «Свободно сегодня» + стили щитка + вход в профиль [protocol-0028/05]"`
7. Push
8. Отчёт
