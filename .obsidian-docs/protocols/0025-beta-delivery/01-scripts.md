# Шаг 1: Requirements + Start Scripts

## Briefing

- **Цель:** Разделить зависимости на runtime/dev, создать start.sh и start.bat
- **Ключевые файлы:**
  - `requirements.txt` — EDIT: убрать pytest, pytest-cov, black, flake8
  - `requirements-dev.txt` — CREATE: `-r requirements.txt` + dev tools
  - `start.sh` — CREATE: bash-скрипт для Linux/macOS
  - `start.bat` — CREATE: batch-скрипт для Windows
- **Доп. информация:** Архитектура из `.obsidian-docs/design/epic-09-phase-3/solution-v2.md`

## Sub-tasks

1. **requirements.txt** — убрать 4 dev-зависимости (pytest, pytest-cov, black, flake8)
2. **requirements-dev.txt** — создать с `-r requirements.txt` + 4 dev-зависимости
3. **start.sh** — создать полный bash-скрипт по псевдокоду из solution-v2:
   - `#!/usr/bin/env bash`, `set -euo pipefail`
   - find_python (python3 → python fallback, >= 3.10)
   - check_venv_package (Ubuntu `python3-venv`)
   - ensure_venv (`.venv/`)
   - ensure_deps (маркер `.venv/.deps_installed` + `-nt` mtime check)
   - check_port (ss → lsof → netstat fallback)
   - open_browser (xdg-open → open fallback, background)
   - trap cleanup INT TERM (kill browser PID)
   - Русские сообщения, цветной вывод
   - `chmod +x start.sh`
4. **start.bat** — создать полный batch-скрипт по псевдокоду из solution-v2:
   - `chcp 65001`, `setlocal EnableDelayedExpansion`
   - py -3 → python fallback, version parsing через `for /f`
   - `if not defined PORT set "PORT=8050"` (КРИТИЧНО: не `set "PORT=8050"`)
   - venv check: `if exist .venv\Scripts\python.exe`
   - deps marker: `xcopy /D /L` для сравнения дат
   - port check: `netstat -an | findstr`
   - `pause` при ошибке (goto :exit_with_pause)
   - `start "" http://localhost:%PORT%` для браузера

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/main.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: Шаг 2
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(delivery): add start scripts and split requirements [protocol-0025/01]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
