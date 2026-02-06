# Шаг 1: format_rub() + тесты

## Briefing

- **Цель:** Создать глобальный форматтер format_rub(), переопределить format_amount() как alias, написать unit тесты
- **Ключевые файлы:**
  - `app/utils/formatters.py` — format_rub() + format_amount() alias
  - `app/utils/__init__.py` — экспорт format_rub
  - `tests/test_formatters.py` — 10 unit тестов
- **Доп. информация:** См. `.design/solution-v2.md` секция "Ключевые интерфейсы" для сигнатуры format_rub()

## Sub-tasks

1. В `app/utils/formatters.py`:
   - Добавить `from decimal import Decimal` (если нет)
   - Добавить `MINUS_SIGN = "\u2212"` (типографский минус)
   - Реализовать `format_rub(amount, show_sign=False) -> str` по спецификации solution-v2.md
   - Переопределить `format_amount(amount) -> str` как alias: `return format_rub(amount)`

2. В `app/utils/__init__.py`:
   - Добавить `format_rub` в экспорт

3. Создать `tests/test_formatters.py` с 10 тестами:
   - test_format_rub_positive_integer: format_rub(15000) == "15 000 ₽"
   - test_format_rub_positive_decimal: format_rub(1234.56) == "1 234.56 ₽"
   - test_format_rub_negative: format_rub(-1200) == "−1 200 ₽" (U+2212)
   - test_format_rub_zero: format_rub(0) == "0 ₽"
   - test_format_rub_none: format_rub(None) == "0 ₽"
   - test_format_rub_show_sign_positive: format_rub(500, show_sign=True) == "+500 ₽"
   - test_format_rub_show_sign_negative: format_rub(-500, show_sign=True) == "−500 ₽"
   - test_format_rub_show_sign_zero: format_rub(0, show_sign=True) == "0 ₽"
   - test_format_rub_decimal_type: format_rub(Decimal("15000.50")) == "15 000.50 ₽"
   - test_format_amount_alias: format_amount(Decimal("1000")) == format_rub(Decimal("1000"))

4. Запустить `pytest tests/test_formatters.py` — 10 тестов PASS
5. Запустить `pytest` — 493 тестов PASS (483 + 10)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/utils/formatters.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step + 1, Next Action
5. Проверь main на случайные файлы
6. Коммит: `git add . && git commit -m "feat(formatters): add format_rub() global formatter [protocol-0021/01]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
