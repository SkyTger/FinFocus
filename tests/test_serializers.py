"""Тесты для сериализаторов RedistributionPreview."""
from decimal import Decimal

from app.schema.goals import AllocationResult, AllocationSummary, RedistributionPreview
from app.utils.serializers import (
    deserialize_redistribution_preview,
    serialize_redistribution_preview,
)


class TestSerializeRedistributionPreviewBasic:
    """Тесты базовой сериализации RedistributionPreview."""

    def test_serialize_redistribution_preview_basic(self):
        """Базовая сериализация без AllocationSummary."""
        preview: RedistributionPreview = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": Decimal("5000.00"),
            "was_skipped_in_old_allocation": False,
            "has_remaining_goals": True,
            "remaining_goals_count": 2,
            "new_allocation": None,
            "old_allocation": None,
            "calculation_time_ms": 12.5,
        }

        result = serialize_redistribution_preview(preview)

        # Проверяем что Decimal конвертирован в str
        assert result["freed_budget"] == "5000.00"
        # Примитивы остаются без изменений
        assert result["completed_goal_id"] == 1
        assert result["completed_goal_name"] == "Отпуск"
        assert result["was_skipped_in_old_allocation"] is False
        assert result["has_remaining_goals"] is True
        assert result["remaining_goals_count"] == 2
        assert result["new_allocation"] is None
        assert result["old_allocation"] is None
        assert result["calculation_time_ms"] == 12.5

    def test_serialize_redistribution_preview_with_allocation(self):
        """Сериализация с вложенным AllocationSummary."""
        allocation_result: AllocationResult = {
            "goal_id": 2,
            "goal_name": "Машина",
            "priority": 1,
            "monthly_contribution_needed": Decimal("10000.00"),
            "allocated_amount": Decimal("8000.00"),
            "is_fully_funded": False,
            "shortfall": Decimal("2000.00"),
            "skipped_reason": None,
        }

        allocation_summary: AllocationSummary = {
            "total_budget": Decimal("15000.00"),
            "total_allocated": Decimal("8000.00"),
            "total_needed": Decimal("10000.00"),
            "total_shortfall": Decimal("2000.00"),
            "results": [allocation_result],
            "all_goals_funded": False,
            "budget_not_set": False,
        }

        preview: RedistributionPreview = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": Decimal("5000.00"),
            "was_skipped_in_old_allocation": False,
            "has_remaining_goals": True,
            "remaining_goals_count": 1,
            "new_allocation": allocation_summary,
            "old_allocation": None,
            "calculation_time_ms": 25.3,
        }

        result = serialize_redistribution_preview(preview)

        # Проверяем вложенные Decimal значения
        assert result["new_allocation"]["total_budget"] == "15000.00"
        assert result["new_allocation"]["total_allocated"] == "8000.00"
        assert result["new_allocation"]["total_shortfall"] == "2000.00"

        # Проверяем Decimal внутри results списка
        assert (
            result["new_allocation"]["results"][0]["monthly_contribution_needed"]
            == "10000.00"
        )
        assert result["new_allocation"]["results"][0]["allocated_amount"] == "8000.00"
        assert result["new_allocation"]["results"][0]["shortfall"] == "2000.00"


class TestDeserializeRedistributionPreview:
    """Тесты десериализации RedistributionPreview."""

    def test_deserialize_redistribution_preview_basic(self):
        """Базовая десериализация."""
        data = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": "5000.00",
            "was_skipped_in_old_allocation": False,
            "has_remaining_goals": True,
            "remaining_goals_count": 2,
            "new_allocation": None,
            "old_allocation": None,
            "calculation_time_ms": 12.5,
        }

        result = deserialize_redistribution_preview(data)

        # Проверяем что str конвертирован обратно в Decimal
        assert result["freed_budget"] == Decimal("5000.00")
        assert isinstance(result["freed_budget"], Decimal)

        # Примитивы остаются без изменений
        assert result["completed_goal_id"] == 1
        assert result["completed_goal_name"] == "Отпуск"

    def test_deserialize_redistribution_preview_none(self):
        """Десериализация None возвращает None."""
        result = deserialize_redistribution_preview(None)
        assert result is None

    def test_deserialize_redistribution_preview_with_allocation(self):
        """Десериализация с вложенным AllocationSummary."""
        data = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": "5000.00",
            "was_skipped_in_old_allocation": False,
            "has_remaining_goals": True,
            "remaining_goals_count": 1,
            "new_allocation": {
                "total_budget": "15000.00",
                "total_allocated": "8000.00",
                "total_needed": "10000.00",
                "total_shortfall": "2000.00",
                "results": [
                    {
                        "goal_id": 2,
                        "goal_name": "Машина",
                        "priority": 1,
                        "monthly_contribution_needed": "10000.00",
                        "allocated_amount": "8000.00",
                        "is_fully_funded": False,
                        "shortfall": "2000.00",
                        "skipped_reason": None,
                    }
                ],
                "all_goals_funded": False,
                "budget_not_set": False,
            },
            "old_allocation": None,
            "calculation_time_ms": 25.3,
        }

        result = deserialize_redistribution_preview(data)

        # Проверяем вложенные Decimal значения
        assert result["new_allocation"]["total_budget"] == Decimal("15000.00")
        assert result["new_allocation"]["total_allocated"] == Decimal("8000.00")
        assert isinstance(result["new_allocation"]["total_budget"], Decimal)

        # Проверяем Decimal внутри results списка
        assert result["new_allocation"]["results"][0][
            "monthly_contribution_needed"
        ] == Decimal("10000.00")
        assert isinstance(
            result["new_allocation"]["results"][0]["allocated_amount"], Decimal
        )


