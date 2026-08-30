# 0032-system-ops-guard — Служебные операции в списке операций: маркировка и защита

## ADR-style Summary

- **Context**: Список операций (`/transactions`) выбирает ВСЕ шесть типов
  транзакций (`get_all_by_user` без фильтра типа), но рендер различает
  только INCOME: всё остальное — включая служебные SAVINGS_RESERVE,
  SAVINGS_CONTRIBUTION, ADJUSTMENT и TRANSFER — показывается красным
  бейджем «Расход». Всем строкам безусловно даются кнопки
  редактирования/удаления и чекбокс bulk-выделения; savings-типы без
  категории получают chips «быстрой категоризации». Календарь при этом
  УЖЕ различает служебные: readonly-строка, эмодзи 💼/🎯, подпись
  «(авто)», id=-1 против кликов (`calendar.py:437-500`), а Calendar
  Guard #6 блокирует SAVINGS_CONTRIBUTION от редактирования.
  Найдено анализом «сшивка разделов со щитком» 2026-08-30
  (ROADMAP, шаг 2 плана; развитие P2 UX-аудита 2026-08-20).
- **Problem Statement**: Пользователь может удалить или отредактировать
  системную операцию из списка. Прямое удаление SAVINGS_CONTRIBUTION
  минует каскад GoalService (Contribution → Transaction → Goal) и
  рассинхронизирует накопленную сумму цели; удаление SAVINGS_RESERVE
  ломает резервирование бюджета. Это класс «защита данных», не косметика.
- **Decision**: Двухуровневая защита. (1) UI: у SAVINGS_RESERVE и
  SAVINGS_CONTRIBUTION не рендерятся кнопки edit/delete, чекбокс bulk
  и chips; бейдж «Накопления» + подпись «(авто)» — зеркало календаря.
  ADJUSTMENT получает бейдж «Корректировка», TRANSFER — «Перевод»
  (подпись «Корректировка» уже существует в TransactionService:410 —
  переиспользовать словарь, не плодить второй). (2) Серверные guard'ы:
  callbacks edit/delete/bulk игнорируют служебные id (устаревший DOM,
  вторая вкладка), `bulk_update_category` исключает savings-типы на
  уровне сервиса.
- **Alternatives**: (а) Прятать служебные операции из списка целиком —
  отвергнуто: пользователь должен видеть, куда ушли деньги, и сверять
  список с календарём; (б) блокировать только на уровне сервиса —
  отвергнуто: мёртвые кнопки в UI с ошибкой по клику хуже отсутствия
  кнопок; (в) полноценный фильтр «служебные/пользовательские» —
  вне scope, кандидат в концепт-обсуждение «разделы после щитка».
- **Consequences**: Служебные операции становятся видимыми, но
  неприкосновенными в списке. Редактирование взносов остаётся ТОЛЬКО
  через Goals UI (протокол 0019 — там каскад корректен). Поведение
  ADJUSTMENT/TRANSFER решается на шаге 1 по факту осмотра модала
  (см. решение Р1 в 01-render-badges.md).

---

## High-Level Plan

> Этот раздел — **контракт**. Не изменяй при реализации.

- **[Шаг 0: Подготовка](./00-setup.md)**: Создание артефактов протокола
- **[Шаг 1: Маркировка и рендер](./01-render-badges.md)**: Бейджи всех
  типов, скрытие кнопок/чекбоксов/chips у служебных, «(авто)», тесты рендера
- **[Шаг 2: Серверные guard'ы](./02-guards.md)**: Защита callbacks
  edit/delete/bulk + `bulk_update_category`, тесты guard'ов
- **[Шаг 3: Финализация](./03-finalize.md)**: Полная верификация, перевод PR в Ready

---

## Protocol Workflow

**Пути:**
- PROJECT_ROOT: `/home/skytiger/Projects/FinFocus`
- CWD (worktree): `/home/skytiger/Projects/worktrees/0032-system-ops-guard`
- Протокол: `.obsidian-docs/protocols/0032-system-ops-guard/`

**Вся работа ведётся из CWD.**

### Цикл выполнения шага

См. `~/.claude/templates/protocol/workflow.md.tpl`

### Формат отчёта

См. `~/.claude/templates/protocol/report-format.md.tpl`

---

## Generic Principles

См. `~/.claude/templates/protocol/principles.md.tpl`

Дополнительно для этого протокола:
- **Тесты без БД, на относительных датах** — хелперы из `tests/conftest.py`,
  захардкоженные даты запрещены (открытый вопрос №6 ROADMAP).
- Линт: black из `.venv` (системный black 26.x форматирует иначе);
  flake8 — «без НОВЫХ замечаний» (6 pre-existing E501 известны).
- Прогон тестов: `/home/skytiger/Projects/FinFocus/.venv/bin/python -m pytest` (845 зелёных на старте).

---

## Reference Materials

- Образец readonly-маркировки: `app/components/calendar.py:437-500`
- Подпись «Корректировка»: `app/services/transaction_service.py:410`
- ADR-003 guard clauses для pattern-matching callbacks:
  `.obsidian-docs/knowledge-bank/patterns/callbacks.md`
- Каскад взносов (почему прямое удаление опасно): протокол 0019,
  `app/services/goal_service.py` (update/delete_contribution)
- План «сшивка разделов со щитком»: `.obsidian-docs/ROADMAP.md`,
  секция «План после Epic-11» (шаг 2)
