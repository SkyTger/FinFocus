# Батч 1: Фундамент — цвета + формат ₽ + KPI-карточки

**Epic**: Epic-05-UI (Dashboard UI Redesign)
**Дата старта**: TBD
**Статус**: 🔄 Планирование
**Протокол**: 0021-dashboard-foundation

---

## 🎯 Цель батча

Обновить фундаментальные элементы Dashboard:
1. Цветовую схему (зелёный `#2ecc71` вместо `#28a745`, палитра Status/Neutral)
2. Глобальный формат денег (`$X,XXX.XX` → `X XXX ₽`) по всему приложению
3. KPI-карточки (убрать градиенты, добавить бордер/тень, кнопка "Сверка")
4. Скрыть AI Assistant и Exchange (код сохранить для будущей реализации)
5. Типографику по спецификации (40px hero, 16px заголовок, 12px подпись)

**Приоритет**: Must Have — блокирует батчи 2-3, т.к. меняет глобальный форматтер и CSS-переменные.

---

## ✅ Задачи (детальный checklist)

### Задача 1: Новые CSS-переменные
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 2`

- [ ] Обновить `app/assets/custom.css` — секция `:root` переменных
- [ ] Удалить старые переменные:
  - `--primary: #28a745` → заменить на `#2ecc71`
  - `--success: #28a745` → удалить или переименовать
- [ ] Добавить новые переменные по спецификации:
  - `--color-primary: #2ecc71` (яркий зелёный, accent)
  - `--color-primary-dark: #27ae60` (темнее, для текста/иконок)
  - `--color-secondary: #3498db` (синий, ссылки/secondary CTA)
  - `--color-secondary-dark: #2980b9`
  - `--color-income: #27ae60` (столбцы графика)
  - `--color-expense: #e74c3c` (столбцы графика)
  - `--color-status-attention: #f39c12` (жёлтый, баланс < 5 000 ₽)
  - `--color-status-risk: #c0152f` (красный, баланс отрицательный)
  - `--color-text-primary: #2c3e50` (тёмный для текста)
  - `--color-text-secondary: #95a5a6` (серый для подписей)
  - `--color-text-muted: #7f8c8d` (серый для описаний)
  - `--color-surface: #ffffff` (белый, карточки)
  - `--color-background: #f8f9fa` (светлый серый, фон страницы)
  - `--color-border: #bdc3c7` (бордеры)
  - `--color-separator: #ecf0f1` (разделители)
- [ ] Обновить существующие компоненты на использование новых переменных

**Файлы**: `app/assets/custom.css`

---

### Задача 2: Глобальный форматтер денег `format_rub()`
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 3`

- [ ] Создать функцию `format_rub()` в `app/utils/formatters.py`:
  - Входные параметры: `amount: Decimal | float`, `show_sign: bool = False` (для дельт)
  - Логика:
    - Округление до 2 знаков (но если `.00` — не показывать)
    - Разделитель тысяч: пробел (не запятая)
    - Символ ₽ в конце (с пробелом перед ним)
    - Если `show_sign=True` и `amount > 0` → добавить `+`
    - Если `amount < 0` → знак минус (не дефис)
  - Примеры:
    - `format_rub(15000)` → `"15 000 ₽"`
    - `format_rub(2350.50, show_sign=True)` → `"+2 350.50 ₽"`
    - `format_rub(-1200, show_sign=True)` → `"−1 200 ₽"`
    - `format_rub(100000)` → `"100 000 ₽"`
- [ ] **Примечание**: В текущем коде нет функции `format_usd()`. Форматирование денег делается inline (например `f"${metrics['total_balance']:,.2f}"`). Необходимо создать `format_rub()` и заменить все inline-форматирования на вызов этой функции.
- [ ] Обновить `app/utils/__init__.py` — экспорт `format_rub`

**Файлы**: `app/utils/formatters.py`, `app/utils/__init__.py`

---

### Задача 3: Обновить все UI-компоненты на `format_rub()`
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 3`

