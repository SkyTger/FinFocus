# Шаг 3: Тесты композитора

## Briefing

- **Цель:** `tests/test_panel_service.py` — тесты сборки `PanelData`, включая целевые на дефекты, найденные циклом проектирования.
- **Ключевые файлы:**
  - `tests/test_panel_service.py` — НОВЫЙ
  - `tests/conftest.py` — хелперы относительных дат (использовать, не хардкодить даты)
- **Доп. информация:** solution-v4.md, план шаг 4. Почему каждый тест именно такой — там объяснено; если тест кажется избыточным, сначала прочитать обоснование.

## Sub-tasks

- [ ] **AC-3**: `panel["calendar"]["days"][0]["balance"] == panel["layers"]["today"]["balance"] == panel["layers"]["days"][0]["forecast_balance"]`
- [ ] **Целевой тест `goals=OK`** (ловит неверный конструктор `AllocationService`): фикстура с двумя активными целями `priority=1/2` и `monthly_savings_budget = 30 000` так, чтобы бюджета хватило первой и не хватило второй → `status == OK`, `others_count == 1`, `others_behind_count == 1`, `top_goal_name` — цель с `priority=1`; **плюс ассерт «в логах нет трейсбека по goals»**
- [ ] **Типы `OperationRow`**: `isinstance(panel["operations"]["recent"][0]["date"], date)`; `kind` ∈ трёх значений на фикстуре со **всеми шестью** `transaction_type`; `is_recurring` True у материализованного recurring-инстанса
- [ ] **Материализация**: собрать `PanelData` внутри `with`, выйти из сессии, прочитать **все** поля всех пяти срезов (ловит `DetachedInstanceError`, которого не видят тесты карточек)
- [ ] **AC-5 в двух вариантах фикстуры**: пустая база **с** `User(id=1)` и **без** пользователя → в обоих все пять блоков `EMPTY`, `goals` не `FAILED`, в логах нет трейсбека
- [ ] **Контракт `_empty_*` на уровне данных**: `others_summary == ""`, `cushion_label == ""`, нули и `Decimal("0")` где положено, Optional — `None`, `href` непусты
- [ ] **Деградация**: `patch` падающего сервиса → один блок `FAILED`, остальные `OK`
- [ ] **Смешанный случай**: `layers["is_empty"] == True` + заведённая цель → `goals=OK` с цифрами, `operations=EMPTY`; и обратный
- [ ] **Согласованность подушки**: `cushion_progress` из `layers` совпадает с `CushionService.get_settings(...)["progress"]`
- [ ] **Счётчики**: `get_money_layers` вызван один раз; счётчик SQL-запросов через `sqlalchemy.event` на `before_cursor_execute`

## Workflow

1. Выполни Sub-tasks последовательно
2. Проверка: `pytest tests/test_panel_service.py -v`
3. Обнови `log.md`, `context.md`
4. Проверь `main` на случайные файлы
5. Коммит: `git add . && git commit -m "test(services): тесты DashboardPanelService [protocol-0030/03]"`
6. Push
7. Отчёт
