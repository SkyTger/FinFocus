# Шаг 7: Переходы с контекстом

## Briefing

- **Цель:** контракт владения `url.search` по pathname + приёмники фокуса в календаре и целях с единой механикой идемпотентности.
- **Ключевые файлы:**
  - `app/main.py` — `handle_panel_query_params`, `_OWNED_SEARCH_PATHS`, три новых Store
  - `app/components/calendar.py` — приёмник `calendar-focus-date`
  - `app/components/goals.py` — приёмник `goals-focus-goal`, якорные id
  - `app/assets/calendar.css` — `.calendar-day-focused`
  - **не трогать**: `transactions.py`, `analytics.py` (C-1, приёмники уже есть)
- **Доп. информация:** solution-v4.md, план шаг 9 + секции «Владение `url.search`» и «Идемпотентность Store-фокусов».

## Sub-tasks

- [ ] `main.py`: три Store — `open-wishlist-trigger`, `calendar-focus-date`, `goals-focus-goal`; payload новых — **словарь** `{"value": …, "ts": …}` (ts нужен и для повторного клика, и как ключ идемпотентности)
- [ ] `_OWNED_SEARCH_PATHS = frozenset({"/calendar", "/goals"})` + докстринг: **почему** — второй читатель `url.search` (`apply_url_date_filter`, `transactions.py:1470-1520`) работает с протокола 0023 и в search не пишет; чистить его search = сломать фильтр периода
- [ ] `handle_panel_query_params`: разбор `open_recon`, `wishlist_item`, `focus_date`, `goal`; **`PreventUpdate` на `/transactions` и на всём остальном**; битые значения игнорировать молча; если ни один параметр не распознан — `PreventUpdate` (search не затирается)
- [ ] `calendar.py`: `Input("calendar-focus-date")` шестым Input'ом в существующий `load_and_navigate_calendar`; **двойной guard идемпотентности**: `ctx.triggered_id == "calendar-focus-date"` **И** `payload["ts"] != state.get("focus_applied_ts")`; ключи `focus_date`/`focus_applied_ts` в возвращаемый `calendar-state`; класс `calendar-day-focused` в `build_day_cell`
- [ ] **Ветку `except` (`:938-948`) НЕ править** — `focus_applied_ts` в неё намеренно не дописывается (после сбоя загрузки повторный клик должен сработать)
- [ ] `goals.py`: якорные id в `_build_goal_card` (`:618`), узел `goals-focus-anchor`, колбэк `apply_goal_focus` с **той же** механикой идемпотентности
- [ ] Логика разделов не переписывается (C-1): только новый Input, ключи в существующий Store, CSS-класс

## Workflow

1. Выполни Sub-tasks последовательно
2. Проверка: `python -m py_compile app/main.py app/components/calendar.py app/components/goals.py` + `pytest tests/test_calendar_service.py tests/test_goals_integration.py`
3. **Ручная проверка:** клик по группе операций → фильтр периода применён; F5 → без ошибки; клик «завтра» → календарь на завтра; **уйти в другой раздел и вернуться по меню → фокус НЕ переприменяется** (пролистать на октябрь, уйти, вернуться — октябрь остался)
4. Обнови `log.md`, `context.md`
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(ui): переходы с контекстом и контракт владения url.search [protocol-0030/07]"`
7. Push
8. Отчёт
