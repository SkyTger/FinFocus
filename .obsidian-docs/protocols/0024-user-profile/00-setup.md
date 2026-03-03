# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.obsidian-docs/protocols/0024-user-profile/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `XX-*.md`

2. Первый коммит:
   ```bash
   git add .obsidian-docs/protocols/0024-user-profile/
   git commit -m "feat(protocol): add plan for 0024-user-profile [protocol-0024-user-profile/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0024-user-profile
   gh pr create --draft --title "WIP: 0024 - User Profile" --body "Protocol: .obsidian-docs/protocols/0024-user-profile/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1
