# Review and Merge Plan for Protocol 0007

## Review/Merge Workflow (Инструкция по выполнению):

Папка проекта (project root): `/home/skytiger/PycharmProjects/FinFocus`
Папка worktree (worktree root): `/home/skytiger/PycharmProjects/worktrees/0007-savings-mode`
Папка протокола: `/home/skytiger/PycharmProjects/worktrees/0007-savings-mode/.protocols/0007-savings-mode`

**Твоя задача — выполнять шаги из `Detailed Plan` ниже, строго следуя этому рабочему циклу.**

### A. Перед началом нового шага
1.  **Проверка окружения:** Выполни и залогируй результат команд `pwd` (должен быть корень проекта) и `git branch --show-current`.
2.  **Чтение инструкций:** Внимательно прочитай описание текущего шага в этом плане.
3.  Сообщи пользователю, какой шаг ты начинаешь.

### B. Во время выполнения шага
1.  Выполняй подзадачи. Используй пути `../worktrees/0007-savings-mode/` для доступа к коду (папка ворктрее).
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
## Protocol Summary:

- **Номер протокола:** 0007-savings-mode
- **Название:** Три режима накоплений (Savings Mode)
- **PR:** #7
- **Ветка:** 0007-savings-mode
- **Шагов в протоколе:** 7 (0-6)
- **Новых тестов:** 13
- **Всего тестов:** 111

---
## Detailed Plan:

### Шаг 1-m. Проверка CI/CD
- [ ] Выполнить `gh pr checks 7`
- [ ] Если есть проваленные проверки — блокировать ревью

### Шаг 2-m. Локальная верификация
- [ ] Запустить `black --check` в worktree
- [ ] Запустить `flake8` в worktree
- [ ] Запустить `pytest` в worktree
- [ ] Все проверки должны пройти

### Шаг 3-m. Ревью кода
- [ ] Сравнить `plan.md` с `log.md` — соответствие плану
- [ ] Выполнить `git diff origin/main...0007-savings-mode`
- [ ] Проверить модель User — поле savings_mode
- [ ] Проверить GoalService — методы get/update_savings_mode
- [ ] Проверить AllocationService — параметр savings_mode и множители
- [ ] Проверить UI — selector и callbacks
- [ ] Проверить тесты — покрытие всех режимов

### Шаг 4-m. Финальное слияние (Merge)
- [ ] Получить разрешение пользователя
- [ ] `git checkout main`
- [ ] `git pull origin main`
- [ ] `git merge --no-ff 0007-savings-mode`
- [ ] `git push origin main`

### Шаг 5-m. Очистка
- [ ] `git push origin --delete 0007-savings-mode`
- [ ] `git branch -d 0007-savings-mode`
- [ ] `git worktree remove ../worktrees/0007-savings-mode`
- [ ] Сообщить о завершении
