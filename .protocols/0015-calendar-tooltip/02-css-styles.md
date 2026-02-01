# Шаг 2: CSS Styles

## Briefing

- **Цель:** Добавить glassmorphism стили tooltip с CSS checkbox hack
- **Ключевые файлы:**
  - `app/assets/calendar.css` — добавить ~200 строк
- **Доп. информация:** Полный CSS в solution-v3.md секция "CSS Glassmorphism Implementation"

## Sub-tasks

1. **Добавить CSS переменные** в `:root`:
   ```css
   --tooltip-hide-delay: 150ms;
   ```

2. **Добавить стили .calendar-day-content**:
   - Wrapper для кликабельной области
   - width/height 100%, flex column, cursor pointer

3. **Добавить стили .calendar-day-tooltip**:
   - Glassmorphism: `backdrop-filter: blur(12px)`, `rgba(255, 255, 255, 0.88)`
   - Positioning: absolute, z-index 1000, top 100%
   - Animation: opacity/transform transitions с delay

4. **Добавить hover trigger**:
   ```css
   .calendar-day:hover .calendar-day-tooltip { display: block; opacity: 1; }
   ```

5. **Добавить edge detection** для правых колонок:
   ```css
   .calendar-day:nth-child(7n-1) .calendar-day-tooltip,
   .calendar-day:nth-child(7n) .calendar-day-tooltip { left: auto; right: 0; }
   ```

6. **Добавить fallback** для backdrop-filter:
   ```css
   @supports not (backdrop-filter: blur(12px)) { ... }
   ```

7. **Добавить стили содержимого tooltip**:
   - `.tooltip-balance` — header с балансом
   - `.tooltip-txn-row` — строка операции
   - `.tooltip-txn-row.skipped` — opacity 0.5, line-through
   - `.tooltip-txn-icon`, `.tooltip-txn-desc`, `.tooltip-txn-amount`

8. **Добавить CSS checkbox hack**:
   - `.tooltip-expand-checkbox` — hidden checkbox
   - `.tooltip-expand-btn` — label кнопка
   - `.tooltip-hidden-txns` — скрытый контейнер
   - `:checked ~ .tooltip-hidden-txns { display: block; }`

9. **Добавить mobile media query**:
   ```css
   @media (max-width: 768px) { .calendar-day-tooltip { display: none !important; } }
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Визуальная проверка в браузере (пока без UI — только CSS)
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 3
5. Коммит: `git add . && git commit -m "style(calendar): add glassmorphism tooltip CSS [protocol-0015/02]"`
6. Push
7. Отчёт
