# Solution v2: Переиспользование шаблонов и автоматический пересчёт exceptions

## Обзор решения
Решение состоит из четырёх ключевых изменений в BudgetReservationService: (1) переиспользование существующего шаблона при переключении режимов вместо создания нового, (2) метод recalculate_current_month_exception() для пересчёта при изменениях взносов/бюджета, (3) интеграция пересчёта в update_contribution_transaction(), (4) унификация логики get_budget_progress() для показа взносов. Дополнительно добавляется метод delete_contribution() в GoalService и документируется порядок вызовов в save_budget callback.

## Архитектура

### Компоненты

**BudgetReservationService (модифицируется)**
- Добавляется `_find_any_reserve_template()` — поиск любого шаблона включая остановленный
- Добавляется `_get_template_day()` — извлечение дня из шаблона (31 = anchor day для EOM)
- Добавляется `_cleanup_orphan_exceptions()` — удаление orphan exceptions (включая остановленные шаблоны)
- Добавляется `_get_reserve_date_for_month()` — вычисление даты резерва
- Добавляется `_delete_exception_for_date()` — удаление exception по дате
- Добавляется `recalculate_current_month_exception()` — пересчёт exception
- Модифицируется `set_mode()` — логика переиспользования шаблона
- Модифицируется `update_contribution_transaction()` — добавляется вызов recalculate
- Модифицируется `get_budget_progress()` — единообразный расчёт used_budget

**GoalService (модифицируется)**
- Добавляется `delete_contribution()` — удаление взноса с пересчётом exception

**goals.py callbacks (документация)**
- `save_budget()` — задокументирован порядок: update_savings_budget → set_mode → recalculate

### Диаграмма взаимодействия

```
set_mode("fixed_date", day=15)
    │
    ▼
_find_any_reserve_template()
    │
    ├─ Найден с day=15 ──► Реактивировать (recurring_end_date=None)
    │                      Exceptions сохраняются!
    │
    └─ Найден с day≠15 ──► _stop_reserve_template()
       или не найден       _cleanup_orphan_exceptions(old_template_id)
                           _create_reserve_template()

add_contribution() / update_contribution_transaction() / delete_contribution()
    │
    ▼
adjust_reserve_for_contribution() / recalculate_current_month_exception()
    │
    ├─ reserve_date < today ──► Skip (дата прошла)
    │
    └─ reserve_date >= today ──► RecurringService.create_exception()
                                 или _delete_exception_for_date()
    │
    ▼
Calendar показывает корректный резерв
```

## Файловая структура

```
app/services/budget_reservation_service.py  — основные изменения (6 новых методов, 3 модификации)
app/services/goal_service.py                — новый метод delete_contribution()
app/components/goals.py                     — документирующий комментарий в save_budget callback
tests/test_budget_reservation_service.py    — новые тестовые классы
```

## Ключевые интерфейсы

