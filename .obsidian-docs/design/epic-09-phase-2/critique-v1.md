# Critique - Solution v1
Date: 2026-03-03
Reviewer: AI Critic (Claude)

---

## Общая оценка

**Рейтинг:** ⭐⭐⭐ (3/5)

**Вердикт:**
- [ ] Отлично, можно кодировать как есть
- [ ] Хорошо, с минорными улучшениями
- [x] Требуются значительные изменения
- [ ] Не рекомендуется, нужен другой подход

**Краткая суммаризация:**
Решение покрывает все requirements из brief и имеет хороший общий дизайн (Store-based обновление, RTM, blast radius). Однако есть одна критическая проблема с dashboard greeting callback (ReferenceError для динамического элемента) и несколько важных проблем с механизмом выбора аватарки, рефакторингом onboarding callbacks и архитектурой profile modal callbacks, которые требуют уточнения перед кодированием.

---

## Сильные стороны

1. **Store-based механизм обновления ("profile-updated")**
2. **Полная RTM (Requirements Traceability Matrix)**
3. **Грамотная стратегия обработки ошибок**
4. **Идемпотентная миграция 007**
5. **Blast radius анализ**
6. **Batching plan (7 батчей)**

---

## Критичные проблемы (Blockers)

### 1. Dashboard greeting callback: ReferenceError для динамического элемента

Решение предлагает server-side callback с Output("dashboard-greeting"). Элемент НЕ существует в глобальном layout -- появляется только при рендере dashboard. suppress_callback_exceptions=True не помогает (client-side ReferenceError).

**Рекомендация:** Вариант A (inline read в create_dashboard_layout()) или Вариант B (clientside_callback с prevent_initial_call=True).

---

## Важные проблемы (Should Fix)

### 2. Avatar selection: механизм не описан
НЕ описан callback механизм выбора аватарки. Рекомендация: dbc.RadioItems со скрытыми radio + custom CSS.

### 3. Onboarding callback flow: не описан после рефакторинга
Новая форма добавляет name input и avatar selector — validation логика меняется. Нужен явный callback flow.

### 4. Sidebar profile container: id и структура не определены
Текущий sidebar НЕ имеет id="sidebar-profile-container". Нужно определить layout и механизм клика.

### 5. Profile modal: два callback'а на один Output
Оба callback'а outputят в profile-modal.is_open. Нужно объединить или allow_duplicate=True.

---

## Незначительные замечания (Optional)

### 6. TypedDict для get_profile() return type
### 7. Поведение skip() относительно defaults
### 8. Breaking change complete_with_balance() -> complete()

---

## Вопросы для архитектора

1. **Avatar selection mechanism**: RadioItems, Pattern-Matching Callbacks, или другой подход?
2. **Dashboard greeting real-time update**: Необходим ли real-time update без навигации?
3. **Sidebar profile click target**: Весь profile container или отдельная кнопка?
4. **Profile modal callback architecture**: Один callback или два с allow_duplicate=True?
5. **OnboardingService.skip()**: Явно устанавливать defaults или полагаться на bootstrap?

---

## Рекомендации для следующей итерации

### Обязательно:
1. Решить проблему dashboard greeting callback
2. Описать механизм avatar selection
3. Уточнить profile modal callback architecture

### Желательно:
4. Дополнить onboarding callback flow
5. Добавить TypedDict для UserProfile
6. Явно указать размещение dcc.Store("profile-updated")

### Опционально:
7. Упомянуть breaking change complete_with_balance() -> complete()
8. Уточнить поведение skip() относительно defaults
