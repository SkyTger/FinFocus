# Review Log: 0026-onboarding-refresh

> Журнал ревью. Записи только добавляются.

---

### Step 1-m — CI/CD
- gh pr checks 26: pytest (3.10) pass, pytest (3.12) pass. Блокеров нет.

### Step 2-m — Локальная верификация
- pytest: 564 passed (полный прогон из worktree).
- flake8 app/ tests/: только предсуществующие E501 (6 в app/ — были в main).
- black --check: app/ чист (56 файлов); в tests/ 1 неотформатированный файл
  (test_migration_007.py) — предсуществующий в main, вне scope, не трогаем
  (проектная норма — black app/).

### Step 2.5-m — Security
- bandit -r app/ -q: 0 находок.
- pip-audit -r requirements.txt: 5 известных уязвимостей в 3 пакетах —
  python-dotenv 1.0.0 (PYSEC-2026-2270, fix 1.2.2),
  flask 3.0.3 (PYSEC-2026-2151, fix 3.1.3),
  werkzeug 3.0.6 (PYSEC-2026-2046/2044/2320, fix 3.1.4-3.1.6).
  ВСЕ предсуществующие: requirements.txt протоколом не менялся.
  НЕ чинить в этом протоколе: бамп flask/werkzeug упирается в пины Dash —
  отдельная задача обновления зависимостей. Передано владельцу
  (кандидат в ROADMAP / открытые вопросы).
- Инструментальная заметка: bandit/black из ~/.local/bin сломаны
  (шебанг на удалённую anaconda) — ставили в scratchpad-venv.

### Step 3-m — Code Review (субагент code-reviewer, независимое ревью)
- **Критичная находка (подтверждена)**: update_dashboard_greeting —
  отдельный колбэк с Output на элемент, существующий только на странице
  дашборда, при глобальном Input (Store profile-updated). Это в точности
  альтернатива, ОТКЛОНЁННАЯ в 0024 plan.md (ADR Alternatives п.2:
  «ReferenceError для динамических элементов»); риск — JS-ошибка при
  правке профиля с других страниц. Юнит-тесты класс проблемы поймать
  не могли (не рендерят DOM) — анти-Гудхарт.
- **Фикс (3-m-fix)**: колбэк update_dashboard_greeting удалён; приветствие —
  7-й Output существующего load_dashboard_data (уже подписан на
  profile-updated, pathname-guard отсекает чужие страницы до записи в DOM;
  его Output-набор и так живёт только на дашборде — новых рисков нет).
  Хелпер _build_greeting_text() переиспользуется layout'ом (устранено
  дублирование inline-чтения). Docstring объясняет «почему» (находка №6).
- Мелкие находки закрыты: №4 — contract-тесты переименованы
  (..._decorator_declares_..., честно про «текст кода, не поведение»),
  общий хелпер _decorator_source(); №5 — test_dismissed_keeps_banner_hidden
  мокает get_db_session + докстринг про short-circuit; №3 — снята
  (колбэк удалён, fallback-семантика хелпера как в исходном layout).
- Тесты переработаны: 10 тестов (contract 3 + greeting helper 2 +
  toggle 3 + load_dashboard_data greeting 2). Полный прогон: 563 passed.
- Plan vs факт: контракт High-Level Plan соблюдён; отступление от
  01-step (отдельный колбэк → 7-й Output) — итог ревью, задокументировано
  здесь и в докстрингах.

### Step 3.5-m — Fidelity-гейт
- Пропущен: протокол ад-хок (из отчёта аудита 2026-08-20), спеки эпика
  нет. Эталон — сам отчёт аудита, сверка выполнена в 3-m.