```python
# app/services/budget_reservation_service.py

class BudgetReservationService:
    """Сервис управления режимами резервирования бюджета на накопления."""

    def _find_any_reserve_template(self, user_id: int) -> Transaction | None:
        """Находит любой recurring шаблон резерва (включая остановленный).

        Ищет последний созданный шаблон SAVINGS_RESERVE для переиспользования.
        Порядок: сначала активные (recurring_end_date IS NULL), затем остановленные.

        Returns:
            Transaction | None: Шаблон или None если не найден.
        """
        ...

    def _get_template_day(self, template: Transaction) -> int:
        """Извлекает день месяца из шаблона.

        Для EOM anchor (recurring_anchor_eom=True) возвращает 31.
        ВАЖНО: 31 — это "anchor day" для сравнения шаблонов,
        не фактический день (фактический определяется _get_anchored_date).

        Returns:
            int: День месяца (1-31). 31 = EOM anchor.
        """
        ...

    def _cleanup_orphan_exceptions(self, template_id: int) -> int:
        """Удаляет exceptions для остановленного шаблона.

        Вызывается при изменении дня месяца для очистки
        невалидных exceptions от старого шаблона.
        Удаляет ВСЕ exceptions для шаблона с recurring_end_date < today.

        Returns:
            int: Количество удалённых exceptions.
        """
        ...

    def _get_reserve_date_for_month(
        self, user_id: int, reference_date: date
    ) -> date | None:
        """Возвращает дату резерва для указанного месяца.

        Учитывает короткие месяцы (min(day_of_month, last_day)).

        Returns:
            date | None: Дата резерва или None если режим != fixed_date.
        """
        ...

    def _delete_exception_for_date(
        self, template_id: int, target_date: date
    ) -> bool:
        """Удаляет exception для конкретной даты.

        Используется при пересчёте когда взносов нет (резерв = полный бюджет).

        Returns:
            bool: True если exception удалён, False если не существовал.
        """
        ...

    def recalculate_current_month_exception(
        self, user_id: int, month: date | None = None
    ) -> bool:
        """Пересчитывает exception для текущего/указанного месяца.

        Вызывается при:
        - Удалении взноса (через delete_contribution)
        - Изменении суммы взноса (через update_contribution_transaction)
        - Изменении monthly_savings_budget (через save_budget callback)

        Логика:
        1. Считает contributions_sum для взносов до даты резерва (< reserve_date)
        2. new_reserve = budget - contributions_sum
        3. Если new_reserve == budget → удаляет exception (нет взносов)
        4. Иначе → создаёт/обновляет exception через RecurringService.create_exception()

        Args:
            user_id: ID пользователя.
            month: Дата в целевом месяце (default: today).

        Returns:
            bool: True если exception обновлён/создан/удалён, False если не требуется.
        """
        ...

    def set_mode(
        self,
        user_id: int,
        mode: ReservationMode,
        day_of_month: int | None = None,
    ) -> BudgetReservationSettings:
        """Устанавливает режим резервирования с переиспользованием шаблона.

        При переключении на fixed_date:
        1. Ищет существующий шаблон (включая остановленный) через _find_any_reserve_template
        2. Если день совпадает — реактивирует (recurring_end_date=None, exceptions сохраняются)
        3. Если день изменился — останавливает старый, чистит orphan exceptions,
           создаёт новый шаблон
        """
        ...

    def update_contribution_transaction(
        self,
        transaction_id: int,
        new_amount: Decimal,
    ) -> bool:
        """Обновляет сумму транзакции, синхронизирует GoalContribution и пересчитывает exception.

        ИЗМЕНЕНИЕ v2: После обновления contribution вызывает
        recalculate_current_month_exception() для корректировки резерва.

        Args:
            transaction_id: ID транзакции.
            new_amount: Новая сумма.

        Returns:
            bool: True если обновление успешно, False если транзакция не найдена.
        """
        ...

    def get_budget_progress(
        self,
        user_id: int,
        reference_date: date | None = None,
    ) -> BudgetProgress:
        """Рассчитывает прогресс использования бюджета.

        ИЗМЕНЕНИЕ v2: Единообразно для обоих режимов считает взносы (contributions),
        не резервы. mode_text = "Внесено" для обоих режимов.
        """
        ...
```

```python
# app/services/goal_service.py

class GoalService:
    """Сервис для операций с целями накопления."""

    def delete_contribution(self, contribution_id: int) -> bool:
        """Удаляет взнос и пересчитывает exception.

        Алгоритм:
        1. Находит GoalContribution по ID
        2. Если есть transaction_id — удаляет через BudgetReservationService.delete_contribution_transaction()
        3. Иначе — удаляет напрямую
        4. Обновляет Goal.current_amount
        5. Вызывает recalculate_current_month_exception()

        Args:
            contribution_id: ID взноса GoalContribution.

        Returns:
            bool: True если взнос удалён, False если не найден.
        """
        ...
```

## Модель данных

Изменений в схеме БД не требуется. Используются существующие структуры:

```python
# Существующие TypedDicts (без изменений)
BudgetReservationSettings = TypedDict(
    "BudgetReservationSettings",
    {
        "mode": ReservationMode,
        "day_of_month": int | None,
        "monthly_budget": Decimal,
        "template_id": int | None,
    },
)

BudgetProgress = TypedDict(
    "BudgetProgress",
    {
        "total_budget": Decimal,
        "used_budget": Decimal,  # v2: Теперь всегда взносы, не резервы
        "available_budget": Decimal,
        "progress_percent": float,
        "status": str,
        "mode": ReservationMode,
        "mode_text": str,  # v2: Теперь всегда "Внесено"
    },
)
```

## Обработка ошибок

**Стратегия: Fail-safe with logging**
- Отсутствие шаблона при пересчёте — логируем warning, возвращаем False (не ошибка)
- Прошедшая дата резерва (reserve_date < today) — логируем debug, не пересчитываем (корректное поведение)
- Отсутствие пользователя — ValueError (существующее поведение)
- Невалидный day_of_month — ValueError (существующее поведение)

