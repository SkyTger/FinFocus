# Память проекта FinFocus

<!-- Одна строка на заметку: - [Заголовок](file.md) — крючок. С 2026-09-02 память живёт в репозитории (.claude/settings.json → autoMemoryDirectory); домашний каталог — заглушка -->

## Key Learnings

### Dash `suppress_callback_exceptions` does NOT prevent client-side ReferenceError
- `suppress_callback_exceptions=True` only suppresses **server-side** layout validation
- The **client-side renderer** (`dash-renderer.js`) still throws `ReferenceError` when resolving callback Inputs against the DOM
- This affects ALL callbacks with Inputs referencing elements that don't exist in the initial layout (multi-page apps, dynamically-rendered elements)
- **Solution**: Use `clientside_callback` (JS) for dynamically-rendered elements that just write to a Store (timestamp trigger pattern). Clientside callbacks with `prevent_initial_call=True` handle missing DOM elements gracefully.
- See: `app/components/dashboard.py` (KPI recon button, empty state buttons) and `app/components/calendar.py` (calendar recon button)


### Протухание дат в тестах
- [Протухание дат в тестах](tests-calendar-rot.md) — 8 падений в августе 2026 были из-за захардкоженных дат в тестах, а не из-за точности Decimal; в conftest.py есть хелперы относительных дат

### Открытые вопросы
- [Открытые вопросы припаркованы](open-questions-parked.md) — в ROADMAP.md, секция «Открытые вопросы» (9 пунктов на 2026-08-21), не в автопамяти; №7 закрыт 2026-08-23 (концепция «щиток», design.md в архиве обсуждений), №9 — в работе (остались пп. 5/7 аудита: жизненный цикл целей)

### Общение / статус проекта
- [Личный проект — без карточки в трекере](personal-project-no-tracker-card.md) — решение 2026-09-02: на доску не заводить, «кандидат на диске» = ложное срабатывание
- [Обращение на «ты»](communication-style.md) — явная просьба пользователя (2026-08-20)

### Консилиум
- [Консилиум](consilium.md) — сохранённый сценарий экспертов+критика, состав в reports/notes/consilium-roster.md

### Аудиты
- [Двойной аудит 2026-08-20](ux-audit-2026-08.md) — UX + код: отчёты, демо графика «деньги с именами»; ждёт решений владельца → protocol-new

### Режим co-pilot (ведение настоящего бюджета)
- [Режим co-pilot](budget-copilot-mode.md) — с 2026-09-04 владелец ведёт в приложении свой настоящий бюджет; точка входа `.obsidian-docs/budget/state.md`; боевая база `data/finfocus.db` с живыми данными
- [Ловушки разбора выписок](budget-analysis-pitfalls.md) — проверять итог сложением всех операций по всем картам; названия операций врут

### Project conventions
- [loguru игнорирует exc_info](loguru-exc-info.md) — трейсбек только через `logger.opt(exception=True)`; старые exc_info в коде «пустые» (п.10 аудита)
- 928 unit tests в main (2026-09-05, после батча 29 «заплатки-параллель»); падений «по умолчанию» нет
- Always run black + flake8 after changes; [black только из .venv](black-version-pin.md) — системный black 26.x форматирует иначе
- ROADMAP.md = Single Source of Truth (located at `.obsidian-docs/ROADMAP.md`)
- Feature progress at `.obsidian-docs/reports/notes/feature_progress.md`

### Delivery decisions (Epic-09 Phase 3)
- Beta delivery: setup-скрипт (start.sh + start.bat) — решение протокола 0025
- ⚠️ УСТАРЕЛО частично: PyInstaller всё же внедрён (сборка Windows/macOS в CI,
  коммиты d9e93c6/3b6a8e0). Какой способ основной — открытый вопрос, см.
  [Открытые вопросы](open-questions-parked.md)
- Target audience: нетехнические пользователи, 3 платформы (Linux/Windows/macOS)
- App runs in browser (localhost:8050), not native window — acceptable for beta
- **Backlog**: Native window (flaskwebgui/pywebview) — deferred post-beta. Production packaging уже НЕ в backlog: PyInstaller реализован
