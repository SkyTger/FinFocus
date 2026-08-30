# Шаг 10: Документация

## Briefing

- **Цель:** Knowledge Bank отражает новое состояние навигации; урок про анимацию на монтировании записан в паттерны.
- **Ключевые файлы:**
  - `.obsidian-docs/knowledge-bank/modules/ui-components.md` — раздел Sidebar
  - `.obsidian-docs/knowledge-bank/patterns/callbacks.md` — «Правила условно присутствующих элементов»
  - `.obsidian-docs/knowledge-bank/modules/routing.md` — номера строк `display_page`

## Sub-tasks

1. `modules/ui-components.md`: раздел «Sidebar Component (Протокол 0030)» переписать как **«Nav Rail Component»** — файл, геометрия, инварианты, механизм разворота, упоминание файла-надгробия `sidebar.py`.

2. `patterns/callbacks.md`: дописать подраздел **«Анимация на монтировании условно присутствующего элемента»**:
   - почему `@keyframes`, а не `transition` (на монтировании нет стартового значения; два кадра требуют JS);
   - почему различитель «пришёл с дашборда» — **пустой слот**, а не хранимый предыдущий pathname (второй источник правды);
   - **почему носитель идентичности узла — `id`, а не `key`**: React-ключ обёртки = `stringifyId(props.id)` (`createContainer` ~3972 в `dash_renderer.dev.js`), проп `key` в этом выражении не участвует и до реконсиляции обёртки не доходит; `dcc.Link` его вообще не принимает;
   - **`id` — не приглашение вешать колбэк**: Output на него = гонка со слот-колбэком.

3. `modules/routing.md`: поправить номера строк `display_page`, если сдвинулись.

4. Проверить `index.md` и `architecture.md` на упоминания навигации (аналитический отчёт `analyses/2026-08-20-full.md` — исторический документ, НЕ переписывать).

## Workflow

1. Выполни Sub-tasks
2. Обнови `log.md`, `context.md` (Current Step 11)
3. Коммит: `docs(knowledge-bank): Nav Rail и паттерн анимации на монтировании [protocol-0031/10]`
4. Push, отчёт
