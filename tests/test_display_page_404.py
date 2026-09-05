"""Тесты ветки 404 в роутинге display_page (app/main.py).

P3 UX-аудита 2026-08-20: 404-страница выпадала из фирменного стиля —
синяя кнопка Bootstrap (color="primary") на зелёно-белом приложении.
Контракт: неизвестный путь отдаёт страницу с текстом «Страница не
найдена» и ссылкой «На главную» на «/», собранную из классов щитка
(panel.css), без btn-primary; второй элемент кортежа — заголовок
«Ошибка» — не трогается.
"""

from typing import Any, Iterator

import dash_bootstrap_components as dbc
import pytest

from app.main import display_page


def _walk(node: Any) -> Iterator[Any]:
    """Обходит дерево Dash-компонентов в глубину, включая строковые листья."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
    else:
        yield from _walk(children)


def _texts(node: Any) -> list[str]:
    """Все строковые листья дерева."""
    return [n for n in _walk(node) if isinstance(n, str)]


def _classes(node: Any) -> set[str]:
    """Все CSS-классы дерева одним множеством."""
    result: set[str] = set()
    for n in _walk(node):
        result.update((getattr(n, "className", None) or "").split())
    return result


@pytest.fixture(params=["/nope", "/settings", "/help", "/transactions/1"])
def not_found(request) -> tuple[Any, Any]:
    """Результат display_page для неизвестного пути: (контент, заголовок)."""
    return display_page(request.param)


class TestNotFoundPage:
    """Неизвестный путь → страница 404 в стиле щитка."""

    def test_text_and_header_preserved(self, not_found):
        content, header = not_found
        assert "Страница не найдена" in _texts(content)
        # Второй элемент кортежа — create_page_header("Ошибка", ...)
        assert "Ошибка" in _texts(header)
        assert "Страница не найдена" in _texts(header)

    def test_home_link(self, not_found):
        content, _ = not_found
        buttons = [n for n in _walk(content) if isinstance(n, dbc.Button)]
        assert len(buttons) == 1, "ровно одна кнопка — «На главную»"
        button = buttons[0]
        assert button.href == "/"
        assert "На главную" in _texts(button)

    def test_button_not_bootstrap_primary(self, not_found):
        """Зелёный контур, как у «Сверки» в шапке щитка, а не синий primary."""
        content, _ = not_found
        button = next(n for n in _walk(content) if isinstance(n, dbc.Button))
        assert button.color != "primary"
        assert button.color == "success"
        assert button.outline is True
        assert "btn-primary" not in _classes(content)

    def test_panel_classes_used(self, not_found):
        """Разметка собрана из классов panel.css, не из display-1/text-muted."""
        content, _ = not_found
        classes = _classes(content)
        assert {
            "pnl-breaker",
            "pnl-empty",
            "pnl-empty-title",
            "pnl-empty-hint",
        } <= classes
        assert "pnl-amount" in classes
        assert "text-muted" not in classes
        assert "display-1" not in classes
