/**
 * Clientside callbacks для элементов, которые рендерятся динамически.
 *
 * Dash client-side renderer бросает ReferenceError для Input элементов,
 * которых нет в начальном DOM (multi-page app, динамический рендеринг).
 * clientside_callback + prevent_initial_call=True обходит эту проблему.
 */
window.dash_clientside = window.dash_clientside || {};

window.dash_clientside.triggers = {
    /**
     * Возвращает Date.now() при клике (timestamp trigger pattern).
     * Используется для: recon buttons (Calendar, Dashboard KPI).
     */
    timestamp_trigger: function(n_clicks) {
        if (!n_clicks) { return window.dash_clientside.no_update; }
        return Date.now();
    },

    /**
     * Открывает create-modal из пустого состояния таблиц.
     * Returns: [is_open=true, source="dashboard"]
     */
    open_create_modal: function(n_clicks) {
        if (!n_clicks) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        return [true, "dashboard"];
    },

    /**
     * Фокус на карточке цели из двери щитка (FR-3, протокол 0030).
     *
     * Единая механика идемпотентности Store-фокусов (RTM #90):
     * payload {"value": goal_id, "ts": ms}; применённый ts хранится в
     * узле goals-focus-anchor (children) — при том же ts (F5, повторная
     * отправка) фокус не переприменяется. Возврат в раздел по меню
     * колбэк не дёргает вовсе: Input — только сам Store.
     *
     * Карточки целей рендерятся асинхронно (goal-card-container
     * наполняется серверным колбэком) — ждём появления якоря
     * с ретраями, а не падаем на первом промахе.
     */
    apply_goal_focus: function(payload, appliedTs) {
        var nu = window.dash_clientside.no_update;
        if (!payload || !payload.ts || !payload.value) { return nu; }
        if (String(payload.ts) === String(appliedTs)) { return nu; }

        var attempts = 0;
        var tryFocus = function() {
            var el = document.getElementById("goal-card-" + payload.value);
            if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "center" });
                el.classList.add("goal-card-focused");
                setTimeout(function() {
                    el.classList.remove("goal-card-focused");
                }, 2500);
            } else if (attempts < 15) {
                attempts += 1;
                setTimeout(tryFocus, 200);
            }
        };
        tryFocus();
        return String(payload.ts);
    }
};
