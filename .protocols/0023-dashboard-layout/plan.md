# 0023-dashboard-layout — Dashboard Layout Redesign (Batch 5.3)

## ADR-style Summary

- **Context**: Epic-05-UI Batch 5.3. Dashboard нуждается в финальной перестройке layout: split таблиц операций, правая колонна с Wishlist + Cushion, sidebar в card, модал сверки на Dashboard, пустые состояния.
- **Problem Statement**: Dashboard layout не соответствует спецификации: операции в одной таблице, нет правой колонны, reconciliation доступен только с Calendar, sidebar без card-контейнера, нет пустых состояний.
- **Decision**: Реализовать по solution-v3 из .design/epic-05-ui-batch-3/: глобализация reconciliation modal через global-transaction-trigger, readonly cushion card в dashboard.py (без дублирования ID), sidebar с callback active highlight, split таблиц 50/50, пустые состояния с CTA.
- **Alternatives**: (1) Оставить reconciliation на Calendar -- отклонено (UX friction). (2) Переиспользовать _build_cushion_card() из goals.py -- отклонено (duplicate ID конфликт). (3) Layout 9/3 вместо 8/4 -- отклонено (ломает wishlist widget width).
- **Consequences**: Dashboard полностью соответствует спецификации. Calendar теряет calendar-refresh-trigger (замена на global-transaction-trigger). 11 файлов изменяются.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Formatters + DashboardService](./01-service-layer.md)**: format_date_human(), get_upcoming_transactions(), рефакторинг get_recent_transactions(), unit тесты
- **[Шаг 2: Reconciliation глобализация](./02-reconciliation.md)**: Удаление calendar-refresh-trigger, рефакторинг apply_reconciliation Output, перенос modal в main.py
- **[Шаг 3: Dashboard UI rebuild](./03-dashboard-ui.md)**: _build_transactions_split_table, _build_empty_state, _build_cushion_card_readonly, layout перестройка, callbacks
- **[Шаг 4: Sidebar + Transactions](./04-sidebar-transactions.md)**: Sidebar card + active highlight callback, transactions query params
- **[Шаг 5: CSS + Финализация](./05-finalize.md)**: CSS стили, black/flake8/pytest, PR Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0023-dashboard-layout`
- Протокол: `.protocols/0023-dashboard-layout/`

**Вся работа ведётся из CWD.**

### Цикл выполнения шага

См. `~/.claude/templates/protocol/workflow.md.tpl`

### Формат отчёта

См. `~/.claude/templates/protocol/report-format.md.tpl`

---

## Generic Principles

См. `~/.claude/templates/protocol/principles.md.tpl`

---

## Reference Materials

- `.design/epic-05-ui-batch-3/solution-v3.md` — финальное архитектурное решение
- `.design/epic-05-ui-batch-3/brief.md` — требования
- `.design/epic-05-ui-batch-3/critique-v2.md` — финальная критика (5/5 READY)
- `.reports/epics/epic-05-ui/dashboard_ui_spec.md` — UI спецификация
