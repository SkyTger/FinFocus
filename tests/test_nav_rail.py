"""Тесты полоски-меню (Epic-11, кусок 3, протокол 0031).

Действующий регрессионный якорь навигации — перенял роль у
tests/test_sidebar.py, который после шага 6 покрывает только мёртвый
модуль sidebar.py и удаляется вместе с ним на шаге 9.

Фиксируются: контракт входов render_nav_rail_slot (ни одного Input на
элемент полоски — класс регрессий C-6), чистота create_nav_rail
(профиль и подсветка на построении, без БД), отсутствие серверных
колбэков в модуле nav_rail, fail-open чтения профиля, предпосылки
механизма реконсиляции (см. докстринг TestNavRailStructureStable),
доступность и единственный вход в профиль.

ЧЕГО ЗДЕСЬ НЕТ (урок протокола 0029): визуальный слой — геометрия,
язычки, анимация разворота — здесь не покрыт: в этом файле проверяется
Python-слой полоски.

Долг закрыт отдельным файлом — tests/test_nav_rail_visual.py: он
держит САМ CSS (геометрию, отсутствие обрезки у кожуха, fill-mode
анимации, reduced-motion, чужие токены) якорными тестами по тексту
правил. Оговорка при этом остаётся в силе: сам факт, что разворот
сыграл при входе с дашборда и НЕ переигрался при переходе
раздел→раздел, подтверждается только живой проверкой (шаг 1 и шаг 8
протокола) — зелёный прогон обоих файлов не означает, что AC-5
выполнен.
"""

import inspect
from unittest.mock import patch

import pytest
from dash import html

from app.components import nav_rail as nav_rail_module
from app.components.nav_rail import RAIL_SECTIONS, create_nav_rail
from app.main import render_nav_rail_slot

PROFILE = {"name": "Николай", "avatar_id": "cat"}

# Маршруты, которые реально обслуживает display_page (app/main.py).
DISPLAY_PAGE_ROUTES = {
    "/dashboard",
    "/calendar",
    "/goals",
    "/transactions",
    "/analytics",
}

DASHBOARD_PATHS = (None, "/", "/dashboard")
SECTION_PATHS = ("/calendar", "/transactions", "/analytics", "/goals")


def _decorator_source(func) -> str:
    """Исходник блока @callback(...) непосредственно перед функцией."""
    module_source = inspect.getsource(inspect.getmodule(func))
    decorator_block = module_source[: module_source.index(f"def {func.__name__}")]
    decorator_start = decorator_block.rfind("@callback(")
    return decorator_block[decorator_start:]


def _iter_tree(component):
    """Обход дерева Dash-компонентов."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if hasattr(child, "_prop_names"):
            yield from _iter_tree(child)
        else:
            yield child


def _joined_text(component) -> str:
    """Все строковые узлы дерева одной строкой."""
    return " | ".join(node for node in _iter_tree(component) if isinstance(node, str))


def _links(component) -> list:
    """Все dcc.Link дерева."""
    return [node for node in _iter_tree(component) if type(node).__name__ == "Link"]


def _find_by_id(component, element_id):
    """Первый узел с указанным id."""
    for node in _iter_tree(component):
        if getattr(node, "id", None) == element_id:
            return node
    return None


class TestRenderNavRailSlotContract:
    """Контракт входов слот-колбэка (класс регрессий C-6)."""

    def test_exactly_two_inputs_on_global_elements(self):
        """Ровно два Input'а — на url и profile-updated."""
        source = _decorator_source(render_nav_rail_slot)

        assert source.count("Input(") == 2
        assert 'Input("url", "pathname")' in source
        assert 'Input("profile-updated", "data")' in source

    def test_no_inputs_on_nav_rail_elements(self):
        """В декораторе не упомянут ни один узел самой полоски.

        Input на условно присутствующий элемент заставляет клиентский
        рендерер Dash молча не отправлять колбэк целиком — без ошибки
        в консоли (протоколы 0026, 0028, 0030).
        """
        source = _decorator_source(render_nav_rail_slot)

        assert 'Input("nav-rail' not in source
        assert 'Input("sidebar' not in source

    @pytest.mark.parametrize("pathname", DASHBOARD_PATHS)
    def test_dashboard_returns_empty_before_session(self, pathname):
        """На дашбордных путях — [] и НИ ОДНОГО обращения к БД."""
        with patch("app.main.get_db_session") as mock_session:
            assert render_nav_rail_slot(pathname, None) == []
            mock_session.assert_not_called()