**Глобальная замена**: Заменить все inline-форматирования денег (например `f"${amount:,.2f}"`) на вызов `format_rub()` во всех компонентах

- [ ] **Dashboard** (`app/components/dashboard.py`):
  - KPI-карточки: Total Balance, Income, Expense, Savings
  - Графики: hover tooltip, подписи осей
  - Таблицы операций (если есть)
- [ ] **Calendar** (`app/components/calendar.py`):
  - Tooltip дней (баланс, операции)
  - Модал создания операции (поле amount preview)
  - Модал сверки (текущий остаток, фактический баланс, preview)
- [ ] **Goals** (`app/components/goals.py`):
  - Карточка цели (current_amount, target_amount)
  - Таблица взносов (amount)
  - Модал создания/редактирования (поле amount placeholder)
  - Safety Cushion карточка (target, current, threshold)
- [ ] **Transactions** (`app/components/transactions.py`):
  - Таблица операций (колонка amount)
  - Фильтры (если есть сумма)
- [ ] **Transaction Modals** (`app/components/transaction_modals.py`):
  - Поля amount (placeholder, validation messages)
  - Preview при создании/редактировании
- [ ] **Wishlist** (`app/components/wishlist.py`):
  - Карточка wishlist (amount)
  - Модал управления (поле amount)
  - Hover data (баланс после покупки)
- [ ] **Onboarding Wizard** (`app/components/onboarding_wizard.py`):
  - Поле starting_balance (placeholder, validation)
  - Toast с балансом

**Файлы**: 8 компонентов (см. список выше)

---

### Задача 4: Переделать 4 KPI-карточки
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 4, 10 (шаг 2)`

**Текущее состояние**: Карточки с цветными градиентными заливками, доллары, нет кнопок действий

**Целевое состояние**:
- Белый фон (`#ffffff`)
- Бордер `1px solid #bdc3c7` ИЛИ тень `0 2px 8px rgba(0,0,0,0.08)` (не одновременно)
- Радиус 8-10px
- Padding 20px
- Заголовок 12-14px, серый (`#95a5a6`)
- Главное число 32-40px, полужирное, чёрный (`#2c3e50`)
- Дельта или дополнительный KPI 14-16px, серый
- Иконка тонкая (Bootstrap Icons), или верхний бордер 2-4px в цвет статуса

**Действия**:
- [ ] Обновить `_build_kpi_card()` функцию в `app/components/dashboard.py`:
  - Параметры: `title, value, subtitle, icon, status_color` (опционально)
  - Layout:
    - dbc.Card с белым фоном, бордер/тень
    - Иконка слева или верхний бордер (если `status_color`)
    - Заголовок 12px, серый
    - Число 40px, bold, чёрный (`format_rub()`)
    - Subtitle 12px, серый (дельта или период)
  - Убрать градиенты, цветные заливки
- [ ] **Total Balance карточка**: добавить кнопку "Сверка" (зелёная, см. спецификацию секция 4)
  - Кнопка: `dbc.Button("Сверка", color="success", size="sm")`
  - Callback: открывает модал сверки (переиспользуем модал с Calendar)
- [ ] **Income карточка**: иконка доход (зелёная), дельта `vs прошлый месяц` (если есть данные)
- [ ] **Expense карточка**: иконка расход (красная), дельта `vs прошлый месяц`
- [ ] **Savings карточка**: иконка цели (синяя), subtitle `X целей активны` или `прогресс X%`

**Файлы**: `app/components/dashboard.py`

---

### Задача 5: Скрыть AI Assistant и Exchange карточки
**Ссылка на спецификацию**: решение из обсуждения #4

**Действия**:
- [ ] В `app/components/dashboard.py` — найти код карточек AI Assistant и Exchange
- [ ] Закомментировать вызовы в основном layout:
  ```python
  # TODO: Epic-08 — реализовать AI Assistant
  # ai_assistant_card,

  # TODO: Epic-08 — реализовать Exchange
  # exchange_card,
  ```
