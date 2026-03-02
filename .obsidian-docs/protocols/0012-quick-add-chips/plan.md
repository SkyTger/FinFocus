# 0012-quick-add-chips — Quick-Add Chips for Transactions

## ADR-style Summary

- **Context**: После Батча 3 (Analytics & UX) создание операций требует 6 шагов. Quick-add chips позволят сократить до 3-4 шагов через предвыбранные категории.
- **Problem Statement**: Как ускорить ежедневный ввод частых операций (продукты, транспорт, зарплата)?
- **Decision**: Реализовать Quick-add chips (Протокол A) — 7 hardcoded чипов с предустановкой категории при открытии модала создания.
- **Alternatives**:
  1. Шаблоны операций (Протокол B) — более сложное решение, запланировано на следующий этап
  2. Автодополнение при вводе — менее визуальное, не даёт экономии кликов
- **Consequences**:
  - (+) Сокращение шагов создания операции с 6 до 3-4
  - (+) Визуальные подсказки частых категорий
  - (+) Фундамент для Протокола B (шаблоны)
  - (-) Hardcoded список (кастомизация в Протоколе B)

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Schema и константы](./01-schema-constants.md)**: TypedDict QuickAddChipData, DEFAULT_QUICK_ADD_CHIP_NAMES
- **[Шаг 2: UI секция Quick-add](./02-ui-quick-add-section.md)**: _build_quick_add_chip(), _build_quick_add_section(), интеграция в layout
- **[Шаг 3: Модал "Ещё..."](./03-more-modal.md)**: _build_category_more_modal() с tabs, динамическая загрузка категорий
- **[Шаг 4: Preselection механизм](./04-preselection.md)**: Stores в transaction_modals.py, callback set_preselection_on_modal_open
- **[Шаг 5: Callbacks Quick-add](./05-callbacks.md)**: open_create_from_quick_add, open_more_modal, select_from_more_modal
- **[Шаг 6: CSS стили](./06-css-styles.md)**: .qa-chip, .qa-chip-section, .qa-more-grid, responsive
- **[Шаг 7: Unit тесты](./07-tests.md)**: test_quick_add_chips.py (9 тестов)
- **[Шаг 8: Финализация](./08-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0012-quick-add-chips`
- Протокол: `.protocols/0012-quick-add-chips/`

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

- **Спецификация**: `.reports/epics/epic-04-advanced/spec-quick-add-chips.md`
- **Техническое решение**: `.design/solution-v3.md`
- **Brief**: `.design/brief.md`
- **ADR-003**: Pattern-Matching callbacks guard clauses