class TestNoCallbacksInNavRailModule:
    """Регрессионный якорь C-1/AC-11: модуль полоски без колбэков.

    Колбэк с Output на узел полоски был бы гонкой с
    render_nav_rail_slot, который этот же узел создаёт и удаляет:
    порядок применения Output'ов Dash не гарантирует.
    """

    def test_no_callback_decorators(self):
        source = inspect.getsource(nav_rail_module)

        # Слово встречается в докстринге модуля как формулировка
        # инварианта — считаем именно декораторы (строка в начале
        # строки, без отступа комментария).
        decorators = [
            line
            for line in source.splitlines()
            if line.lstrip().startswith("@callback")
        ]
        assert decorators == []

    def test_old_sidebar_callbacks_gone(self):
        """Функций удалённых колбэков сайдбара в модуле нет."""
        for name in (
            "create_sidebar",
            "highlight_active_sidebar",
            "update_sidebar_profile",
        ):
            assert not hasattr(nav_rail_module, name)


class TestCreateNavRailPure:
    """create_nav_rail — чистая функция от (pathname, profile)."""

    def test_avatar_emoji_in_tree(self):
        """Эмодзи аватара берётся из профиля-аргумента."""
        from app.config.avatars import get_avatar_emoji

        tree = create_nav_rail("/calendar", PROFILE)

        assert get_avatar_emoji(PROFILE["avatar_id"]) in _joined_text(tree)

    @pytest.mark.parametrize("pathname", SECTION_PATHS)
    def test_exactly_one_active_slot(self, pathname):
        """На каждом разделе подсвечен ровно один слот — его собственный."""
        tree = create_nav_rail(pathname, PROFILE)

        active = [
            link
            for link in _links(tree)
            if "nav-rail-slot--active" in (link.className or "")
        ]
        assert len(active) == 1
        assert active[0].href == pathname

    @pytest.mark.parametrize("pathname", DASHBOARD_PATHS)
    def test_no_active_slot_on_dashboard_paths(self, pathname):
        """Дашборда среди разделов нет — активных слотов ноль."""
        tree = create_nav_rail(pathname, PROFILE)

        active = [
            link
            for link in _links(tree)
            if "nav-rail-slot--active" in (link.className or "")
        ]
        assert active == []

    def test_no_db_access_on_build(self):
        """NFR-1: в модуле нет обращений к БД."""
        source = inspect.getsource(nav_rail_module)

        assert "get_db_session" not in source
        assert "Service(" not in source

    def test_settings_and_version_absent(self):
        """FR-4/FR-5/AC-9: ни «Настроек», ни /settings, ни версии."""
        tree = create_nav_rail("/calendar", PROFILE)

        text = _joined_text(tree)
        assert "Настройки" not in text
        assert "v1.0.0" not in text
        assert all(link.href != "/settings" for link in _links(tree))

    def test_all_hrefs_are_real_routes(self):
        """FR-4: из навигации нельзя попасть на несуществующий маршрут.

        Именно так «Настройки» вели на 404 (P1 UX-аудита 2026-08-20).
        """
        tree = create_nav_rail("/calendar", PROFILE)

        hrefs = {link.href for link in _links(tree)}
        unknown = hrefs - DISPLAY_PAGE_ROUTES
        assert not unknown, f"вне маршрутов display_page: {unknown}"

    def test_four_sections(self):
        """Ровно четыре раздела; дашборд среди них не числится."""
        assert len(RAIL_SECTIONS) == 4
        assert all(section["href"] != "/dashboard" for section in RAIL_SECTIONS)


