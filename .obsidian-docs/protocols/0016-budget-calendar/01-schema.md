# Шаг 1: Database Schema

## Briefing

- **Цель:** Расширить модели данных для поддержки режимов резервирования
- **Ключевые файлы:**
  - `app/models/database.py` — TransactionType, User, GoalContribution
  - `scripts/migrate_004_reservation.py` — idempotent migration
- **Доп. информация:** См. solution-v2.md секция "Модель данных"

## Sub-tasks

1. **TransactionType enum** — добавить два значения:
   ```python
   SAVINGS_RESERVE = "savings_reserve"        # Резерв на цели (recurring)
   SAVINGS_CONTRIBUTION = "savings_contribution"  # Взнос в цель
   ```

2. **User модель** — добавить поля:
   ```python
   reservation_mode = Column(String(20), default="from_balance", nullable=False)
   reservation_day = Column(Integer, nullable=True)  # 1-31 для fixed_date
   ```

3. **GoalContribution модель** — добавить FK и Index:
   ```python
   transaction_id = Column(
       Integer,
       ForeignKey("transactions.id", ondelete="SET NULL"),
       nullable=True
   )
   __table_args__ = (Index("ix_contribution_date", "contribution_date"),)
   transaction = relationship("Transaction")
   ```

4. **Migration script** `scripts/migrate_004_reservation.py`:
   - Idempotent: проверить PRAGMA table_info перед ALTER
   - Добавить User.reservation_mode, User.reservation_day
   - Добавить GoalContribution.transaction_id
   - Создать Index ix_contribution_date

5. **Unit тесты** — добавить в `tests/test_models.py`:
   - Тест TransactionType.SAVINGS_RESERVE, SAVINGS_CONTRIBUTION
   - Тест User.reservation_mode default
   - Тест GoalContribution.transaction_id nullable

## Workflow

1. Выполни Sub-tasks последовательно
2. Базовая проверка: `python -m py_compile app/models/database.py`
3. Запустить миграцию: `python scripts/migrate_004_reservation.py`
4. Тесты: `pytest tests/test_models.py -v`
5. Обнови `log.md` — что сделано
6. Обнови `context.md` — Current Step: 2
7. Коммит: `git add . && git commit -m "feat(models): add reservation mode and contribution FK [protocol-0016/01]"`
8. Push
