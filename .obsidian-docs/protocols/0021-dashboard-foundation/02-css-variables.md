# Шаг 2: CSS-переменные + типографика

## Briefing

- **Цель:** Обновить CSS-переменные с новой палитрой #2ecc71, добавить типографические классы, заменить hardcoded цвета
- **Ключевые файлы:**
  - `app/assets/custom.css` — 7 замен + 15 новых переменных + 9 типографических классов
  - `app/assets/calendar.css` — 6 замен hardcoded цветов
  - `app/assets/transactions.css` — 2 замены
  - `app/assets/onboarding.css` — 3 замены
- **Доп. информация:** См. `.design/solution-v2.md` секция "CSS-переменные -- ПОЛНАЯ LINE-BY-LINE КАРТА"

## Sub-tasks

1. В `custom.css` :root:
   - Добавить 15 новых CSS-переменных:
     - `--color-primary: #2ecc71`
     - `--color-primary-dark: #27ae60`
     - `--color-secondary: #3498db`
     - `--color-danger: #e74c3c`
     - `--color-warning: #f39c12`
     - `--color-text-primary: #2c3e50`
     - `--color-text-secondary: #7f8c8d`
     - `--color-text-muted: #95a5a6`
     - `--color-bg-card: #ffffff`
     - `--color-bg-page: #f8f9fa`
     - `--color-border: #bdc3c7`
     - `--color-border-light: #ecf0f1`
     - `--color-success: #2ecc71`
     - `--color-info: #3498db`
     - `--color-separator: #dfe6e9`
   - Deprecated aliases: `--primary-green: var(--color-primary)`, `--light-green: var(--color-primary-dark)`
   - 7 замен hardcoded цветов по карте из solution-v2.md

2. В `custom.css` — добавить 9 типографических классов:
   - `.kpi-number` (40px, 600 weight, --color-text-primary)
   - `.kpi-title` (16px, 500 weight, --color-text-secondary)
   - `.kpi-subtitle` (12px, 400, --color-text-muted)
   - `.table-amount` (14px, 600, --color-text-primary)
   - `.table-amount.positive` (--color-success)
   - `.table-amount.negative` (--color-danger)
   - `.table-description` (13px, 400, --color-text-secondary)
   - `.link-show-all` (13px, 500, --color-secondary)
   - `.kpi-card` (белый фон, border, radius 10px, padding 20px)

3. В `calendar.css`: 6 замен по карте
4. В `transactions.css`: 2 замены по карте
5. В `onboarding.css`: 3 замены по карте

## Workflow

1. Выполни Sub-tasks последовательно
2. Обнови `log.md` — что сделано, неочевидные решения
3. Обнови `context.md` — Current Step + 1, Next Action
4. Коммит: `git add . && git commit -m "style(css): update color palette to #2ecc71 and add typography classes [protocol-0021/02]"`
5. Push
6. Отчёт по формату из `report-format.md.tpl`
