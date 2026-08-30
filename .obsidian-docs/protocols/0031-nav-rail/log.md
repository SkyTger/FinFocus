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

---

### Step 02 — Источник версии

Создан `app/version.py` с константой `__version__ = "0.9.0-beta.1"`,
наполнен `app/__init__.py` (реэкспорт + инвариант), написан
`tests/test_version.py` — 7 тестов.

#### Что сделано

- **`app/version.py`** — константа + докстринг, объясняющий: почему
  модуль кода, а не data-файл (попадает в PYZ, читается импортом);
  условие достижимости по графу импортов от `run.py`; почему отвергнуты
  `importlib.metadata` (нет дистрибутива), data-файл (нужен `datas` в
  спеке), `git describe` в рантайме (нет `.git` в бандле); бамп руками
  вместе с git-тегом; почему имя `version.py`, а не `__version__.py`.
- **`app/__init__.py`** — был 0 байт. Теперь докстринг с инвариантом
  («ничего, кроме докстринга, реэкспорта и `__all__`» — файл
  выполняется при любом `import app.<...>`, импорт сервисов отсюда
  даст цикл), `from app.version import __version__`, `__all__`.
- **`tests/test_version.py`** — непустота, PEP 440, «не 1.0.0»,
  совпадение реэкспорта с модулем, инвариант `__init__` через AST,
  сверка с git-тегом (skip без `.git`/`git`), grep на захардкоженные
  версии в `app/`.

#### Проверки

`py_compile` OK, black чист, flake8 по трём файлам — пусто (в `app/`
остались те же 4 pre-existing E501, новых нет).
`pytest tests/test_version.py` — **6 passed, 1 xfailed**.

**Mutation-проверка (4 порчи, все пойманы адресными тестами):**

| порча | поймал |
|---|---|
| `__version__ = "1.0.0"` | `test_version_is_not_placeholder` + `test_version_matches_git_tag` |
| `__version__ = "v0.9.0-beta.1"` | `test_version_is_pep440_compatible` + `test_version_matches_git_tag` |
| лишний `from app.config.avatars import AVATARS` в `__init__` | `test_app_init_contains_only_version_reexport` |
| `__version__ = "0.9.2"` (разъезд с тегом) | `test_version_matches_git_tag` |

После восстановления — снова 6 passed, 1 xfailed.

#### Решение: `xfail(strict=True)` вместо нестрогого

Шаг 2 предписывает «пометить xfail / активировать после шага 9» для
теста на захардкоженные версии (строка `v1.0.0` живёт в
`sidebar.py:166` до шага 9). Взят **strict=True**: после шага 9 тест
начнёт проходить, и strict превратит это в XPASS-падение — громкое
напоминание снять маркер. Нестрогий xfail остался бы тихо зелёным
навсегда, и маркер пережил бы протокол.

Механизм проверен симуляцией шага 9 (временно убрана строка версии из
сайдбара): получено `[XPASS(strict)] ... 1 failed, 6 passed` — работает
как задумано, файл восстановлен.

#### Расхождение с текстом шага (не блокер)

Шаг 2 ссылается на «полный текст — solution-v3, "Ключевые интерфейсы"».
**Файла `solution-v3.md` для куска 3 на диске нет** — в
`.obsidian-docs/design/epic-11-panel-batch-3/` лежит только `spec.md`
(для кусков 1-2 solution-файлы есть, для 3-го не сохранились из
контекста `/design-loop`). Докстринг написан по списку пунктов,
перечисленных в самом шаге 2 — там они даны явно и полностью.
То же ждать на последующих шагах, если они ссылаются на solution-v3.

#### ⚠️ Постороннее падение (НЕ моё, вне scope шага)

Полная сюита: **771 passed, 1 xfailed, 1 failed**. Падает
`test_dashboard_panel_ui.py::TestLegendAndTooltips::test_payments_tooltip_lists_operations`.

Проверено, что падение **не связано с шагом 2**: временно убрал свои
файлы и откатил `app/__init__.py` до чистого дерева (`git status`
пуст) — тест падает точно так же.

**Причина — протухание по датам, тот самый паттерн из открытого
вопроса №6 ROADMAP.** Фикстура `make_layers_data` кладёт платежи на
`сегодня + 2` и `сегодня + 4` дня, а `_build_payments_tooltip`
отсекает по концу текущего месяца. Сегодня 30 августа → обе даты
уезжают на 1 и 3 сентября, тултип честно отдаёт «До конца месяца
платежей больше нет», а тест ждёт заголовок со списком.

Тест зелёный ~27 дней в месяц и красный последние 2-4 дня. В main
он такой же — просто до сегодня никто не запускал сюиту в конце
месяца. Чужой тест, к навигации отношения не имеет; чинить его
внутри шага 2 не стал (scope), но и молча оставлять красный CI
нельзя — вынесено отдельным пунктом ниже.

**Действие**: починка вынесена в отдельный коммит этого протокола
(фикстура на относительных датах не должна пересекать границу месяца)
— см. следующую запись журнала.
