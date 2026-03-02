# Шаг 11: Финализация

## Briefing

- **Цель:** Полная верификация кода, перевод PR в Ready
- **Ключевые файлы:** Все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   black . && flake8 . && pytest
   ```
   Исправлять до полного прохождения.

2. **Коммит правок** (если были):
   ```bash
   git add . && git commit -m "chore: final QA fixes [protocol-0014/11]"
   ```

3. **Перевод PR в Ready:**
   ```bash
   gh pr ready
   ```

4. **Обновить context.md:**
   - Status: `Completed`
   - Next Action: `Ожидается /protocol-review-merge`

5. **Финальный коммит протокола:**
   ```bash
   git add .protocols/0014-onboarding-wizard/ && git commit -m "docs(protocol): finalize 0014-onboarding-wizard [protocol-0014/11]"
   git push
   ```

## Checklist перед завершением

- [ ] Black: все файлы отформатированы
- [ ] Flake8: 0 ошибок
- [ ] Pytest: все тесты проходят (включая новые 8+ для OnboardingService)
- [ ] Manual test: wizard показывается при first_launch=True
- [ ] Manual test: Toast показывается при balance=0
- [ ] Manual test: CTA переводит на /calendar и открывает модал сверки

## Отчёт

```
(Протокол 0014-onboarding-wizard — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/PycharmProjects/worktrees/0014-onboarding-wizard
**Статус**: Completed. Ожидается /protocol-review-merge
```
