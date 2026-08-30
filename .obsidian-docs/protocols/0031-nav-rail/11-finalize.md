# Шаг 11: Финализация

## Briefing

- **Цель:** Полная верификация, живой чек-лист приёмки, перевод PR в Ready
- **Ключевые файлы:** все изменённые в рамках протокола

## Sub-tasks

1. **Полная верификация:**
   ```bash
   .venv/bin/python -m black app/ tests/
   .venv/bin/python -m flake8 app/
   .venv/bin/python -m pytest
   ```
   `black` — **только из `.venv`** (системный 26.x форматирует иначе). Известные pre-existing E501 (goals.py:3085, dashboard_service.py:375/420, transaction_service.py:54) — новых быть не должно.

2. **Живой чек-лист приёмки** (полный — в solution-v3, «Проверить после реализации»; ключевое):
   - AC-1 на каждом из четырёх разделов: полоска 60px, широкой карточки нет
   - AC-2: на `/dashboard` слева пусто, `.nav-rail-column` имеет `display: none`
   - AC-3: язычок на каждом из четырёх слотов, не обрезан, поверх содержимого
   - AC-4: подсветка переезжает при переходе
   - AC-5: оба сценария (пройдено на шаге 8, подтвердить)
   - AC-6: `prefers-reduced-motion` — сразу целиком
   - **AC-7 на КАЖДОМ из четырёх разделов отдельно**: `/calendar`, `/transactions`, `/analytics`, `/goals` → аватар → модал открылся
   - AC-7 дополнительно: шестерёнка на дашборде по-прежнему открывает профиль
   - Язычок «Профиль» на аватаре
   - AC-8: логотип ведёт на дашборд
   - AC-9: версия в модале совпадает с `git describe --tags --abbrev=0`
   - **AC-10, все четыре параметра**: `?focus_date=`, `?goal=`, `?wishlist_item=`, `?open_recon=1`
   - Клавиатура: Tab обходит логотип → 4 слота → аватар, фокус видим
   - Высота окна 600px и 1400px: аватар прижат к низу
   - Fallback без `backdrop-filter`: подложка читаема
   - **Сборка PyInstaller** (`pyinstaller finfocus.spec --noconfirm`) проходит, версия в модале во frozen-запуске верна — единственная проверка, которую рассуждением заменить нельзя
   - F5 на разделе: разворот играет (корректно, R10), подсветка не ломается

3. Коммит правок (если были): `chore: final QA fixes [protocol-0031/11]`

4. `gh pr ready`

5. Обновить `context.md`: Status `Completed`, Next Action `Ожидается /protocol-review-merge`

6. Финальный коммит: `docs(protocol): finalize 0031-nav-rail [protocol-0031/11]` + push

## Отчёт

```
(Протокол 0031-nav-rail — Финализация):

**Верификация**: black/flake8/pytest — результаты
**Живая приёмка**: AC-1..AC-11 + PyInstaller
**Git**: PR URL (Ready), ветка, коммиты
**CWD**: /home/skytiger/Projects/worktrees/0031-nav-rail
**Статус**: Completed. Ожидается /protocol-review-merge
```
