# Epic-10: UI Polish & Design System

## Цель

Довести визуальное качество интерфейса до уровня современных SaaS-дашбордов (shadcn/ui reference): консистентные токены, микро-анимации, отзывчивые hover/focus-состояния, стройная типографика. Без смены технологического стека (Dash + CSS).

## Scope

### Входит:
- Формализация design tokens (spacing, typography, radius, shadows, transitions)
- Замена хардкод-значений на CSS-переменные во всех 8 CSS-файлах
- Унификация hover/focus/active состояний для всех интерактивных элементов
- Микро-анимации: staggered fade-in, button press, skeleton loading
- Typography hierarchy (h1-h4) и tabular-nums для цифр
- Focus-visible ring для доступности
- Smooth input/select focus transitions
- Page transition animation при смене URL
- Firefox scrollbar + selection color

### Не входит:
- Смена технологического стека (React, shadcn/ui, Tailwind)
- Dark theme (отдельный Epic-07 в Backlog)
- Mobile responsive < 576px (отдельный Epic-08 в Backlog)
- Новая функциональность (только визуальные улучшения)
- Изменения в Python-коде (только CSS + минимальные правки className в компонентах)

## Предыстория

**Проблема**:
CSS-аудит выявил системные несоответствия, накопившиеся за 20 батчей разработки:

1. **10 разных border-radius** (3px-9999px) без системы — каждый компонент использует свои значения
2. **Нет шкалы spacing** — padding варьируется: 6/10/12/14/16/18/20/24/40px
3. **Нет шкалы typography** — font-size хардкод, KPI-number: 24px в одном месте, 30px в другом
4. **3 разных hover-стиля для таблиц** — rgba(0,0,0,0.02), rgba(255,255,255,0.3), rgba(46,204,113,0.04)
5. **Модалы стилизованы по-разному** — radius 12px vs 24px, shadow разный
6. **Минимум анимаций** — только fadeIn и spin, нет staggered появления, нет press-эффекта кнопок
7. **Focus ring** — только на .btn и .nav-link, остальные элементы без стилей

