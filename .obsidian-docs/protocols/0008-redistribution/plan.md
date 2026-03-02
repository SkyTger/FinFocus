# 0008 — Перераспределение средств при достижении цели

## ADR-style Summary:

- **Context**: FinFocus поддерживает множественные накопительные цели с приоритетами (протокол 0006). При достижении цели освобождается бюджет, который ранее выделялся на неё. Пользователю нужно понимать, как это повлияет на остальные цели, и иметь возможность подтвердить или отклонить перераспределение.

- **Problem Statement**: При завершении накопительной цели (goal.is_completed = True после взноса) необходимо автоматически рассчитать освободившийся бюджет и предложить перераспределить его на оставшиеся активные цели с визуализацией изменений.

- **Decision**: Создать RedistributionService с "Temporary Status Pattern" для расчета OLD/NEW allocation. Добавить модальное окно с preview сравнения распределений и кнопками Confirm/Decline. Использовать существующий AllocationService без изменения алгоритма.

- **Alternatives**:
  1. Автоматическое перераспределение без подтверждения — отклонено: пользователь должен контролировать свои финансы
  2. Ручной выбор целей для перераспределения — отклонено: усложняет MVP, нарушает приоритетную модель
  3. Хранение allocation history в БД — отклонено: over-engineering для MVP

- **Consequences**:
  - (+) Пользователь видит влияние достижения цели на остальные цели
  - (+) Возможность отклонить перераспределение сохраняет контроль
  - (+) Аудит-логирование для анализа поведения
  - (-) Дополнительная сложность в UI (модал, timing requirements)
  - (-) "Temporary Status Pattern" требует внимания к exception safety

---

## High-Level Plan:

Этот раздел является **контрактом**, не меняй его при реализации.

- **[Шаг 0: Подготовка и фиксация плана](./00-setup.md)**: Создание и фиксация артефактов этого протокола.
- **[Шаг 1: TypedDicts и Serializers](./01-typedicts-serializers.md)**: Добавить RedistributionPreview, RedistributionEvent TypedDicts и функции сериализации.
- **[Шаг 2: RedistributionService](./02-redistribution-service.md)**: Создать сервис с "Temporary Status Pattern", timing logs и аудитом.
- **[Шаг 3: Unit тесты RedistributionService](./03-service-tests.md)**: Покрыть все сценарии сервиса unit тестами.
- **[Шаг 4: Redistribution Modal UI](./04-modal-ui.md)**: Создать модальное окно с preview и action buttons.
- **[Шаг 5: Goals Callbacks](./05-callbacks.md)**: Модифицировать add_contribution и добавить confirm/decline callbacks.
- **[Шаг 6: Integration тесты](./06-integration-tests.md)**: E2E тесты полного flow перераспределения.
- **[Шаг 7: Финализация](./07-finalize.md)**: Полная верификация кода (black, flake8, pytest), перевод PR в Ready.

---

## Protocol Workflow (Инструкция по выполнению):

**Твоя задача — выполнять шаги из `High-Level Plan`, строго следуя этому рабочему циклу для каждого шага.**

- **Папка проекта (PROJECT_ROOT)**: `/home/skytiger/PycharmProjects/FinFocus`
- **Папка worktree (CWD)**: `/home/skytiger/PycharmProjects/worktrees/0008-redistribution`
- **Папка протокола**: `/home/skytiger/PycharmProjects/worktrees/0008-redistribution/.protocols/0008-redistribution`

**Вся работа ведется из папки worktree (CWD).**

### A. Перед началом нового шага (Восстановление контекста)
1.  Определи текущий шаг, прочитав `Current Step` из файла `context.md` в папке протокола.
2.  **Открой и изучи файл этого шага** (например, `01-typedicts-serializers.md`). Он содержит полный набор инструкций.
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
4.  Проверь ветку main чтобы не было случайно добавленных наших файлов из нашей ветки. **Сделай коммит** с сообщением по формату `type(scope): subject [protocol-0008/YY]`. Сделай пуш.
5.  Сообщи пользователю о завершении шага в установленном формате.

---

## Generic Principles (MUST follow):

1. **Баланс и простота**: Избегать оверинжиниринга. Использовать существующий AllocationService без модификаций. Не вводить лишних слоёв абстракций.

2. **Никакого легаси**: Удалять устаревший код. Обратная совместимость не требуется.

3. **Стандарты кодирования**:
   - Python 3.12 с type annotations
   - Docstrings на русском языке
   - Black + flake8 для форматирования
   - Guard clauses в начале функций

4. **Memory Bank**: После завершения протокола обновить `.memory-bank/modules/services.md` с описанием RedistributionService.

5. **Качественные тесты**:
   - Unit тесты для RedistributionService (все сценарии)
   - Integration тесты для E2E flow
   - Использовать существующие фикстуры из conftest.py

6. **Pattern-Matching Callbacks**:
   - Проверять `ctx.triggered[0].get('value') is None` для фильтрации автовызовов
   - Использовать `prevent_initial_call=True` для модалов
   - Guard clauses в начале каждого callback

7. **Session Management**:
   - Использовать `get_db_session()` context manager
   - Сервисы используют flush(), caller делает commit

8. **NFR Requirements**:
   - NFR-1: Modal открывается < 100ms
   - NFR-2: Расчет allocation < 50ms
   - Timing logs через time.perf_counter()

---

## Reference Materials

- **Brief**: `.design/brief.md` — функциональные и нефункциональные требования
- **Solution**: `.design/solution-v3.md` — детальное техническое решение
- **Existing Services**:
  - `app/services/allocation_service.py` — жадный алгоритм распределения
  - `app/services/goal_service.py` — CRUD для целей
- **TypedDicts**: `app/schema/goals.py` — существующие AllocationSummary, AllocationResult
- **UI Patterns**: `app/components/goals.py` — существующие модалы и callbacks
- **ADR-003**: `docs/adr/ADR-003-pattern-matching-callbacks-issue.md` — guard clauses для callbacks
