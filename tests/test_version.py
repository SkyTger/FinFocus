"""Тесты источника версии — app/version.py (протокол 0031, шаг 2).

Версия приложения должна иметь ровно один источник правды, устойчивый
к запуску из PyInstaller-бандла. Здесь фиксируются: формат константы,
совпадение реэкспорта из пакета с самим модулем, инвариант пустоты
app/__init__.py и соответствие константы git-тегу.
"""

import ast
import re
import subprocess
from pathlib import Path

import pytest

import app
from app.version import __version__

# Упрощённый PEP 440: релиз + необязательные пре-релиз/пост/дев-сегменты.
# Достаточно, чтобы поймать очевидный мусор ("v1.0", "", "1.0.0 beta"),
# но не тянуть packaging ради одной проверки.
PEP440_RE = re.compile(
    r"^\d+(\.\d+)*"
    r"((a|b|rc)\d+|-(alpha|beta|rc)(\.\d+)?)?"
    r"(\.post\d+)?"
    r"(\.dev\d+)?$"
)

APP_INIT = Path(app.__file__)


def test_version_is_not_empty():
    """Версия непустая и не состоит из пробелов."""
    assert __version__
    assert __version__.strip() == __version__


def test_version_is_pep440_compatible():
    """Версия совместима с PEP 440 (без ведущей 'v', без пробелов)."""
    assert PEP440_RE.match(__version__), (
        f"Версия {__version__!r} не похожа на PEP 440. "
        "Ведущая 'v' — часть git-тега, а не константы."
    )


def test_version_is_not_placeholder():
    """Версия не равна захардкоженной заглушке '1.0.0'.

    До этого протокола в сайдбаре была зашита строка 'v1.0.0' при
    реальном релизе v0.9.0-beta.1 (P3 UX-аудита 2026-08-20). Тест —
    якорь против возврата заглушки.
    """
    assert __version__ != "1.0.0"


def test_package_reexport_matches_module():
    """`from app import __version__` — тот же объект, что и в модуле."""
    assert app.__version__ == __version__


def test_app_init_contains_only_version_reexport():
    """Инвариант: в app/__init__.py нет ничего, кроме реэкспорта версии.

    Проверка идёт разбором синтаксического дерева, а НЕ построчным
    сравнением текста: текстовая проверка сломалась бы от любого
    переформатирования black, хотя смысл файла не изменился бы.

    Зачем инвариант: app/__init__.py выполняется при любом импорте
    вида `import app.<...>`. Любой импорт сервиса отсюда потянет за
    собой цикл импортов (см. докстринг самого файла).
    """
    tree = ast.parse(APP_INIT.read_text(encoding="utf-8"))
    body = list(tree.body)

    # Докстринг модуля — разрешён и не считается «содержимым».
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body.pop(0)

    kinds = [type(node).__name__ for node in body]
    assert kinds == ["ImportFrom", "Assign"], (
        "app/__init__.py должен содержать только докстринг, "
        f"`from app.version import __version__` и `__all__`. Найдено: {kinds}"
    )

    import_node, assign_node = body

    assert import_node.module == "app.version"
    assert [alias.name for alias in import_node.names] == ["__version__"]

    assert [target.id for target in assign_node.targets] == ["__all__"]
    assert [elt.value for elt in assign_node.value.elts] == ["__version__"]


def test_version_matches_git_tag():
    """Константа версии совпадает с последним git-тегом.

    Бамп версии делается руками одновременно с git-тегом, и разъехаться
    они могут незаметно. Тест ловит это на CI.

    Пропускается там, где сверять не с чем: в PyInstaller-бандле нет
    каталога .git, на машине пользователя может не быть самого git.
    """
    repo_root = APP_INIT.parent.parent
    if not (repo_root / ".git").exists():
        pytest.skip("нет каталога .git — сверять версию не с чем (бандл?)")

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("git недоступен")

    if result.returncode != 0:
        pytest.skip(f"git describe не дал тега: {result.stderr.strip()}")

    tag = result.stdout.strip()
    assert tag == f"v{__version__}", (
        f"git-тег {tag!r} разошёлся с константой {__version__!r}. "
        "Бампить нужно оба одновременно."
    )


def test_no_hardcoded_version_in_app():
    """В app/ не осталось захардкоженных версий помимо app/version.py.

    Единственный источник правды имеет смысл, только если других
    источников нет. До шага 9 протокола 0031 тест был помечен
    xfail(strict=True): строка "v1.0.0" жила в сайдбаре
    (P3 UX-аудита 2026-08-20 — зашитая версия при реальном релизе
    v0.9.0-beta.1). Сайдбар снят, маркер снят вместе с ним.

    Ищем ОТОБРАЖАЕМЫЕ строковые литералы вида "v1.0.0"/"1.0.0", а не
    любое совпадение по файлу: в комментариях и докстрингах номера
    версий законны и неизбежны ("dash 2.17.1", "WCAG 2.5.5",
    объяснение в надгробии сайдбара, почему v1.0.0 больше нет).
    Поэтому разбираем синтаксическое дерево и смотрим только
    строковые константы, исключая докстринги.
    """
    app_dir = APP_INIT.parent
    version_module = app_dir / "version.py"
    pattern = re.compile(r"^v?\d+\.\d+\.\d+")

    offenders = []
    for path in sorted(app_dir.rglob("*.py")):
        if path == version_module:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"))

        # Докстринги модуля, классов и функций — не отображаемый текст.
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                doc_node = (
                    node.body[0]
                    if node.body and isinstance(node.body[0], ast.Expr)
                    else None
                )
                if doc_node is not None and isinstance(doc_node.value, ast.Constant):
                    docstrings.add(id(doc_node.value))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docstrings:
                continue
            if pattern.match(node.value.strip()):
                rel = path.relative_to(app_dir.parent)
                offenders.append(f"{rel}:{node.lineno}: {node.value!r}")

    assert not offenders, "Захардкоженные версии вне app/version.py:\n" + "\n".join(
        offenders
    )
