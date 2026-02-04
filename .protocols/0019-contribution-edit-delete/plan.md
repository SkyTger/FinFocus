# 0019-contribution-edit-delete — Редактирование и удаление взносов в цели

## ADR-style Summary

- **Context**: GoalContribution можно только создавать — нет возможности отредактировать или удалить взнос. Существующий delete_contribution() содержит баг: не откатывает статус COMPLETED для fixed_date режима. SAVINGS_CONTRIBUTION кликабелен в calendar tooltip, что приводит к рассинхронизации данных.
- **Problem Statement**: Необходимо реализовать полноценное CRUD для взносов с каскадной синхронизацией GoalContribution ↔ Transaction ↔ Goal.current_amount ↔ Exception.
- **Decision**: Расширить GoalService методами update_contribution() и get_contribution_by_id(). Переписать delete_contribution() по Варианту A (прямое удаление без вызова delete_contribution_transaction()). Добавить Guard #6 в calendar tooltip. Добавить UI в goals.py.
- **Alternatives**: Вариант B (делегировать delete в BudgetReservationService) — отклонен из-за дублирования логики current_amount.
- **Consequences**: Полный lifecycle взносов, устранение data corruption при удалении, блокировка обхода через calendar.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Schema и GoalService helpers](./01-schema-helpers.md)**: TypedDicts + _get_budget_service() + get_contribution_by_id()
- **[Шаг 2: update_contribution() и fix delete_contribution()](./02-service-methods.md)**: Основная бизнес-логика с каскадной синхронизацией
- **[Шаг 3: Calendar Guard #6](./03-calendar-guard.md)**: Блокировка SAVINGS_CONTRIBUTION в tooltip
- **[Шаг 4: Goals UI](./04-goals-ui.md)**: Таблица с кнопками, модалы, callbacks
- **[Шаг 5: Unit тесты](./05-tests.md)**: 22+ тестов для service и guard
- **[Шаг 6: Финализация](./06-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0019-contribution-edit-delete`
- Протокол: `.protocols/0019-contribution-edit-delete/`

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

- **ADR-004**: `.memory-bank/adrs/ADR-004-contribution-edit-delete.md`
- **Brief**: `.design/brief.md` (8 FR, 3 NFR)
- **Solution v4**: `.design/solution-v4.md` (финальная архитектура)
- **Critique v4**: `.design/critique-v4.md` (5/5, READY)
- **Существующий GoalService**: `app/services/goal_service.py`
- **BudgetReservationService**: `app/services/budget_reservation_service.py` (delete_contribution_transaction, строки 786-806)
- **Calendar tooltip**: `app/components/calendar.py` (Guard #5, строка ~1030)
- **Goals UI**: `app/components/goals.py` (_build_contributions_table)
