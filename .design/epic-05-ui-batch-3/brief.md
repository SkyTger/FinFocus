# Brief: Dashboard Layout Redesign (Batch 5.3)

## Цель
Завершить Dashboard UI redesign (Epic-05-UI) -- реализовать финальный layout с двухколоночной таблицей операций, правой колонной (Wishlist + Safety Cushion), sidebar в card-контейнере, модалом сверки на Dashboard и пустыми состояниями.

## Функциональные требования
- FR-1: Метод `DashboardService.get_upcoming_transactions()` -- возвращает операции от сегодня до конца месяца (ASC), limit 5
- FR-2: Расширить `get_recent_transactions()` для диапазона 1-е число месяца..сегодня (DESC), limit 5
- FR-3: Две колонки операций 50/50: "Недавние" (1..сегодня) и "Предстоящие" (сегодня..конец месяца)
- FR-4: Формат таблиц: дата в формате "5 февраля", описание + категория во вторую строку, сумма RIGHT, без "Completed" бейджей
- FR-5: Ссылки "Все операции" -> /transactions?start=YYYY-MM-DD&end=YYYY-MM-DD с явным диапазоном дат
- FR-6: Страница /transactions обрабатывает query params `?start=&end=` и предзаполняет фильтры дат
- FR-7: Правая колонна Dashboard: Wishlist widget + Safety Cushion card
- FR-8: Sidebar обернут в dbc.Card с активным пунктом, подсвеченным зеленым (border-left 4px)
- FR-9: Модал "Сверка" доступен с Dashboard через кнопку на Total Balance KPI
- FR-10: Пустые состояния: иконка bi-inbox + текст + CTA "Добавить"
- FR-11: CTA "Добавить" в пустых состояниях открывает create-modal

## Нефункциональные требования
- Все 508+ тестов проходят без регрессий
- Black + Flake8 OK (0 ошибок)
- Производительность Dashboard < 2 сек загрузка
- Desktop-first layout (1440px+), базовый responsive на 768px (single-column)

## Ограничения
- Dash callback architecture: модалы и их callbacks должны быть в DOM при загрузке страницы (suppress_callback_exceptions=True помогает, но Stores/Outputs должны существовать)
- Reconciliation modal сейчас внутри calendar_layout -- нужно извлечь в глобальный scope или продублировать
- Cushion modal и callbacks сейчас внутри goals_layout -- аналогичная проблема
- Не менять логику ReconciliationService, GoalService, CushionService
- Python 3.12, docstrings на русском

## Критерии приемки
- [ ] 2 колонки операций 50/50: "Недавние" (1..сегодня DESC) и "Предстоящие" (сегодня..конец ASC)
- [ ] Формат: дата "5 февраля", категория/тип во вторую строку, без "Completed", сумма RIGHT
- [ ] Ссылки "Все операции" -> /transactions с фильтром дат (предзаполнение работает)
- [ ] Правая колонна: Wishlist + Safety Cushion (одинаковая ширина, одинаковые бордеры)
- [ ] Sidebar как card-контейнер, активный пункт подсвечен зеленым
- [ ] Кнопка "Сверка" на Total Balance -> модал сверки баланса (работает с Dashboard)
- [ ] Пустые состояния с CTA "Добавить" (открывает create-modal)
- [ ] Pytest >= 515 (508 + ~7 новых), Black + Flake8 OK
- [ ] Нет регрессий на Calendar, Goals, Transactions, Analytics

## Вне scope (out of scope)
- Dark Theme (Epic-06)
- Mobile responsive < 576px (Epic-07)
- AI Assistant / Exchange cards (Epic-08)
- Tablet responsive (768px) -- базовый breakpoint допускается, но не обязателен
