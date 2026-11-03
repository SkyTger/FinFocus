# Шаг 4: Финализация

## Briefing

- **Цель:** Полная верификация; след в истории — последним коммитом ветки.

## Sub-tasks

1. **Полная верификация:**
   ```bash
   .venv/bin/black --check app/ tests/ && .venv/bin/flake8 app/ ; .venv/bin/pytest -q
   ```
   flake8 — только pre-existing E501 из log.md шага 0. Гейт
   прокси-успеха: тест не глушить и не скипать ради зелёного.
2. Коммит правок, если были: `chore: final QA fixes [protocol-0034-one-off-expenses/04]`.
3. PR в Ready — пропустить (фон «без push»; делает /protocol-review-merge).
4. `context.md`: Status `Completed`, Next Action `Ожидается /protocol-review-merge`.
5. **След в истории — последним коммитом ветки:** ROADMAP.md п.10 P2
   «Разовые траты отдельно от регулярных» — `[x]` с датой и «протокол
   0034, ветка 0034-one-off-expenses, коммит <последний коммит работы>»;
   отметить, что п.4 (разрезание полосы) не делался. feature_progress.md
   — «Батч 31» (3 строки + файлы + число тестов), «Тестов в main»,
   rolling window — самый старый батч (29) в архив
   `feature_progress_archive.md`.
6. Финальный коммит: `docs(protocol): finalize 0034-one-off-expenses [protocol-0034-one-off-expenses/04]`
   со строкой «Документы: обновлены ROADMAP п.10, feature_progress (батч 31)».

## Отчёт

```
(Протокол 0034-one-off-expenses — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Git**: ветка, коммиты
**Статус**: Completed. Ожидается /protocol-review-merge
```
