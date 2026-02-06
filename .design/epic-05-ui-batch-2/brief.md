# Brief: Daily Cashflow Chart on Dashboard (Batch 5.2)

## Цель
Реализовать дневной график кассового календаря на Dashboard -- центральный элемент UI спецификации Epic-05-UI: DashboardService.get_daily_cashflow() для агрегации дневных данных, Plotly grouped bar chart с линией running balance, маркером минимума, hover tooltip, клик на день для создания операции, переключатель Month/Year.

## Функциональные требования
- FR-1: Метод `DashboardService.get_daily_cashflow(user_id, year, month)` возвращает `MonthlyCashflowData` с дневной агрегацией income/expense, running balance, минимумом месяца
- FR-2: Running balance учитывает starting_balance + все операции (включая recurring) от начала времен до каждого дня
- FR-3: ADJUSTMENT учитывается как income (amount > 0) или expense (amount < 0); TRANSFER не учитывается (0/0); SAVINGS_RESERVE и SAVINGS_CONTRIBUTION учитываются как расход
- FR-4: Минимум месяца: определяется день с наименьшим balance, статус "risk" (< 0), "attention" (< 5000), "ok" (>= 5000)
- FR-5: Plotly grouped bar chart: столбцы income (#27ae60) и expense (#e74c3c), barmode="group"
- FR-6: Линия running balance (go.Scatter, lines+markers, width=2.5), цвет единый по статусу min_balance_point
- FR-7: Маркер минимума (go.Scatter, 1 точка, diamond marker, text "Мин: дата, сумма")
- FR-8: X-ось: tickvals кратные 7 (1, 8, 15, 22, 29), вертикальная пунктирная линия на today
- FR-9: Y-ось: горизонтальные gridlines opacity 10-15%, без вертикальных gridlines
- FR-10: Hover tooltip: hovermode="x unified" с датой, доходом, расходом, балансом
- FR-11: Клик на день -> открытие create-transaction-modal с preselected-date через Preselection Store Pattern
- FR-12: Переключатель Month/Year (ButtonGroup или существующий RadioItems)

## Нефункциональные требования
- NFR-1: get_daily_cashflow() выполняется < 200ms для месяца ~100 операций
- NFR-2: Не переиспользовать CalendarService.get_balance_on_date() для каждого дня (30 запросов); использовать CalendarService.calculate_daily_balances() (1 вызов) или прямой запрос
- NFR-3: Все тесты проходят (pytest >= 502, было 492 + 10 новых)
- NFR-4: Black + Flake8 OK

## Ограничения
- Линия баланса: единый цвет по минимуму месяца (не сегменты разных цветов, Plotly ограничение)
- Year режим: может быть отложен (кнопка "Год" скрыта или показывает старый chart). Не блокирует батч
- Тёмная тема: откладывается (Epic-06)
- Адаптивность: desktop-first, мобильная адаптация -- Epic-07

## Критерии приёмки
- [ ] DailyCashflow, DailyBalancePoint, MonthlyCashflowData TypedDicts определены
- [ ] get_daily_cashflow() корректно агрегирует income/expense по дням (включая recurring)
- [ ] Running balance вычисляется правильно (кумулятивный от starting_balance)
- [ ] Минимум месяца определяется правильно (день, значение, статус)
- [ ] ADJUSTMENT учитывается, TRANSFER не учитывается
- [ ] Plotly grouped bar chart отображается с income/expense столбцами
- [ ] Линия running balance отображается с цветом по статусу
- [ ] Маркер минимума отображается с текстом
- [ ] X-ось: подписи кратные 7, today подсвечен
- [ ] Hover tooltip с unified mode
- [ ] Клик на день -> модал создания с preselected датой
- [ ] Переключатель Month/Year работает без перезагрузки
- [ ] 10+ unit тестов для get_daily_cashflow()
- [ ] pytest >= 502, Black + Flake8 OK

## Вне scope (out of scope)
- Year режим (агрегированный по месяцам) -- может быть отложен
- Тёмная тема (Epic-06)
- Мобильная адаптивность (Epic-07)
- Split "Недавние/Предстоящие" операции (Batch 5.3)
- Sidebar как card-контейнер (Batch 5.3)
- Правая колонна layout (Batch 5.3)