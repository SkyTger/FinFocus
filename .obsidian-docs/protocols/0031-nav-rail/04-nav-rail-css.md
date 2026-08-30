# Шаг 4: CSS полоски

## Briefing

- **Цель:** Геометрия полоски по утверждённому эскизу. **Разворот на этом шаге НЕ добавляется** — сперва надо увидеть статическую геометрию и убедиться, что язычок выходит за кожух и не обрезан.
- **Ключевые файлы:**
  - `app/assets/nav_rail.css` — **НОВЫЙ**
  - `.visual/finfocus-panel-rail/v4.html` — эскиз, значения переносятся без пересчёта
  - `app/assets/panel.css` — токены `--pnl-radius`, `--pnl-radius-sm`, образец `prefers-reduced-motion` (строки 282, 830)
  - `app/assets/custom.css` — `--glass-*`, `--shadow`, `--color-*`
- **Доп. информация:** Ни одного нового `:root`-токена, кроме локальных `--rail-w/--rail-h/--rail-slot/--rail-icon`.

## Sub-tasks

1. `.nav-rail-column` — `position: sticky; top: 24px; flex: 0 0 60px; width/min-width: 60px; height: var(--rail-h); z-index: 100` + **единственное правило видимости** `.nav-rail-column:empty { display: none }` (инвариант 2 — второй механизм не вводить).

2. `.nav-rail` — кожух: `background: var(--glass-bg)`, `backdrop-filter: var(--glass-blur)` + `-webkit-`, `border: 1px solid var(--glass-border)`, `border-top: 1px solid var(--glass-border-top)`, `box-shadow: var(--shadow)`, `border-radius: var(--pnl-radius)`, **`height: 100%`** (без неё процентная высота ребёнка вырождается в `auto` и распорка перестаёт прижимать аватар; у прежнего `.sidebar-card` это стояло явно, `sidebar.css:34`), **БЕЗ `overflow: hidden` и БЕЗ `clip-path`**. Плюс `@supports not (backdrop-filter: blur(16px)) { background: rgba(255,255,255,0.92) }`.

3. `.nav-rail-inner` — `display: flex; flex-direction: column; align-items: center; height: 100%; padding: 10px 0 12px`. Носитель будущей анимации (шаг 8).

4. Элементы по таблице геометрии (RTM #38-62 решения):
   - `.nav-rail-logo` — 44×44, `border-radius: 12px`, градиент бренда, знак 24px белый, `box-shadow: 0 3px 10px rgba(46,204,113,.30)`
   - `.nav-rail-sep` — 26×1px, `margin: 11px 0 9px`, градиент к прозрачному
   - `.nav-rail-slot` — 44×44, `flex: 0 0 44px`, `border-radius: 9999px`, знак `var(--rail-icon)` 22px, цвет `var(--color-text-secondary)`, фона нет; `.nav-rail-nav { gap: 7px }`
   - `.nav-rail-slot:hover` — подкладка `rgba(46,204,113,.10)`
   - `.nav-rail-slot--active` — `background: var(--color-primary)`, знак белый, `box-shadow: 0 2px 8px rgba(46,204,113,.20)`
   - `.nav-rail-tip` — язычок: `left: calc(100% + 9px)`, фон `var(--color-text-primary)`, белый 12.5px/600, `border-radius: var(--pnl-radius-sm)`, `box-shadow: 0 4px 14px rgba(31,38,135,.18)`, `z-index: 5`, `::before` — треугольный носик
   - `.nav-rail-spacer` — `flex: 1 1 auto; min-height: 16px`
   - `.nav-rail-avatar` — круг 44×44, подклад `rgba(46,204,113,.15)`, `border: 1px solid rgba(46,204,113,.28)`, 20px, `cursor: pointer`; **его собственный язычок «Профиль»** тем же механизмом

5. **Не удалять `sidebar.css`** — он живёт до шага 9. Имена `.nav-rail-*` и `.sidebar-*` не пересекаются, конфликта нет.

## Workflow

1. Выполни Sub-tasks
2. Базовая проверка: CSS компилировать нечем — визуальная сверка с `v4.png`
3. Обнови `log.md`, `context.md` (Current Step 5)
4. Коммит: `feat(nav-rail): CSS полоски по геометрии эскиза [protocol-0031/04]`
5. Push, отчёт
