# Work Log: 0031-nav-rail — Полоска-меню вместо сайдбара

> Журнал работы. Записи только добавляются.

---

## Restore Context Log

<!-- Записи вида: Restore context: protocol-0031#ctx-N -->

Restore context: protocol-0031#ctx-1

---

## Step Log

<!--
Формат записи:
### Step XX — [название] (commit: abc1234)
- Что сделано
- Неочевидные решения и почему
- Проблемы и как решены
-->
### Step 01 — Проверка гипотезы реконсиляции

**Итог: гипотеза подтверждена в ОБОИХ режимах.** Исход по матрице —
строка 1 («не моргает / не моргает»): идти дальше по основному пути,
`id` остаётся страховкой от вставки второго элемента в слот (Epic-08).

#### Как мерялось

Приложение: `.venv` главного чекаута (dash 2.17.1, Python 3.10.12),
код — из worktree, порт 8051, `DEBUG=False`. Браузер — Playwright
(agent-browser), переходы — **настоящими кликами мыши** по ссылкам
сайдбара (mouse move + down + up по координатам центра ссылки),
не `location.assign` и не программным `.click()`.

Наблюдение (в) из Sub-tasks — прямое, не опосредованное анимацией:
узел `.sidebar-card` сохранялся в `window.__probeNode`, после каждого
перехода проверялись `document.contains(window.__probeNode)` и
строгое тождество `document.querySelector('.sidebar-card') === window.__probeNode`.
Наблюдение (б) — глобальный слушатель `animationstart` с фильтром по
`e.animationName === '__probe'`, счётчик + лог путей.

#### Проба 1.a — контроль (без `id`, индексное сопоставление)

Подтверждено, что на живом узле `id` действительно отсутствует:
`hasId: null`.

Цепочка `/calendar → /goals → /analytics → /transactions → /calendar → /goals`
(5 переходов), после каждого:

```
{"url":"/goals",       "sameNodeInDoc":true,"currentIsSame":true,"animCount":0,"animLog":[]}
{"url":"/analytics",   "sameNodeInDoc":true,"currentIsSame":true,"animCount":0,"animLog":[]}
{"url":"/transactions","sameNodeInDoc":true,"currentIsSame":true,"animCount":0,"animLog":[]}
{"url":"/calendar",    "sameNodeInDoc":true,"currentIsSame":true,"animCount":0,"animLog":[]}
{"url":"/goals",       "sameNodeInDoc":true,"currentIsSame":true,"animCount":0,"animLog":[]}
```

Узел ни разу не пересоздан, анимация не запускалась ни разу.

#### Проба 1.b — целевой режим (`id="__probe-rail"`, именованный ключ)

Подтверждено, что `id` доехал до DOM: `hasId: "__probe-rail"`.
Та же цепочка из 5 переходов:

```
{"url":"/goals",       "sameNodeInDoc":true,"currentIsSame":true,"curId":"__probe-rail","animCount":0,"animLog":[]}
{"url":"/analytics",   "sameNodeInDoc":true,"currentIsSame":true,"curId":"__probe-rail","animCount":0,"animLog":[]}
{"url":"/transactions","sameNodeInDoc":true,"currentIsSame":true,"curId":"__probe-rail","animCount":0,"animLog":[]}
{"url":"/calendar",    "sameNodeInDoc":true,"currentIsSame":true,"curId":"__probe-rail","animCount":0,"animLog":[]}
{"url":"/goals",       "sameNodeInDoc":true,"currentIsSame":true,"curId":"__probe-rail","animCount":0,"animLog":[]}
```

Результат идентичен пробе 1.a.

#### Контроль чувствительности пробы (добавлено сверх Sub-tasks)

Само по себе «animCount: 0» ничего не доказывает, если проба немая:
нулевой счётчик одинаково выглядит и при переиспользовании узла, и при
неработающем слушателе/анимации. Поэтому в обеих пробах прогнан
контрольный случай через дашборд, где сайдбар снимается физически
(`render_sidebar_slot` возвращает `[]`), — там узел ОБЯЗАН пересоздаться:

- `/goals → /dashboard` (снятие): `cards: 0`, `oldNodeInDoc: false`
  — старый узел действительно исчез из документа;
- `/dashboard → /calendar` (монтирование заново): `animCount: 1`,
  `animLog: ["/calendar"]` — анимация сыграла.

Оба контроля дали ожидаемый результат в обеих пробах. Значит инструмент
различает «переиспользован» и «пересоздан», и нули в основных прогонах —
настоящий результат, а не молчание сломанной пробы.

#### Неочевидное, что всплыло по ходу

1. **`.venv` в worktree нет** — он машинно-локальный и с worktree не
   переезжает. Запуск: интерпретатор из `/home/skytiger/Projects/FinFocus/.venv/bin/python`,
   но CWD — worktree, поэтому исполняется код ветки. Для шага 8
   (проверка `clip-path`) — та же схема.
2. **База в worktree создалась пустой** → приложение открывало
   блокирующий онбординг-визард (`backdrop="static"`), который
   перехватывал ВСЕ клики: `document.elementFromPoint` в точке ссылки
   возвращал `DIV|fade modal show`, навигация не происходила, и это
   выглядело как «ссылки не работают». Лечится копированием рабочей
   базы из главного чекаута (`data/finfocus.db`, 32 операции, 2 цели,
   `first_launch=0`); файл под `.gitignore` (`*.db`), в коммит не попадает.
   Для шага 8 — учесть сразу.
3. Побочно подтверждено поведение AC-1 куска 2: на `/dashboard`
   сайдбара в DOM нет вообще (`sidebar-cards: 0`).

#### Откат

`git checkout app/assets/sidebar.css app/components/sidebar.py` выполнен,
`grep -rn "__probe" app/` — пусто, `py_compile app/components/sidebar.py` — OK.
В рабочей копии остались только файлы протокола (`context.md`, `log.md`).
Кода в коммите шага 1 нет — только эта запись.
