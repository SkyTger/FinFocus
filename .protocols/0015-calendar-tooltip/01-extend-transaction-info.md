# Шаг 1: Extend TransactionInfo

## Briefing

- **Цель:** Добавить поля `is_skipped: bool` и `category_icon: str | None` в TransactionInfo и VirtualTransaction
- **Ключевые файлы:**
  - `app/services/calendar_service.py` — TransactionInfo TypedDict
  - `app/services/recurring_service.py` — VirtualTransaction dict
- **Доп. информация:** Поля нужны для визуализации пропущенных операций и emoji категорий в tooltip

## Sub-tasks

1. **Обновить TransactionInfo TypedDict** в `calendar_service.py`:
   ```python
   category_icon: str | None  # Bootstrap icon class (bi-cart, etc.)
   is_skipped: bool           # True для пропущенных recurring
   ```

2. **Обновить заполнение TransactionInfo** в `get_transactions_by_date()`:
   - Добавить `"category_icon": txn.category_rel.icon if txn.category_rel else None`
   - Добавить `"is_skipped": getattr(txn, 'is_skipped', False)`

3. **Обновить заполнение TransactionInfo** в `get_all_transactions_for_period()`:
   - Для regular transactions: добавить category_icon, is_skipped
   - Для exceptions: добавить category_icon, is_skipped

4. **Обновить VirtualTransaction** в `recurring_service.py`:
   - Добавить `"category_icon": template.category_rel.icon if template.category_rel else None`
   - is_skipped для virtual приходит из existing exceptions (уже есть)

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/services/calendar_service.py app/services/recurring_service.py`
3. Обнови `log.md` — что сделано, неочевидные решения
4. Обнови `context.md` — Current Step: 2, Next Action: CSS Styles
5. Коммит: `git add . && git commit -m "feat(calendar): extend TransactionInfo with category_icon and is_skipped [protocol-0015/01]"`
6. Push
7. Отчёт по формату
