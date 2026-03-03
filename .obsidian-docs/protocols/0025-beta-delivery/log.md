# Work Log: 0025-beta-delivery — Delivery & Setup for Beta Testers

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0025#ctx-N -->
Restore context: protocol-0025#ctx-1

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->

### Step 01 — Requirements + Start Scripts
- Разделены requirements: runtime (requirements.txt) / dev (requirements-dev.txt)
- Создан start.sh: Python 3.10+ check, venv, deps marker, port check, trap handler, цветной вывод
- Создан start.bat: py -3/python fallback, version parsing, venv, deps marker (xcopy /D /L), netstat port check, pause on error
- shellcheck недоступен в окружении — пропущено

### Step 02 — Документация
- Создан BETA_README.md: 3 шага установки, 6 FAQ, раздел bug report с ссылкой на GitHub issues
- Создан docs/RELEASE_GUIDE.md: tag format v0.9.0-beta.N, git archive команда, шаблон Release Notes, checklist

### Step 03 — Финализация
- Верификация: black (1 файл reformatted — goals.py, pre-existing), flake8 (6 E501 pre-existing), pytest 546 passed / 6+1 failed (все pre-existing на main)
- PR переведён в Ready
