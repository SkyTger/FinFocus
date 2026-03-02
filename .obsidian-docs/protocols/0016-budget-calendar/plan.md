# 0016-budget-calendar — Интеграция бюджета целей с кассовым календарём

## ADR-style Summary

- **Context**: FinFocus MVP имеет систему накопительных целей с monthly_savings_budget, но бюджет не отражается в кассовом календаре. Пользователь не видит, как накопления влияют на остатки по дням.
- **Problem Statement**: Как связать бюджет накоплений с календарём, чтобы пользователь видел влияние резервирования на остаток и мог выбирать удобный режим резервирования?
- **Decision**: Два режима резервирования: "fixed_date" (recurring операция "Резерв на цели") и "from_balance" (операции при взносах). Новый BudgetReservationService, два TransactionType (SAVINGS_RESERVE, SAVINGS_CONTRIBUTION), FK связь GoalContribution → Transaction.
- **Alternatives**: (1) Отдельная таблица reservations — отвергнуто (усложняет синхронизацию); (2) Описание в Transaction.description без FK — отвергнуто (хрупкая связь)
- **Consequences**: (+) Полная интеграция бюджета с календарём; (+) Гибкость режимов; (-) Сложность синхронизации при edit/delete; (-) 2 новых TransactionType увеличивают case-handling

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Database Schema](./01-schema.md)**: TransactionType enum, User поля, GoalContribution FK, миграция
- **[Шаг 2: BudgetReservationService Core](./02-service-core.md)**: TypedDicts, get_settings, set_mode, get_budget_progress
- **[Шаг 3: BudgetReservationService CRUD](./03-service-crud.md)**: create/update/delete contribution transactions, sync_template_amount
- **[Шаг 4: CalendarService Integration](./04-calendar-integration.md)**: Добавить SAVINGS_RESERVE/CONTRIBUTION в расчёты баланса
- **[Шаг 5: GoalService Integration](./05-goal-integration.md)**: Расширить add_contribution для создания транзакций
- **[Шаг 6: Goals UI](./06-goals-ui.md)**: Карточка бюджета, расширенный модал настройки
- **[Шаг 7: Calendar UI](./07-calendar-ui.md)**: Визуализация SAVINGS_RESERVE/CONTRIBUTION, edit/delete callbacks
- **[Шаг 8: Финализация](./08-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0016-budget-calendar`
- Протокол: `.protocols/0016-budget-calendar/`

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

- **Brief**: `.design/brief.md`
- **Solution**: `.design/solution-v2.md`
- **Spec**: `.reports/epics/epic-04-advanced/spec-budget-calendar-integration.md`
- **Existing patterns**: ADR-003 (guard clauses), ADR-004 (recurring transactions)
- **Related services**: RecurringService, GoalService, CalendarService
