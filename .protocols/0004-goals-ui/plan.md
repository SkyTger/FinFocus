# 0004 — Goals UI (Накопительная цель)

## ADR-style Summary:

- **Context**: FinFocus — MVP приложение для планирования бюджета. Фаза 5 Core MVP требует реализации UI для управления накопительной целью. GoalService уже реализован (CRUD операции), но отсутствует UI и метод `get_contributions()`.

- **Problem Statement**: Пользователь не может создавать/редактировать накопительные цели и вносить взносы через UI. Страница /goals содержит заглушку.

- **Decision**: Реализовать полнофункциональный Goals UI компонент (`goals.py`) с модалами для CRUD операций, прогресс-баром, историей взносов. Использовать простые callbacks (без Pattern-Matching) так как MVP поддерживает только одну активную цель. Вынести общие функции форматирования в `app/utils/formatters.py`.

- **Alternatives**:
  1. Pattern-Matching Callbacks (как в transactions.py) — отклонено: одна цель = излишняя сложность
  2. dbc.Modal для подтверждения удаления — отклонено: dcc.ConfirmDialog проще и надежнее

- **Consequences**:
  - (+) Простые callbacks без ADR-003 guard clauses для Pattern-Matching
  - (+) DRY: общие formatters переиспользуются в transactions.py и goals.py
  - (-) При переходе к множественным целям (Batch 2) потребуется рефакторинг на Pattern-Matching

---

## High-Level Plan:

Этот раздел является **контрактом**, не меняй его при реализации.

- **[Шаг 0: Подготовка и фиксация плана](./00-setup.md)**: Создание и фиксация артефактов этого протокола.
- **[Шаг 1: Utils и GoalService Extension](./01-utils-service.md)**: Создание formatters.py, добавление get_contributions() в GoalService, обновление импортов в transactions.py.
- **[Шаг 2: Goals Layout](./02-goals-layout.md)**: Создание goals.py с layout, build-функциями и TypedDicts.
- **[Шаг 3: Goals Callbacks](./03-goals-callbacks.md)**: Реализация всех callbacks для CRUD операций.
- **[Шаг 4: Стили и интеграция](./04-styles-integration.md)**: Создание goals.css, интеграция в main.py.
- **[Шаг 5: Финализация](./05-finalize.md)**: Тестирование, QA, перевод PR в Ready.

---

## Protocol Workflow (Инструкция по выполнению):

**Твоя задача — выполнять шаги из `High-Level Plan`, строго следуя этому рабочему циклу для каждого шага.**

- **Папка проекта (PROJECT_ROOT)**: `/home/skytiger/PycharmProjects/FinFocus`
- **Папка worktree (CWD)**: `/home/skytiger/PycharmProjects/worktrees/0004-goals-ui`
- **Папка протокола**: `/home/skytiger/PycharmProjects/worktrees/0004-goals-ui/.protocols/0004-goals-ui`

**Вся работа ведется из папки worktree (CWD).**

### A. Перед началом нового шага (Восстановление контекста)
1.  Определи текущий шаг, прочитав `Current Step` из файла `context.md` в папке протокола.
2.  **Открой и изучи файл этого шага** (например, `01-utils-service.md`). Он содержит полный набор инструкций.
3.  Убедись, что все предыдущие изменения закоммичены.

### B. Во время выполнения шага (Исполнение)
1.  Выполняй подзадачи, описанные в файле текущего шага.
2.  **Не изменяй файлы планов** (`plan.md`, `XX-*.md`). Они являются контрактом.
3.  Следуй общим принципам, изложенным ниже.

### C. Сразу после завершения шага (Верификация и Фиксация)
1.  Выполни проверки: `black`, `flake8`, `pytest`. Исправляй проблемы, пока все проверки не пройдут.
2.  **Добавь запись в `log.md`**: Опиши, что было сделано, и **почему** были приняты неочевидные решения. Сошлись на ID коммита.
3.  **Полностью перезапиши `context.md`** новым состоянием для следующего шага.
4.  Проверь ветку main чтобы не было случайно добавленных наших файлов из нашей ветки. **Сделай коммит** с сообщением по формату `type(scope): subject [protocol-0004/YY]`. Сделай пуш.
5.  Сообщи пользователю о завершении шага в установленном формате.

---

## Generic Principles (MUST follow):

1. **Баланс и простота**: Избегай оверинжиниринга. Решения — самые простые из возможных, но функциональные и надежные.

2. **Никакого легаси**: Удаляй устаревший код. Обратная совместимость не требуется.

3. **Стандарты кодирования**:
   - Python 3.12+ с type annotations
   - Docstrings на русском языке
   - Black + flake8 перед каждым коммитом
   - Commits: `type(scope): subject [protocol-0004/YY]`

4. **Паттерны из transactions.py**:
   - `prevent_initial_call=True` для всех callbacks
   - dcc.Store для хранения ID цели
   - dbc.Alert для отображения ошибок
   - Guard clauses в начале callbacks

5. **Тестирование**: Unit тесты для новых методов сервисов. Ручное тестирование UI flows.

6. **Детализация**: Каждый шаг самодостаточен и может быть выполнен без дополнительного контекста.

---

## Reference Materials

- **brief.md**: `/home/skytiger/PycharmProjects/FinFocus/.design/brief.md`
- **solution-v2.md**: `/home/skytiger/PycharmProjects/FinFocus/.design/solution-v2.md`
- **transactions.py** (паттерн): `app/components/transactions.py`
- **goal_service.py**: `app/services/goal_service.py`
- **database.py** (модели): `app/models/database.py`
- **ADR-003**: `docs/adr/ADR-003-pattern-matching-callbacks-issue.md`