- [ ] Оставить функции `_build_ai_assistant_card()` и `_build_exchange_card()` (не удалять код)
- [ ] Добавить комментарии с ссылкой на план эпика:
  ```python
  # См. .reports/epics/epic-05-ui/plan.md — отложенные задачи
  ```

**Файлы**: `app/components/dashboard.py`

---

### Задача 6: Типографика по спецификации
**Ссылка на спецификацию**: `dashboard_ui_spec.md:секция 3`

**Действия**:
- [ ] Обновить CSS-классы в `app/assets/custom.css`:
  - `.kpi-number` — 40px, semibold/bold, `#2c3e50`
  - `.kpi-title` — 16px, medium, `#95a5a6`
  - `.kpi-subtitle` — 12px, regular, `#95a5a6`
  - `.table-amount` — 14-16px, regular, `#2c3e50`, text-align: right
  - `.table-description` — 13px, regular, `#7f8c8d`
  - `.link-show-all` — 13px, semibold, `#3498db`, underline on hover
- [ ] Применить классы в компонентах Dashboard:
  - KPI-карточки: `.kpi-number`, `.kpi-title`, `.kpi-subtitle`
  - Таблицы операций (если есть): `.table-amount`, `.table-description`

**Файлы**: `app/assets/custom.css`, `app/components/dashboard.py`

---

### Задача 7: Unit тесты для `format_rub()`
**Действия**:
- [ ] Создать/обновить `tests/test_formatters.py`:
  - `test_format_rub_positive()` — `15000` → `"15 000 ₽"`
  - `test_format_rub_negative()` — `-1200` → `"−1 200 ₽"`
  - `test_format_rub_with_sign_positive()` — `2350.50, show_sign=True` → `"+2 350.50 ₽"`
  - `test_format_rub_with_sign_negative()` — `-1200, show_sign=True` → `"−1 200 ₽"`
  - `test_format_rub_zero()` — `0` → `"0 ₽"`
  - `test_format_rub_large_number()` — `1000000` → `"1 000 000 ₽"`
  - `test_format_rub_decimal()` — `Decimal("15000.00")` → `"15 000 ₽"`
  - `test_format_rub_decimal_with_cents()` — `Decimal("1234.56")` → `"1 234.56 ₽"`
- [ ] Запустить pytest — все тесты должны проходить (≥ 491 тестов, было 483 + 8 новых)

**Файлы**: `tests/test_formatters.py`

---

### Задача 8: Финализация
- [ ] Black: переформатировать изменённые файлы
- [ ] Flake8: исправить E501, F401 (если есть)
- [ ] Pytest: запустить полный набор тестов (≥ 491)
- [ ] Проверить Dashboard в браузере:
  - KPI-карточки без градиентов, с бордером/тенью
  - Формат денег `X XXX ₽` везде
  - Кнопка "Сверка" на Total Balance
  - AI Assistant и Exchange скрыты
- [ ] Обновить `feature_progress.md` — добавить батч 15

---

## 📊 Затронутые файлы с описанием изменений

### Новые файлы
Нет новых файлов в этом батче.

### Модифицированные файлы

