# Шаг 3: Unit Tests

## Briefing

- **Цель:** Написать unit тесты для CushionService (15+ тестов)
- **Ключевые файлы:**
  - `tests/test_cushion_service.py` — NEW
- **Доп. информация:** См. solution-v3.md, секция "Дополнительные unit тесты для v3"

## Sub-tasks

1. **Создать `tests/test_cushion_service.py`:**

   Тесты должны покрывать:
   - `_validate_percent()`: valid (0, 30, 100), invalid (-1, 101)
   - `get_settings()`: not configured (target=0), configured (target>0), progress calculation
   - `update_settings()`: valid update, invalid target (<0), invalid percent
   - `reset_settings()`: reset to defaults
   - `calculate_recommendation()`: sum mode, max_scenario mode, invalid mode

2. **Минимум 15 тестов:**
   ```python
   # Примеры из solution-v3.md:
   def test_validate_percent_valid():
       assert _validate_percent(0) == Percent(0)
       assert _validate_percent(30) == Percent(30)
       assert _validate_percent(100) == Percent(100)

   def test_validate_percent_invalid_negative():
       with pytest.raises(ValidationError) as exc_info:
           _validate_percent(-1)
       assert "0-100" in str(exc_info.value)

   def test_get_settings_not_configured():
       # target=0 → is_configured=False
       ...

   def test_get_settings_progress_capped_at_100():
       # current > target → progress = 100.0
       ...
   ```

3. **Запустить тесты:**
   ```bash
   pytest tests/test_cushion_service.py -v
   ```

## Workflow

1. Создать файл тестов с 15+ тест-кейсами
2. Запустить: `pytest tests/test_cushion_service.py -v`
3. Убедиться что все тесты проходят
4. Обнови `log.md`
5. Обнови `context.md` — Current Step: 4
6. Коммит: `git add . && git commit -m "test(cushion): add unit tests for CushionService [protocol-0013/03]"`
7. Push
8. Отчёт