class TestFailOpenProfile:
    """Сбой чтения профиля не должен уносить навигацию."""

    def test_failing_profile_keeps_navigation(self):
        """Профиль не прочитался → полоска рисуется с заглушкой.

        Находимость разделов важнее аватара: без навигации
        пользователь заперт на странице.
        """
        with patch("app.main.get_db_session", side_effect=RuntimeError("БД упала")):
            tree = render_nav_rail_slot("/calendar", None)

        hrefs = {link.href for link in _links(tree)}
        assert hrefs == DISPLAY_PAGE_ROUTES


class TestNavRailStructureStable:
    """ПРЕДПОСЫЛКИ механизма реконсиляции — не сам механизм.

    Здесь фиксируется только то, что проверяемо статически:
    стабильный React-ключ (через id), единственность ребёнка слота
    (стабильная позиция), отсутствие серверных колбэков на узлах
    полоски, отсутствие пропа key.

    САМ разворот и то, что он не переигрывается при переходах
    раздел→раздел, эти тесты НЕ проверяют и проверить не могут:
    реконсиляция происходит в браузере. Она подтверждена живой
    пробой (шаг 1 протокола) и проверяется живьём на шаге 8.
    Зелёный прогон этого класса не означает выполнения AC-5.
    """

    @pytest.mark.parametrize(
        "pathname", (None, "/", "/calendar", "/transactions", "/analytics", "/goals")
    )
    def test_root_is_div_with_stable_id(self, pathname):
        """Корень — html.Div с id="nav-rail" при любом pathname."""
        tree = create_nav_rail(pathname, PROFILE)

        assert isinstance(tree, html.Div)
        assert tree.id == "nav-rail"

    @pytest.mark.parametrize("pathname", SECTION_PATHS)
    def test_slot_returns_single_component_not_list(self, pathname):
        """Слот отдаёт РОВНО ОДИН компонент, не список.

        Единственный ребёнок держит позицию узла стабильной. Обернуть
        возврат в список — сломать реконсиляцию молча: визуально всё
        останется на месте, поедет только анимация разворота.
        """
        with patch("app.main.get_db_session"), patch(
            "app.main.OnboardingService"
        ) as service:
            service.return_value.get_profile.return_value = PROFILE
            result = render_nav_rail_slot(pathname, None)

        assert not isinstance(result, list)
        assert getattr(result, "id", None) == "nav-rail"

    def test_no_server_callback_targets_nav_rail_nodes(self):
        """Ни один СЕРВЕРНЫЙ колбэк не смотрит на узлы полоски.

        Единственное разрешённое упоминание — clientside-триггер
        аватара в main.py (он и проверяется отдельно ниже).
        """
        import app.main as main_module

        source = inspect.getsource(main_module)

        # Единственное легитимное упоминание аватара — clientside-триггер.
        # Всё остальное упоминание узлов полоски должно приходиться на
        # слот-колбэк (Output "nav-rail-slot"), а не на сами узлы.
        assert source.count('Input("nav-rail-avatar", "n_clicks")') == 1
        assert 'Input("nav-rail", ' not in source
        assert 'Output("nav-rail", ' not in source
        assert 'Output("nav-rail-avatar"' not in source

    def test_key_prop_not_used(self):
        """Проп key не ставится: ключ берётся из id, а dcc.Link key не принимает."""
        source = inspect.getsource(nav_rail_module)

        assert "key=" not in source


