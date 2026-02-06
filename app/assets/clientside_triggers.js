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
    }
};
