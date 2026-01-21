# Шаг 1: TypedDicts и Serializers

## Briefing
- **Цель:** Добавить TypedDicts для перераспределения (RedistributionPreview, RedistributionEvent) и функции сериализации для передачи данных через dcc.Store.
- **Ключевые файлы:**
  - `app/schema/goals.py` (модифицировать — добавить TypedDicts)
  - `app/schema/__init__.py` (модифицировать — экспорт)
  - `app/utils/serializers.py` (создать — функции сериализации)
  - `app/utils/__init__.py` (модифицировать — экспорт)
  - `tests/test_serializers.py` (создать — unit тесты)
- **Additional info:**
  - RedistributionPreview содержит calculation_time_ms для NFR-2 verification
  - RedistributionEvent используется для аудит-логирования (NFR-4)
  - Сериализация нужна для Decimal → str конвертации (JSON не поддерживает Decimal)

## Sub-tasks

1. **Добавить TypedDicts в `app/schema/goals.py`:**
   ```python
   class RedistributionPreview(TypedDict):
       """Preview данные для модала перераспределения."""
       completed_goal_id: int
       completed_goal_name: str
       freed_budget: Decimal
       was_skipped_in_old_allocation: bool
       has_remaining_goals: bool
       remaining_goals_count: int
       new_allocation: AllocationSummary | None
       old_allocation: AllocationSummary | None
       calculation_time_ms: float

   class RedistributionEvent(TypedDict):
       """Структура события перераспределения для аудита (NFR-4)."""
       timestamp: str
       user_id: int
       completed_goal_id: int
       completed_goal_name: str
       freed_budget: str  # str для JSON
       remaining_goals_count: int
       action: str  # "confirmed" | "declined"
       new_allocation_summary: dict | None
   ```

2. **Обновить `app/schema/__init__.py`:**
   - Добавить экспорт RedistributionPreview, RedistributionEvent

3. **Создать `app/utils/serializers.py`:**
   ```python
   def serialize_redistribution_preview(preview: RedistributionPreview) -> dict:
       """Сериализует RedistributionPreview для dcc.Store."""
       # Конвертация Decimal → str
       # Рекурсивная обработка AllocationSummary
       pass

   def deserialize_redistribution_preview(data: dict | None) -> RedistributionPreview | None:
       """Десериализует данные из dcc.Store обратно в RedistributionPreview."""
       # Конвертация str → Decimal
       # Восстановление типов
       pass
   ```

4. **Обновить `app/utils/__init__.py`:**
   - Добавить экспорт serialize_redistribution_preview, deserialize_redistribution_preview

5. **Создать `tests/test_serializers.py` с тестами:**
   - `test_serialize_redistribution_preview_basic` — базовая сериализация
   - `test_serialize_redistribution_preview_with_allocation` — с AllocationSummary
   - `test_deserialize_redistribution_preview_basic` — базовая десериализация
   - `test_deserialize_redistribution_preview_none` — None input
   - `test_roundtrip_serialization` — serialize → deserialize → compare

## Workflow (Порядок работы)

1. **Выполнение:** Последовательно выполняй подзадачи.

2. **Базовая проверка:** Убедись что код синтаксически корректен:
   ```bash
   python -m py_compile app/schema/goals.py
   python -m py_compile app/utils/serializers.py
   python -m py_compile tests/test_serializers.py
   ```

3. **Фиксация:** После успешной базовой проверки:
   - **Добавь запись в `log.md`**: Опиши добавленные TypedDicts и функции сериализации.
   - **Обнови `context.md`**: Увеличь `Current Step` на 1 и подготовь `Next Action` для Шага 2.
   - Проверь ветку main в поисках случайно добавленных файлов из нашей ветки.

4. **Сделай коммит:**
   ```bash
   git add . && git commit -m "feat(schema): add redistribution TypedDicts and serializers [protocol-0008/01]"
   ```
   Сделай пуш.

5. **Отчет пользователю:** Сообщи о завершении шага в установленном формате.