class TestNavRailAccessibility:
    """Доступность: имена элементов и пометка текущей страницы."""

    def test_every_link_has_accessible_name(self):
        """У логотипа и всех четырёх слотов непустое доступное имя.

        Имя даётся через title, а не aria-label: dcc.Link 2.17.1
        имеет закрытый список пропсов и на aria-* бросает TypeError
        (проверено на построении, шаг 5). title — валидное доступное
        имя по HTML-спецификации.
        """
        tree = create_nav_rail("/calendar", PROFILE)

        links = _links(tree)
        assert len(links) == 5  # домик + четыре раздела
        for link in links:
            assert link.title, f"без доступного имени: {link.href}"

    @pytest.mark.parametrize("pathname", SECTION_PATHS)
    def test_avatar_has_accessible_name_and_role(self, pathname):
        """Аватар — html.Div, поэтому aria-атрибуты ему доступны.

        Параметризован по всем разделам (AC-7).
        """
        tree = create_nav_rail(pathname, PROFILE)

        avatar = _find_by_id(tree, "nav-rail-avatar")
        props = avatar.to_plotly_json()["props"]
        assert props.get("aria-label")
        assert props.get("role") == "button"

    @pytest.mark.parametrize("pathname", SECTION_PATHS)
    def test_avatar_is_keyboard_reachable(self, pathname):
        """Аватар обходится по Tab — иначе в профиль не попасть с клавиатуры.

        Аватар — html.Div, а не ссылка или кнопка: без явного
        tabIndex он выпадает из обхода целиком (поймано живой
        проверкой на шаге 11).

        Параметризован по всем разделам (AC-7).
        """
        tree = create_nav_rail(pathname, PROFILE)

        avatar = _find_by_id(tree, "nav-rail-avatar")
        assert avatar.tabIndex == 0

    def test_keyboard_activation_handler_exists(self):
        """Enter/Space на аватаре превращаются в клик.

        От элемента с role="button" этого ждут; у html.Div нативной
        клавиатурной активации нет.
        """
        import pathlib

        handler = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app"
            / "assets"
            / "nav_rail_keyboard.js"
        )
        source = handler.read_text(encoding="utf-8")

        assert "nav-rail-avatar" in source
        assert "Enter" in source
        assert ".click()" in source

    @pytest.mark.parametrize("pathname", SECTION_PATHS)
    def test_avatar_has_profile_tip(self, pathname):
        """У аватара свой язычок «Профиль» на каждом разделе (AC-7)."""
        tree = create_nav_rail(pathname, PROFILE)

        avatar = _find_by_id(tree, "nav-rail-avatar")
        assert "Профиль" in _joined_text(avatar)

    def test_every_section_has_tip_with_its_label(self):
        """Язычок каждого раздела несёт его подпись."""
        tree = create_nav_rail("/calendar", PROFILE)

        text = _joined_text(tree)
        for section in RAIL_SECTIONS:
            assert section["label"] in text


class TestNavRailProfileEntry:
    """Единственный вход в профиль — Store-триггер (инвариант 3)."""

    @pytest.mark.parametrize("pathname", SECTION_PATHS)
    def test_avatar_node_is_clickable(self, pathname):
        """В дереве есть nav-rail-avatar с n_clicks.

        Параметризован по всем разделам: AC-7 требует, чтобы вход в
        профиль проверялся «на каждом из разделов, а не на одном».
        """
        tree = create_nav_rail(pathname, PROFILE)

        avatar = _find_by_id(tree, "nav-rail-avatar")
        assert avatar is not None
        assert avatar.n_clicks == 0

    def test_main_registers_clientside_trigger_on_avatar(self):
        """main.py вешает clientside-триггер именно на аватар полоски."""
        import app.main as main_module

        source = inspect.getsource(main_module)

        assert 'Input("nav-rail-avatar", "n_clicks")' in source
        assert 'Output("open-profile-trigger", "data", allow_duplicate=True)' in source

    def test_no_server_input_on_avatar(self):
        """C-3: серверного Input на аватар нет — только clientside.

        Прямой серверный Input молча отключил бы колбэк профиля на
        дашборде, где полоски нет, вместе со вторым входом —
        шестерёнкой щитка (регрессия 0028, шаг 3.5-m-fix).
        """
        from app.components import profile_modal

        source = inspect.getsource(profile_modal)

        assert "nav-rail-avatar" not in source
        assert 'Input("open-profile-trigger", "data")' in source


