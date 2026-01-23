# 0010 — Analytics & UX Improvements (Батч 3.2)

## ADR-style Summary:

- **Context**: Батч 3.1 завершен — реализована ленивая категоризация операций (16 предустановленных категорий, nullable category_id) и механизм сверки баланса. Пользователи могут присваивать категории, но UX требует улучшений: нужны быстрые действия для некатегоризированных операций и визуальная аналитика расходов.

- **Problem Statement**: Текущий UX категоризации требует открытия модала для каждой операции — это медленно при массовой работе. Отсутствует визуализация структуры расходов и динамики по категориям. Нет возможности экспорта данных.

- **Decision**: Реализовать 3-фазный план:
  1. Backend: AnalyticsService + расширение TransactionService (bulk update, CSV export) + CategoryService (frequent categories)
  2. Transactions UI: Chips для быстрой категоризации + Bulk actions panel + CSV export
  3. Analytics Page: Donut chart структуры + Bar chart динамики

- **Alternatives**:
  - Inline editing вместо chips — отвергнуто (сложнее реализовать, менее интуитивно)
  - Клик на donut → фильтрация списка — отложено на Батч 4
  - AI-рекомендации по категориям — отложено (out of MVP scope)

- **Consequences**:
  - Positive: Ускорение категоризации в 5-10 раз, наглядная аналитика, экспорт данных
  - Negative: Увеличение сложности transactions.py (~250 строк), новая страница /analytics
  - Risks: Pattern-Matching callbacks конфликты → уникальные type prefixes

---

## High-Level Plan:

Этот раздел является **контрактом**, не меняй его при реализации.

- **[Шаг 0: Подготовка и фиксация плана](./00-setup.md)**: Создание и фиксация артефактов этого протокола.
- **[Шаг 1: TypedDicts и AnalyticsService](./01-analytics-service.md)**: Создание схемы и сервиса аналитики.
- **[Шаг 2: TransactionService extensions](./02-transaction-extensions.md)**: bulk_update_category() и export_to_csv().
- **[Шаг 3: CategoryService extension](./03-category-frequent.md)**: get_frequent_for_type() для chips.
- **[Шаг 4: Transactions UI — Chips](./04-ui-chips.md)**: Быстрые кнопки категорий для некатегоризированных операций.
- **[Шаг 5: Transactions UI — Bulk Actions](./05-ui-bulk.md)**: Multi-select и массовое присвоение категорий.
- **[Шаг 6: Transactions UI — CSV Export](./06-ui-export.md)**: Кнопка экспорта и dcc.Download.
- **[Шаг 7: Analytics Page](./07-analytics-page.md)**: Новая страница /analytics с charts.
- **[Шаг 8: Финализация](./08-finalize.md)**: Полная верификация, QA fixes, перевод PR в Ready.

---

## Protocol Workflow (Инструкция по выполнению):

**Твоя задача — выполнять шаги из `High-Level Plan`, строго следуя этому рабочему циклу для каждого шага.**

- **Папка проекта (PROJECT_ROOT)**: `/home/skytiger/PycharmProjects/FinFocus`
- **Папка worktree (CWD)**: `/home/skytiger/PycharmProjects/worktrees/0010-analytics-ux`
- **Папка протокола**: `/home/skytiger/PycharmProjects/worktrees/0010-analytics-ux/.protocols/0010-analytics-ux`

**Вся работа ведется из папки worktree (CWD).**

### A. Перед началом нового шага (Восстановление контекста)
1.  Определи текущий шаг, прочитав `Current Step` из файла `context.md` в папке протокола.
2.  **Открой и изучи файл этого шага** (например, `01-analytics-service.md`). Он содержит полный набор инструкций.
3.  Убедись, что все предыдущие изменения закоммичены.

### B. Во время выполнения шага (Исполнение)
1.  Выполняй подзадачи, описанные в файле текущего шага.
2.  **Не изменяй файлы планов** (`plan.md`, `XX-*.md`). Они являются контрактом.
3.  Следуй общим принципам, изложенным ниже.
4.  **Важно:** На промежуточных шагах проводится только базовая проверка синтаксиса. Полная верификация (black, flake8, pytest) выполняется ТОЛЬКО на финальном шаге для экономии токенов и контекста.

### C. Сразу после завершения шага (Верификация и Фиксация)
1.  Выполни базовую проверку: убедись что код синтаксически корректен (python -m py_compile для измененных Python файлов).
2.  **Добавь запись в `log.md`**: Опиши, что было сделано, и **почему** были приняты неочевидные решения. Сошлись на ID коммита.
3.  **Полностью перезапиши `context.md`** новым состоянием для следующего шага.
4.  Проверь ветку main чтобы не было случайно добавленных наших файлов из нашей ветки. **Сделай коммит** с сообщением по формату `type(scope): subject [protocol-0010/YY]`. Сделай пуш.
5.  Сообщи пользователю о завершении шага в установленном формате.

---

## Generic Principles (MUST follow):

1. **Баланс и простота**: Избегай оверинжиниринга. Решения — самые простые из возможных, но функциональные и надежные. Доверяй фреймворкам (Dash, SQLAlchemy).

2. **Никакого легаси**: Удаляй устаревший код. Обратная совместимость не требуется.

3. **Стандарты кодирования**:
   - Type annotations обязательны для public API
   - Docstrings на русском языке
   - Guard clauses в начале функций
   - Session management: сервисы используют flush(), caller делает commit()

4. **Pattern-Matching Callbacks**:
   - Уникальные type prefixes: `tx-chip-btn`, `tx-checkbox`, `bulk-apply-btn`
   - Проверка `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
   - `prevent_initial_call=True` для модалов

5. **TypedDicts**: Все новые типы в `app/schema/analytics.py`

6. **Тестирование**: Каждый сервисный метод покрывается unit тестами. Описание что проверяет каждый тест.

7. **Memory Bank**: После завершения протокола обновить `.memory-bank/modules/services.md` и `architecture.md`.

---

## Reference Materials

- **Спецификация**: `.design/solution-v2.md` — детальный план с интерфейсами и диаграммами
- **Критика**: `.design/solution-v2.md` содержит учтенные замечания из critique v1
- **Паттерны**: `.memory-bank/architecture.md` — Dash callbacks, Session management
- **Стиль кода**: `.memory-bank/code-style.md`
- **Существующие сервисы**: `app/services/` — примеры реализации
- **TypedDicts**: `app/schema/goals.py`, `app/schema/categories.py` — примеры
