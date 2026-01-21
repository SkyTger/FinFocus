# Шаг 7: Финализация

## Briefing
- **Цель:** Финальное тестирование, написание интеграционных тестов, обновление документации, перевод PR в статус Ready.
- **Ключевые файлы:**
  - `tests/test_goals_integration.py` (создать)
  - `ROADMAP.md` (обновить)
  - `.reports/notes/feature_progress.md` (обновить)
  - `.memory-bank/` (обновить при необходимости)
- **Additional info:**
  - Интеграционные тесты проверяют E2E сценарии
  - ROADMAP.md — отметить задачу как завершенную
  - feature_progress.md — добавить запись о батче

## Sub-tasks

1. **Написать интеграционные тесты** в `tests/test_goals_integration.py` (3 теста):
   ```python
   def test_create_multiple_goals_with_auto_priority():
       """E2E: создание 3+ целей с автоматическим назначением приоритетов.

       1. Создать 3 цели без указания priority
       2. Проверить что priorities = [1, 2, 3]
       3. Проверить сортировку в get_all_by_user
       """

   def test_priority_reorder_updates_allocation():
       """E2E: изменение приоритета пересчитывает распределение.

       1. Создать 3 цели с monthly_contribution [100, 200, 300]
       2. Установить budget = 250
       3. Проверить allocation: [100, 150, 0]
       4. Поменять приоритеты (цель 3 → 1)
       5. Проверить новый allocation: [250, 0, 0]
       """

   def test_budget_change_updates_allocation():
       """E2E: изменение бюджета пересчитывает распределение.

       1. Создать 2 цели с monthly_contribution [100, 100]
       2. Установить budget = 150
       3. Проверить allocation: [100, 50]
       4. Увеличить budget до 200
       5. Проверить allocation: [100, 100]
       """
   ```

2. **Запустить полный цикл тестов**:
   ```bash
   pytest tests/ -v --tb=short
   ```
   Убедиться что все 16+ тестов проходят.

3. **Проверить coverage** (опционально):
   ```bash
   pytest tests/ --cov=app --cov-report=term-missing
   ```

4. **Обновить ROADMAP.md**:
   - Найти задачу "Множественные цели с приоритетами" в Батч 2
   - Отметить как `[x] ✅` с датой и ссылкой на PR
   - Обновить прогресс Батч 2: `50%` (2/4 фичи)

5. **Обновить feature_progress.md**:
   - Добавить запись о Батч 9: Multiple Goals
   - Формат как предыдущие батчи
   - Включить: цель, выполненные задачи, ключевые файлы, уроки

6. **Обновить Memory Bank** (если нужно):
   - `modules/services.md` — добавить AllocationService
   - `modules/database.md` — добавить monthly_savings_budget

7. **Финальная проверка качества**:
   ```bash
   black app/ tests/
   flake8 app/ tests/
   pytest tests/ -v
   ```

8. **Перевести PR в Ready**:
   ```bash
   gh pr ready
   ```

9. **Добавить финальную запись в log.md** и обновить context.md:
   - `Current Step`: 7
   - `Status`: Completed
   - `Last Action Summary`: "Протокол 0006 завершен. PR готов к review."
   - `Next Action`: "Ожидание review и merge."

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи 1-9.

2. **Верификация:**
   ```bash
   black app/ tests/
   flake8 app/ tests/
   pytest tests/ -v
   ```

3. **Фиксация:**
   - Добавь финальную запись в `log.md`
   - Обнови `context.md` с финальным статусом
   - Проверь ветку main

4. **Коммит:**
   ```bash
   git add .
   git commit -m "chore(docs): finalize protocol 0006 and update documentation [protocol-0006/07]"
   git push
   ```

5. **Отчет пользователю:**
   - Сообщить что протокол завершен
   - Дать ссылку на PR
   - Перечислить что было реализовано
