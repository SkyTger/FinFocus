"""Тесты для callbacks в dashboard.py — подписки на profile-updated.

Протокол: 0026-onboarding-refresh, шаг 2 (переработан после ревью 3-m).

Регрессионная защита подписок дашборда на event bus `profile-updated`:
щиток (шапка, график полос, таблицы) и баннер нулевого баланса должны
обновляться сразу после онбординга/правки профиля, без ручной
перезагрузки страницы.

Приветствие снято решением владельца п. 3г (протокол 0028): главное
место шапки отдано цифре «Свободно сегодня». Имя и аватар обновляются
первым Output'ом того же колбэка — шапкой, а не отдельным колбэком:
отдельный Output на элемент, существующий только на странице дашборда,
отклонён ещё в протоколе 0024 (риск ReferenceError на других страницах).
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from app.components.dashboard import (
    load_dashboard_data,
    toggle_balance_toast,
)
from app.models.database import User


def _decorator_source(func) -> str:
    """Исходник блока @callback(...) непосредственно перед функцией.

    Полноценная интроспекция Dash callback map в тестовой среде (без
    запущенного приложения и HTTP-запроса) нестабильна: callback map
    ключуется по строке Output, собранной при импорте, — хрупко
    привязываться к её формату. Анализ исходника декоратора — устойчивая
    альтернатива: фиксирует контракт (какие Input/Output объявлены),
    но НЕ проверяет поведение — поведенческие тесты ниже, по классам.
    """
    module_source = inspect.getsource(inspect.getmodule(func))
    decorator_block = module_source[: module_source.index(f"def {func.__name__}")]
    decorator_start = decorator_block.rfind("@callback(")
    return decorator_block[decorator_start:]


class TestCallbackContracts:
    """Фиксация контракта декораторов: подписки и целевые Output'ы.

    Это защита от синтаксической регрессии (Input/Output не потеряны
    при рефакторинге), а не поведенческое покрытие — см. _decorator_source.
    """

    def test_load_dashboard_data_decorator_declares_profile_updated_input(self):
        """Декоратор load_dashboard_data объявляет Input profile-updated."""
        assert 'Input("profile-updated", "data")' in _decorator_source(
            load_dashboard_data
        )

    def test_toggle_balance_toast_decorator_declares_profile_updated_input(self):
        """Декоратор toggle_balance_toast объявляет Input profile-updated."""
        assert 'Input("profile-updated", "data")' in _decorator_source(
            toggle_balance_toast
        )

    def test_load_dashboard_data_decorator_declares_header_output(self):
        """Декоратор load_dashboard_data объявляет Output шапки щитка.

        Имя и аватар обновляются первым Output'ом этого колбэка, НЕ
        отдельным колбэком (решение 0024/0026 — см. докстринг модуля).
        """
        assert 'Output("dashboard-free-header", "children")' in _decorator_source(
            load_dashboard_data
        )


class TestToggleBalanceToastProfileUpdated:
    """Тесты колбэка toggle_balance_toast с триггером profile-updated."""

    def test_balance_positive_hides_banner(self, db_session):
        """Ненулевой баланс в БД → баннер скрыт (False)."""
        user = User(
            email="balance@example.com",
            name="Пётр",
            starting_balance=5000,
        )
        db_session.add(user)
        db_session.commit()

        with patch("app.components.dashboard.ctx") as mock_ctx:
            mock_ctx.triggered_id = "profile-updated"

            with patch("app.components.dashboard.get_db_session") as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                result = toggle_balance_toast(
                    pathname="/dashboard",
                    is_open=True,
                    profile_updated=123456.0,
                    is_dismissed=False,
                )

        assert result is False

    def test_balance_zero_shows_banner(self, db_session):
        """Нулевой баланс в БД → баннер показан (True)."""
        user = User(
            email="zero-refresh@example.com",
            name="Анна",
            starting_balance=0,
        )
        db_session.add(user)
        db_session.commit()

        with patch("app.components.dashboard.ctx") as mock_ctx:
            mock_ctx.triggered_id = "profile-updated"

            with patch("app.components.dashboard.get_db_session") as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                result = toggle_balance_toast(
                    pathname="/dashboard",
                    is_open=False,
                    profile_updated=123456.0,
                    is_dismissed=False,
                )

        assert result is True

    def test_dismissed_keeps_banner_hidden(self, db_session):
        """is_dismissed=True → баннер скрыт, БД не опрашивается.

        Guard по is_dismissed стоит РАНЬШЕ обращения к БД (short-circuit);
        мок get_db_session здесь страхует тест от смены порядка guard'ов:
        если реализация начнёт ходить в БД до проверки dismissed, тест
        останется корректным, а не упадёт с невнятной ошибкой подключения.
        """
        with patch("app.components.dashboard.ctx") as mock_ctx:
            mock_ctx.triggered_id = "profile-updated"

            with patch("app.components.dashboard.get_db_session") as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                result = toggle_balance_toast(
                    pathname="/dashboard",
                    is_open=False,
                    profile_updated=123456.0,
                    is_dismissed=True,
                )

        assert result is False


class TestLoadDashboardDataProfile:
    """Интеграция профиля в load_dashboard_data (шапка щитка)."""

    def test_returns_three_values_with_profile_name_in_header(self, db_session):
        """Успешная загрузка возвращает 3 значения; имя профиля — в шапке.

        Было 5 Output'ов (шапка, график, recent, upcoming, подушка);
        протокол 0030 заменил split-таблицы и readonly-подушку рядом
        карточек-дверей: (шапка, график, cards_row).
        """
        user = User(
            email="seven@example.com",
            name="Ольга",
            starting_balance=10000,
        )
        db_session.add(user)
        db_session.commit()

        with patch("app.components.dashboard.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = load_dashboard_data(
                pathname="/dashboard",
                profile_updated=123456.0,
                period_state={"period": "month"},
            )

        assert len(result) == 3
        # Имя профиля попадает в шапку — первый Output
        assert "Ольга" in str(result[0])

    def test_wrong_pathname_prevents_update(self, db_session):
        """pathname вне дашборда → PreventUpdate (guard до работы с БД)."""
        from dash.exceptions import PreventUpdate

        with pytest.raises(PreventUpdate):
            load_dashboard_data(
                pathname="/goals",
                profile_updated=123456.0,
                period_state={"period": "month"},
            )
