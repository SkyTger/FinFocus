# 0017-budget-ui-improvements — Улучшение UI бюджета накоплений + механика fixed_date

## ADR-style Summary

- **Context**: Протокол 0016 реализовал интеграцию бюджета целей с календарём, но выявлены проблемы: непонятный текст "Резерв на цели: Авто", дублирование UI (две карточки), задержка refresh, и взносы до даты резерва не уменьшают сумму резервирования.
- **Problem Statement**: Как улучшить UX бюджета накоплений и реализовать корректное поведение при досрочных взносах в режиме fixed_date?
- **Decision**: (1) Изменить текст на "Резервирование бюджета"; (2) Удалить верхнюю карточку, объединить в "Сводку по целям" с форматом "X / Y ₽"; (3) При взносе до даты резерва — создавать Exception для recurring с уменьшенной суммой.
- **Alternatives**: (1) Обновлять шаблон вместо Exception — отвергнуто (проблема с расчётом следующего месяца); (2) Виртуальный расчёт при рендере — отвергнуто (производительность).
- **Consequences**: (+) Чистый UX без дублирования; (+) Корректное резервирование с учётом досрочных взносов; (-) Сложность пересчёта Exception при удалении/редактировании взносов.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: UI Description](./01-ui-description.md)**: Изменить RESERVE_DESCRIPTION на "Резервирование бюджета"
- **[Шаг 2: Remove Budget Card](./02-remove-budget-card.md)**: Удалить верхнюю карточку "Бюджет накоплений (месяц)"
- **[Шаг 3: Update Summary Section](./03-update-summary.md)**: Обновить "Сводку по целям" с форматом "X / Y ₽"
- **[Шаг 4: Fixed Date Mechanism](./04-fixed-date-mechanism.md)**: Реализовать adjust_reserve_for_contribution()
- **[Шаг 5: Integration & Tests](./05-integration-tests.md)**: Интеграция с GoalService + unit/integration тесты
- **[Шаг 6: Финализация](./06-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0017-budget-ui-improvements`
- Протокол: `.protocols/0017-budget-ui-improvements/`

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

- **Спецификация**: `.reports/epics/epic-04-advanced/spec-budget-ui-improvements.md`
- **Протокол 0016**: `.protocols/0016-budget-calendar/`
- **BudgetReservationService**: `app/services/budget_reservation_service.py`
- **RecurringService (exceptions)**: `app/services/recurring_service.py:283-310`
- **GoalService**: `app/services/goal_service.py`
- **Goals UI**: `app/components/goals.py`
