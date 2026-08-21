# 0027-audit-quick-wins — Быстрые победы аудита: тихий fail-open и мёртвый блок

## ADR-style Summary

- **Context**: Двойной аудит 2026-08-20, приоритизированный план доработок
  (`knowledge-bank/analyses/2026-08-20-full.md`), пункты 2 (🔴) и 3 (🟡).
  Решение владельца 2026-08-21: мелкие однородные фиксы аудита ехать пачкой
  в одном протоколе; реализацию и тесты делегировать субагентам.
- **Problem Statement**:
  1. `purchase_recommendation_service.py:66-70`: `except Exception:
     threshold = Decimal("0")` без логирования — при сбое CushionService
     сервис молча отключает критерий подушки и выдаёт «безопасные даты»
     fail-open. Финансово-значимая тихая деградация.
  2. `analytics_service.py:218-235`: end_of_month вычисляется дважды —
     первый блок с ошибочным hardcoded fallback 28 сразу перезаписывается
     корректным (`calendar.monthrange`); `import calendar` внутри цикла.
     Мёртвый код — мина при будущем рефакторинге.
- **Decision**:
  1. Логировать сбой: `logger.warning(..., exc_info=True)`; поведение
     оставить fail-open (threshold=0 → критерий подушки отключён),
     задокументировав это в докстринге. Плюс регрессионный тест.
  2. Удалить мёртвый блок end_of_month (оставить monthrange-вариант),
     поднять `import calendar` на уровень модуля.
- **Alternatives**:
  - Fail-closed для п.1 (пробрасывать исключение / помечать все даты
    небезопасными) — отклонено: критерий отрицательного баланса продолжает
    защищать; сбой одной настройки не должен ронять весь режим рекомендаций;
    реальный сценарий сбоя (недоступность БД) уронил бы расчёт балансов
    строкой выше — до этого except почти не дойти. Решение зафиксировано
    здесь как ответ на «рассмотреть fail-closed» из аудита.
  - Оставить п.2 «как есть, работает же» — отклонено: перезаписываемый
    блок с fallback 28 вводит в заблуждение при чтении и рефакторинге.
- **Consequences**: Поведение приложения не меняется (только лог + чистка);
  диффы минимальные, по одному сервису на шаг. Загадочные сбои подушки
  станут видимыми в логах.

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Логирование fail-open в рекомендациях покупок](./01-recommendation-logging.md)**: logger.warning + докстринг + тест
- **[Шаг 2: Мёртвый блок в аналитике](./02-analytics-dead-code.md)**: удалить двойное вычисление end_of_month, поднять import
- **[Шаг 3: Финализация](./03-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/Projects/FinFocus`
- CWD (worktree): `/home/skytiger/Projects/worktrees/0027-audit-quick-wins`
- Протокол: `.obsidian-docs/protocols/0027-audit-quick-wins/`

**Вся работа ведётся из CWD.**
**Исполнение**: шаги 1-2 делегируются субагентам (решение владельца);
главный агент — план, проверка результатов, коммиты.

### Цикл выполнения шага

См. `~/.claude/templates/protocol/workflow.md.tpl`

### Формат отчёта

См. `~/.claude/templates/protocol/report-format.md.tpl`

---

## Generic Principles

См. `~/.claude/templates/protocol/principles.md.tpl`

---

## Reference Materials

- Отчёт аудита: `.obsidian-docs/knowledge-bank/analyses/2026-08-20-full.md` (🔴 №2, 🟡 п.3 плана)
- Тесты рекомендаций: `tests/test_purchase_recommendation.py` (11 тестов)
- Тесты аналитики: `tests/test_analytics_service.py` (16 тестов)
- ВАЖНО: black только из PROJECT_ROOT/.venv (23.11.0) — системный black 26.x форматирует иначе
