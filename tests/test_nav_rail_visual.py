"""Тесты визуального слоя полоски-меню (долг куска 3, протокол 0031).

Закрывают долг, зафиксированный при мерже PR #31: геометрия, язычки
подписей и анимация разворота проверялись только вживую. Тот же вид
долга кусок 1 закрывал протоколом 0029 (tests/test_dashboard_panel_ui.py).

ЧТО ЗДЕСЬ ПРОВЕРЯЕТСЯ И ПОЧЕМУ ИМЕННО ТАК
------------------------------------------
У щитка (кусок 1) визуальный слой — чистые build-функции на Python,
их можно вызвать и осмотреть дерево. У полоски он другой: разметка
тривиальна и уже покрыта tests/test_nav_rail.py, а всё поведение
живёт в CSS. Поэтому здесь проверяется САМ CSS как текст.

Это тесты-якоря, а не тесты рендеринга. Они ловят класс регрессий
«правку сделали, эффекта не заметили»: CSS не падает и не логирует
ошибок — сломанное правило просто молча перестаёт работать, а
внешне полоска остаётся на месте. Каждый тест ниже привязан к
конкретному разрушению, названному в комментариях самого CSS.

ЧЕГО ЗДЕСЬ НЕТ (осознанно, не забыто)
-------------------------------------
Проверки РЕАЛЬНОГО рендеринга: что язычок действительно всплыл,
что разворот сыграл ровно один раз, что 44px на экране — это 44px.
Для этого нужен браузер (Playwright/Selenium), а в проекте нет ни
одной браузерной зависимости (requirements-dev.txt: pytest, pytest-cov,
black, flake8). Тянуть браузер в CI ради непблокирующего долга —
цена выше пользы; решение это за владельцем, не за тестами.

Поэтому зелёный прогон этого файла НЕ означает, что AC-5 (разворот
играет при входе с дашборда и не переигрывает при переходах между
разделами) выполнен: сам факт проигрывания анимации подтверждается
только живой проверкой, как и было на приёмке протокола. Здесь
зафиксированы ПРЕДПОСЫЛКИ этого механизма — то, что можно сломать
правкой CSS, не приходя в браузер.

Парсер CSS не используется по той же причине (нет tinycss2 и
добавлять его ради долга избыточно): правила ищутся по тексту,
поэтому хелперы ниже аккуратно вырезают комментарии — иначе тест
поймал бы упоминание свойства в пояснении и прошёл бы впустую.
"""

import ast
import pathlib
import re

import pytest

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "app" / "assets"
NAV_RAIL_CSS = ASSETS / "nav_rail.css"


# ===========================================================================
# Хелперы: работа с CSS как с текстом
# ===========================================================================


def read_css(path: pathlib.Path = NAV_RAIL_CSS) -> str:
    """Содержимое CSS-файла."""
    return path.read_text(encoding="utf-8")


