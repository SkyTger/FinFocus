# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.obsidian-docs/protocols/0032-system-ops-guard/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `XX-*.md`

2. Первый коммит:
   ```bash
   git add .obsidian-docs/protocols/0032-system-ops-guard/
   git commit -m "feat(protocol): add plan for 0032-system-ops-guard [protocol-0032-system-ops-guard/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0032-system-ops-guard
   gh pr create --draft --title "WIP: 0032-system-ops-guard" --body "Protocol: .obsidian-docs/protocols/0032-system-ops-guard/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1

## Отчёт

```
(Протокол 0032-system-ops-guard, шаг 0 — Setup):

**Создано**: .obsidian-docs/protocols/0032-system-ops-guard/ с планом и артефактами
**PR**: см. отчёт (Draft)
**Ветка**: 0032-system-ops-guard
**CWD**: /home/skytiger/Projects/worktrees/0032-system-ops-guard
**Статус**: Готов к шагу 1. Файлы плана: см. .obsidian-docs/protocols/0032-system-ops-guard/
```

> НЕ печатай содержимое plan.md в чат
