# Brief: Edit/Delete Contribution Management with Cascade Sync

## Цель
Реализовать полноценное управление взносами в накопительные цели: редактирование (сумма, дата, описание) и удаление с корректной синхронизацией всех связанных сущностей (Transaction, GoalContribution, Goal.current_amount) и автоматическим пересчетом Exception резерва для режима fixed_date.

## Функциональные требования
- FR-1: Редактирование суммы взноса с каскадным обновлением Goal.current_amount и Transaction.amount (если есть)
- FR-2: Редактирование даты взноса с обновлением Transaction.transaction_date и пересчетом Exception для старого и нового месяца (fixed_date режим)
- FR-3: Редактирование описания взноса с обновлением Transaction.description (если есть)
- FR-4: Удаление взноса с откатом Goal.current_amount и корректным статусом COMPLETED → ACTIVE
- FR-5: Блокировка редактирования SAVINGS_CONTRIBUTION через calendar tooltip (redirect to Goals UI)
- FR-6: UI кнопки Edit/Delete в таблице истории взносов на /goals
- FR-7: Модал редактирования взноса с предзаполнением текущих значений
- FR-8: Toast уведомления при удалении и откате статуса цели

## Нефункциональные требования
- NFR-1: Атомарность операций - все изменения в рамках одной транзакции БД
- NFR-2: Производительность - операции < 100ms (одна сессия, один commit)
- NFR-3: Логирование всех изменений через loguru (audit trail)

## Ограничения
- Работа только с user_id = 1 (MVP ограничение)
- Не реализуем batch-операции (удаление нескольких взносов)
- Редактирование SAVINGS_CONTRIBUTION только через Goals UI, не через Calendar tooltip

## Критерии приёмки
- [ ] GoalService.update_contribution() корректно обновляет amount, date, description
- [ ] При уменьшении суммы взнос COMPLETED цель → ACTIVE с toast уведомлением
- [ ] При увеличении суммы до target_amount цель → COMPLETED
- [ ] При смене даты между месяцами (fixed_date) оба месяца пересчитаны (Exception)
- [ ] delete_contribution() откатывает статус для всех взносов (не только с transaction_id)
- [ ] Клик на SAVINGS_CONTRIBUTION в calendar tooltip заблокирован
- [ ] UI: кнопки Edit/Delete в таблице взносов работают корректно
- [ ] Unit тесты покрывают все edge cases

## Вне scope (out of scope)
- Batch удаление взносов
- Undo/Redo операций
- История изменений взносов (audit log UI)
- Редактирование через Calendar tooltip (только блокировка)