def strip_comments(css: str) -> str:
    """CSS без /* ... */.

    Обязательный шаг: в nav_rail.css комментарии подробные и прямо
    цитируют свойства, которых в правилах быть не должно (например
    «НЕТ overflow: hidden»). Без вырезания комментариев тест на
    отсутствие свойства нашёл бы его в пояснении и дал ложный
    результат — в обе стороны.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def rule_body(css: str, selector: str) -> str:
    """Тело правила для точного селектора (без комментариев).

    Селектор ищется целиком: у `.nav-rail` и `.nav-rail-inner` общий
    префикс, и наивный поиск подстроки вернул бы не то правило.
    Собираются ВСЕ вхождения — свойства одного селектора в этом файле
    намеренно разнесены (`.nav-rail-inner` объявлен и в секции 3, и в
    секции 10 — раскладка отдельно, анимация отдельно).
    """
    clean = strip_comments(css)
    pattern = re.compile(
        r"(?:^|[},])\s*" + re.escape(selector) + r"\s*\{(.*?)\}",
        flags=re.DOTALL | re.MULTILINE,
    )
    bodies = [m.group(1) for m in pattern.finditer(clean)]
    assert bodies, f"правило {selector} не найдено в nav_rail.css"
    return "\n".join(bodies)


def declared_vars(body: str) -> set[str]:
    """Имена CSS-переменных, ОБЪЯВЛЕННЫХ в теле правила."""
    return set(re.findall(r"(--[\w-]+)\s*:", body))


def used_vars(css_fragment: str) -> set[str]:
    """Имена CSS-переменных, ИСПОЛЬЗОВАННЫХ через var()."""
    return set(re.findall(r"var\(\s*(--[\w-]+)", css_fragment))


# ===========================================================================
# Геометрия и цепочка наследования переменных
# ===========================================================================


class TestRailGeometry:
    """Геометрия полоски и цепочка, по которой её переменные доезжают.

    Разрушение, от которого страхуют тесты: локальные --rail-*
    объявлены на .nav-rail-column, а используются потомками. CSS-
    переменные наследуются ВНИЗ по дереву и не поднимаются вверх —
    перенос объявления на кожух схлопнул бы высоту колонки в auto,
    а вместе с ней распорку и прижатие аватара к низу. Об этот
    порядок протокол уже спотыкался (комментарий в секции 1 CSS).
    """

    def test_local_vars_declared_on_column_not_on_shell(self):
        """--rail-* объявлены на колонке — предке всех потребителей."""
        css = read_css()
        column = declared_vars(rule_body(css, ".nav-rail-column"))

        assert {"--rail-w", "--rail-h", "--rail-slot"} <= column, (
            "--rail-* должны объявляться на .nav-rail-column: "
            f"объявлено {sorted(column)}"
        )

        # На кожухе их быть не должно: оттуда они не видны колонке.
        assert not declared_vars(rule_body(css, ".nav-rail")) & {
            "--rail-w",
            "--rail-h",
            "--rail-slot",
        }, "--rail-* объявлены на .nav-rail — колонка их не увидит"

    def test_column_is_60px_wide_and_fixed(self):
        """Ширина 60px и она не сжимается флексом."""
        body = rule_body(read_css(), ".nav-rail-column")

        assert "--rail-w: 60px" in body, "ширина полоски должна быть 60px"
        # flex-basis + width + min-width: колонка не должна ужиматься
        # соседним контентом, иначе иконки наедут друг на друга.
        for prop in ("flex:", "width:", "min-width:"):
            assert prop in body, f"у колонки нет {prop} — она сожмётся"

    def test_slot_is_44px_touch_target(self):
        """Слот 44×44 — минимум по WCAG 2.5.5 Target Size.

        Знак внутри 22px, но нажимаемая зона должна быть все 44px
        (докстринг _build_section_slot). Уменьшение слота — доступность
        ломается молча: визуально ничего не меняется.
        """
        css = read_css()
        assert "--rail-slot: 44px" in rule_body(css, ".nav-rail-column")

        slot = rule_body(css, ".nav-rail-slot")
        assert "var(--rail-slot" in slot, "слот должен брать размер из --rail-slot"

    @pytest.mark.parametrize(
        "selector",
        [".nav-rail", ".nav-rail-inner"],
    )
    def test_height_chain_unbroken(self, selector):
        """height задана и у кожуха, и у inner.

        Без неё процентная высота ребёнка вырождается в auto,
        .nav-rail-spacer перестаёт растягиваться, и аватар уезжает
        вверх вместо низа полоски (комментарий в секции 2 CSS).
        """
        assert "height:" in rule_body(read_css(), selector), (
            f"у {selector} нет height — распорка перестанет работать, "
            "аватар уедет вверх"
        )

    def test_spacer_grows(self):
        """Распорка растягивается — именно она прижимает аватар к низу."""
        body = rule_body(read_css(), ".nav-rail-spacer")
        assert re.search(r"flex:\s*1", body), (
            "распорка должна растягиваться (flex: 1 ...), иначе аватар "
            "не прижмётся к низу"
        )


# ===========================================================================
# Видимость колонки
# ===========================================================================


class TestColumnVisibility:
    """Колонку скрывает РОВНО ОДНО правило — :empty.

    Инвариант 2 модуля: второй механизм (переключение className из
    колбэка) не вводить. Два источника правды о видимости разъезжаются
    — тот же класс дефектов, из-за которого в куске 2 у сайдбара
    убрали колбэк подсветки.
    """

    def test_empty_column_is_hidden(self):
        """.nav-rail-column:empty { display: none } на месте."""
        body = rule_body(read_css(), ".nav-rail-column:empty")
        assert "display: none" in body, (
            "без этого правила пустая колонка на дашборде займёт 60px " "и щиток съедет"
        )

    def test_visibility_is_not_toggled_from_python(self):
        """Ни один Python-модуль не управляет видимостью колонки.

        Ловит появление второго механизма: если кто-то начнёт
        подмешивать класс скрытия или style={"display": ...} к слоту
        полоски, источников правды станет два.
        """
        root = pathlib.Path(__file__).resolve().parent.parent
        offenders = []

        # Признаки управления видимостью из Python.
        manipulation = re.compile(r"display\s*[\"']?\s*:|hidden|d-none|visibility")

        for path in (root / "app").rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            if "nav-rail" not in source:
                continue

            # Докстринги и комментарии вырезаются ПО AST, а не по виду
            # строки: докстринг render_nav_rail_slot дословно цитирует
            # правило `.nav-rail-column:empty { display: none }`,
            # описывая ровно тот инвариант, который проверяет этот
            # тест. Текстовый фильтр такую цитату от кода не отличит.
            code_lines = set(range(1, source.count("\n") + 2))
            for node in ast.walk(ast.parse(source)):
                if not isinstance(node, ast.Constant) or not isinstance(
                    node.value, str
                ):
                    continue
                code_lines -= set(
                    range(node.lineno, (node.end_lineno or node.lineno) + 1)
                )

            for lineno, line in enumerate(source.splitlines(), start=1):
                if lineno not in code_lines:
                    continue
                if "nav-rail-column" not in line and "nav-rail-slot" not in line:
                    continue
                if not manipulation.search(line):
                    continue
                offenders.append(f"{path.relative_to(root)}:{lineno}: {line.strip()}")

        assert not offenders, (
            "видимостью колонки управляет кто-то кроме CSS :empty: " f"{offenders}"
        )


# ===========================================================================
# Язычки подписей
# ===========================================================================


class TestTips:
    """Язычок подписи выходит ЗА правый край кожуха.

    Из-за этого кожух намеренно оставлен без обрезки. Появление
    overflow: hidden или clip-path на .nav-rail срежет все подписи
    разом — и это ровно та регрессия, которую в браузере замечают
    не сразу, потому что сама полоска выглядит целой.
    """

    def test_tip_is_positioned_outside_the_shell(self):
        """Язычок позиционируется правее слота."""
        body = rule_body(read_css(), ".nav-rail-tip")

        assert "position: absolute" in body
        assert "left: calc(100% +" in body, (
            "язычок должен выходить за правый край слота " "(left: calc(100% + ...))"
        )

    def test_tip_is_hidden_until_hover(self):
        """В покое язычок скрыт и не перехватывает курсор."""
        body = rule_body(read_css(), ".nav-rail-tip")

        assert "opacity: 0" in body
        assert "visibility: hidden" in body
        # Без этого язычок ловил бы курсор и мигал под ним.
        assert "pointer-events: none" in body

    def test_shell_never_clips_tips(self):
        """У кожуха нет обрезки — иначе язычки срежутся.

        Комментарии вырезаны хелпером: в секции 2 CSS про overflow
        написано словами («НЕТ overflow: hidden»), и без вырезания
        тест поймал бы пояснение вместо правила.
        """
        body = rule_body(read_css(), ".nav-rail")

        assert "overflow" not in body, (
            "на .nav-rail появился overflow — язычки подписей "
            "будут срезаны по краю кожуха"
        )
        assert "clip-path" not in body, (
            "на .nav-rail появился clip-path — язычки подписей "
            "будут срезаны по краю кожуха"
        )

    def test_every_hoverable_slot_reveals_its_tip(self):
        """Язычок показывается у всех трёх носителей.

        Носителей ровно три: знак-домик, слот раздела и аватар.
        Если у какого-то не окажется своего :hover-правила, его
        подпись не всплывёт — а в 60px подпись единственный способ
        узнать, куда ведёт иконка.
        """
        clean = strip_comments(read_css())

        for carrier in (".nav-rail-slot", ".nav-rail-logo", ".nav-rail-avatar"):
            # Селектор должен ЗАКАНЧИВАТЬСЯ на .nav-rail-tip: голая
            # проверка вхождения проходит и на `.nav-rail-tip-DISABLED`,
            # то есть на правиле, которое ничего уже не показывает
            # (поймано mutation-прогоном).
            assert re.search(
                re.escape(f"{carrier}:hover .nav-rail-tip") + r"\s*[,{]", clean
            ), (
                f"у {carrier} нет правила показа язычка — подпись "
                "не всплывёт при наведении"
            )

    def test_tip_carriers_are_positioning_anchors(self):
        """Носители язычка спозиционированы — язычок считает от них.

        position: absolute у язычка отсчитывается от ближайшего
        спозиционированного предка. Пропадёт position: relative у
        носителя — язычок улетит к краю страницы.
        """
        css = read_css()

        for carrier in (".nav-rail-slot", ".nav-rail-logo", ".nav-rail-avatar"):
            assert "position: relative" in rule_body(css, carrier), (
                f"у {carrier} нет position: relative — язычок "
                "отсчитается не от него и улетит"
            )


# ===========================================================================
# Разворот при входе с дашборда
# ===========================================================================


class TestUnfoldAnimation:
    """Предпосылки разворота (FR-2/AC-5).

    ВАЖНО про границы: сам факт «разворот сыграл при входе с дашборда
    и не переигрался при переходе раздел→раздел» здесь НЕ проверяется
    — это требует браузера и подтверждается живой приёмкой. Ниже
    зафиксировано то, что ломается правкой CSS без захода в браузер.
    """

    def test_animation_runs_on_inner_not_on_shell(self):
        """Анимируется содержимое, а не стеклянная плашка.

        Решение владельца Р5: в эскизе схлопывалась сама плашка, но
        это требует обрезки по её краю и срезало бы язычки постоянно.
        Перенос анимации на кожух вернул бы ту самую проблему.
        """
        css = read_css()

        assert "animation:" in rule_body(
            css, ".nav-rail-inner"
        ), "анимация разворота должна висеть на .nav-rail-inner"
        assert "animation" not in rule_body(css, ".nav-rail"), (
            "анимация переехала на кожух — обрезка по его краю "
            "срежет язычки подписей"
        )

    def test_fill_mode_is_backwards_not_both(self):
        """fill-mode именно backwards.

        `both` оставил бы to-кадр (clip-path: inset(0)) на узле
        навсегда, а inset(0) обрезает по border-box — язычки
        оказались бы срезаны после каждого разворота. Ровно тот
        случай, когда «естественная» правка на both тихо ломает
        соседнюю механику.
        """
        body = rule_body(read_css(), ".nav-rail-inner")
        animation = re.search(r"animation:\s*([^;]+);", body)
        assert animation, "у .nav-rail-inner не найдено свойство animation"

        value = animation.group(1)
        assert "backwards" in value, f"ожидался fill-mode backwards, а не: {value}"
        assert "both" not in value, (
            "fill-mode both залипнет на to-кадре и срежет язычки "
            f"после разворота: {value}"
        )

    def test_keyframes_exist_and_reveal_only_the_logo_first(self):
        """Первый кадр открывает домик, последний — всю полоску."""
        clean = strip_comments(read_css())

        assert "@keyframes nav-rail-unfold" in clean, "нет @keyframes разворота"
        # Первый кадр обрезает снизу, оставляя padding-top + логотип.
        assert re.search(
            r"clip-path:\s*inset\(0 0 calc\(100% - ", clean
        ), "первый кадр должен отсекать всё ниже знака-домика"
        # Последний кадр снимает обрезку целиком.
        assert re.search(
            r"clip-path:\s*inset\(0 0 0 0\)", clean
        ), "последний кадр должен снимать обрезку полностью"

    def test_keyframes_reuse_the_geometry_variable(self):
        """Кадр считается от --rail-slot, а не от зашитых 44px.

        Иначе правка размера слота разъедется с первым кадром: домик
        окажется подрезан или из-под обрезки выглянет соседняя иконка.
        Переменная доезжает по наследованию колонка → кожух → inner —
        цепочку держит TestRailGeometry.
        """
        clean = strip_comments(read_css())
        keyframes = re.search(
            r"@keyframes nav-rail-unfold\s*\{(.*?\n\})\s*\n", clean, flags=re.DOTALL
        )
        assert keyframes, "не удалось выделить тело @keyframes"

        assert "--rail-slot" in keyframes.group(1), (
            "первый кадр должен считаться от --rail-slot, иначе "
            "геометрия и анимация разъедутся при правке размера слота"
        )

    def test_reduced_motion_disables_animation_entirely(self):
        """При prefers-reduced-motion анимация снимается ЦЕЛИКОМ.

        Не duration: 0 — при нулевой длительности первый кадр всё
        равно применится и залипнет, оставив полоску обрезанной по
        домику навсегда. Тест ловит подмену animation: none на
        обнуление длительности.
        """
        clean = strip_comments(read_css())
        block = re.search(
            r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*)",
            clean,
            flags=re.DOTALL,
        )
        assert block, "нет блока @media (prefers-reduced-motion: reduce)"

        media = block.group(1)
        assert "animation: none" in media, (
            "в reduced-motion анимация должна сниматься целиком "
            "(animation: none), иначе первый кадр залипнет"
        )
        assert not re.search(r"animation-duration:\s*0", media), (
            "animation-duration: 0 не годится — первый кадр применится "
            "и полоска останется обрезанной по домику"
        )


# ===========================================================================
# Внешние токены
# ===========================================================================


class TestBorrowedTokens:
    """Полоска не заводит своих глобальных токенов, а берёт чужие.

    Решение куска 3: новых :root-переменных не вводить. Обратная
    сторона — переименование токена в custom.css или panel.css
    молча обесцветит полоску: невалидная var() без fallback гасит
    свойство целиком, ошибки при этом нигде нет.
    """

    def test_no_global_tokens_introduced(self):
        """nav_rail.css не объявляет переменные в :root."""
        clean = strip_comments(read_css())
        assert ":root" not in clean, (
            "полоска не должна заводить глобальные токены — "
            "локальные объявляются на .nav-rail-column"
        )

    def test_every_borrowed_token_exists(self):
        """Каждый чужой токен реально объявлен в другом файле."""
        clean = strip_comments(read_css())

        # Что объявила сама полоска — из проверки исключаем.
        local = declared_vars(clean)
        borrowed = used_vars(clean) - local

        assert borrowed, "полоска обязана опираться на общие токены проекта"

        declared_elsewhere: set[str] = set()
        for css_file in ASSETS.glob("*.css"):
            if css_file.name == "nav_rail.css":
                continue
            declared_elsewhere |= declared_vars(
                strip_comments(css_file.read_text(encoding="utf-8"))
            )

        missing = sorted(borrowed - declared_elsewhere)
        assert not missing, (
            f"полоска ссылается на несуществующие токены {missing} — "
            "свойство погаснет молча, без ошибки в консоли"
        )
