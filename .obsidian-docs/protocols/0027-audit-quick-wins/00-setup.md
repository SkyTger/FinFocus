# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать артефакты в `.obsidian-docs/protocols/0027-audit-quick-wins/`:
   `plan.md`, `context.md`, `log.md`, `00-setup.md`,
   `01-recommendation-logging.md`, `02-analytics-dead-code.md`, `03-finalize.md`

2. Первый коммит:
   ```bash
   git add .obsidian-docs/protocols/0027-audit-quick-wins/
   git commit -m "feat(protocol): add plan for 0027-audit-quick-wins [protocol-0027/00]"
   ```

3. Draft PR:
   ```bash
   git push --set-upstream origin 0027-audit-quick-wins
   gh pr create --draft --title "WIP: 0027 - Audit quick wins" --body "Protocol: .obsidian-docs/protocols/0027-audit-quick-wins/"
   ```

4. Обновить `context.md` (Current Step: 1, Status: In Progress) — не коммитить
