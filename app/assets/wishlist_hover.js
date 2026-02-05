/**
 * Wishlist Hover — каскадный пересчет остатков при наведении на день
 * в wishlist-mode календаря.
 *
 * Данные берутся из hidden div #wishlist-hover-data (HoverBalances JSON):
 *   base_balances: {date_iso: balance_str}
 *   by_candidate:  {candidate_date_iso: {day_iso: balance_str}}
 *
 * При hover на .calendar-day (не .past-day-wishlist) все .calendar-day-balance
 * заменяются на пересчитанные значения из by_candidate[hovered_date].
 * При mouseleave восстанавливаются base_balances.
 */
(function () {
    "use strict";

    var rubleFormatter = new Intl.NumberFormat("ru-RU", {
        style: "decimal",
        maximumFractionDigits: 0,
        useGrouping: true,
    });

    function formatRubles(val) {
        return rubleFormatter.format(Math.round(parseFloat(val))) + " \u20BD";
    }

    /**
     * Читает HoverBalances из DOM (hidden div с JSON).
     */
    function getHoverData() {
        var el = document.getElementById("wishlist-hover-data");
        if (!el) return null;
        try {
            var raw = el.textContent || "";
            if (!raw || raw === "null") return null;
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    /**
     * Применяет пересчитанные балансы для candidateDate.
     */
    function applyHoverBalances(hoverData, candidateDate) {
        if (!hoverData || !hoverData.by_candidate) return;
        var adjusted = hoverData.by_candidate[candidateDate];
        if (!adjusted) return;

        var balanceEls = document.querySelectorAll(
            ".calendar-grid.wishlist-mode .calendar-day-balance[data-date]"
        );
        balanceEls.forEach(function (el) {
            var d = el.getAttribute("data-date");
            if (adjusted[d] !== undefined) {
                var val = parseFloat(adjusted[d]);
                el.textContent = formatRubles(val);
                el.classList.add("hover-recalculated");
                // Red for negative balances
                if (val < 0) {
                    el.classList.add("hover-negative");
                }
            }
        });
    }

    /**
     * Восстанавливает исходные балансы из base_balances.
     */
    function restoreBaseBalances(hoverData) {
        if (!hoverData || !hoverData.base_balances) return;

        var balanceEls = document.querySelectorAll(
            ".calendar-grid.wishlist-mode .calendar-day-balance[data-date]"
        );
        balanceEls.forEach(function (el) {
            var d = el.getAttribute("data-date");
            if (hoverData.base_balances[d] !== undefined) {
                el.textContent = formatRubles(hoverData.base_balances[d]);
                el.classList.remove("hover-recalculated", "hover-negative");
            }
        });
    }

    /**
     * Навешивает mouseenter/mouseleave на дни wishlist-grid.
     */
    function attachHoverListeners(grid) {
        if (grid.getAttribute("data-hover-attached") === "true") return;
        grid.setAttribute("data-hover-attached", "true");

        var days = grid.querySelectorAll(
            ".calendar-day:not(.past-day-wishlist)"
        );

        days.forEach(function (dayEl) {
            var balanceEl = dayEl.querySelector(
                ".calendar-day-balance[data-date]"
            );
            if (!balanceEl) return;
            var candidateDate = balanceEl.getAttribute("data-date");
            if (!candidateDate) return;

            // Determine if this day is safe or unsafe
            var isSafe = dayEl.classList.contains("wishlist-day-safe");
            var isUnsafe = dayEl.classList.contains("wishlist-day-unsafe");

            dayEl.addEventListener("mouseenter", function () {
                var hoverData = getHoverData();
                applyHoverBalances(hoverData, candidateDate);

                // Group hover effect
                if (isSafe) {
                    grid.classList.add("hover-safe");
                } else if (isUnsafe) {
                    grid.classList.add("hover-unsafe");
                }
            });

            dayEl.addEventListener("mouseleave", function () {
                var hoverData = getHoverData();
                restoreBaseBalances(hoverData);

                // Remove group hover effect
                grid.classList.remove("hover-safe", "hover-unsafe");
            });
        });
    }

    /**
     * Наблюдает за .calendar-container: обнаруживает появление
     * .calendar-grid.wishlist-mode и навешивает hover listeners.
     */
    function observeContainer(container) {
        var observer = new MutationObserver(function () {
            var grid = container.querySelector(
                ".calendar-grid.wishlist-mode"
            );
            if (grid) {
                attachHoverListeners(grid);
            }
        });

        observer.observe(container, { childList: true, subtree: true });

        // Проверяем немедленно (grid мог уже быть)
        var existing = container.querySelector(
            ".calendar-grid.wishlist-mode"
        );
        if (existing) {
            attachHoverListeners(existing);
        }
    }

    /**
     * Инициализация: ищет .calendar-container или ждёт через MutationObserver.
     */
    function init() {
        var container = document.querySelector(".calendar-container");
        if (container) {
            observeContainer(container);
            return;
        }

        // Fallback: ждём появления .calendar-container
        var bodyObserver = new MutationObserver(function (mutations, obs) {
            var c = document.querySelector(".calendar-container");
            if (c) {
                obs.disconnect();
                observeContainer(c);
            }
        });

        bodyObserver.observe(document.body, {
            childList: true,
            subtree: true,
        });
    }

    // Запуск
    if (
        document.readyState === "complete" ||
        document.readyState === "interactive"
    ) {
        init();
    } else {
        document.addEventListener("DOMContentLoaded", init);
    }
})();
