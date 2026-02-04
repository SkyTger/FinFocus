# Шаг 9: JS hover asset

## Briefing

- **Цель:** Создать wishlist_hover.js — полностью JS-based hover для каскадного пересчета остатков
- **Ключевые файлы:**
  - `app/assets/wishlist_hover.js` — JS hover (~80 строк)
- **Доп. информация:** solution-v3.md — полный код JS hover. MutationObserver на .calendar-container. Intl.NumberFormat для форматирования рублей. Math.round(parseFloat()) для округления.

## Sub-tasks

1. Создать `app/assets/wishlist_hover.js`:
   - IIFE pattern `(function() { 'use strict'; ... })();`
   - `rubleFormatter = new Intl.NumberFormat('ru-RU', { style: 'decimal', maximumFractionDigits: 0, useGrouping: true })`
   - `init()` — поиск .calendar-container, fallback через MutationObserver на body
   - `observeContainer(container)` — MutationObserver на .calendar-container для обнаружения .calendar-grid.wishlist-mode
   - `getHoverData()` — JSON.parse из DOM элемента #wishlist-hover-data
   - `applyHoverBalances(hoverData, candidateDate)` — применить балансы из by_candidate к .calendar-day-balance[data-date]
   - `restoreBaseBalances(hoverData)` — восстановить base_balances
   - `formatRubles(val)` — Intl.NumberFormat + ' ₽'
   - `attachHoverListeners(grid)` — mouseenter/mouseleave на .calendar-day:not(.past-day-wishlist)
   - data-hover-attached guard для предотвращения повторного подключения
   - DOMContentLoaded / readyState check для инициализации

2. Верификация: файл должен быть синтаксически корректным JS

## Workflow

1. Выполни Sub-tasks
2. Обнови `log.md`
3. Обнови `context.md` — Current Step: 10, Next Action: Шаг 10
4. Коммит: `git add . && git commit -m "feat(wishlist): JS hover asset [protocol-0020/09]"`
5. Push
6. Отчёт