class TestRoundtripSerialization:
    """Тесты roundtrip сериализации (serialize → deserialize)."""

    def test_roundtrip_serialization(self):
        """Проверка что serialize → deserialize сохраняет данные."""
        original: RedistributionPreview = {
            "completed_goal_id": 1,
            "completed_goal_name": "Отпуск",
            "freed_budget": Decimal("5000.00"),
            "was_skipped_in_old_allocation": False,
            "has_remaining_goals": True,
            "remaining_goals_count": 2,
            "new_allocation": {
                "total_budget": Decimal("15000.00"),
                "total_allocated": Decimal("13000.00"),
                "total_needed": Decimal("12000.00"),
                "total_shortfall": Decimal("0.00"),
                "results": [
                    {
                        "goal_id": 2,
                        "goal_name": "Машина",
                        "priority": 1,
                        "monthly_contribution_needed": Decimal("7000.00"),
                        "allocated_amount": Decimal("7000.00"),
                        "is_fully_funded": True,
                        "shortfall": Decimal("0.00"),
                        "skipped_reason": None,
                    },
                    {
                        "goal_id": 3,
                        "goal_name": "Ремонт",
                        "priority": 2,
                        "monthly_contribution_needed": Decimal("5000.00"),
                        "allocated_amount": Decimal("5000.00"),
                        "is_fully_funded": True,
                        "shortfall": Decimal("0.00"),
                        "skipped_reason": None,
                    },
                ],
                "all_goals_funded": True,
                "budget_not_set": False,
            },
            "old_allocation": None,
            "calculation_time_ms": 42.7,
        }

        # Serialize → Deserialize
        serialized = serialize_redistribution_preview(original)
        restored = deserialize_redistribution_preview(serialized)

        # Проверяем основные поля
        assert restored["completed_goal_id"] == original["completed_goal_id"]
        assert restored["completed_goal_name"] == original["completed_goal_name"]
        assert restored["freed_budget"] == original["freed_budget"]
        assert restored["calculation_time_ms"] == original["calculation_time_ms"]

        # Проверяем вложенные данные
        assert (
            restored["new_allocation"]["total_budget"]
            == original["new_allocation"]["total_budget"]
        )
        assert (
            restored["new_allocation"]["total_allocated"]
            == original["new_allocation"]["total_allocated"]
        )

        # Проверяем results
        assert len(restored["new_allocation"]["results"]) == 2
        assert (
            restored["new_allocation"]["results"][0]["monthly_contribution_needed"]
            == original["new_allocation"]["results"][0]["monthly_contribution_needed"]
        )
        assert (
            restored["new_allocation"]["results"][1]["goal_name"]
            == original["new_allocation"]["results"][1]["goal_name"]
        )

    def test_roundtrip_with_empty_allocation(self):
        """Roundtrip с пустым allocation (no remaining goals)."""
        original: RedistributionPreview = {
            "completed_goal_id": 1,
            "completed_goal_name": "Единственная цель",
            "freed_budget": Decimal("10000.00"),
            "was_skipped_in_old_allocation": False,
            "has_remaining_goals": False,
            "remaining_goals_count": 0,
            "new_allocation": None,
            "old_allocation": None,
            "calculation_time_ms": 5.2,
        }

        serialized = serialize_redistribution_preview(original)
        restored = deserialize_redistribution_preview(serialized)

        assert restored["freed_budget"] == original["freed_budget"]
        assert restored["has_remaining_goals"] is False
        assert restored["new_allocation"] is None
