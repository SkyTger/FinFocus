# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.protocols/0022-daily-cashflow-chart/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-04.md` + `05-finalize.md`

2. Первый коммит:
   ```bash
   git add .protocols/0022-daily-cashflow-chart/
   git commit -m "feat(protocol): add plan for 0022-daily-cashflow-chart [protocol-0022/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0022-daily-cashflow-chart
   gh pr create --draft --title "WIP: 0022 - Daily & Yearly Cashflow Chart" --body "Protocol: .protocols/0022-daily-cashflow-chart/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1
