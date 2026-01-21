# Critique - Solution v2
Date: 2026-01-20
Reviewer: AI Critic (Claude Opus 4.5)

---

## 🎯 Общая оценка

**Рейтинг:** ⭐⭐⭐⭐ (4/5)

**Вердикт:**
- [ ] ✅ Отлично, можно кодировать как есть
- [x] 🟢 Хорошо, с минорными улучшениями
- [ ] 🟡 Требуются значительные изменения
- [ ] 🔴 Не рекомендуется, нужен другой подход

**Краткая суммаризация:**
Решение v2 значительно улучшено: добавлено хранение monthly_savings_budget в User модели, детально описан алгоритм shift-down для приоритетов, определено поведение PAUSED целей. Критичные проблемы из v1 устранены. Остаются важные замечания по drag-and-drop реализации и несколько незначительных улучшений.

---

## ✅ Сильные стороны

1. **Полное устранение критичных проблем из v1**
   - Добавлено поле `User.monthly_savings_budget` с описанием UI для редактирования
   - Детально описан алгоритм shift-down для update_priority() с двумя сценариями
   - Определено поведение PAUSED целей: не участвуют в allocation, сохраняют priority

2. **Качественная таблица соответствия замечаниям**
   - Раздел "Учтенные замечания из критики v1" с четким mapping проблема -> решение
   - Ответы на все вопросы критика документированы
   - Прослеживаемость между критикой и исправлениями

3. **Детальный data flow для GoalsSummary.monthly_budget**
   - Явная цепочка: User.monthly_savings_budget -> AllocationService -> GoalsSummary.monthly_budget -> UI
   - Диаграмма взаимодействия компонентов обновлена

4. **Формула агрегации для Dashboard**
   - Описана логика: `total_target = sum(all goals)`, `total_current = sum(all goals)`
   - Показано как отображать при > 1 цели: `savings_name = f"{len(active_goals)} целей"`

5. **Валидация в reorder_priorities()**
   - Проверка на дубликаты в списке goal_ids
   - Проверка что список содержит ВСЕ активные цели
   - PAUSED/COMPLETED цели явно исключены из reorder

6. **Продуманный TypedDicts для AllocationService**
   - AllocationResult содержит все нужные поля: shortfall, is_fully_funded, monthly_contribution_needed
   - AllocationSummary предоставляет агрегированную сводку с all_goals_funded flag

7. **Реалистичная оценка времени**
   - 14-16 часов с разбивкой на 6 фаз
   - Учитывает drag-and-drop сложность (5ч на UI рефакторинг)

---

## 🔴 Критичные проблемы (Blockers)

Нет критичных проблем. Все блокеры из v1 устранены.

---

## 🟡 Важные проблемы (Should Fix)

### 1. Выбор dash-draggable требует верификации

**Проблема:**
`dash-draggable` - не официальный Plotly компонент. Необходимо проверить совместимость с Dash 2.17.1, поддержку touch events, активность maintainer.

**Рекомендация:**
1. Добавить в план Фазу 0: "Verification spike (1ч)" с POC
2. Определить точный fallback: кнопки "Вверх"/"Вниз" или числовое поле приоритета
3. Если не подходит - использовать clientside callback с HTML5 Drag API

---

### 2. UserService создает circular dependency risk

**Проблема:**
UserService описан минимально (2 метода), scope размыт. Если в будущем потребует GoalService - circular import.

**Рекомендация:**
Уточнить scope: UserService только для settings (не full CRUD). Документировать в decisions.md.

---

### 3. Не описана миграция БД для monthly_savings_budget

**Проблема:**
`monthly_savings_budget` - НОВОЕ поле. SQLAlchemy с SQLite не выполняет auto-migrate.

**Рекомендация:**
Добавить в Фазу 1: `ALTER TABLE users ADD COLUMN monthly_savings_budget NUMERIC(10,2) DEFAULT 0`

---

## 🟢 Незначительные замечания (Optional)

### 4. Отсутствует UI-индикатор для "бюджет не настроен"
При `monthly_savings_budget = 0` показать подсказку настроить бюджет.

### 5. TypedDicts можно централизовать
Рассмотреть `app/types/goals.py` для переиспользования.

### 6. Нет fallback для `Goal.monthly_contribution = 0`
Добавить `skipped_reason` в AllocationResult для прозрачности.

### 7. Test count в плане превышает требования brief
16 тестов vs требуемых 10 - это хорошо, но стоит уточнить покрытие allocation logic.

---

## 🔄 Изменения с предыдущей итерации

| Проблема из v1 | Статус | Комментарий |
|---------------|--------|-------------|
| 🔴 #1 Отсутствует хранение monthly_savings_budget | ✅ Исправлено | Добавлено поле User.monthly_savings_budget |
| 🔴 #2 Не определена логика сдвига приоритетов | ✅ Исправлено | Алгоритм shift-down с примерами |
| 🟡 #3 GoalsSummary.monthly_budget не связан | ✅ Исправлено | Data flow описан |
| 🟡 #4 Dashboard интеграция неполна | ✅ Исправлено | Формула агрегации |
| 🟡 #5 reorder_priorities() консистентность | ✅ Исправлено | Валидация добавлена |
| 🟡 #6 Нет UI для приоритета при создании | ✅ Исправлено | auto-assign max+1 |

**Прогресс:** v1: ⭐⭐⭐ (3/5) → v2: ⭐⭐⭐⭐ (4/5) (+1 звезда)

---

## 📋 Рекомендации для следующей итерации

### Обязательно:
Нет обязательных изменений - решение готово к реализации.

### Желательно:
1. Добавить verification spike для dash-draggable (1ч)
2. Описать миграцию БД (ALTER TABLE script)
3. Уточнить scope UserService в decisions.md

### Опционально:
4. UI-индикатор "бюджет не настроен"
5. Централизация TypedDicts
6. `skipped_reason` в AllocationResult
