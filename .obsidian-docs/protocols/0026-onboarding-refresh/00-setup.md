# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.obsidian-docs/protocols/0026-onboarding-refresh/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-dashboard-subscriptions.md`, `02-tests.md`, `03-finalize.md`

2. Первый коммит:
   ```bash
   git add .obsidian-docs/protocols/0026-onboarding-refresh/
   git commit -m "feat(protocol): add plan for 0026-onboarding-refresh [protocol-0026/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0026-onboarding-refresh
   gh pr create --draft --title "WIP: 0026 - Onboarding dashboard refresh" --body "Protocol: .obsidian-docs/protocols/0026-onboarding-refresh/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1
