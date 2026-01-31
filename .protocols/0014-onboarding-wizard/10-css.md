# Шаг 10: CSS Styles

## Briefing

- **Цель:** Создать стили для onboarding wizard и balance toast
- **Ключевые файлы:**
  - `app/assets/onboarding.css` — NEW
- **Доп. информация:** Следовать существующим паттернам проекта (green/white palette)

## Sub-tasks

1. **Создать CSS файл** (`app/assets/onboarding.css`):
   ```css
   /* ==============================================
      Onboarding Wizard Styles
      ============================================== */

   .onboarding-modal .modal-content {
       border-radius: 12px;
       border: none;
       box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
   }

   .onboarding-modal .modal-header {
       background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
       color: white;
       border-radius: 12px 12px 0 0;
       border-bottom: none;
   }

   .onboarding-modal .modal-title {
       font-weight: 600;
       font-size: 1.25rem;
   }

   .onboarding-modal .modal-body {
       padding: 1.5rem;
   }

   .onboarding-balance-input {
       font-size: 1.25rem;
       text-align: right;
       padding: 0.75rem 1rem;
   }

   .onboarding-balance-input:focus {
       border-color: #28a745;
       box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25);
   }

   .onboarding-warning {
       font-size: 0.875rem;
       margin-top: 0.25rem;
   }

   .onboarding-modal .modal-footer {
       border-top: 1px solid #e9ecef;
       padding: 1rem 1.5rem;
   }

   /* ==============================================
      Balance Alert Toast Styles
      ============================================== */

   .balance-toast {
       z-index: 1050;
   }

   .balance-toast .toast-header {
       background-color: #fff3cd;
       color: #856404;
       font-weight: 600;
   }

   .balance-toast .toast-body {
       background-color: #fffcf5;
   }

   /* ==============================================
      Responsive Adjustments
      ============================================== */

   @media (max-width: 576px) {
       .onboarding-modal .modal-dialog {
           margin: 0.5rem;
       }

       .onboarding-balance-input {
           font-size: 1rem;
       }

       .balance-toast {
           width: calc(100% - 40px) !important;
           right: 20px !important;
           left: 20px !important;
       }
   }
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Визуальная проверка (опционально): запустить приложение и проверить стили
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 11, Next Action: Шаг 11
5. Коммит: `git add . && git commit -m "style(onboarding): add CSS styles [protocol-0014/10]"`
6. Push
7. Отчёт по формату
