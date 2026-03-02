# 0014-onboarding-wizard — Onboarding Wizard with Balance Setup

## ADR-style Summary

- **Context**: FinFocus требует корректной настройки starting_balance для точных расчетов кассового календаря. Новые пользователи часто пропускают этот шаг.
- **Problem Statement**: Как обеспечить настройку starting_balance при первом входе без блокировки опытных пользователей?
- **Decision**: Blocking modal-wizard при first_launch=True + Toast на Dashboard для пользователей с balance=0
- **Alternatives**:
  - Inline форма на Dashboard (отклонено: легко пропустить)
  - Принудительный redirect на Settings (отклонено: плохой UX)
- **Consequences**:
  - (+) Гарантированный onboarding flow
  - (+) Toast как мягкое напоминание
  - (-) Дополнительная сложность в calendar.py (query param handler)

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Schema + Model](./01-schema-model.md)**: User.first_launch + OnboardingStatus TypedDict
- **[Шаг 2: Migration Script](./02-migration.md)**: scripts/migrate_first_launch.py
- **[Шаг 3: OnboardingService](./03-service.md)**: get_status, complete_with_balance, skip
- **[Шаг 4: Unit Tests](./04-tests.md)**: 8+ тестов для OnboardingService
- **[Шаг 5: Wizard UI](./05-wizard-ui.md)**: Modal с backdrop="static"
- **[Шаг 6: Wizard Callbacks](./06-wizard-callbacks.md)**: check_onboarding_and_validate, handle_onboarding_action
- **[Шаг 7: main.py Integration](./07-main-integration.md)**: Global wizard + stores
- **[Шаг 8: Dashboard Toast](./08-dashboard-toast.md)**: Toast + callbacks
- **[Шаг 9: Calendar Query Param](./09-calendar-query.md)**: Auto-open reconciliation modal
- **[Шаг 10: CSS Styles](./10-css.md)**: onboarding.css
- **[Шаг 11: Финализация](./11-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0014-onboarding-wizard`
- Протокол: `.protocols/0014-onboarding-wizard/`

**Вся работа ведётся из CWD.**

### Цикл выполнения шага

См. `.protocols/_core/workflow.md` или `~/.claude/templates/protocol/workflow.md.tpl`

### Формат отчёта

См. `.protocols/_core/report-format.md` или `~/.claude/templates/protocol/report-format.md.tpl`

---

## Generic Principles

См. `.protocols/_core/principles.md` или `~/.claude/templates/protocol/principles.md.tpl`

---

## Reference Materials

- **Brief**: `.design/brief.md` (в PROJECT_ROOT, untracked)
- **Solution v3**: `.design/solution-v3.md` (approved 5/5)
- **Existing patterns**:
  - ADR-003 guard clauses
  - Preselection Store Pattern (quick-add chips)
  - Refresh Trigger Pattern (transaction_modals.py)
- **Related files**:
  - `app/models/database.py` — User model
  - `app/components/calendar.py` — Reconciliation modal
  - `app/components/dashboard.py` — Toast target
