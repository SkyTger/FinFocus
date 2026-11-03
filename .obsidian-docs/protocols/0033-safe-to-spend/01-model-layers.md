# Шаг 1: Модель слоёв на удлинённом горизонте

## Briefing

- **Цель:** `MoneyLayersService` считает слои через `available(t)` и
  суффиксный минимум `m(D)` до горизонта H; появляются нехватка и
  узкое место; C-5 и `payments_end` удалены. Формулы — plan.md,
  раздел «Спецификация».
- **Ключевые файлы:**
  - `app/services/money_layers_service.py` (`get_money_layers`, `_horizons`,
    `_forecast_balances`, `_collect_operations`, `_payments_tail_by_day` →
    заменить, `_window_min_free` → удалить, `_split_day` НЕ трогать)
  - `app/schema/money_layers.py` (Horizons, DayLayers, MoneyLayersData, новый LimitPeriod), `app/schema/__init__.py`
  - `tests/test_money_layers_service.py`
- **Доп. информация:** Сбор доходов нужен для H: `_collect_operations`
  сейчас собирает только расходные типы — добавить сбор дат доходов
  (income, по фактическим датам, включая экземпляры регулярных) или
  получить их из того же источника, откуда CalendarService строит
  прогноз. Прогноз и сбор тянуть до H, не до window_end.

## Sub-tasks

0. **Сначала — окружение и базовая линия** из `00-setup.md`, пп. 1–2
   (venv в worktree через uv, прогон 928 тестов, известные E501 → log.md),
   если в log.md этого ещё нет.
1. Схема: `Horizons` — `collect_start, window_end, horizon_end,
   horizon_has_income_after` (без `payments_end`); `LimitPeriod`;
   новые поля `MoneyLayersData` по plan.md; удалить `min_free`,
   `min_free_date`, `payments_end`. Переписать докстринги (C-5 отменён
   протоколом 0033).
2. Модель: H по правилу plan.md (константа горизонта рядом с
   `WINDOW_DAYS`); `available(t)` с резервом того же дня; `m(D)` одним
   проходом справа налево по ряду [ref, H]; вход `_split_day` —
   `payments_raw = available(D) − m(D)`; `shortfall`/`shortfall_date`.
   Поля лимита в этом шаге заполнить временно пустыми/None — их считает
   шаг 2 (поля уже есть в схеме, чтобы читатели не ломались дважды).
   `bottleneck_*` в этом шаге = день минимума `available` на [ref, H]
   (первый при равенстве); шаг 2 заменит на конец первого периода.
3. **Прогнать тесты ДО правки тестов:** `.venv/bin/pytest -q 2>&1 | tail -60`.
   Записать в log.md ПОЛНЫЙ список упавших (файл::тест) с одной строкой
   «почему упал: новый смысл / ошибка реализации». Падения из-за
   ошибки реализации — чинить код, не тест.
4. Переписать упавшие по новому смыслу — ожидания из ручного расчёта
   фикстуры (расчёт — в log.md). Тесты «0 после конца месяца» и
   «платежи монотонно тают» заменяются тестами нового смысла, не
   удаляются молча.
5. Новые тесты модели (минимум):
   - инвариант `free + payments + reserve == balance` для всех дней оси
     на сценариях: доход до платежа, платёж через границу месяца,
     нехватка (balance > 0, m < 0), reserve > 0 при нехватке;
   - доход 20-го покрывает платёж 25-го → «Платежи» на 3-е не включают
     платёж 25-го (ложный ноль ушёл);
   - платёж за краем оси (после window_end), до ближайшего дохода — есть
     в слое «Платежи» последних дней оси;
   - нет доходов после оси → `horizon_has_income_after is False`,
     H = ref + 89;
   - пример со взносом на цели (бюджет 10 000, взнос 10 000 на 25-е,
     остаток 50 000 на 3-е): с авансом 100 000 20-го → free 50 000,
     payments 0, reserve 0; без аванса → free 40 000, payments 10 000;
   - нехватка: `shortfall` и `shortfall_date` на сценарии с дефицитом.
6. `.venv/bin/black app/ tests/`, `.venv/bin/flake8 app/` (только
   pre-existing), `.venv/bin/pytest -q` — тесты UI/композитора,
   читающие удалённые поля, допустимо чинить здесь МИНИМАЛЬНО (замена
   имени поля), смысловые правки UI — шаги 3–4.

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `.venv/bin/python -m py_compile {FILES}`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Проверь отсутствие случайных файлов (`git status`)
6. Коммит: `git add . && git commit -m "feat(layers): available и суффиксный минимум на удлинённом горизонте [protocol-0033-safe-to-spend/01]"`
7. Push — не делать (фон «без push»)
8. Отчёт по формату из `report-format.md.tpl`