**Референс**: shadcn/ui Dashboard (https://ui.shadcn.com/examples/dashboard) — консистентные токены, плавные переходы, единый design language.

**Решение**: CSS-only polish в 5 фаз, инкрементально, без переписки кода.

## Timeline

- **Старт**: TBD
- **Завершение**: TBD
- **Статус**: Планирование

## Фазы эпика

### Фаза 1: Design Tokens (фундамент)
**Цель**: Единый источник правды для всех визуальных значений

**Файл**: `app/assets/custom.css` — секция `:root`

**Задачи**:
- [ ] Spacing scale: `--space-1` (4px) .. `--space-10` (40px)
- [ ] Font size scale: `--font-xs` (11px) .. `--font-2xl` (30px)
- [ ] Border-radius scale: `--radius-sm` (8px), `--radius-md` (12px), `--radius-lg` (16px), `--radius-xl` (24px), `--radius-pill` (9999px)
- [ ] Shadow scale: `--shadow-sm`, `--shadow-md`, `--shadow-lg` (3 уровня)
- [ ] Transition tokens: `--duration` (0.2s), `--ease` (cubic-bezier(0.4, 0, 0.2, 1))

**Критерии приемки**:
- Все токены определены в `:root`
- Существующие `--shadow` и `--shadow-hover` заменены на новую шкалу
- Deprecated aliases помечены комментарием для удаления в Фазе 2

---

### Фаза 2: Консистентность (замена хардкода на токены)
**Цель**: Все 8 CSS-файлов используют единые токены

**Файлы**: custom.css, sidebar.css, calendar.css, goals.css, transactions.css, analytics.css, onboarding.css, wishlist.css

**Задачи**:
- [ ] Border-radius: заменить 3/4/6px -> `--radius-sm`, 10px -> `--radius-md`, 16px -> `--radius-lg`, 24px -> `--radius-xl`
- [ ] Shadows: убрать ad-hoc тени, привести к `--shadow-sm/md/lg`
- [ ] Table hover: единый стиль `rgba(46, 204, 113, 0.04)` для всех таблиц
- [ ] Modal стиль: единый `border-radius: var(--radius-xl)` + `box-shadow: var(--shadow-lg)`
- [ ] Transition duration: заменить 0.15s/0.3s на `var(--duration)` где уместно
- [ ] Удалить deprecated aliases (`--primary-green`, `--light-green`, `--bg-light`, `--text-muted`, `--border-color`)

**Критерии приемки**:
- 0 хардкод border-radius (кроме 50% для кругов и 9999px для pill)
- 0 ad-hoc box-shadow
- Визуальная регрессия: нет (проверка скриншотами до/после)

---

### Фаза 3: Micro-interactions (отзывчивость)
**Цель**: Интерфейс "чувствуется живым" — как в shadcn/ui

**Задачи**:
- [ ] Focus-visible ring: `outline: 2px solid var(--color-primary)` + `outline-offset: 2px` для всех интерактивных элементов
- [ ] `:focus:not(:focus-visible)` — убрать outline для мыши
- [ ] Input/select focus: `border-color` + `box-shadow` transition с green glow
- [ ] Button press: `:active { transform: scale(0.97) }` для всех .btn
- [ ] KPI staggered fade-in: `animation-delay: 0/60/120/180ms` для 4 карточек
- [ ] Skeleton loading CSS: `@keyframes shimmer` для состояний загрузки
- [ ] Card появление: `slideUp` animation при рендере страниц

**Критерии приемки**:
- Все input/select/button имеют visible focus ring при Tab-навигации
- KPI-карточки появляются с задержкой (staggered)
- Кнопки визуально "нажимаются" при клике

---

### Фаза 4: Typography polish
**Цель**: Стройная типографическая иерархия

**Задачи**:
- [ ] Heading hierarchy: h1 (30px/800), h2 (24px/700), h3 (20px/600), h4 (16px/600) с letter-spacing
- [ ] KPI number: единый `var(--font-xl)` (устранить конфликт 24px vs 30px)
- [ ] `font-variant-numeric: tabular-nums` для всех числовых элементов (KPI, таблицы, баланс)
- [ ] Замена хардкод font-size на токены (`--font-xs` .. `--font-2xl`) где возможно

**Критерии приемки**:
- h1-h4 стилизованы через CSS (не inline styles)
- Числа в KPI и таблицах выровнены по колонкам (tabular-nums)
- 0 конфликтов font-size для одного компонента

---

### Фаза 5: Final polish
**Цель**: Финальные штрихи

**Задачи**:
- [ ] Page transition: `slideUp` animation для `.main-content > div`
- [ ] Firefox scrollbar: `scrollbar-width: thin; scrollbar-color`
- [ ] Selection color: `::selection { background: var(--color-primary-glow) }`
- [ ] Удалить неиспользуемые CSS-классы (аудит)
- [ ] Проверка всех страниц: Dashboard, Calendar, Goals, Transactions, Analytics

**Критерии приемки**:
- Переходы между страницами плавные
- Scrollbar стилизован одинаково во всех браузерах
- Визуальная регрессия: проверка всех 5 страниц

---

## Критерии готовности эпика

- [ ] Все CSS-файлы используют design tokens (0 хардкод значений для radius/shadow/spacing)
- [ ] Единый hover/focus/active стиль для каждого типа элемента
- [ ] Staggered animations на KPI-карточках и страницах
- [ ] Focus-visible ring на всех интерактивных элементах
- [ ] Typography hierarchy через CSS (h1-h4)
- [ ] tabular-nums для числовых элементов
- [ ] Визуальная регрессия: 0 поломок на всех 5 страницах

## Связи

**Зависит от**:
- Epic-09 (IN PROGRESS) — стабильная кодовая база, все UI-компоненты готовы

**Блокирует**:
- Epic-07 Dark Theme — dark theme будет использовать design tokens из этого эпика
- Epic-08 Mobile Responsive — адаптивность проще делать с консистентными токенами

**Не блокирует**:
- Epic-09 Phase 4 (Bug fixes) — можно делать параллельно

## Технические детали

### Новые CSS-переменные (Фаза 1):
```css
:root {
  /* Spacing scale */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;

  /* Font size scale */
  --font-xs: 11px;
  --font-sm: 13px;
  --font-base: 14px;
  --font-md: 16px;
  --font-lg: 20px;
  --font-xl: 24px;
  --font-2xl: 30px;

  /* Border-radius scale */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-pill: 9999px;

  /* Shadow scale */
  --shadow-sm: 0 2px 8px rgba(31, 38, 135, 0.05);
  --shadow-md: 0 8px 32px rgba(31, 38, 135, 0.07);
  --shadow-lg: 0 16px 48px rgba(31, 38, 135, 0.12);

  /* Transition */
  --duration: 0.2s;
  --ease: cubic-bezier(0.4, 0, 0.2, 1);
}
```

### Ключевые CSS-паттерны (Фаза 3):
```css
/* Focus-visible ring */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
:focus:not(:focus-visible) {
  outline: none;
  box-shadow: none;
}

/* Button press */
.btn:active {
  transform: scale(0.97);
  transition-duration: 0.1s;
}

/* Staggered KPI */
.kpi-card {
  animation: slideUp 0.4s var(--ease) both;
}
.kpi-card:nth-child(1) { animation-delay: 0ms; }
.kpi-card:nth-child(2) { animation-delay: 60ms; }
.kpi-card:nth-child(3) { animation-delay: 120ms; }
.kpi-card:nth-child(4) { animation-delay: 180ms; }

/* Skeleton loading */
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton {
  background: linear-gradient(90deg,
    rgba(0,0,0,0.04) 25%,
    rgba(0,0,0,0.08) 50%,
    rgba(0,0,0,0.04) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}
```

## Оценка объема

| Фаза | Сложность | Файлы | Риск регрессии |
|------|-----------|-------|----------------|
| 1. Design Tokens | Простая | custom.css | Нулевой (добавление) |
| 2. Консистентность | Механическая, объемная | все 8 CSS | Средний (поиск/замена) |
| 3. Micro-interactions | Средняя | custom.css + компоненты | Низкий (новые правила) |
| 4. Typography | Простая | custom.css | Низкий |
| 5. Final polish | Простая | custom.css | Низкий |

## Ключевые решения

1. **CSS-only подход** — без смены стека (React/shadcn), все улучшения через CSS-переменные и правила
2. **Инкрементальные фазы** — каждая фаза самодостаточна и дает видимый результат
3. **Фаза 1 = фундамент** — без токенов остальные фазы невозможны
4. **Фаза 2 = основной объем** — механическая замена, но затрагивает все файлы
5. **Shadcn-easing** — `cubic-bezier(0.4, 0, 0.2, 1)` вместо линейного `ease` для более "живых" переходов

---

*Последнее обновление: 2026/03/14*