```python
# Паттерн обработки в recalculate_current_month_exception
def recalculate_current_month_exception(self, user_id: int, month: date | None = None) -> bool:
    if month is None:
        month = date.today()

    settings = self.get_settings(user_id)

    # Guard: только fixed_date режим
    if settings["mode"] != "fixed_date":
        return False

    reserve_date = self._get_reserve_date_for_month(user_id, month)
    if reserve_date is None:
        return False

    # Guard: не пересчитываем ПРОШЕДШИЕ даты (< today, не <=)
    # ВАЖНО: если reserve_date == today, пересчёт НУЖЕН — recurring экземпляр
    # ещё не "материализован", взнос должен уменьшить резерв
    if reserve_date < date.today():
        logger.debug(f"Reserve date {reserve_date} already passed, skipping recalc")
        return False

    template = self._get_reserve_template(user_id)
    if not template:
        logger.warning(f"No active template for user {user_id}, skipping recalc")
        return False

    # === Расчёт суммы взносов ===
    # ВАЖНО: Считаем только взносы ДО даты резерва (< reserve_date),
    # т.к. взносы ПОСЛЕ резерва не влияют на его сумму (бюджет уже "потрачен")
    month_start = date(month.year, month.month, 1)
    contributions_sum = (
        self.session.query(func.coalesce(func.sum(GoalContribution.amount), 0))
        .join(Goal, Goal.id == GoalContribution.goal_id)
        .filter(
            Goal.user_id == user_id,
            GoalContribution.contribution_date >= month_start,
            GoalContribution.contribution_date < reserve_date,  # СТРОГО < (не <=)
        )
        .scalar()
    )
    contributions_sum = Decimal(str(contributions_sum))

    # Расчёт новой суммы резерва
    budget = settings["monthly_budget"]
    new_amount = max(budget - contributions_sum, Decimal("0"))

    # Если нет взносов до резерва — удаляем exception (резерв = полный бюджет)
    if contributions_sum == Decimal("0"):
        deleted = self._delete_exception_for_date(template.id, reserve_date)
        if deleted:
            logger.info(f"Deleted exception for {reserve_date}, no contributions before reserve")
        return deleted

    # Создаём/обновляем exception
    description = (
        f"{RESERVE_DESCRIPTION} (внесено досрочно)"
        if new_amount == 0
        else RESERVE_DESCRIPTION
    )

    from app.services import RecurringService
    recurring_service = RecurringService(self.session)
    recurring_service.create_exception(
        template_id=template.id,
        original_date=reserve_date,
        new_amount=new_amount,
        new_description=description,
    )

    logger.info(
        f"Recalculated exception for user {user_id}, month {month}, "
        f"contributions_sum={contributions_sum}, new_reserve={new_amount}"
    )
    return True
```

## План реализации

**Порядок вызовов в save_budget (ДОКУМЕНТИРОВАТЬ):**
```
1. goal_service.update_savings_budget()  — обновляет User.monthly_savings_budget
                                          + sync_template_amount()
2. reservation_service.set_mode()        — переиспользует/создаёт шаблон с НОВЫМ бюджетом
3. reservation_service.recalculate_current_month_exception()
                                          — пересчитывает exception с НОВЫМ бюджетом
```

1. **Добавить helper методы в BudgetReservationService** (~80 строк)
   - `_find_any_reserve_template()` — query с сортировкой: активные первые, затем по дате создания desc
   - `_get_template_day()` — возвращает 31 для anchor_eom=True (с комментарием)
   - `_cleanup_orphan_exceptions()` — удаляет exceptions для шаблонов с recurring_end_date < today
   - `_get_reserve_date_for_month()` — min(day_of_month, last_day)
   - `_delete_exception_for_date()` — filter + delete + flush

2. **Реализовать recalculate_current_month_exception()** (~60 строк)
   - Guard clauses: mode, reserve_date, template
   - Комментарий про фильтрацию `< reserve_date`
   - Логика "нет взносов → удалить exception"
   - Вызов RecurringService.create_exception()

3. **Модифицировать set_mode()** (~40 строк изменений)
   - Вызов _find_any_reserve_template() вместо _get_reserve_template()
   - Сравнение дней через _get_template_day()
   - Условие реактивации (day совпадает) vs создания (day изменился)
   - Вызов _cleanup_orphan_exceptions() при смене дня

4. **Модифицировать update_contribution_transaction()** (~10 строк)
   - После обновления contribution: получить user_id через contribution.goal.user_id
   - Вызов recalculate_current_month_exception(user_id)

5. **Модифицировать get_budget_progress()** (~15 строк изменений)
   - Заменить _get_reserve_sum_for_month на _get_contributions_sum_for_month для обоих режимов
   - mode_text = "Внесено" для обоих режимов

6. **Добавить delete_contribution() в GoalService** (~40 строк)
   - Поиск GoalContribution
   - Условная логика: если transaction_id — через BudgetReservationService
   - Обновление Goal.current_amount
   - Вызов recalculate_current_month_exception

7. **Добавить документирующий комментарий в save_budget callback** (~5 строк)
   - Порядок: update_savings_budget → set_mode → recalculate

