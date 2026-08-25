# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.obsidian-docs/protocols/0029-panel-debts/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `XX-*.md`

2. Первый коммит:
   ```bash
   git add .obsidian-docs/protocols/0029-panel-debts/
   git commit -m "feat(protocol): add plan for 0029-panel-debts [protocol-0029/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0029-panel-debts
   gh pr create --draft --title "WIP: 0029 - Долги куска 1: savings в базе календаря + тесты щитка" --body "Protocol: .obsidian-docs/protocols/0029-panel-debts/"
   ```

4. Обновить `context.md`: Current Step: 1, Status: In Progress, Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1
