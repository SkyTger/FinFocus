# Review and Merge Plan for Protocol 0003

## Review/Merge Workflow (Инструкция по выполнению):

**Папка проекта (project root)**: `/home/skytiger/PycharmProjects/FinFocus`
**Папка worktree (worktree root)**: `/home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration`
**Папка протокола**: `/home/skytiger/PycharmProjects/worktrees/0003-dashboard-integration/.protocols/0003-dashboard-integration`

**Твоя задача — выполнять шаги из `Detailed Plan` ниже, строго следуя этому рабочему циклу.**

### A. Перед началом нового шага
1.  **Проверка окружения:** Выполни и залогируй результат команд `pwd` (должен быть корень проекта) и `git branch --show-current`.
2.  **Чтение инструкций:** Внимательно прочитай описание текущего шага в этом плане.
3.  Сообщи пользователю, какой шаг ты начинаешь.

### B. Во время выполнения шага
1.  Выполняй подзадачи. Используй пути `../worktrees/0003-dashboard-integration/` для доступа к коду (папка ворктрее).
2.  Следуй `Review/Merge Principles`.

### C. Сразу после завершения шага
1.  **Добавь запись в `review-log.md`**: Детально опиши, что сделано, результаты проверок, ID коммита (если был).
2.  **Закоммить изменения** в `review-log.md` и `review-plan.md` в ветку `main`.
3.  **Повторная проверка окружения:** Снова выполни и залогируй `pwd` и `git branch --show-current`, чтобы убедиться, что ты остался в правильном контексте.
4.  Отчитайся пользователю о завершении шага.

---
## Review/Merge Principles (MUST follow):

- **Методичность:** Строго следуй плану. Никаких пропусков шагов без команды пользователя.
- **Контроль окружения:** Постоянно проверяй свой CWD и текущую ветку Git.
- **Отчетность:** Все действия подробно фиксируй в `review-log.md`.

---
## Protocol Summary (из plan.md и log.md):

**Цель**: Интеграция дашборда с реальными данными из SQLite — Фаза 4 Core MVP.

**Шаги протокола**:
- [x] Шаг 0: Подготовка протокола (commit 0882ab2)
- [x] Шаг 1: Расширение CalendarService (commit 4e898f7)
- [x] Шаг 2: Создание DashboardService (commit 66b27da)
- [x] Шаг 3: Обновление exports (commit 15a7853)
- [x] Шаг 4: Рефакторинг Dashboard UI (commit 6f882aa)
- [x] Шаг 5: Unit тесты (commit a5113e8)
- [x] Шаг 6: Финализация (commit e5afb1b)

**PR**: #3 (статус: OPEN)

---
## Detailed Plan:

### Шаг 1-m. Проверка CI/CD
- [ ] Выполни `gh pr checks 3`.
- [ ] Если есть проваленные проверки (`failure`), останови ревью и сообщи об этом как о блокирующей проблеме.

### Шаг 2-m. Локальная верификация
- [ ] Из корня проекта запусти проверки для кода в worktree:
  - `black --check ../worktrees/0003-dashboard-integration/app/`
  - `flake8 ../worktrees/0003-dashboard-integration/app/`
  - `cd ../worktrees/0003-dashboard-integration && pytest -v`
- [ ] Если найдены проблемы, согласуй с пользователем их исправление.

### Шаг 3-m. Ревью кода
- [ ] Сверь план с фактом: `plan.md` vs `log.md` vs фактические изменения.
- [ ] Выполни `git diff origin/main...0003-dashboard-integration` и проанализируй.
- [ ] Проверь:
  - Соответствие реализации плану
  - Стандарты кодирования (type annotations, docstrings на русском)
  - Guard clauses в callbacks
  - Session management pattern
  - Отсутствие hardcoded данных в dashboard.py

### Шаг 4-m. Финальное слияние (Merge)
- [ ] Получить явное разрешение от пользователя на слияние.
- [ ] Выполнить:
  ```bash
  git checkout main
  git pull origin main
  git merge --no-ff 0003-dashboard-integration
  git push origin main
  ```
- [ ] При конфликтах — остановиться, согласовать с пользователем.

### Шаг 5-m. Очистка
- [ ] Удалить ветку на сервере: `git push origin --delete 0003-dashboard-integration`
- [ ] Удалить локальную ветку: `git branch -d 0003-dashboard-integration`
- [ ] Удалить worktree: `git worktree remove ../worktrees/0003-dashboard-integration`
- [ ] Сообщить пользователю о полном завершении работы.
