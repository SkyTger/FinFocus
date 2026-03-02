# Epic-09 Design Spec — UI Redesign (Glassmorphism Light Theme)

**Статус**: Reference document для реализации
**Источники**: Stitch-generated HTML (dash.html, dark_calendar.html, dark_goals.html)
**Дата**: 2026-02-28

---

## 1. Design Tokens

### 1.1 Палитра

```css
:root {
    /* Primary */
    --color-primary: #2ecc71;          /* Основной зелёный (сохраняем наш) */
    --color-primary-dark: #27ae60;
    --color-primary-glow: rgba(46, 204, 113, 0.2);  /* Для свечения */

    /* Текст */
    --color-text-primary: #2c3e50;
    --color-text-secondary: #64748b;   /* slate-500 */
    --color-text-muted: #94a3b8;       /* slate-400 */

    /* Семантические */
    --color-income: #2ecc71;           /* Зелёный для доходов */
    --color-expense: #f43f5e;          /* rose-500 для расходов */
    --color-warning: #f59e0b;          /* amber-500 для предупреждений */
    --color-cushion: #eab308;          /* yellow-500 для подушки */
    --color-priority-high: #f97316;    /* orange-500 */
    --color-priority-medium: #3b82f6;  /* blue-500 */

    /* Фон */
    --color-bg-page-from: #eaf2ee;     /* Верх градиента */
    --color-bg-page-to: #dce8e0;       /* Низ градиента */

    /* Glass */
    --glass-bg: rgba(255, 255, 255, 0.25);
    --glass-bg-hover: rgba(255, 255, 255, 0.35);
    --glass-border: rgba(255, 255, 255, 0.5);
    --glass-border-top: rgba(255, 255, 255, 0.8);  /* Блик сверху */
    --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    --glass-shadow-hover: 0 12px 40px 0 rgba(31, 38, 135, 0.12);
}
```

### 1.2 Типографика

```css
/* Шрифт: оставляем системный стек (Segoe UI), НЕ подключаем Manrope
   Причина: Dash не CDN-based, а Manrope добавит лишний вес */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
```

### 1.3 Радиусы

| Элемент | Значение | Заметка |
|---------|----------|---------|
| Карточки (KPI, chart, stats) | 16px | Из Stitch: `rounded-xl` = 1rem |
| Sidebar card | 16px | Единообразие с карточками |
| Active nav pill | 12px | `rounded-full` слишком круглый, 12px — компромисс |
| Кнопки | 8px | Текущее значение, сохраняем |
| Calendar day cells | 12px | Из dark_calendar: `rounded-2xl` адаптируем |
| Tooltip | 16px | Текущее значение, сохраняем |

### 1.4 Тени

```css
/* Базовая тень (карточки) */
--shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);

/* Hover / lifted тень */
--shadow-hover: 0 12px 40px 0 rgba(31, 38, 135, 0.12);

/* Sidebar (акцентная) */
--shadow-sidebar: 0 8px 32px rgba(31, 38, 135, 0.1),
                  0 2px 8px rgba(0, 0, 0, 0.04);
```

---

## 2. Фон страницы

**Было:** `background-color: #f8f9fa` (плоский серый)

**Стало:**
```css
body {
    background: linear-gradient(135deg, #eaf2ee 0%, #dce8e0 100%);
    min-height: 100vh;
}
```

Мятно-зелёный градиент. Спокойный, но с характером. Создаёт глубину.

---

## 3. Glassmorphism (базовый класс)

```css
.glass-card {
    background: rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.5);
    border-top: 1px solid rgba(255, 255, 255, 0.8);  /* Блик сверху! */
    border-radius: 16px;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.12);
}

/* Fallback для браузеров без backdrop-filter */
@supports not (backdrop-filter: blur(16px)) {
    .glass-card {
        background: rgba(255, 255, 255, 0.92);
    }
}
```

**Ключевой визуальный приём:** `border-top: 1px solid rgba(255,255,255,0.8)` — имитация блика света на верхней грани стекла. Это создаёт ощущение толщины/объёма.

---

## 4. Компоненты

### 4.1 Sidebar

**Из Stitch берём:**
- Floating card (auto-height, НЕ full-height)
- Profile card с зеленоватым оттенком внутри sidebar
- Active nav item = pill с зелёной заливкой (border-radius: 12px)
- Зелёный разделитель (градиент green → transparent)

