# Шаг 4: Onboarding UI

## Briefing

- **Цель:** Перестроить onboarding wizard — единый экран с именем, аватаркой (RadioItems) и балансом
- **Ключевые файлы:**
  - `app/components/onboarding_wizard.py` — EDIT: полная перестройка layout + callbacks
  - `app/assets/onboarding.css` — EDIT: +avatar grid стили, +profile modal стили
- **Доп. информация:** См. solution-v3.md секции "4. Onboarding Wizard" и "CSS стили". Два callback'а: (1) check+validate с ctx.triggered_id оптимизацией, (2) handle action (submit/skip).

## Sub-tasks

1. Перестроить `create_onboarding_wizard()`:
   - Заголовок: "Добро пожаловать в FinFocus!"
   - Имя: dbc.Input с placeholder="Как вас зовут?", maxLength=50
   - Аватарка: dbc.RadioItems с 10 emoji, inputClassName="avatar-radio-hidden", labelClassName="avatar-option", labelCheckedClassName="avatar-option-selected"
   - Баланс: dbc.InputGroup с ₽, warning для отрицательного
   - Кнопки: "Пропустить" (secondary) + "Продолжить" (success, disabled=True)

2. Callback 1 — check_onboarding_and_validate:
   - Inputs: url.pathname, onboarding-name-input.value, onboarding-balance-input.value
   - Outputs: onboarding-modal.is_open, onboarding-submit-btn.disabled, onboarding-balance-warning.style
   - Логика по ctx.triggered_id:
     - "url"/None → check first_launch from DB (ONLY DB call)
     - "onboarding-name-input" → validate name, disabled = not has_name (NO DB call)
     - "onboarding-balance-input" → warning for negative (NO DB call)

3. Callback 2 — handle_onboarding_action:
   - Inputs: submit.n_clicks, skip.n_clicks
   - States: name.value, avatar.value, balance.value
   - Outputs: onboarding-modal.is_open (allow_duplicate=True), profile-updated.data
   - submit → complete(name, avatar, balance) + session.commit() + timestamp
   - skip → skip() + session.commit() + timestamp

4. Добавить CSS в `app/assets/onboarding.css`:
   - `.avatar-grid` — flex wrap, gap 10px
   - `.avatar-radio-hidden` — display: none
   - `.avatar-option` — 56x56px, border-radius 50%, font-size 1.8rem
   - `.avatar-option:hover` — border-color primary, scale 1.05
   - `.avatar-option-selected` — border primary, glow, scale 1.1
   - `.profile-modal .modal-content` — border-radius 12px, box-shadow

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/components/onboarding_wizard.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 5, Next Action: Шаг 5
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(profile): rebuild onboarding wizard with name, avatar, balance [protocol-0024-user-profile/04]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
