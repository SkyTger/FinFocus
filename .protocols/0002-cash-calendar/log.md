# Work Log: 0002 — Кассовый календарь

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

---

## Шаг 0: Подготовка (2026-01-18)

**Действия:**
- Создана ветка `0002-cash-calendar` с worktree
- Сгенерированы артефакты протокола: plan.md, context.md, log.md, 00-05 step files
- Открыт Draft PR

**Решения:**
- Разбиение на 5 шагов (кроме setup): CalendarService → UI → Callbacks → Integration → Finalize
- Использование существующего `create-modal` из transactions.py вместо создания дублирующего
- TRANSFER транзакции исключаются из расчетов баланса

**Детали:**
- Дизайн-документ: `.design/solution-v2.md`
- Критика v1 учтена: Decimal сериализация, guard clauses, fallback для starting_balance
