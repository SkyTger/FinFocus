"""Тесты колбэка модала профиля — контракт входов и guard триггера.

Протоколы: 0028 (шаг 3.5-m-fix, шестерёнка через Store) и 0030
(кусок 2: сайдбар снят с дашборда — вход через аватар ТОЖЕ переведён
на Store, прямых Input на динамические элементы не осталось).

Регрессионная защита от дефекта, найденного на ревью 0028: элемент,
подключённый к колбэку прямым Input'ом, вне своей страницы в DOM
отсутствует, из-за чего клиентский рендерер Dash молча перестаёт
отправлять колбэк целиком — ломаются ВСЕ входы колбэка (ошибки в
консоль при этом не пишется). После куска 2 динамическими стали оба
входа: шестерёнка (рождается в dashboard-free-header) и аватар
(сайдбар живёт в sidebar-slot и на дашборде отсутствует).

Правильный паттерн проекта для динамических элементов — clientside
timestamp trigger + Store (см. assets/clientside_triggers.js).
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest
from dash.exceptions import PreventUpdate

from app import main as main_module
from app.components import dashboard as dashboard_module
from app.components.profile_modal import handle_profile_modal


def _decorator_source(func) -> str:
    """Исходник блока @callback(...) непосредственно перед функцией."""
    module_source = inspect.getsource(inspect.getmodule(func))
    decorator_block = module_source[: module_source.index(f"def {func.__name__}")]
    decorator_start = decorator_block.rfind("@callback(")
    return decorator_block[decorator_start:]


class TestProfileModalContract:
    """Контракт входов: шестерёнка — только через Store, не напрямую."""

    def test_cog_is_not_a_direct_input(self):
        """Прямого Input на динамическую шестерёнку быть не должно.

        Прямой Input на элемент, которого нет в начальном DOM, ломает
        колбэк на всех страницах, где элемента нет.
        """
        source = _decorator_source(handle_profile_modal)
        assert 'Input("dashboard-settings-cog"' not in source

    def test_store_trigger_is_declared(self):
        """Открытие из шестерёнки подключено через Store-триггер."""
        source = _decorator_source(handle_profile_modal)
        assert 'Input("open-profile-trigger", "data")' in source

    def test_sidebar_avatar_is_not_a_direct_input(self):
        """Прямого Input на аватар сайдбара быть не должно (протокол 0030).

        Сайдбар рендерится динамически в sidebar-slot и на дашборде
        отсутствует — прямой Input молча отключил бы колбэк на
        дашборде целиком, включая вход через шестерёнку (риск R1).
        """
        source = _decorator_source(handle_profile_modal)
        assert 'Input("sidebar-profile-container"' not in source

    def test_clientside_trigger_registered_for_sidebar_avatar(self):
        """Аватар сайдбара пишет в Store через clientside-триггер (main.py)."""
        source = inspect.getsource(main_module)
        assert 'Input("sidebar-profile-container", "n_clicks")' in source
        assert 'Output("open-profile-trigger", "data", allow_duplicate=True)' in source

    def test_clientside_trigger_registered_for_cog(self):
        """Шестерёнка пишет в Store через clientside-триггер."""
        source = inspect.getsource(dashboard_module)
        assert 'Output("open-profile-trigger", "data", allow_duplicate=True)' in source
        assert 'Input("dashboard-settings-cog", "n_clicks")' in source


class TestProfileModalTriggerGuard:
    """Поведение guard'а: пустой триггер не открывает модал."""

    @pytest.mark.parametrize("empty_value", [None, 0])
    def test_empty_trigger_does_not_open(self, empty_value):
        """Восстановленное пустое значение Store не открывает профиль.

        Store сохраняет значение между переходами по разделам, поэтому
        колбэк обязан отличать свежий клик от восстановления.
        """
        with patch("app.components.profile_modal.ctx") as mock_ctx:
            mock_ctx.triggered_id = "open-profile-trigger"
            with pytest.raises(PreventUpdate):
                handle_profile_modal(
                    cog_trigger=empty_value,
                    save_clicks=None,
                    cancel_clicks=None,
                    name_value=None,
                    avatar_value=None,
                )

    def test_fresh_trigger_opens_modal(self, db_session):
        """Непустой timestamp открывает модал с данными профиля."""
        with patch("app.components.profile_modal.ctx") as mock_ctx:
            mock_ctx.triggered_id = "open-profile-trigger"
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            with patch(
                "app.components.profile_modal.get_db_session",
                return_value=mock_session,
            ), patch("app.components.profile_modal.OnboardingService") as mock_service:
                mock_service.return_value.get_profile.return_value = {
                    "name": "Тест",
                    "avatar_id": "smile",
                }
                is_open, name, avatar, _ = handle_profile_modal(
                    cog_trigger=1234567890.0,
                    save_clicks=None,
                    cancel_clicks=None,
                    name_value=None,
                    avatar_value=None,
                )

        assert is_open is True
        assert name == "Тест"
        assert avatar == "smile"
