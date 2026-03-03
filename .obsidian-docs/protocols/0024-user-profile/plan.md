# 0024-user-profile — User Profile — Персонализация приложения

## ADR-style Summary

- **Context**: FinFocus готовится к бета-тестированию на реальных пользователях. Sidebar содержит хардкод "Иван Иванов" и "🦊", onboarding wizard спрашивает только баланс. Нужна персонализация: имя, аватарка, динамический sidebar, модал редактирования.
- **Problem Statement**: Приложение не персонализировано — пользователь не может задать имя и аватарку, sidebar статичен, нет возможности редактировать профиль после onboarding.
- **Decision**: Расширить User модель полем avatar_id, перестроить onboarding wizard (имя + аватарка + баланс), сделать sidebar динамическим через Store-based обновление, добавить глобальный profile modal. Dashboard greeting через inline read.
- **Alternatives**: (1) Отдельная страница /profile — отклонено (overkill для single-user). (2) Callback для dashboard greeting — отклонено (ReferenceError для динамических элементов). (3) Pattern-Matching Callbacks для аватарок — отклонено (RadioItems проще и нативнее).
- **Consequences**: 17 файлов изменяются/создаются. Обратная совместимость через deprecated wrapper complete_with_balance(). Store("profile-updated") как event bus для sidebar обновлений.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Data Layer](./01-data-layer.md)**: Конфиг аватарок, avatar_id в User модели
- **[Шаг 2: Migration + Bootstrap + Schema](./02-migration-bootstrap-schema.md)**: Миграция 007, bootstrap с avatar_id, TypedDicts
- **[Шаг 3: Service Layer](./03-service-layer.md)**: OnboardingService расширение (complete, update_profile, get_profile, validate)
- **[Шаг 4: Onboarding UI](./04-onboarding-ui.md)**: Перестройка wizard (имя + RadioItems аватарка + баланс + callbacks)
- **[Шаг 5: Sidebar + Profile Modal](./05-sidebar-profile-modal.md)**: Динамический sidebar, profile modal, CSS стили
- **[Шаг 6: Main + Dashboard](./06-main-dashboard.md)**: Интеграция в main.py, dashboard greeting
- **[Шаг 7: Tests](./07-tests.md)**: Unit тесты для сервисов, конфига, миграции
- **[Шаг 8: Финализация](./08-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0024-user-profile`
- Протокол: `.obsidian-docs/protocols/0024-user-profile/`

**Вся работа ведётся из CWD.**

### Цикл выполнения шага

См. `.obsidian-docs/protocols/_core/workflow.md` или `~/.claude/templates/protocol/workflow.md.tpl`

### Формат отчёта

См. `.obsidian-docs/protocols/_core/report-format.md` или `~/.claude/templates/protocol/report-format.md.tpl`

---

## Generic Principles

См. `.obsidian-docs/protocols/_core/principles.md` или `~/.claude/templates/protocol/principles.md.tpl`

---

## Reference Materials

- **Design Solution**: `.obsidian-docs/design/epic-09-phase-2/solution-v3.md` — финальное архитектурное решение (5/5, READY)
- **Brief**: `.obsidian-docs/design/epic-09-phase-2/brief.md` — требования
- **Spec**: `.obsidian-docs/design/epic-09-phase-2/spec.md` — спецификация
- **Validation**: `.obsidian-docs/design/epic-09-phase-2/validation-v3.md` — отчёт валидации (PASS 27/27)
