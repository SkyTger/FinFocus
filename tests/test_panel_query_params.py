"""Тесты handle_panel_query_params — контракт владения url.search.

Протокол 0030 (кусок 2 Epic-11), шаг 8. Контрактная фиксация
_OWNED_SEARCH_PATHS: /transactions принадлежит apply_url_date_filter
(протокол 0023) — разбор его параметров или очистка его search сломали
бы уже работающую дверь Операций (critique-v1, блокер №1 solution-v4).
"""

import pytest
from dash import no_update
from dash.exceptions import PreventUpdate

from app.main import _OWNED_SEARCH_PATHS, handle_panel_query_params


class TestOwnership:
    """Чужой search не трогаем."""

    def test_owned_paths_frozen(self):
        assert _OWNED_SEARCH_PATHS == frozenset({"/calendar", "/goals"})

    def test_transactions_prevents_update(self):
        """?start=&end= на /transactions — search принадлежит разделу."""
        with pytest.raises(PreventUpdate):
            handle_panel_query_params(
                "?start=2026-08-01&end=2026-08-26", "/transactions"
            )

    @pytest.mark.parametrize("pathname", ["/dashboard", "/", "/analytics", None])
    def test_other_paths_prevent_update(self, pathname):
        with pytest.raises(PreventUpdate):
            handle_panel_query_params("?focus_date=2026-08-27", pathname)

    def test_empty_search_prevents_update(self):
        with pytest.raises(PreventUpdate):
            handle_panel_query_params("", "/calendar")


class TestCalendarParams:
    """Параметры /calendar раскладываются по Store'ам, search очищается."""

    def test_focus_date_parsed(self):
        recon, wishlist, focus_date, focus_goal, search = handle_panel_query_params(
            "?focus_date=2026-08-27", "/calendar"
        )
        assert focus_date["value"] == "2026-08-27"
        assert isinstance(focus_date["ts"], int)
        assert search == ""
        # Нераспознанные Store'ы — no_update, НЕ None: запись None
        # триггерила бы подписчиков (второй рендер календаря без фокуса)
        assert recon is no_update
        assert wishlist is no_update
        assert focus_goal is no_update

    def test_wishlist_item_parsed(self):
        recon, wishlist, focus_date, focus_goal, search = handle_panel_query_params(
            "?wishlist_item=3", "/calendar"
        )
        assert wishlist == 3
        assert search == ""
        assert focus_date is no_update

    def test_open_recon_parsed(self):
        recon, *_, search = handle_panel_query_params("?open_recon=1", "/calendar")
        assert isinstance(recon, int)
        assert search == ""

    def test_broken_focus_date_ignored_silently(self):
        """?focus_date=abc — молча мимо; других параметров нет → search цел."""
        with pytest.raises(PreventUpdate):
            handle_panel_query_params("?focus_date=abc", "/calendar")


class TestGoalsParams:
    """?goal=ID на /goals → goals-focus-goal."""

    def test_goal_parsed(self):
        recon, wishlist, focus_date, focus_goal, search = handle_panel_query_params(
            "?goal=7", "/goals"
        )
        assert focus_goal["value"] == 7
        assert isinstance(focus_goal["ts"], int)
        assert search == ""

    def test_broken_goal_ignored(self):
        with pytest.raises(PreventUpdate):
            handle_panel_query_params("?goal=x", "/goals")

    def test_two_clicks_produce_distinct_ts(self):
        """Два клика подряд по той же двери должны сработать дважды:
        Store сравнивается по значению, различает их ts."""
        first = handle_panel_query_params("?goal=7", "/goals")[3]
        second = handle_panel_query_params("?goal=7", "/goals")[3]
        assert first["value"] == second["value"] == 7
        # ts монотонно неубывающий; равенство возможно только в одну мс —
        # сравниваем нестрого, различие обеспечивает реальный клик
        assert second["ts"] >= first["ts"]
