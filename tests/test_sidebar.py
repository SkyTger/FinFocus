"""Тесты сайдбара — остаточные, до его удаления (шаг 9 протокола 0031).

ВНИМАНИЕ: сайдбар больше НЕ подключён к приложению. Куском 3
(протокол 0031, шаг 6) его место занял nav_rail, а слот-колбэк
переименован в render_nav_rail_slot. Здесь остались только проверки
самого модуля sidebar.py, который живёт мёртвым кодом до шага 9:
чистота create_sidebar и отсутствие в нём колбэков.

Проверки слот-колбэка и fail-open чтения профиля переехали в
tests/test_nav_rail.py — там они и есть действующий регрессионный
якорь. Этот файл удаляется вместе с sidebar.py на шаге 9.
"""

import inspect
import pytest

from app.components import sidebar as sidebar_module
from app.components.sidebar import create_sidebar
from app.config.avatars import get_avatar_emoji

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