class TestRailIcons:
    """Иконки разделов существуют в Bootstrap Icons."""

    # Имена, которых в Bootstrap Icons НЕТ, хотя они кажутся
    # очевидными. Пойманы живой проверкой: bi-target достался
    # полоске по наследству от сайдбара и не отрисовывался вовсе
    # (`content: none`) — в сайдбаре это скрывала подпись рядом,
    # в полоске 60px слот превращался в пустой кружок.
    NONEXISTENT_ICONS = frozenset(
        {"bi-target", "bi-crosshair", "bi-home", "bi-settings", "bi-chart"}
    )

    def test_no_nonexistent_icon_names(self):
        """Ни один раздел не использует несуществующее имя иконки.

        Полноценная проверка требует шрифта Bootstrap Icons (грузится
        с CDN), поэтому здесь — якорь на известные ловушки. Живая
        проверка: `getComputedStyle(el, '::before').content !== 'none'`.
        """
        for section in RAIL_SECTIONS:
            assert (
                section["icon"] not in self.NONEXISTENT_ICONS
            ), f"иконки {section['icon']!r} не существует — слот будет пустым"

    def test_every_section_has_bootstrap_icon(self):
        """У каждого раздела задана иконка в формате Bootstrap Icons."""
        for section in RAIL_SECTIONS:
            assert section["icon"].startswith("bi-")

    def test_icons_are_unique(self):
        """Иконки разделов не повторяются — иначе слоты неразличимы."""
        icons = [section["icon"] for section in RAIL_SECTIONS]
        assert len(icons) == len(set(icons))


class TestSidebarRetired:
    """Сайдбар свёрнут до надгробия (шаг 9 протокола 0031)."""

    def test_sidebar_module_has_only_the_constant(self):
        """От модуля остались докстринг-надгробие и ADDITIONAL_NAV_ITEMS.

        Файл сохранён намеренно, а не удалён: решение владельца Р2
        (2026-08-27) — константа остаётся. Прецедент «решение владельца
        можно обойти удачной трактовкой» дороже почти пустого файла.
        """
        from app.components import sidebar as sidebar_module

        public = [name for name in vars(sidebar_module) if not name.startswith("__")]
        assert public == ["ADDITIONAL_NAV_ITEMS"]

    def test_removed_sidebar_functions_are_gone(self):
        """create_sidebar и её помощники удалены отовсюду."""
        from app.components import sidebar as sidebar_module
        import app.components as components_package

        for name in ("create_sidebar", "_build_nav_links", "MAIN_NAV_ITEMS"):
            assert not hasattr(sidebar_module, name)

        # И реэкспорт из пакета снят — иначе импорт пакета упал бы.
        assert not hasattr(components_package, "create_sidebar")
        assert "create_sidebar" not in components_package.__all__

    def test_constant_is_not_imported_anywhere(self):
        """ADDITIONAL_NAV_ITEMS сейчас никем не импортируется.

        Она ждёт появления реальных маршрутов /settings и /help:
        пункт «Настройки» вёл на 404 (P1 UX-аудита, FR-4).
        """
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        importers = []
        for path in list((root / "app").rglob("*.py")) + list(
            (root / "tests").rglob("*.py")
        ):
            if path.name in ("sidebar.py", "test_nav_rail.py"):
                continue
            if "ADDITIONAL_NAV_ITEMS" in path.read_text(encoding="utf-8"):
                importers.append(str(path.relative_to(root)))

        assert not importers, f"константу кто-то использует: {importers}"

    def test_sidebar_css_and_classes_gone(self):
        """CSS сайдбара удалён, классов .sidebar-* в стилях не осталось."""
        import pathlib

        assets = pathlib.Path(__file__).resolve().parent.parent / "app" / "assets"

        assert not (assets / "sidebar.css").exists()

        for css in assets.glob("*.css"):
            for lineno, line in enumerate(
                css.read_text(encoding="utf-8").splitlines(), start=1
            ):
                stripped = line.strip()
                # Комментарии со ссылкой на прежний сайдбар — законны.
                if stripped.startswith(("*", "/*")):
                    continue
                assert ".sidebar-" not in line, f"{css.name}:{lineno}: {stripped}"
