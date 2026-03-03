# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.obsidian-docs/protocols/0025-beta-delivery/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `01-scripts.md`, `02-docs.md`, `03-finalize.md`

2. Первый коммит:
   ```bash
   git add .obsidian-docs/protocols/0025-beta-delivery/
   git commit -m "feat(protocol): add plan for 0025-beta-delivery [protocol-0025/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0025-beta-delivery
   gh pr create --draft --title "WIP: 0025 - Beta Delivery & Setup" --body "Protocol: .obsidian-docs/protocols/0025-beta-delivery/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1

## Отчёт

```
(Протокол 0025-beta-delivery, шаг 0 — Setup):

**Создано**: .obsidian-docs/protocols/0025-beta-delivery/ с планом и артефактами
**PR**: {PR_URL} (Draft)
**Ветка**: 0025-beta-delivery
**CWD**: /home/skytiger/PycharmProjects/worktrees/0025-beta-delivery
**Статус**: Готов к шагу 1. Файлы плана: см. .obsidian-docs/protocols/0025-beta-delivery/
```

> НЕ печатай содержимое plan.md в чат