**Что меняется vs текущий код:**

| Свойство | Было | Стало |
|----------|------|-------|
| Высота | `height: 100vh` (full) | `auto` (по контенту), `margin: 16px` со всех сторон |
| Active item | `border-left: 4px solid green` | `background: #2ecc71; color: white; border-radius: 12px` |
| Фон sidebar | `#ffffff` (белый) | Glass: `rgba(255,255,255,0.25)` + blur |
| Profile section | Белый bg-light | `rgba(232, 245, 236, 0.4)` — зеленоватый оттенок |
| Тень | `0 0.125rem 0.25rem` (маленькая) | `0 8px 32px rgba(31,38,135,0.1)` (глубокая) |

**CSS sidebar — целевой вид:**
```css
.sidebar-card {
    background: rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.5);
    border-top: 1px solid rgba(255, 255, 255, 0.8);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1),
                0 2px 8px rgba(0, 0, 0, 0.04);
    /* Auto-height вместо 100vh */
    height: auto;
    margin: 16px;
}

/* Profile card inside sidebar */
.sidebar-profile {
    background: rgba(232, 245, 236, 0.4);
    border-radius: 12px;
    padding: 12px;
    margin: 0 12px 16px;
}

/* Active nav item — pill style */
.sidebar-nav-item-active {
    background-color: var(--color-primary) !important;
    color: white !important;
    border-radius: 12px !important;
    border-left: none !important;  /* Убираем старый border-left */
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(46, 204, 113, 0.3);
}

/* Separator — gradient line */
.sidebar-separator {
    height: 1px;
    background: linear-gradient(90deg, var(--color-primary) 0%, transparent 100%);
    margin: 12px 16px;
    opacity: 0.3;
}
```

### 4.2 KPI Cards

**Из Stitch берём:**
- Иконка в правом нижнем углу (полупрозрачная, декоративная)
- Подпись под числом ("+2.4% за сегодня", "Лимит почти исчерпан")
- Hover lift effect (translateY -4px)

**Целевая структура:**
```
┌─────────────────────────┐
│ ОБЩИЙ БАЛАНС      🏛   │  ← label uppercase + icon (opacity 0.1)
│                         │
│ 450 200 ₽              │  ← large number (kpi-number)
│ +2.4% за сегодня       │  ← trend/subtitle (green/red)
└─────────────────────────┘
```

**CSS:**
```css
.kpi-card {
    /* Наследует .glass-card */
    position: relative;
    overflow: hidden;
    padding: 20px 24px;
}

.kpi-card-icon {
    position: absolute;
    right: -8px;
    bottom: -8px;
    font-size: 5rem;
    opacity: 0.08;
    transition: opacity 0.2s;
}

.kpi-card:hover .kpi-card-icon {
    opacity: 0.15;
}

.kpi-trend {
    font-size: 13px;
    font-weight: 600;
    margin-top: 4px;
}

.kpi-trend.positive { color: var(--color-income); }
.kpi-trend.negative { color: var(--color-expense); }
.kpi-trend.warning { color: var(--color-warning); }
```

### 4.3 Calendar

**Из dark_calendar берём (адаптируем в светлую тему):**
- Day cells как отдельные glass-плитки с gap между ними
- Цветные точки (зелёная/красная, 6px) вместо текстовых иконок
- Today: зелёный border + лёгкое свечение
- Low balance: красноватый тинт + красный текст
- Stats cards сверху (3 карточки: остаток, доходы, расходы)

**Ключевое изменение:** Текущий календарь использует таблично-подобную сетку с borders между ячейками. Stitch использует отдельные карточки с gap. **Берём Stitch-подход** — ячейки как отдельные стеклянные плитки.

**Целевой вид ячейки:**
```
┌──────────────┐
│ 15       ●●  │  ← номер (bold) + точки (зел/красн) справа
│              │
│              │
│   147 200 ₽  │  ← баланс внизу
└──────────────┘
```

