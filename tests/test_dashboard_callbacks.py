"""Тесты для callbacks в dashboard.py — подписки на profile-updated.

Протокол: 0026-onboarding-refresh, шаг 2.

Регрессионная защита подписок дашборда на event bus `profile-updated`:
приветствие, KPI/график/таблицы и баннер нулевого баланса должны
обновляться сразу после онбординга/правки профиля, без ручной
перезагрузки страницы.
"""

import inspect
from unittest.mock import MagicMock, patch

from dash.exceptions import PreventUpdate
import pytest

from app.components.dashboard import (
    load_dashboard_data,
    toggle_balance_toast,
    update_dashboard_greeting,
)
from app.models.database import User


class TestCallbackContracts:
    """Фиксация контракта: колбэки подписаны на profile-updated.

    Полноценная интроспекция Dash callback map в тестовой среде (без
    запущенного `Dash(__name__)` приложения и реального HTTP-запроса)
    нестабильна: `callback_context`/`ctx.triggered` недоступны вне
    запроса, а внутренний `dash.callback_map` ключуется по строке
    Output, собранной во время импорта модуля — хрупко привязываться
    к её точному формату. Поэтому вместо этого используется устойчивая
    альтернатива из спецификации: анализ исходного кода декоратора
    `@callback` через `inspect.getsource`, чтобы зафиксировать наличие
    `Input("profile-updated", "data")` в декораторе конкретной функции.
    Это не эмулирует Dash целиком, но защищает от потери подписки при
    рефакторинге.
    """

    def test_load_dashboard_data_subscribed_to_profile_updated(self):
        """load_dashboard_data содержит Input('profile-updated', 'data')."""
        # Декоратор идёт перед определением функции — достаём весь блок
        # исходников модуля, чтобы увидеть @callback(...) над функцией.
        module_source = inspect.getsource(inspect.getmodule(load_dashboard_data))
        decorator_block = module_source[
            : module_source.index("def load_dashboard_data")
        ]
        # Берём последний @callback перед определением функции.
        decorator_start = decorator_block.rfind("@callback(")
        decorator_source = decorator_block[decorator_start:]

        assert 'Input("profile-updated", "data")' in decorator_source

    def test_toggle_balance_toast_subscribed_to_profile_updated(self):
        """toggle_balance_toast содержит Input('profile-updated', 'data')."""
        module_source = inspect.getsource(inspect.getmodule(toggle_balance_toast))
        decorator_block = module_source[
            : module_source.index("def toggle_balance_toast")
        ]
        decorator_start = decorator_block.rfind("@callback(")
        decorator_source = decorator_block[decorator_start:]

        assert 'Input("profile-updated", "data")' in decorator_source

    def test_update_dashboard_greeting_signature(self):
        """update_dashboard_greeting принимает profile_updated и pathname."""
        signature = inspect.signature(update_dashboard_greeting)
        params = list(signature.parameters)

        assert params == ["profile_updated", "pathname"]


class TestUpdateDashboardGreeting:
    """Тесты колбэка update_dashboard_greeting."""

    def test_valid_profile_returns_greeting_with_name(self, db_session):
        """С валидным профилем в БД возвращает приветствие с именем."""
        user = User(
            email="greeting@example.com",
            name="Иван",
            starting_balance=10000,
        )
        db_session.add(user)
        db_session.commit()

        with patch("app.components.dashboard.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = update_dashboard_greeting(
                profile_updated=123456.0,
                pathname="/dashboard",
            )

        assert result == "Добро пожаловать, Иван!"

    def test_data_none_prevents_update(self, db_session):
        """profile_updated=None → PreventUpdate (событие ещё не наступало)."""
        with patch("app.components.dashboard.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(PreventUpdate):
                update_dashboard_greeting(
                    profile_updated=None,
                    pathname="/dashboard",
                )

    def test_wrong_pathname_prevents_update(self, db_session):
        """pathname не '/' и не '/dashboard' → PreventUpdate."""
        with patch("app.components.dashboard.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(PreventUpdate):
                update_dashboard_greeting(
                    profile_updated=123456.0,
                    pathname="/goals",
                )

    def test_root_pathname_is_allowed(self, db_session):
        """pathname='/' проходит guard так же, как '/dashboard'."""
        user = User(
            email="root@example.com",
            name="Мария",
            starting_balance=10000,
        )
        db_session.add(user)
        db_session.commit()

        with patch("app.components.dashboard.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = update_dashboard_greeting(
                profile_updated=1.0,
                pathname="/",
            )

        assert result == "Добро пожаловать, Мария!"

    def test_db_error_prevents_update(self, db_session):
        """Ошибка БД (например, пользователь не найден) → PreventUpdate."""
        # db_session пустая — get_profile подымет ValueError.
        with patch("app.components.dashboard.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=db_session)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(PreventUpdate):
                update_dashboard_greeting(
                    profile_updated=1.0,
                    pathname="/dashboard",
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
        """is_dismissed=True → баннер остаётся скрытым, БД не важна."""
        with patch("app.components.dashboard.ctx") as mock_ctx:
            mock_ctx.triggered_id = "profile-updated"

            result = toggle_balance_toast(
                pathname="/dashboard",
                is_open=False,
                profile_updated=123456.0,
                is_dismissed=True,
            )

        assert result is False
