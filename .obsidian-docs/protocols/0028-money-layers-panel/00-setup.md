# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.obsidian-docs/protocols/0028-money-layers-panel/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-*.md` … `08-finalize.md`

2. Первый коммит:
   ```bash
   git add .obsidian-docs/protocols/0028-money-layers-panel/
   git commit -m "feat(protocol): add plan for 0028-money-layers-panel [protocol-0028/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0028-money-layers-panel
   gh pr create --draft --title "WIP: 0028 - Модель «свободно/платежи/резерв» + шапка + график полос" \
     --body "Protocol: .obsidian-docs/protocols/0028-money-layers-panel/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1

## Отчёт

```
(Протокол 0028-money-layers-panel, шаг 0 — Setup):

**Создано**: .obsidian-docs/protocols/0028-money-layers-panel/ с планом и артефактами
**PR**: [URL] (Draft)
**Ветка**: 0028-money-layers-panel
**CWD**: /home/skytiger/Projects/worktrees/0028-money-layers-panel
**Статус**: Готов к шагу 1
```

> НЕ печатай содержимое plan.md в чат
