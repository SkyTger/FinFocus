# 0020-postponed-purchases — Отложенные покупки (Postponed Purchases)

## ADR-style Summary

- **Context**: Пользователю нужен инструмент для управления списком желаемых покупок с подбором безопасной даты на основе кассового календаря, чтобы не опускать баланс ниже порога подушки безопасности и не уходить в минус.
- **Problem Statement**: Нет механизма планирования крупных покупок с учетом кассового прогноза и подушки безопасности. Пользователь вручную считает "когда можно купить".
- **Decision**: Реализовать WishlistItem (ORM), WishlistService (CRUD), PurchaseRecommendationService (расчет safe dates через CalendarService + CushionService). Dashboard виджет для фокусных покупок. Модал управления. Режим выбора даты в календаре с overlay-баннером, маркерами safe/unsafe дней, JS-based hover для каскадного пересчета остатков. Preselection Store Pattern для создания транзакции.
- **Alternatives**: (1) Отдельная страница /wishlist — отклонено (модал достаточен для 5-15 хотелок). (2) Dash clientside_callback для hover — отклонено (проблемы с _dashprivate_setProps). (3) Tooltip + hover одновременно — отклонено (конфликт, Known Limitation для MVP).
- **Consequences**: +1 ORM модель, +2 сервиса, +1 JS файл, +1 новый компонент (calendar_wishlist.py). Tooltip отключен в wishlist-mode (MVP limitation). Hover работает только с мышью (MVP limitation).

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Schema + Model + Migration](./01-schema-model-migration.md)**: TypedDicts, WishlistItem ORM, idempotent migration
- **[Шаг 2: WishlistService](./02-wishlist-service.md)**: CRUD, mark_as_planned, reset_planned, planned guards
- **[Шаг 3: PurchaseRecommendationService](./03-purchase-recommendation.md)**: Safe dates map, hover data precalculation
- **[Шаг 4: Unit тесты сервисов](./04-unit-tests.md)**: ~25 тестов WishlistService, ~15 тестов PurchaseRecommendation
- **[Шаг 5: Wishlist UI (виджет + модал)](./05-wishlist-ui.md)**: Dashboard виджет, модал управления, confirm replan modal
- **[Шаг 6: Dashboard + Main интеграция](./06-dashboard-main.md)**: Виджет в dashboard, модал в layout, query params handler
- **[Шаг 7: Calendar wishlist module](./07-calendar-wishlist.md)**: Overlay-баннер, wishlist day cell, calendar grid builder
- **[Шаг 8: Calendar.py расширение](./08-calendar-extension.md)**: data-date, dcc.Stores, load_and_navigate расширение, CSS
- **[Шаг 9: JS hover asset](./09-js-hover.md)**: wishlist_hover.js, MutationObserver, Intl.NumberFormat
- **[Шаг 10: Preselection + mark_planned](./10-preselection-mark-planned.md)**: Расширение transaction_modals, mark planned callback, orphan detection
- **[Шаг 11: Финализация](./11-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0020-postponed-purchases`
- Протокол: `.protocols/0020-postponed-purchases/`

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

- `.design/brief.md` — бриф задачи
- `.design/solution-v3.md` — финальное техническое решение (v3)
- `.design/critique-v3.md` — критика v2, учтена в v3
- `.reports/epics/epic-04-advanced/postponed-purchases-spec.md` — спецификация
- `app/models/database.py` — существующие ORM модели
- `app/services/calendar_service.py` — CalendarService (calculate_daily_balances)
- `app/services/cushion_service.py` — CushionService (get_settings)
- `app/components/calendar.py` — Calendar UI (build_day_cell, load_and_navigate)
- `app/components/transaction_modals.py` — Preselection Store Pattern
- `app/components/goals.py` — пример confirm modal (_build_delete_contribution_confirm_modal)
