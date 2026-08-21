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
