# Шаг 3: Композитор и маркер узкого места

## Briefing

- **Цель:** «Ближайшая просадка» на карточке «Календарь» и маркер на
  графике полос показывают узкое место (`bottleneck_date`,
  `bottleneck_available`), а не минимум «Свободно» (который по новой
  формуле всегда сегодня).
- **Ключевые файлы:** `app/services/panel_service.py:390-400`,
  `app/schema/panel.py` (`CalendarCardData.dip_*` — переименовать или
  оставить имена, но переписать докстринг), `app/components/panel_cards.py`,
  `app/components/dashboard.py:520-560` (маркер и аннотация «минимум: …»),
  тесты `tests/test_panel_service.py:182-186`,
  `tests/test_panel_cards_ui.py:397`, `tests/test_dashboard_panel_ui.py:398-411`
- **Доп. информация:** `dip_is_strong` = есть нехватка (shortfall > 0)
  либо `bottleneck_available <= 0` — факт знака, без порогов.

## Sub-tasks

1. Композитор берёт узкое место из модели; при `shortfall > 0`
   карточка показывает дату и сумму нехватки.
2. Маркер графика: точка на `bottleneck_date` (если в оси; если узкое
   место за краем оси — маркера нет, это не ошибка), аннотация
   «узкое место: N ₽» (или «не хватает N ₽»).
3. Тесты: в ноябрьском сценарии (фикстура шага 2) маркер и карточка
   показывают одну дату — конец первого периода, не ref; пустое окно;
   узкое место за краем оси.
4. black / flake8 / pytest.

## Workflow

1. Sub-tasks последовательно
2. `.venv/bin/python -m py_compile {FILES}`
3. log.md, context.md
4. `git status`
5. Коммит: `git add . && git commit -m "feat(panel): маркер и карточка — узкое место вместо минимума свободного [protocol-0033-safe-to-spend/03]"`
6. Push — не делать
7. Отчёт