**CSS:**
```css
.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 8px;
    background: transparent;
    border: none;
}

.calendar-day {
    background: rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 12px;
    min-height: 80px;
    padding: 8px;
    cursor: pointer;
    transition: background 0.2s, transform 0.15s;
}

.calendar-day:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
}

.calendar-day-today {
    border: 2px solid var(--color-primary);
    box-shadow: 0 0 12px rgba(46, 204, 113, 0.15);
    background: rgba(46, 204, 113, 0.05);
}

.calendar-day-low-balance {
    background: rgba(244, 63, 94, 0.05);
    border-color: rgba(244, 63, 94, 0.15);
}

/* Transaction dots */
.calendar-day-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
}

.calendar-day-dot.income { background: var(--color-income); }
.calendar-day-dot.expense { background: var(--color-expense); }
```

### 4.4 Goals

**Из dark_goals берём (адаптируем в светлую тему):**
- Budget card сверху с прогресс-баром распределения
- Goal cards горизонтальные: badge #N + icon + info + кнопки
- Priority-цветовое кодирование: #1 = зелёный/оранжевый, #2 = синий
- Cushion card с золотым акцентом (gradient + glow border)

**Целевой вид goal card:**
```
┌──────────────────────────────────────────────────────────────┐
│  [#1]  [✈️]  Отпуск в Турцию  [ВЫСОКИЙ ПРИОРИТЕТ]           │
│              📅 Август 2026 · 💰 10 000 ₽/мес               │
│              67 500 ₽ из 150 000 ₽    ████████░░░ 45%       │
│                                    [Редактировать] [Внести]  │
└──────────────────────────────────────────────────────────────┘
```

**Cushion card — особый стиль:**
```css
.cushion-card {
    /* Glass base */
    background: rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(16px);
    border-radius: 16px;
    /* Золотой акцент */
    border: 1px solid rgba(234, 179, 8, 0.2);
    box-shadow: 0 0 20px rgba(234, 179, 8, 0.05);
    position: relative;
}

/* Glow border effect on hover */
.cushion-card::before {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: 17px;
    background: linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(46, 204, 113, 0.15));
    z-index: -1;
    opacity: 0.5;
    transition: opacity 0.3s;
}

.cushion-card:hover::before {
    opacity: 1;
}

/* Gold progress bar */
.progress-bar-cushion {
    background: linear-gradient(90deg, #eab308, #2ecc71);
    box-shadow: 0 0 12px rgba(234, 179, 8, 0.3);
}
```

---

## 5. Что НЕ меняем

- **Plotly графики** — стиль задаётся через Python код, не CSS. Отдельная задача.
- **Модалы** — текущий стиль (зелёный gradient header) сохраняем.
- **Tooltip** — glassmorphism уже есть, только обновить цвета.
- **Шрифт** — оставляем системный, не подключаем Manrope.
- **Bootstrap Icons** — не переходим на Material Symbols (Stitch использует Google Material).

---

## 6. Stitch Reference Files

Оригинальные HTML-файлы из Google Stitch:
- `~/Загрузки/temp/ФФ/dash.html` — Dashboard (светлая тема, glassmorphism)
- `~/Загрузки/temp/ФФ/dark_calendar.html` — Calendar (тёмная тема)
- `~/Загрузки/temp/ФФ/dark_goals.html` — Goals (тёмная тема)
- `~/Загрузки/temp/ФФ/screen*.png` — Скриншоты предыдущих итераций

---

## 7. Приоритет реализации

### Батч A: CSS Foundation (design tokens + glass)
**Файлы:** `custom.css`, `sidebar.css`
1. Обновить `:root` — новые переменные (glass, bg gradient, shadows)
2. Добавить `.glass-card` класс
3. Обновить `body` background на gradient
4. Sidebar: glass + auto-height + pill active
5. KPI cards: glass + icon + trend

### Батч B: Calendar Redesign
**Файлы:** `calendar.css`, `calendar.py`
1. Calendar grid → CSS Grid с gap (вместо table borders)
2. Day cells как glass tiles
3. Transaction dots вместо текстовых иконок
4. Today glow + low balance tint

### Батч C: Goals Redesign
**Файлы:** `goals.py`, `custom.css`
1. Goal cards → horizontal layout с badge + icon
2. Budget card сверху
3. Cushion card с золотым акцентом
4. Priority цветовое кодирование

### Батч D: Polish
1. Hover animations
2. Scrollbar style update
3. Responsive adjustments
4. Cross-browser testing (backdrop-filter fallbacks)
