# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.protocols/0020-postponed-purchases/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-11`

2. Первый коммит:
   ```bash
   git add .protocols/0020-postponed-purchases/
   git commit -m "feat(protocol): add plan for 0020-postponed-purchases [protocol-0020/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0020-postponed-purchases
   gh pr create --draft --title "WIP: 0020 - Postponed Purchases" --body "Protocol: .protocols/0020-postponed-purchases/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1
