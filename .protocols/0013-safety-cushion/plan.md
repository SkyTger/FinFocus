# 0013-safety-cushion — Финансовая подушка безопасности

## ADR-style Summary

- **Context**: В MVP планировщика бюджета отсутствует функционал финансовой подушки безопасности — резервного фонда для непредвиденных расходов.
- **Problem Statement**: Пользователям нужен инструмент для планирования и отслеживания резервного фонда с визуализацией прогресса и порога риска.
- **Decision**: Реализовать подушку как 3 поля в User (не Goal), отдельный CushionService, карточку и модал на странице /goals. Percent NewType для type safety.
- **Alternatives**: (1) Подушка как Goal — отвергнуто, т.к. подушка не участвует в распределении бюджета. (2) Отдельная таблица Cushion — излишне для MVP single-user.
- **Consequences**: Простая модель данных, быстрая реализация, возможность расширения в будущем (календарная визуализация в протоколе 4.2).

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Schema + Model](./01-schema-model.md)**: TypedDicts (cushion.py) + 3 поля в User
- **[Шаг 2: CushionService](./02-cushion-service.md)**: Сервис с CRUD методами
- **[Шаг 3: Unit Tests](./03-unit-tests.md)**: Тесты для CushionService (15+ тестов)
- **[Шаг 4: Карточка UI](./04-card-ui.md)**: Карточка подушки на /goals
- **[Шаг 5: Модал UI](./05-modal-ui.md)**: Модал настройки с калькулятором сценариев
- **[Шаг 6: Callbacks](./06-callbacks.md)**: 9 callbacks для модала и карточки
- **[Шаг 7: CSS](./07-css.md)**: Стили .cushion-*
- **[Шаг 8: Финализация](./08-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0013-safety-cushion`
- Протокол: `.protocols/0013-safety-cushion/`

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
- **Solution v3**: `.design/solution-v3.md`
- **ADR-003**: Guard clauses pattern для Dash callbacks
