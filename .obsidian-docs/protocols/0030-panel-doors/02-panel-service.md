# Шаг 2: Композитор данных

## Briefing

- **Цель:** `DashboardPanelService` — один сбор `PanelData` за одну сессию БД, пять блоков, поблочная деградация.
- **Ключевые файлы:**
  - `app/services/panel_service.py` — НОВЫЙ (~340 строк)
  - `app/services/__init__.py` — экспорт
  - читать: `money_layers_service.py`, `goal_service.py`, `allocation_service.py`, `dashboard_service.py`, `analytics_service.py`, `wishlist_service.py`
- **Доп. информация:** solution-v4.md, секция «Сервис-композитор» — докстринг класса с контрактом материализации и стратегией загрузки приведён полностью.

## Sub-tasks

- [ ] Класс + докстринг: контракт материализации ORM (блок возвращает только примитивы; обращение к ORM-атрибутам — внутри сессии) + стратегия загрузки с названными дублями
- [ ] `get_panel_data(user_id, reference_date)` — `get_money_layers` **вне** try/except (базовая модель не деградирует), четыре блока — каждый в своём try/except с `logger.opt(exception=True)`
- [ ] `_calendar_block(layers)` — чистая функция, ноль запросов: «сегодня» из `layers["days"][0]`, «завтра» из `[1]`; `dip_*` из `min_free`/`min_free_date`, при `status != OK` игнорируются
- [ ] `_goals_block(user_id, layers)` — **одно** `session.get(User, uid)` → три поля (`cushion_target`, `monthly_savings_budget`, `savings_mode`); `user is None` → `EMPTY`. **`AllocationService()` БЕЗ аргументов** — у класса нет `__init__` (проверить `grep "def __init__" app/services/allocation_service.py`). Подушка из `layers["cushion_threshold"]` + `layers["today"]["balance"]` + `User.cushion_target`, **без** `CushionService.get_settings`
- [ ] `_operations_block(user_id, ref)` — **явные преобразования** типов: `date.fromisoformat(row["date"])`, `TRANSACTION_KIND_MAP.get(v, "other")`, `is_recurring_instance → is_recurring`, `title = description or category_name or "Без описания"`
- [ ] `_analytics_block(user_id, ref)` — `get_expenses_by_category`, `month_total` = Σ `total`, `month_label` из `reference_date` (не из результата запроса)
- [ ] `_wishlist_block(user_id)` — `get_focus(limit=5)` + `to_data` **внутри** сессии (читает `category_rel`)
- [ ] Пять `_empty_*` по контракту из решения: Optional → `None`, числовые → `0`/`Decimal("0")`/`0.0`, строковые → `""` (не текст), списки → `[]`, `href` и `month_label` — как обычно
- [ ] `MoneyLayersService` и `app/schema/money_layers.py` **не трогать** (решение владельца про «вчера»)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/panel_service.py`
3. Обнови `log.md`, `context.md`
4. Проверь `main` на случайные файлы
5. Коммит: `git add . && git commit -m "feat(services): DashboardPanelService — один сбор данных щитка [protocol-0030/02]"`
6. Push
7. Отчёт
