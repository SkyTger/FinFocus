"""Тесты UI компонентов для накопительных целей."""
from decimal import Decimal

from dash import html
import dash_bootstrap_components as dbc

from app.components.goals import (
    _build_congratulation_section,
    _build_freed_budget_section,
)


class TestBuildCongratulationSection:
    """Тесты для _build_congratulation_section."""

    def test_build_congratulation_section_basic(self):
        """Базовый тест структуры congratulation секции."""
        preview = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": Decimal("5000.00"),
        }

        result = _build_congratulation_section(preview)

        # Проверяем что возвращается html.Div
        assert isinstance(result, html.Div)
        # Проверяем наличие класса
        assert "congratulation-section" in result.className
        # Проверяем структуру children
        children = result.children
        assert len(children) == 3
        # Иконка
        assert isinstance(children[0], html.I)
        assert "bi-trophy-fill" in children[0].className
        # Заголовок
        assert isinstance(children[1], html.H5)
        assert children[1].children == "Поздравляем!"
        # Текст с названием цели
        assert isinstance(children[2], html.P)
        assert "Отпуск" in children[2].children

    def test_build_congratulation_section_missing_name(self):
        """Тест с отсутствующим названием цели."""
        preview = {
            "completed_goal_id": 1,
            "freed_budget": Decimal("5000.00"),
        }

        result = _build_congratulation_section(preview)

        # Должен использовать fallback "Цель"
        assert isinstance(result, html.Div)
        children = result.children
        assert "Цель" in children[2].children


class TestBuildFreedBudgetSection:
    """Тесты для _build_freed_budget_section."""

    def test_build_freed_budget_section_normal(self):
        """Стандартный случай без was_skipped."""
        preview = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": Decimal("5000.00"),
            "was_skipped_in_old_allocation": False,
        }

        result = _build_freed_budget_section(preview)

        # Проверяем структуру
        assert isinstance(result, html.Div)
        assert "freed-budget" in result.className
        children = result.children
        # Label + Value (без Alert)
        assert len(children) == 2
        # Label
        assert isinstance(children[0], html.P)
        assert "Освободился бюджет:" in children[0].children
        # Value
        assert isinstance(children[1], html.Span)
        assert "freed-budget-value" in children[1].className
        assert "/мес" in children[1].children

    def test_build_freed_budget_section_skipped(self):
        """Тест с was_skipped_in_old_allocation=True."""
        preview = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": Decimal("5000.00"),
            "was_skipped_in_old_allocation": True,
        }

        result = _build_freed_budget_section(preview)

        # Проверяем структуру
        assert isinstance(result, html.Div)
        children = result.children
        # Label + Value + Alert
        assert len(children) == 3
        # Alert
        assert isinstance(children[2], dbc.Alert)
        assert children[2].color == "info"

    def test_build_freed_budget_section_zero_budget(self):
        """Тест с нулевым бюджетом."""
        preview = {
            "completed_goal_id": 1,
            "freed_budget": Decimal("0"),
            "was_skipped_in_old_allocation": False,
        }

        result = _build_freed_budget_section(preview)

        # Должен корректно обработать нулевой бюджет
        assert isinstance(result, html.Div)
        children = result.children
        assert len(children) == 2

    def test_build_freed_budget_section_missing_fields(self):
        """Тест с отсутствующими полями."""
        preview = {
            "completed_goal_id": 1,
        }

        result = _build_freed_budget_section(preview)

        # Должен использовать fallback значения
        assert isinstance(result, html.Div)
        children = result.children
        # Без Alert (was_skipped по умолчанию False)
        assert len(children) == 2
