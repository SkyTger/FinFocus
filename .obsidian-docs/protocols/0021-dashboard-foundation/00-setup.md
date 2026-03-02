# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.protocols/0021-dashboard-foundation/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-06-*.md`

2. Первый коммит:
   ```bash
   git add .protocols/0021-dashboard-foundation/
   git commit -m "feat(protocol): add plan for 0021-dashboard-foundation [protocol-0021/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0021-dashboard-foundation
   gh pr create --draft --title "WIP: 0021-dashboard-foundation" --body "Protocol: .protocols/0021-dashboard-foundation/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1
