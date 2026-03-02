# Шаг 6: CSS стили

## Briefing

- **Цель:** Добавить стили для Quick-add chips с responsive поведением
- **Ключевые файлы:**
  - `app/assets/transactions.css`
- **Доп. информация:** Prefix `.qa-*` для изоляции от других стилей

## Sub-tasks

1. Добавить стили для секции (~80 строк):
   ```css
   /* Quick-add section */
   .qa-chip-section {
       margin-bottom: 1.5rem;
       padding: 1rem;
       background: var(--bs-light);
       border-radius: 0.5rem;
   }

   .qa-chip-section-title {
       font-weight: 600;
       margin-bottom: 0.75rem;
       color: var(--bs-secondary);
   }

   .qa-chip-group {
       display: flex;
       flex-wrap: wrap;
       gap: 0.75rem;
       margin-bottom: 1rem;
   }

   .qa-chip-group-title {
       width: 100%;
       font-size: 0.875rem;
       color: var(--bs-gray-600);
       margin-bottom: 0.5rem;
   }
   ```

2. Добавить стили для chip:
   ```css
   .qa-chip {
       width: 100px;
       height: 80px;
       display: flex;
       flex-direction: column;
       align-items: center;
       justify-content: center;
       gap: 0.5rem;
       border-radius: 0.5rem;
       transition: transform 0.15s, box-shadow 0.15s;
   }

   .qa-chip:hover {
       transform: translateY(-2px);
       box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
   }

   .qa-chip-label {
       font-size: 0.75rem;
       text-align: center;
       line-height: 1.2;
   }

   .qa-more-btn {
       width: 80px;
       height: 80px;
   }
   ```

3. Добавить стили для модала "Ещё...":
   ```css
   .qa-more-grid {
       display: grid;
       grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
       gap: 0.75rem;
       padding: 0.5rem 0;
   }

   .qa-more-category-btn {
       padding: 0.5rem 1rem;
       text-align: left;
   }
   ```

4. Добавить responsive стили:
   ```css
   @media (max-width: 768px) {
       .qa-chip-group {
           flex-wrap: nowrap;
           overflow-x: auto;
           padding-bottom: 0.5rem;
       }

       .qa-chip {
           flex-shrink: 0;
       }
   }
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Визуальная проверка: запустить приложение, проверить /transactions
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 7, Next Action: Шаг 7
5. Коммит: `git add . && git commit -m "style(quick-add): add CSS for chips and modal [protocol-0012/06]"`
6. Push
7. Отчёт
