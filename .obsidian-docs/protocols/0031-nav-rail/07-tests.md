# Шаг 7: Тесты полоски

## Briefing

- **Цель:** `tests/test_nav_rail.py` **параллельно ещё живому** `tests/test_sidebar.py` — двух шагов без регрессионного якоря C-1 быть не должно.
- **Ключевые файлы:**
  - `tests/test_nav_rail.py` — **НОВЫЙ**
  - `tests/test_sidebar.py` — образец переносимых классов, пока НЕ удаляется
- **Доп. информация:** Урок протокола 0029 — визуальный слой тестами не покрывается, и тест этого не скрывает.

## Sub-tasks

1. `TestRenderNavRailSlotContract` — ровно два Input'а на `url` и `profile-updated`; в декораторе не упомянут ни один узел полоски; на дашбордных путях `[]` без открытия сессии.

2. `TestNoCallbacksInNavRailModule` — **регрессионный якорь C-1/AC-11**: `"@callback" not in inspect.getsource(nav_rail)`; функций `create_sidebar`/`highlight_active_sidebar`/`update_sidebar_profile` в модуле нет.

3. `TestCreateNavRailPure` — эмодзи аватара в дереве; ровно один активный слот на каждом из четырёх разделов; `get_db_session` в модуле отсутствует (NFR-1); «Настройки», `/settings`, `v1.0.0` в дереве отсутствуют (FR-4/FR-5/AC-9); множество `href` совпадает с маршрутами `display_page` (FR-4: попасть на несуществующий маршрут из навигации нельзя); `len(RAIL_SECTIONS) == 4`.

4. `TestFailOpenProfile` — перенос из `test_sidebar.py`.

5. **`TestNavRailStructureStable`** — вокруг фактического механизма Dash:
   - (а) `create_nav_rail` возвращает `html.Div` с `id == "nav-rail"` для всех пяти pathname (`None`, `/`, `/calendar`, `/transactions`, `/analytics`, `/goals`);
   - (б) `render_nav_rail_slot` возвращает **ровно один компонент, не список** на не-дашбордных путях и `[]` на дашбордных — фиксирует стабильность позиции;
   - (в) ни `"nav-rail"`, ни `"nav-rail-avatar"` не встречаются в декораторах **серверных** колбэков (единственное разрешённое упоминание — clientside-триггер аватара в `main.py`);
   - (г) проп `key` в дереве не используется.
   **Докстринг класса — честный:** тест фиксирует **предпосылки** механизма (стабильный React-ключ через `id`, единственность ребёнка слота, отсутствие серверных колбэков). Сам разворот и его непереигрывание проверяются **только живьём** — шаг 1 и шаг 8. Зелёный тест не означает, что AC-5 выполнен.

6. `TestNavRailAccessibility` — у логотипа, четырёх слотов и аватара непустое доступное имя; `aria-current="page"` ровно на одном слоте; у аватара есть язычок «Профиль».

7. `TestNavRailProfileEntry` — в дереве есть `id="nav-rail-avatar"` с `n_clicks`; `main.py` регистрирует clientside-триггер именно на него; серверного Input на него нет (C-3).

## Workflow

1. Выполни Sub-tasks
2. `.venv/bin/python -m pytest tests/test_nav_rail.py -v`
3. `.venv/bin/python -m pytest` — весь прогон, `test_sidebar.py` ещё жив и должен быть зелёным
4. Обнови `log.md`, `context.md` (Current Step 8)
5. Коммит: `test(nav-rail): тесты полоски и регрессионный якорь [protocol-0031/07]`
6. Push, отчёт
