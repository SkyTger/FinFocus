# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.protocols/0019-contribution-edit-delete/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-06`

2. Первый коммит:
   ```bash
   git add .protocols/0019-contribution-edit-delete/
   git commit -m "feat(protocol): add plan for 0019-contribution-edit-delete [protocol-0019/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0019-contribution-edit-delete
   gh pr create --draft --title "WIP: 0019 - Contribution Edit/Delete" --body "Protocol: .protocols/0019-contribution-edit-delete/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1
