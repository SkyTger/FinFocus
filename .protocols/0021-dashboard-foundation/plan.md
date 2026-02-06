# 0021-dashboard-foundation — Dashboard UI Foundation: Colors, Currency Format, KPI Cards

## ADR-style Summary

- **Context**: Dashboard отображает суммы в долларовом формате ($X,XXX.XX), использует устаревшую цветовую палитру (#28a745), KPI-карточки с градиентами не соответствуют новой UI-спецификации
- **Problem Statement**: Необходимо обновить фундаментальные элементы Dashboard и всего приложения: единый формат денег (X XXX ₽), новая палитра (#2ecc71), переработанные KPI-карточки
- **Decision**: format_rub() как глобальный форматтер + format_amount() alias для обратной совместимости; CSS-переменные с deprecated aliases; _build_kpi_card() вместо create_metric_card()
- **Alternatives**: (1) Прямая замена format_amount() без alias — отвергнуто, слишком много callsites; (2) Plotly hovertemplate кастомизация — отложено на batch 5.2
- **Consequences**: Все суммы в приложении в формате ₽; .00 копейки скрываются; 493+ тестов; AI/Exchange скрыты (TODO Epic-08)

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: format_rub() + тесты](./01-format-rub.md)**: Глобальный форматтер, alias, unit тесты
- **[Шаг 2: CSS-переменные + типографика](./02-css-variables.md)**: Палитра #2ecc71, типографические классы
- **[Шаг 3: Dashboard.py переработка](./03-dashboard.md)**: KPI карточки, format_rub, AI/Exchange, русские label
- **[Шаг 4: Calendar.py обновления](./04-calendar.md)**: format_balance() рефакторинг, 11 inline замен
- **[Шаг 5: Analytics.py обновления](./05-analytics.md)**: 2 inline замены
- **[Шаг 6: Финализация](./06-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/PycharmProjects/FinFocus`
- CWD (worktree): `/home/skytiger/PycharmProjects/worktrees/0021-dashboard-foundation`
- Протокол: `.protocols/0021-dashboard-foundation`

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

- `.design/solution-v2.md` — финальное архитектурное решение (READY, 5/5)
- `.design/brief.md` — требования батча
- `.reports/epics/epic-05-ui/batch-1.md` — спецификация батча 5.1
- `.reports/epics/epic-05-ui/dashboard_ui_spec.md` — UI/UX спецификация
- `.design/validation-v2.md` — валидация 47/47 требований PASS
