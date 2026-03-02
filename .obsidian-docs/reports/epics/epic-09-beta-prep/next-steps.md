# Epic-09 — Next Steps (UI Redesign)

**Последнее обновление**: 2026-02-28
**Статус**: Design Spec создан, готовы к реализации

---

## Что уже сделано

- [x] Фаза 1: Auto-bootstrap (User + Categories + Migrations) — ✅ в main
- [x] Google Stitch итерации (3 раунда, 3 финальных HTML-файла)
- [x] Design Spec создан: `design-spec.md`

## Что делать дальше

### Шаг 2: CSS Foundation (Батч A из design-spec.md)

**Файлы для изменения:**
- `app/assets/custom.css` — обновить `:root`, добавить `.glass-card`, body gradient
- `app/assets/sidebar.css` — glass sidebar, pill active, auto-height

**Конкретные действия:**
1. Обновить CSS-переменные в `:root` (добавить glass-*, bg-gradient, shadow)
2. Изменить `body` background с плоского `#f8f9fa` на `linear-gradient(135deg, #eaf2ee, #dce8e0)`
3. Добавить класс `.glass-card` (background, blur, border-top highlight, shadow)
4. Sidebar: убрать `height: 100vh`, добавить glass, margin 16px
5. Active nav: убрать `border-left: 4px`, добавить pill-style (bg green, radius 12px)
6. KPI cards: перевести на `.glass-card`, добавить icon/trend компоненты

**Тесты:** CSS-only изменения не требуют новых тестов. Визуальная проверка в браузере.

### Шаг 3: Calendar Redesign (Батч B)

**Файлы:** `app/assets/calendar.css`, `app/components/calendar.py`

Переход с table-like grid на CSS Grid с gap. Day cells как glass tiles. Transaction dots.

### Шаг 4: Goals Redesign (Батч C)

**Файлы:** `app/components/goals.py`, `app/assets/custom.css`

Horizontal goal cards с priority badges. Cushion с золотым акцентом.

### Шаг 5: Polish (Батч D)

Hover animations, scrollbar, responsive, fallbacks.

---

## Параллельно (Фаза 2 Epic-09)

После UI redesign:
- [ ] User Profile: welcome screen, avatar, sidebar profile, edit modal
- [ ] Phase 3: Delivery & Setup (README для тестеров)
- [ ] Phase 4: Bug fixes из бета-тестирования

---

## Reference

- Design Spec: `.obsidian-docs/reports/epics/epic-09-beta-prep/design-spec.md`
- Stitch HTML: `~/Загрузки/temp/ФФ/` (dash.html, dark_calendar.html, dark_goals.html)
- Скриншоты: `~/Загрузки/temp/ФФ/screen*.png`