8. **Unit тесты для новых методов** (~180 строк)
   - TestFindAnyReserveTemplate (активный, остановленный, несколько)
   - TestGetTemplateDay (обычный, anchor_eom, 31)
   - TestCleanupOrphanExceptions (остановленный шаблон, будущие exceptions)
   - TestRecalculateException (с взносами, без взносов, удаление)
   - TestSetModeReuse (реактивация, смена дня)
   - TestUpdateContributionRecalc (изменение суммы → recalc)
   - TestBudgetProgressUnified (оба режима → взносы)

9. **Integration тесты** (~60 строк)
   - TestModeSwitch E2E: fixed_date → from_balance → fixed_date
   - TestContributionFlow: взнос → изменение → удаление

10. **Финализация** (lint, format, full test suite)

## Зависимости

Новых библиотек не требуется. Используются существующие:
- SQLAlchemy (ORM)
- loguru (logging)
- datetime, decimal (stdlib)

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| Регрессия в CalendarService при изменении get_budget_progress | Средняя | Calendar использует виртуальные экземпляры, не get_budget_progress напрямую. Добавить integration тесты calendar + reservation |
| Некорректная логика EOM anchor при _get_template_day | Низкая | Отдельные unit тесты для day=31 и anchor_eom=True. Комментарий в коде что 31 = anchor |
| Race condition при параллельных вызовах recalculate | Низкая | Single-user приложение в MVP. Для multi-user добавить pessimistic locking |
| Orphan exceptions не удаляются полностью | Низкая | _cleanup_orphan_exceptions удаляет ВСЕ exceptions для остановленных шаблонов (recurring_end_date < today), не только для переданного template_id |
| Удаление exception при 0 взносов создаёт дублирующий резерв | Низкая | Тест: создать взнос → удалить → проверить что резерв = budget |

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 Отсутствует пересчет при изменении суммы взноса | Добавлен вызов recalculate_current_month_exception() в update_contribution_transaction() после обновления GoalContribution |
| 🔴 Граничное условие <= некорректно | Изменено на `reserve_date < date.today()` — взнос в день резерва корректно создаёт exception |
| 🟡 Неполная очистка orphan exceptions | _cleanup_orphan_exceptions() удаляет ВСЕ exceptions для шаблонов с recurring_end_date < today |
| 🟡 Отсутствует комментарий про фильтрацию | Добавлен комментарий в recalculate_current_month_exception(): "ВАЖНО: Считаем только взносы ДО даты резерва (< reserve_date)..." |
| 🟡 Порядок вызовов не задокументирован | Добавлен документирующий комментарий в save_budget callback + секция в плане реализации |
| 🟢 EOM anchor логика | Добавлен комментарий в _get_template_day(): "31 — это anchor day для сравнения шаблонов, не фактический день" |
| 🟢 Именование метода | Оставлено _delete_exception_for_date (консистентно с проектом: delete_goal, delete_contribution_transaction) |

## Ответы на вопросы критика

1. **Вопрос:** Порядок вызовов в save_budget
   **Ответ:** Порядок задокументирован: update_savings_budget → set_mode → recalculate. Зависимости:
   - update_savings_budget обновляет User.monthly_savings_budget и вызывает sync_template_amount()
   - set_mode использует НОВОЕ значение бюджета из User для шаблона
   - recalculate использует НОВОЕ значение бюджета из settings для exception
   Документирующий комментарий добавляется в callback для предотвращения нарушения порядка.

2. **Вопрос:** Удаление взноса через UI
   **Ответ:** Да, планируется добавить UI для удаления взноса. Метод delete_contribution() в GoalService будет использоваться. Сейчас удаление возможно через календарь (delete_contribution_transaction), но это удаляет только транзакцию. Новый метод delete_contribution() обеспечит полную очистку (GoalContribution + Transaction + recalculate).

3. **Вопрос:** Редактирование суммы взноса
   **Ответ:** Редактирование возможно в календаре для взносов с transaction_id (режим from_balance и взносы до резерва в fixed_date). Вызывается update_contribution_transaction(), который теперь включает recalculate. Для взносов без transaction_id (режим fixed_date, после резерва) — планируется в будущем через отдельный метод update_contribution() в GoalService.

4. **Вопрос:** Тайминг recurring генерации
   **Ответ:** CalendarService "материализует" виртуальные экземпляры при каждом рендере периода через RecurringService.generate_instances(). Это происходит в реальном времени, не как cron job. Поэтому:
   - Если reserve_date == today, recurring экземпляр ещё виртуальный
   - Взнос в день резерва ДОЛЖЕН создавать exception
   - Условие изменено на `reserve_date < today` (строго меньше)
   - Таким образом взнос в 8:00 корректно уменьшит резерв, который будет показан при рендере в 9:00
