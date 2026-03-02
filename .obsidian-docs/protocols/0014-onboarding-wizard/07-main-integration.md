# Шаг 7: main.py Integration

## Briefing

- **Цель:** Интегрировать wizard в глобальный layout и добавить stores
- **Ключевые файлы:**
  - `app/main.py` — добавить wizard в layout
  - `app/components/__init__.py` — экспорт
- **Доп. информация:** Wizard должен быть в корневом layout для работы на всех страницах

## Sub-tasks

1. **Экспортировать wizard** (`app/components/__init__.py`):
   ```python
   from app.components.onboarding_wizard import create_onboarding_wizard
   ```

2. **Интегрировать в main.py**:
   ```python
   # В imports добавить:
   from app.components import create_onboarding_wizard

   # В app.layout добавить после page-content:
   app.layout = html.Div([
       dcc.Location(id="url", refresh=False),
       create_sidebar(),
       html.Div(id="page-content", className="content"),
       create_transaction_modals(),
       create_onboarding_wizard(),  # NEW
       # Глобальный store для toast dismissal (до перезагрузки)
       dcc.Store(id="balance-toast-dismissed", data=False),
   ])
   ```

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/main.py`
3. Обнови `log.md` — что сделано
4. Обнови `context.md` — Current Step: 8, Next Action: Шаг 8
5. Коммит: `git add . && git commit -m "feat(main): integrate onboarding wizard [protocol-0014/07]"`
6. Push
7. Отчёт по формату
