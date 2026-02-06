# Brief: Dashboard UI Foundation -- Colors, Currency Format, KPI Cards

## Цель
Обновить фундаментальные элементы Dashboard и всего приложения: новая цветовая палитра (#2ecc71), глобальный формат денег (X XXX p.), переработка KPI-карточек, скрытие AI/Exchange, типографика по спецификации. Этот батч является blocking-фундаментом для батчей 5.2 (дневной график) и 5.3 (layout + таблицы).

## Функциональные требования
- FR-1: Создать функцию `format_rub(amount, show_sign)` для единообразного форматирования денежных сумм (пробел-разделитель тысяч, символ рубля в конце, знак минус U+2212, опциональный `+` для дельт)
- FR-2: Заменить все inline-форматирования денег (``f"${amount:,.2f}"``, ``f"{amount:,.0f}".replace(",", " ")``, `format_amount()`) на вызовы `format_rub()` во всех UI-компонентах
- FR-3: Обновить 4 KPI-карточки Dashboard: белый фон, бордер/тень вместо градиентов, число 40px bold, заголовок 12px серый
- FR-4: Добавить кнопку "Сверка" на карточку Total Balance, открывающую модал сверки с Calendar
- FR-5: Скрыть карточки AI Assistant и Exchange из layout Dashboard (код сохранить)
- FR-6: Применить новые CSS-переменные цветовой палитры (#2ecc71 primary, Status/Neutral семантика)
- FR-7: Добавить CSS-классы типографики (.kpi-number, .kpi-title, .kpi-subtitle, .table-amount, .table-description, .link-show-all)

## Нефункциональные требования
- Производительность Dashboard не ухудшается (< 2 сек загрузка)
- Нет регрессий в Calendar, Goals, Transactions, Analytics, Wishlist
- WCAG AA контраст для текста на всех карточках
- CSV экспорт корректно обрабатывает символ рубля (UTF-8 BOM уже включен)
- Минимальные изменения: format_rub() должна быть drop-in replacement для format_amount()

## Ограничения
- Не трогать логику сервисного слоя (DashboardService, CalendarService и т.д.)
- Не рефакторить main.py layout
- Не реализовывать Dark Theme (Epic-06)
- Не реализовывать Mobile Responsive (Epic-07)
- Не удалять функции AI Assistant и Exchange -- только закомментировать вызовы в layout
- Модал сверки уже реализован в calendar.py -- переиспользовать, не дублировать

## Критерии приемки
- [ ] Все числа в приложении отображаются в формате `X XXX p.` (пробел как разделитель тысяч, символ рубля в конце)
- [ ] Отрицательные числа со знаком минус (U+2212) и красным цветом
- [ ] 4 KPI-карточки: белый фон, бордер `1px solid #bdc3c7` или тень `0 2px 8px rgba(0,0,0,0.08)`, радиус 8-10px, padding 20px
- [ ] Кнопка "Сверка" на Total Balance открывает модал сверки
- [ ] AI Assistant и Exchange карточки не видны на Dashboard
- [ ] Цветовая схема: зеленый accent #2ecc71 вместо #28a745
- [ ] Pytest >= 491 тестов (483 + 8 новых для format_rub)
- [ ] Black + Flake8 OK

## Вне scope (out of scope)
- Dark Theme (Epic-06)
- Mobile breakpoints (Epic-07)
- Дневной график (батч 5.2)
- Split таблиц операций на Недавние/Предстоящие (батч 5.3)
- Правая колонна Wishlist + Safety Cushion на Dashboard (батч 5.3)
- Sidebar как card-контейнер (батч 5.3)
- Модал "Сверка" доступен с Dashboard (батч 5.3 по плану, но кнопка добавляется в 5.1)
- Пустые состояния (батч 5.3)
