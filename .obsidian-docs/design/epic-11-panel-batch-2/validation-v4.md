# Spec Validation Report — Solution v4

**Spec:** `.obsidian-docs/design/epic-11-panel-batch-2/spec.md`
**Solution:** `.obsidian-docs/design/epic-11-panel-batch-2/solution-v4.md`
**Date:** 2026-08-26
**Validator:** spec-validator (haiku)

## Результат: PASS

## Статистика
- Всего конкретных требований в spec: 25
- Покрыто в RTM: 25
- Покрыто в solution (с конкретной реализацией, а не отсылкой): 25
- Пропущено: 0
- Пропущено критичных: 0

## Покрытие по категориям

| Категория | Требований | Покрыто | Статус |
|---|---|---|---|
| Visual | 4 | 4 | ✅ |
| UX Copy | 3 | 3 | ✅ |
| Performance | 2 | 2 | ✅ |
| Edge Cases | 8 | 8 | ✅ |
| Integration | 9 | 9 | ✅ |
| **Итого** | **25** | **25** | **PASS** |

## Детали

### Visual
| Requirement | Секция spec | RTM | Реализация |
|---|---|---|---|
| Маркер просадки, усиленный при ≤ 0 | FR-1.a, AC-7 | #91 | `build_calendar_card`, флаг `dip_is_strong` |
| Стили дверей `.pnl-door*` | FR-1, эскиз v3 | #72 | `app/assets/panel.css` |
| Пустые состояния без артефактов (0 ₽, 0%) | FR-5, AC-5 | #81, #96 | контракт `_empty_*`, build-функции |
| Адаптив 1180px → 2 колонки, 680px → 1 | эскиз v3 | #73 | брейкпоинты `panel.css` |

### UX Copy
| Requirement | Секция spec | RTM | Реализация |
|---|---|---|---|
| Подпись «расходы августа · без регулярных и взносов в цели» | FR-1.d | #87 | `AnalyticsCardData`, `build_analytics_card` |
| Пустое состояние — `""`, не текст | FR-5, AC-5 | #96 | `others_summary=""`, `cushion_label=""` |
| Постоянно пустая подпись окошка «вчера» | FR-1.a, FR-6 | #62 | пункт 18 ручного чек-листа (решение на живой базе) |

### Performance
| Requirement | Секция spec | RTM | Реализация |
|---|---|---|---|
| Открытие дашборда < 2 сек | NFR-1 | #33, #95 | замер `_load_dashboard_components` + счётчик SQL |
| Не более 1 сессии на сборку панели | NFR-1, FR-6 | #32, #95 | `DashboardPanelService(session)` — единая сессия |

### Edge Cases
| Requirement | Секция spec | RTM | Реализация |
|---|---|---|---|
| «Вчера»: платежи из расширенного списка дат | FR-1.a, FR-6, C-5 | #89, #93 | `calc_dates` → `_payments_tail_by_day`, тест на значение + mutation |
| Резерв «вчера» по дню `ref`, не `yday` | FR-1.a, FR-6, C-5 | #93 | `_yesterday_slice`: `goals_part[ref]`, тест на 1-е число |
| `AllocationService` — stateless, без `__init__` | C-3, NFR-2, AC-4 | #94 | `AllocationService()`, целевой тест `goals=OK` |
| Отсутствие пользователя → `EMPTY`, не `FAILED` | FR-5, AC-5, NFR-2 | #92 | `session.get(User)` → `None` → `_empty_goals()` |
| `dip_*` не рисуется при `status != OK` | AC-7, AC-5 | #91 | оговорка в `CalendarCardData` + целевой тест UI |
| Контракт `_empty_*` для пяти блоков | FR-5, AC-5, NFR-2 | #96 | таблица значений + тест на уровне данных |
| Материализация ORM после закрытия сессии | C-2, NFR-2 | #84 | контракт в докстринге + тест после `with` |
| Явные преобразования типов `OperationRow` | C-2 | #85 | `date.fromisoformat`, `TRANSACTION_KIND_MAP`, тест `isinstance` |

### Integration
| Requirement | Секция spec | RTM | Реализация |
|---|---|---|---|
| Владение `url.search` по pathname | C-1, AC-2 | #79 | `_OWNED_SEARCH_PATHS`, `PreventUpdate` на `/transactions` |
| Удаление элемента → удаление его Input | C-6, AC-8 | #80 | `open-wishlist-modal-btn` + его Input удаляются вместе |
| Один источник правды пустоты — `CardStatus` | FR-5, AC-5 | #81 | `is_new_user` убрано, тесты смешанного случая |
| Операции — только материализованные | FR-1.c, C-3 | #82 | ограничение в трёх местах (решение владельца) |
| Output на условно присутствующие узлы сайдбара сняты | C-6, AC-1, AC-9 | #83, #88 | оба колбэка удаляются, данные в построении |
| Идемпотентность Store-фокусов — одна механика | FR-3, C-1, AC-2 | #90 | `ctx.triggered_id` + `focus_applied_ts` |
| Сайдбар — чистая функция без БД | C-2, C-6, FR-2 | #88 | `create_sidebar(pathname, profile)` |
| Форма `days` неизменна относительно куска 1 | C-5, C-7 | #86 | регрессионный тест формы, 47 тестов без правок |
| Расхождение цифры «Аналитика» объявлено | FR-6, C-3, AC-2 | #87 | докстринг + подпись карточки + тест на подпись |

## Пропущенные требования

Нет. Все пункты спецификации (FR-1.a–e, FR-2…FR-6, NFR-1…NFR-2, C-1…C-7, AC-1…AC-10, out of scope) учтены в RTM и имеют конкретную реализацию.

## Заключение

Блокеров нет. RTM — 97 строк с явными ссылками на требования спеки и места реализации; каждый архитектурный выбор обоснован перепроверкой по телам функций проекта.
