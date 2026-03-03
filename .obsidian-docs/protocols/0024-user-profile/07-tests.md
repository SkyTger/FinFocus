# Шаг 7: Tests

## Briefing

- **Цель:** Unit тесты для конфига аватарок, OnboardingService расширения, миграции 007
- **Ключевые файлы:**
  - `tests/test_avatars.py` — CREATE: тесты конфига аватарок
  - `tests/test_onboarding_service.py` — EDIT: +тесты complete(), update_profile(), get_profile(), _validate_profile_fields()
  - `tests/test_migration_007.py` — CREATE: тест миграции avatar_id
- **Доп. информация:** Exclude pre-existing failure: `pytest -k "not test_budget_change_updates_allocation"`

## Sub-tasks

1. Создать `tests/test_avatars.py`:
   - test_avatars_has_10_entries
   - test_default_avatar_id_exists
   - test_get_avatar_emoji_valid
   - test_get_avatar_emoji_invalid_fallback
   - test_avatars_structure (каждый имеет emoji и label)

2. Расширить `tests/test_onboarding_service.py`:
   - test_complete_with_name_and_avatar — полный onboarding
   - test_complete_sets_first_launch_false
   - test_complete_with_balance — creates correct starting_balance
   - test_complete_invalid_name_empty — ValueError
   - test_complete_invalid_name_too_long — ValueError
   - test_complete_invalid_avatar_fallback — fallback на default
   - test_update_profile — обновляет name и avatar_id
   - test_update_profile_user_not_found — ValueError
   - test_get_profile — возвращает UserProfile dict
   - test_validate_profile_fields_strips_whitespace
   - test_complete_with_balance_deprecated_wrapper — backward compat
   - test_get_status_includes_name_and_avatar

3. Создать `tests/test_migration_007.py`:
   - test_migration_007_adds_avatar_id_column
   - test_migration_007_idempotent — повторный запуск безопасен
   - test_migration_007_default_value — default "emoji-default"

4. Запустить тесты: `pytest -k "not test_budget_change_updates_allocation" -v`

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `pytest -k "not test_budget_change_updates_allocation" -v`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 8, Next Action: Шаг 8 (Финализация)
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "test(profile): add tests for avatars, onboarding service, migration 007 [protocol-0024-user-profile/07]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
