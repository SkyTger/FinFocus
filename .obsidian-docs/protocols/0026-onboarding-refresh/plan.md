# 0026-onboarding-refresh — Онбординг: мгновенное применение профиля на дашборде

## ADR-style Summary

- **Context**: Двойной аудит 2026-08-20 (UX + код), находка 🔴 №1
  (`knowledge-bank/analyses/2026-08-20-full.md`). После завершения онбординга
  дашборд не обновляется без ручной перезагрузки: приветствие остаётся
  «Пользователь», KPI показывают баланс 0 ₽, баннер «Сверить баланс» висит.
- **Problem Statement**: Онбординг-визард и ProfileModal пишут timestamp в
  Store `profile-updated` (event bus протокола 0024). Sidebar на него подписан,
  а дашборд — нет: `load_dashboard_data` и `toggle_balance_toast` не имеют
  Input на этот Store, а приветствие вообще читается inline при построении
  layout (dashboard.py:84-91) и живёт только до следующей навигации.
  Это нарушение собственного паттерна Selective Refresh
  (knowledge-bank/patterns/callbacks.md).
- **Decision**:
  1. Добавить `Input("profile-updated", "data")` в `load_dashboard_data`
     (KPI, график, таблицы, подушка обновятся после онбординга/сверки профиля).
  2. Добавить `Input("profile-updated", "data")` в `toggle_balance_toast`
     (баннер нулевого баланса скроется сразу после ввода баланса).
  3. Приветствие: дать заголовку id `dashboard-greeting` и завести отдельный
     лёгкий callback `update_dashboard_greeting(profile-updated)` со
     State("url","pathname") и guard'ом по pathname. Inline-чтение имени в
     layout остаётся как начальное значение (корректно при навигации).
- **Alternatives**:
  - Выносить greeting 7-м Output'ом в `_load_dashboard_components()` —
    отвергнуто: helper делят два колбэка (load + refresh_after_crud),
    расширение сигнатуры раздувает объём правок ради текстовой строки.
  - Полная перезагрузка страницы после онбординга (`dcc.Location.refresh`) —
    отвергнуто: против SPA-паттерна проекта, мигание UI.
- **Consequences**: Дашборд становится полноценным подписчиком event bus
  `profile-updated`. Новые Input'ы требуют ADR-003 guard'ов (событие может
  прилететь на другой странице — pathname guard уже есть в load_dashboard_data,
  в greeting-callback добавим). Обновляется patterns/callbacks.md — дашборд
  в списке подписчиков.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Подписки дашборда на profile-updated](./01-dashboard-subscriptions.md)**: Input'ы в load_dashboard_data и toggle_balance_toast, callback приветствия
- **[Шаг 2: Тесты](./02-tests.md)**: Колбэчные тесты подписок и приветствия
- **[Шаг 3: Финализация](./03-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/Projects/FinFocus`
- CWD (worktree): `/home/skytiger/Projects/worktrees/0026-onboarding-refresh`
- Протокол: `.obsidian-docs/protocols/0026-onboarding-refresh/`

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

- Отчёт аудита: `.obsidian-docs/knowledge-bank/analyses/2026-08-20-full.md` (🔴 №1, план п.1)
- Паттерн Selective Refresh / event bus: `.obsidian-docs/knowledge-bank/patterns/callbacks.md`
- Event bus введён протоколом 0024 (`.obsidian-docs/protocols/0024-user-profile/`)
- Рабочий пример подписчика: `app/components/sidebar.py:170`
- Эмиттеры: `app/components/onboarding_wizard.py:193`, `app/components/profile_modal.py:93`
- UX-находка №1: ROADMAP.md, секция «UX-аудит 2026-08-20 — итоги», P1
