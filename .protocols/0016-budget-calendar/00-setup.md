# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.protocols/0016-budget-calendar/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-08.md`

2. Первый коммит:
   ```bash
   git add .protocols/0016-budget-calendar/
   git commit -m "feat(protocol): add plan for 0016-budget-calendar [protocol-0016/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0016-budget-calendar
   gh pr create --draft --title "WIP: 0016 - Budget Calendar Integration" --body "Protocol: .protocols/0016-budget-calendar/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1

## Отчёт

```
(Протокол 0016-budget-calendar, шаг 0 — Setup):

**Создано**: .protocols/0016-budget-calendar/ с планом и артефактами
**PR**: [URL] (Draft)
**Ветка**: 0016-budget-calendar
**CWD**: /home/skytiger/PycharmProjects/worktrees/0016-budget-calendar
**Статус**: Готов к шагу 1
```

> НЕ печатай содержимое plan.md в чат
