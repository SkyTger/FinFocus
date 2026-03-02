# Шаг 7: CSS

## Briefing

- **Цель:** Добавить CSS стили для карточки и модала подушки
- **Ключевые файлы:**
  - `app/assets/goals.css` — MODIFY
- **Доп. информация:** Prefix `.cushion-*`, прогресс-бар с маркером порога

## Sub-tasks

1. **Добавить стили в `app/assets/goals.css`:**
   ```css
   /* ===== Cushion Card ===== */
   .cushion-card {
       margin-bottom: 1.5rem;
       border-left: 4px solid var(--bs-success);
   }

   .cushion-not-configured {
       border-left-color: var(--bs-secondary);
       background-color: #f8f9fa;
   }

   .cushion-title {
       color: var(--bs-success);
       font-weight: 600;
   }

   /* Progress bar with threshold marker */
   .cushion-progress-container {
       position: relative;
       height: 24px;
       background-color: #e9ecef;
       border-radius: 4px;
       overflow: visible;
   }

   .cushion-progress-bar {
       height: 100%;
       background-color: var(--bs-success);
       border-radius: 4px 0 0 4px;
       transition: width 0.3s ease;
   }

   .cushion-progress-bar.danger {
       background-color: var(--bs-danger);
   }

   .cushion-progress-bar.warning {
       background-color: var(--bs-warning);
   }

   .cushion-threshold-marker {
       position: absolute;
       top: -6px;
       bottom: -6px;
       width: 3px;
       background-color: var(--bs-dark);
       border-radius: 2px;
   }

   .cushion-threshold-label {
       position: absolute;
       top: -22px;
       font-size: 0.75rem;
       color: var(--bs-secondary);
       transform: translateX(-50%);
   }

   /* ===== Cushion Modal ===== */
   .cushion-modal .modal-body {
       padding: 1.5rem;
   }

   .cushion-scenario-item {
       display: flex;
       gap: 0.5rem;
       margin-bottom: 0.5rem;
       padding: 0.5rem;
       background-color: #f8f9fa;
       border-radius: 4px;
   }

   .cushion-recommendation {
       padding: 1rem;
       background-color: #e8f5e9;
       border-radius: 4px;
       margin-top: 1rem;
   }
   ```

## Workflow

1. Добавь стили в goals.css
2. Проверь визуально (запусти приложение если нужно)
3. Обнови `log.md`
4. Обнови `context.md` — Current Step: 8
5. Коммит: `git add . && git commit -m "style(cushion): add CSS styles for cushion card and modal [protocol-0013/07]"`
6. Push
7. Отчёт
