"""Тесты сайдбара — Подход B протокола 0030 (кусок 2 Epic-11).

До этого протокола сайдбар не был покрыт НИЧЕМ — именно поэтому
регрессия профиля (0028, шаг 3.5-m-fix) не ловилась тестами. Здесь
фиксируются: контракт входов render_sidebar_slot (ни одного Input на
элемент сайдбара — класс регрессий C-6), чистота create_sidebar
(профиль и подсветка на построении), отсутствие серверных колбэков
в модуле sidebar (регрессионный якорь против их возврата), fail-open
чтения профиля (навигация важнее имени).
"""

import inspect
from unittest.mock import patch

import pytest

from app import main as main_module
from app.components import sidebar as sidebar_module
from app.components.sidebar import create_sidebar
from app.config.avatars import get_avatar_emoji
from app.main import render_sidebar_slot

PROFILE = {"name": "Никита", "avatar_id": "rocket"}


def iter_tree(component):
    """Рекурсивный обход дерева Dash-компонентов (включая строки-листья)."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        yield from iter_tree(child)


def joined_text(component) -> str:
    """Все тексты дерева одной строкой."""
    return " | ".join(node for node in iter_tree(component) if isinstance(node, str))


def all_classes(component) -> str:
    """Все className дерева одной строкой."""
    return " ".join(
        getattr(node, "className", "") or "" for node in iter_tree(component)
    )


def _decorator_source(func) -> str:
    """Исходник блока @callback(...) непосредственно перед функцией."""
    module_source = inspect.getsource(inspect.getmodule(func))
    decorator_block = module_source[: module_source.index(f"def {func.__name__}")]
    decorator_start = decorator_block.rfind("@callback(")
    return decorator_block[decorator_start:]


class TestRenderSidebarSlotContract:
    """Контракт входов: только всегда присутствующие url и profile-updated."""

    def test_exactly_two_inputs_on_global_elements(self):
        source = _decorator_source(render_sidebar_slot)
        assert 'Input("url", "pathname")' in source
        assert 'Input("profile-updated", "data")' in source
        assert source.count("Input(") == 2

    def test_no_inputs_on_sidebar_elements(self):
        """Ни одного Input/Output на условно присутствующие узлы сайдбара."""
        source = _decorator_source(render_sidebar_slot)
        for element in (
            "sidebar-nav",
            "sidebar-profile-name",
            "sidebar-profile-avatar",
            "sidebar-profile-container",
        ):
            assert element not in source

    def test_dashboard_returns_empty_before_session(self):
        """На дашборде — [] БЕЗ открытия сессии (стратегия загрузки)."""
        with patch("app.main.get_db_session") as mock_session:
            for pathname in (None, "/", "/dashboard"):
                assert render_sidebar_slot(pathname, None) == []
            mock_session.assert_not_called()


class TestNoCallbacksInSidebarModule:
    """Регрессионный якорь: в модуле sidebar нет ни одного @callback.

    Оба прежних колбэка (highlight_active_sidebar, update_sidebar_profile)
    удалены Подходом B: их Output'ы стали бы условно присутствующими, а
    запись children в узлы, которые render_sidebar_slot одновременно
    создаёт/удаляет, — гонка. Возврат любого колбэка в модуль — регрессия.
    """

    def test_no_callback_decorators(self):
        source = inspect.getsource(sidebar_module)
        assert "@callback" not in source

    def test_old_callbacks_gone(self):
        assert not hasattr(sidebar_module, "highlight_active_sidebar")
        assert not hasattr(sidebar_module, "update_sidebar_profile")


class TestCreateSidebarPure:
    """create_sidebar — чистая функция от (pathname, profile)."""

    def test_profile_name_and_emoji_in_tree(self):
        tree = create_sidebar("/calendar", PROFILE)
        text = joined_text(tree)
        assert "Никита" in text
        assert get_avatar_emoji("rocket") in text
        # Литералов-заглушек в дереве нет
        assert "Пользователь" not in text

    @pytest.mark.parametrize(
        "pathname,label",
        [
            ("/calendar", "Календарь"),
            ("/transactions", "Операции"),
            ("/analytics", "Аналитика"),
            ("/goals", "Цели"),
        ],
    )
    def test_active_item_highlighted(self, pathname, label):
        tree = create_sidebar(pathname, PROFILE)
        active_nodes = [
            node
            for node in iter_tree(tree)
            if "sidebar-nav-item-active" in (getattr(node, "className", "") or "")
        ]
        assert len(active_nodes) == 1
        assert label in joined_text(active_nodes[0])

    def test_no_db_access_on_build(self):
        """Чистота: построение не открывает сессий (их в модуле нет)."""
        source = inspect.getsource(sidebar_module)
        assert "get_db_session" not in source


class TestFailOpenProfile:
    """Сбой чтения профиля не лишает пользователя навигации (FR-2)."""

    def test_failing_profile_keeps_navigation(self):
        with patch.object(
            main_module.OnboardingService,
            "get_profile",
            side_effect=RuntimeError("db unavailable"),
        ):
            tree = render_sidebar_slot("/calendar", None)

        text = joined_text(tree)
        # Все пять пунктов меню на месте
        for label in ("Дашборд", "Календарь", "Операции", "Аналитика", "Цели"):
            assert label in text
        # Профиль-заглушка вместо падения
        assert "Пользователь" in text
