# 0018-budget-reservation-bugfix — Исправление переиспользования шаблонов резервирования

## ADR-style Summary

- **Context**: При переключении режима резервирования (fixed_date → from_balance → fixed_date) создавался новый recurring шаблон с новым ID. Exceptions, привязанные к старому template_id, становились orphan и игнорировались. Это приводило к потере информации о досрочных взносах.
- **Problem Statement**: Два бага: (1) внесённые ранее суммы не учитываются при переключении режимов, (2) exception сбрасывается после переключения режимов.
- **Decision**: Переиспользовать существующий шаблон при совпадении дня, добавить recalculate_current_month_exception() для пересчёта при изменении взносов/бюджета.
- **Alternatives**: Event-driven пересчёт через signals — отклонено как overcomplicated для MVP.
- **Consequences**: ~250 строк нового кода в BudgetReservationService, GoalService. Сохранение консистентности exceptions при любых переключениях режимов.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Helper методы](./01-helper-methods.md)**: _find_any_reserve_template, _get_template_day, _get_reserve_date_for_month, _delete_exception_for_date
- **[Шаг 2: recalculate метод](./02-recalculate-method.md)**: recalculate_current_month_exception с reference_date параметром
- **[Шаг 3: cleanup + logging](./03-cleanup-logging.md)**: _cleanup_orphan_exceptions с логированием
- **[Шаг 4: set_mode модификация](./04-set-mode.md)**: Логика переиспользования шаблона
- **[Шаг 5: get_budget_progress](./05-budget-progress.md)**: Унификация расчёта used_budget
- **[Шаг 6: GoalService](./06-goal-service.md)**: delete_contribution с lazy import
- **[Шаг 7: Callbacks интеграция](./07-callbacks.md)**: save_budget + update_contribution_transaction
- **[Шаг 8: Unit тесты](./08-unit-tests.md)**: Тесты для новых методов
- **[Шаг 9: Integration тесты](./09-integration-tests.md)**: E2E тесты calendar + reservation
- **[Шаг 10: Финализация](./10-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0018-budget-reservation-bugfix`
- Протокол: `.protocols/0018-budget-reservation-bugfix/`

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

- **Спецификация:** `.reports/epics/epic-04-advanced/spec-budget-reservation-bugfix.md`
- **Brief:** `.design/brief.md`
- **Solution v3:** `.design/solution-v3.md` (финальная версия)
- **Critique v3:** `.design/critique-v3.md` (5/5 — готов к реализации)
- **Существующий код:** `app/services/budget_reservation_service.py`, `app/services/goal_service.py`
