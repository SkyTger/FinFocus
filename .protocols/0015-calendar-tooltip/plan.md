# 0015-calendar-tooltip — Tooltip для дней календаря

## ADR-style Summary

- **Context**: В кассовом календаре пользователь видит только иконки операций и баланс, но не детали. Нужен быстрый способ просмотра списка операций дня без открытия модала.
- **Problem Statement**: Как показать детальную информацию о дне при наведении без конфликта с существующим кликом (создание операции)?
- **Decision**: CSS-only hover tooltip как sibling элемент к кликабельной области. Expand через CSS checkbox hack. На mobile — отключен.
- **Alternatives**: (1) dbc.Tooltip — не поддерживает кликабельные элементы внутри. (2) Callback-based — server round-trip задержка.
- **Consequences**: Zero server calls на hover/expand. Glassmorphism стиль. Требует расширения TransactionInfo.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Extend TransactionInfo](./01-extend-transaction-info.md)**: Добавить is_skipped и category_icon поля
- **[Шаг 2: CSS Styles](./02-css-styles.md)**: Glassmorphism tooltip стили с checkbox hack
- **[Шаг 3: DOM Restructure](./03-dom-restructure.md)**: Sibling structure в build_day_cell()
- **[Шаг 4: Tooltip Builder Functions](./04-tooltip-builders.md)**: _build_day_tooltip, _build_tooltip_balance, _build_tooltip_transaction_row
- **[Шаг 5: Edit Callback](./05-edit-callback.md)**: Pattern-Matching callback для клика по операции
- **[Шаг 6: Unit Tests](./06-unit-tests.md)**: Тесты для tooltip функций
- **[Шаг 7: Финализация](./07-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0015-calendar-tooltip`
- Протокол: `.protocols/0015-calendar-tooltip/`

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

- `.design/brief.md` — требования к tooltip
- `.design/solution-v3.md` — финальное архитектурное решение
- `app/components/calendar.py` — текущая реализация календаря
- `app/services/calendar_service.py` — TransactionInfo TypedDict
- `app/utils/formatters.py` — ICON_TO_EMOJI mapping
