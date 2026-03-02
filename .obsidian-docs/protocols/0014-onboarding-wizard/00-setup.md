# Шаг 0: Подготовка и фиксация плана

## Briefing

- **Цель:** Зафиксировать артефакты протокола, создать PR
- **Это технический шаг** — выполняется автоматически при `/protocol-new`

## Sub-tasks

1. Создать все артефакты в `.protocols/0014-onboarding-wizard/`:
   - `plan.md`, `context.md`, `log.md`
   - `00-setup.md` и файлы шагов `XX-*.md`

2. Первый коммит:
   ```bash
   git add .protocols/0014-onboarding-wizard/
   git commit -m "feat(protocol): add plan for 0014-onboarding-wizard [protocol-0014/00]"
   ```

3. Создать Draft PR:
   ```bash
   git push --set-upstream origin 0014-onboarding-wizard
   gh pr create --draft --title "WIP: 0014 - Onboarding Wizard" --body "Protocol: .protocols/0014-onboarding-wizard/"
   ```

4. Обновить `context.md`:
   - Current Step: 1
   - Status: In Progress
   - Next Action: Шаг 1

5. **Не коммитить** изменённый context.md — войдёт в коммит шага 1

## Отчёт

```
(Протокол 0014-onboarding-wizard, шаг 0 — Setup):

**Создано**: .protocols/0014-onboarding-wizard/ с планом и артефактами
**PR**: [URL] (Draft)
**Ветка**: 0014-onboarding-wizard
**CWD**: /home/skytiger/PycharmProjects/worktrees/0014-onboarding-wizard
**Статус**: Готов к шагу 1. Файлы плана: см. .protocols/0014-onboarding-wizard/
```

> НЕ печатай содержимое plan.md в чат
