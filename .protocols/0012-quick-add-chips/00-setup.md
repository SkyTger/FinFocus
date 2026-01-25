# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.protocols/0012-quick-add-chips/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-08*.md`

2. Первый коммит:
   ```bash
   git add .protocols/0012-quick-add-chips/
   git commit -m "feat(protocol): add plan for 0012-quick-add-chips [protocol-0012/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0012-quick-add-chips
   gh pr create --draft --title "WIP: 0012 - Quick-Add Chips" --body "Protocol: .protocols/0012-quick-add-chips/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1

## Отчёт

```
(Протокол 0012-quick-add-chips, шаг 0 — Setup):

**Создано**: .protocols/0012-quick-add-chips/ с планом и артефактами
**PR**: {{PR_URL}} (Draft)
**Ветка**: 0012-quick-add-chips
**CWD**: /home/skytiger/PycharmProjects/worktrees/0012-quick-add-chips
**Статус**: Готов к шагу 1. Файлы плана: см. .protocols/0012-quick-add-chips/
```

> НЕ печатай содержимое plan.md в чат
