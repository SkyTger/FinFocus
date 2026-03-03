# 0025-beta-delivery — Delivery & Setup for Beta Testers

## ADR-style Summary

- **Context**: FinFocus — веб-приложение на Dash, запускается через `python run.py`. Бета-тестеры (нетехнические пользователи) не знают терминал, pip, venv.
- **Problem Statement**: Нужен способ установки и запуска одним действием: скачал → запустил → работает.
- **Decision**: Два платформенных скрипта (start.sh + start.bat) с автоматической настройкой venv и зависимостей. Маркер-файл для идемпотентности. Проверка Python 3.10+ и порта перед запуском. BETA_README.md для инструкций.
- **Alternatives**: Python-based launcher (отклонён: chicken-and-egg), Docker (отклонён: сложен для целевой аудитории), PyInstaller (отклонён: сложная сборка Dash на 3 платформы)
- **Consequences**: Пользователи получают 1-click запуск при наличии Python 3.10+. Docker/PyInstaller/native window отложены в Backlog.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Requirements + Start Scripts](./01-scripts.md)**: Разделение зависимостей, создание start.sh и start.bat
- **[Шаг 2: Документация](./02-docs.md)**: BETA_README.md и docs/RELEASE_GUIDE.md
- **[Шаг 3: Финализация](./03-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0025-beta-delivery`
- Протокол: `.obsidian-docs/protocols/0025-beta-delivery/`

**Вся работа ведётся из CWD.**

### Цикл выполнения шага

См. `.obsidian-docs/protocols/_core/workflow.md` или `~/.claude/templates/protocol/workflow.md.tpl`

### Формат отчёта

См. `.obsidian-docs/protocols/_core/report-format.md` или `~/.claude/templates/protocol/report-format.md.tpl`

---

## Generic Principles

См. `.obsidian-docs/protocols/_core/principles.md` или `~/.claude/templates/protocol/principles.md.tpl`

---

## Reference Materials

- **Спецификация**: `.obsidian-docs/design/epic-09-phase-3/spec.md`
- **Архитектурное решение**: `.obsidian-docs/design/epic-09-phase-3/solution-v2.md`
- **Brief**: `.obsidian-docs/design/epic-09-phase-3/brief.md`
- **Критика**: `.obsidian-docs/design/epic-09-phase-3/critique-v2.md`
- **Валидация**: `.obsidian-docs/design/epic-09-phase-3/validation-v2.md`
