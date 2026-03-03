# Шаг 3: Service Layer

## Briefing

- **Цель:** Расширить OnboardingService: complete(), update_profile(), get_profile(), _validate_profile_fields()
- **Ключевые файлы:**
  - `app/services/onboarding_service.py` — EDIT: новые/модифицированные методы
  - `app/schema/__init__.py` — EDIT: re-export UserProfile
- **Доп. информация:** См. solution-v3.md секция "3. Сервисный слой". DRY-валидация через приватный метод. Module-level imports AVATARS/DEFAULT_AVATAR_ID. Deprecated wrapper complete_with_balance().

## Sub-tasks

1. Добавить module-level import в `onboarding_service.py`:
   ```python
   from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID
   from app.schema.onboarding import OnboardingStatus, UserProfile
   ```

2. Добавить приватный метод `_validate_profile_fields(self, name, avatar_id) -> tuple[str, str]`:
   - strip + length check (1-50 символов), ValueError при нарушении
   - Whitelist avatar_id check, fallback на DEFAULT_AVATAR_ID
   - Docstring с Note о намеренном расхождении String(100) vs валидация 50

3. Модифицировать `complete()` — новая сигнатура:
   ```python
   def complete(self, user_id, name, avatar_id, starting_balance) -> None
   ```
   - Использует _validate_profile_fields()
   - Устанавливает name, avatar_id, starting_balance, first_launch=False
   - flush() без commit()

4. Добавить deprecated wrapper `complete_with_balance()`:
   - Вызывает complete() с defaults (name="Пользователь", avatar_id=DEFAULT_AVATAR_ID)

5. Добавить `update_profile(self, user_id, name, avatar_id) -> None`:
   - Использует _validate_profile_fields()
   - Обновляет name и avatar_id
   - flush() без commit()

6. Добавить `get_profile(self, user_id) -> UserProfile`:
   - Возвращает UserProfile(name=user.name, avatar_id=user.avatar_id)

7. Обновить `get_status()` — добавить name и avatar_id в возвращаемый OnboardingStatus

8. Обновить `app/schema/__init__.py` — re-export UserProfile

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/onboarding_service.py app/schema/__init__.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 4, Next Action: Шаг 4
5. Проверь `main` на случайные файлы
6. Коммит: `git add . && git commit -m "feat(profile): extend OnboardingService with profile methods [protocol-0024-user-profile/03]"`
7. Push
8. Отчёт по формату из `report-format.md.tpl`
