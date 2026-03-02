# 0022-daily-cashflow-chart — Daily & Yearly Cashflow Chart

## ADR-style Summary

- **Context**: Dashboard батч 5.2 (Epic-05-UI) — центральный график кассового календаря. Текущий dashboard показывает агрегированный bar chart по месяцам через `get_cashflow_data()`. Нужен дневной grouped bar chart с линией running balance, маркером минимума, hover tooltip, клик→создание операции, полноценный Year mode.
- **Problem Statement**: Нет дневной визуализации cashflow на Dashboard. Нет Year mode с end-of-month balance. Нет клика по дню для быстрого создания операции.
- **Decision**: Добавить `get_daily_cashflow()` и `get_yearly_cashflow()` в DashboardService, новый public API `CalendarService.get_recurring_income_expense_by_day()`, Plotly grouped bars + balance line для обоих режимов, helper `_load_dashboard_components()` для устранения дублирования callbacks.
- **Alternatives**: (1) Единый Y-axis → отклонён (разный масштаб bars vs balance). (2) Protected access к CalendarService → отклонён (blocker из critique). (3) Year mode stub → отклонён (решение пользователя: полный Year mode).
- **Consequences**: +8 файлов (~940 строк), 16 новых тестов, CalendarService расширен публичным API. Старый `build_cashflow_chart()` сохраняется, но не используется из Dashboard callbacks.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Schema + CalendarService](./01-schema-calendar.md)**: TypedDicts, константы, CalendarService public method
- **[Шаг 2: DashboardService](./02-dashboard-service.md)**: get_daily_cashflow(), get_yearly_cashflow(), private helpers
- **[Шаг 3: Unit тесты](./03-unit-tests.md)**: 16 unit тестов (12 daily + 4 yearly)
- **[Шаг 4: Charts + Integration](./04-charts-integration.md)**: Plotly chart builders, _load_dashboard_components(), callbacks, transaction_modals
- **[Шаг 5: Финализация](./05-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0022-daily-cashflow-chart`
- Протокол: `.protocols/0022-daily-cashflow-chart/`

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

- **Solution**: `.design/epic-05-ui-batch-2/solution-v2.md` (в PROJECT_ROOT)
- **Brief**: `.design/epic-05-ui-batch-2/brief.md` (в PROJECT_ROOT)
- **Critique**: `.design/epic-05-ui-batch-2/critique-v2.md` (в PROJECT_ROOT)
- **UI Spec**: `.reports/epics/epic-05-ui/dashboard_ui_spec.md`
- **Batch Spec**: `.reports/epics/epic-05-ui/batch-2.md`
- **Knowledge Bank**: `.knowledge-bank/modules/services.md`, `.knowledge-bank/modules/schema.md`
