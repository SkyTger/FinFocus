# Work Log: 0010 — Analytics & UX Improvements

Этот раздел является **журналом**. Записи только добавляются, старые не изменяются.

---

## Restore context: protocol-0010#ctx-2

**Дата:** 2026-01-23
**Статус на момент восстановления:** Шаг 0 завершен, готов к началу шага 1
**Последний коммит:** c4117ae (protocol-0010/00)
**Незакоммиченные изменения:** context.md (обновлен после шага 0, не требует коммита)
**Диагноз:** Чистое состояние (Сценарий A)

---

## [2026-01-23] Шаг 1: TypedDicts и AnalyticsService

**Действия:**
- Создан `app/schema/analytics.py` с TypedDicts:
  - `CategorySummary` — агрегация по категории для donut chart
  - `MonthlyTrend` — данные за месяц для bar chart
- Создан `app/services/analytics_service.py` (~290 строк):
  - `MIN_PERCENTAGE_THRESHOLD = 3.0` — порог для группировки в "Прочее"
  - `MONTH_LABELS_RU` — русские названия месяцев
  - `get_expenses_by_category()` — SQL GROUP BY агрегация с LEFT JOIN на Category
  - `_group_small_categories()` — внутренний метод для группировки < 3%
  - `get_monthly_trends()` — генерация трендов за N месяцев
  - `get_uncategorized_count()` — подсчет некатегоризированных
- Обновлены экспорты в `app/schema/__init__.py` и `app/services/__init__.py`
- Создан `tests/test_analytics_service.py` с 16 unit тестами:
  - TestGetExpensesByCategory: 9 тестов (базовая агрегация, uncategorized, grouping, etc.)
  - TestGetMonthlyTrends: 3 теста (6/12 месяцев, пустые месяцы)
  - TestGetUncategorizedCount: 3 теста (базовый, исключение recurring, zero)
  - TestMinPercentageThreshold: 1 тест (значение константы)

**Результат:**
- 16 новых тестов, все проходят
- Всего тестов в проекте: 229 (было 213)
- Black + Flake8: OK

**Решения:**
- Использован LEFT JOIN вместо отдельных запросов для эффективности
- "Без категории" и "Прочее" различаются: первое — NULL category_id, второе — объединение мелких
- Месячные тренды генерируются от reference_date назад для гибкости

---

## [2026-01-23] Шаг 0: Инициализация протокола

**Действия:**
- Создана ветка `0010-analytics-ux` от `origin/main`
- Создан worktree в `../worktrees/0010-analytics-ux`
- Созданы артефакты протокола: plan.md, context.md, log.md, 00-08 step files

**Контекст:**
- Базовая ветка: `main` (commit fea04fe)
- Предыдущий протокол: 0009-categories-reconciliation (завершен, PR #9 смержен)
- Спецификация: `.design/solution-v2.md`

**Решения:**
- Разбивка на 8 шагов (0-7 + финализация) вместо 3 протоколов из solution-v2.md для лучшего контроля прогресса
- Chips UI и Bulk Actions разделены на отдельные шаги для изоляции сложности Pattern-Matching callbacks