| Файл | Изменения | Строк (примерно) |
|------|-----------|------------------|
| `app/assets/custom.css` | +15 CSS-переменных, +6 типографических классов | +50 строк |
| `app/utils/formatters.py` | `format_rub()` функция (логика форматирования) | +30 строк |
| `app/utils/__init__.py` | Экспорт `format_rub` | +1 строка |
| `app/components/dashboard.py` | Переделка 4 KPI-карточек, замена format_usd() → format_rub(), скрыть AI/Exchange | ~150 строк изменено |
| `app/components/calendar.py` | Замена format_usd() → format_rub() | ~30 строк изменено |
| `app/components/goals.py` | Замена format_usd() → format_rub() | ~40 строк изменено |
| `app/components/transactions.py` | Замена format_usd() → format_rub() | ~20 строк изменено |
| `app/components/transaction_modals.py` | Замена format_usd() → format_rub() | ~15 строк изменено |
| `app/components/wishlist.py` | Замена format_usd() → format_rub() | ~25 строк изменено |
| `app/components/onboarding_wizard.py` | Замена format_usd() → format_rub() | ~10 строк изменено |
| `tests/test_formatters.py` | +8 unit тестов для format_rub() | +80 строк |

**Всего**: 11 файлов, ~451 строк изменено/добавлено

---

## ✅ Acceptance Criteria

### Visual
- [ ] Все числа в приложении отображаются в формате `X XXX ₽` (пробел как разделитель тысяч, символ ₽ в конце)
- [ ] Отрицательные числа со знаком `−` и красным цветом (`#e74c3c`)
- [ ] 4 KPI-карточки на Dashboard:
  - Белый фон, бордер `1px solid #bdc3c7` или тень
  - Радиус 8-10px, padding 20px
  - Заголовок 12px серый, число 40px чёрное bold
  - Кнопка "Сверка" на Total Balance (зелёная)
- [ ] AI Assistant и Exchange карточки скрыты (не видны на Dashboard)
- [ ] Цветовая схема обновлена:
  - Зелёный accent `#2ecc71` (было `#28a745`)
  - Новые переменные Status/Neutral применены

### Functional
- [ ] `format_rub()` корректно форматирует все типы чисел (positive, negative, zero, large, decimal)
- [ ] Кнопка "Сверка" на Total Balance открывает модал сверки (переиспользуем модал с Calendar)
- [ ] Модал сверки показывает текущий остаток и preview коррекции в формате ₽

### Technical
- [ ] Все тесты проходят (pytest ≥ 491)
- [ ] Black + Flake8 OK (0 ошибок)
- [ ] Нет регрессий в других страницах (Calendar, Goals, Transactions)
- [ ] Производительность Dashboard не ухудшилась (< 2 сек загрузка)

---

## 🔗 Зависимости и риски

### Зависимости
- **Блокирует**: Батч 2 (дневной график), Батч 3 (таблицы операций) — используют `format_rub()` и новые CSS-переменные
- **Не блокируется**: Независим от других батчей

### Риски

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Регрессия форматирования в старых компонентах | Средняя | Высокое | Полное тестирование всех страниц (Dashboard, Calendar, Goals, Transactions) |
| Несовместимость формата ₽ с Excel экспортом | Низкая | Среднее | CSV экспорт уже использует UTF-8 BOM (протокол 0011), должен корректно отображать ₽ |
| Пропущенные вызовы `format_usd()` | Средняя | Среднее | Поиск по кодовой базе: `grep -r "format_usd" app/` перед финализацией |
| Конфликт CSS-переменных с Bootstrap | Низкая | Низкое | Использовать префикс `--color-*` для избежания конфликтов |

---

## 📝 Примечания

### Формат минуса
- **Важно**: Использовать символ минус `−` (U+2212), а не дефис `-` (U+002D)
- **Реализация**: В Python `chr(0x2212)` или `"\u2212"`

### Кнопка "Сверка"
- **Переиспользуем**: Модал сверки уже реализован в `app/components/calendar.py` (протокол 0010-categories)
- **Интеграция**: Добавить callback `open_reconciliation_from_dashboard()` в `dashboard.py`, который триггерит тот же модал

### AI Assistant и Exchange
- **Не удаляем код**: Функции `_build_ai_assistant_card()` и `_build_exchange_card()` остаются в файле
- **TODO комментарии**: Явно указать ссылку на Epic-08 для будущей реализации

---

**Статус**: ✅ Scope батча 1 финализирован, готов к протоколу 0021
