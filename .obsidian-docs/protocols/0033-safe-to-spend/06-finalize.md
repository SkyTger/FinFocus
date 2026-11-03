# Шаг 6: Финализация

## Briefing

- **Цель:** Полная верификация; след в истории — последним коммитом ветки.

## Sub-tasks

1. **Полная верификация:**
   ```bash
   .venv/bin/black --check app/ tests/ && .venv/bin/flake8 app/ ; .venv/bin/pytest -q
   ```
   flake8 — допустимы только pre-existing E501 из log.md шага 0.
   Исправлять до прохождения. Гейт прокси-успеха: тест не глушить и не
   скипать ради зелёного.
2. Коммит правок, если были: `chore: final QA fixes [protocol-0033-safe-to-spend/06]`.
3. PR в Ready — пропустить (фон «без push»; делает /protocol-review-merge).
4. `context.md`: Status `Completed`, Next Action `Ожидается /protocol-review-merge`.
5. **След в истории — последним коммитом ветки:** ROADMAP.md — в п.10
   отметить P1 «режим можно тратить» (частично: лимит есть, излишек в
   подушку — нет), «обрыв слоя Платежи», «ложный ноль» как сделанные
   `[x]` с датой и ссылкой «протокол 0033, ветка 0033-safe-to-spend»;
   план «сшивка» не трогать. feature_progress.md — «Батч 30» (3 строки
   + файлы + число тестов), rolling window — самый старый батч в архив.
6. Финальный коммит: `docs(protocol): finalize 0033-safe-to-spend [protocol-0033-safe-to-spend/06]`
   со строкой «Документы: обновлены ROADMAP п.10, feature_progress (батч 30)».

## Отчёт

```
(Протокол 0033-safe-to-spend — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: ветка, коммиты
**CWD**: /home/skytiger/Projects/worktrees/0033-safe-to-spend
**Статус**: Completed. Ожидается /protocol-review-merge
```
