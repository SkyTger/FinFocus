# 0011-chips-bulk-export — Chips + Bulk + Export UI

## ADR-style Summary

- **Context**: Батч 3.2 завершен, но при merge потеряны UI компоненты для быстрой категоризации (chips), массовых операций (bulk actions) и экспорта (CSV). Backend методы готовы: `bulk_update_category`, `export_to_csv`, `get_frequent_for_type`.
- **Problem Statement**: Для транзакций без категории нет быстрого способа присвоить категорию. Пользователь вынужден открывать модал редактирования для каждой транзакции. Нет bulk операций и экспорта.
- **Decision**: Реализовать solution-v2 из `.design/`: chips UI, bulk selection с WYSIWYG, export CSV. Все Pattern-Matching callbacks с 3-уровневыми guard clauses по ADR-003.
- **Alternatives**: Server-side bulk (отвергнут — меньше гибкости), virtualized table (отложен на Batch 4)
- **Consequences**: +280 строк в transactions.py, улучшение UX категоризации, готовность к MVP launch

---

## Замечания из Critique v2 (включить в реализацию)

1. **ВАЖНО**: Добавить `prevent_initial_call=True` в `toggle_bulk_panel` callback
2. **ВАЖНО**: Guard для TRANSFER/ADJUSTMENT типов в `_build_chips_cell()` — chips не показывать
3. **ЖЕЛАТЕЛЬНО**: Сброс "Select All" checkbox при очистке selection через filter change
4. **ОПЦИОНАЛЬНО**: TODO комментарий для замены user_id=1

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Layout + Helpers](./01-layout-helpers.md)**: dcc.Store, Export button, Bulk Panel, helper functions
- **[Шаг 2: Table + Chips](./02-table-chips.md)**: Checkboxes в таблице, chips cell для некатегоризированных
- **[Шаг 3: Chips Callbacks](./03-chips-callbacks.md)**: chip_assign, chip_dropdown, load_frequent_categories
- **[Шаг 4: Bulk Callbacks](./04-bulk-callbacks.md)**: selection state, filter change clear, toggle panel, bulk assign
- **[Шаг 5: Export + Tests](./05-export-tests.md)**: export callback, unit tests
- **[Шаг 6: Финализация](./06-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0011-chips-bulk-export`
- Протокол: `.protocols/0011-chips-bulk-export/`

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

- **Design**: `PROJECT_ROOT/.design/solution-v2.md` — архитектурное решение (5/5 ⭐)
- **Critique**: `PROJECT_ROOT/.design/critique-v2.md` — замечания для учёта
- **Brief**: `PROJECT_ROOT/.design/brief.md` — требования
- **ADR-003**: Pattern-Matching guard clauses (обязательны!)
- **Backend**: `app/services/transaction_service.py`, `app/services/category_service.py`
- **CSS**: `app/assets/transactions.css` — стили готовы
