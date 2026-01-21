"""Сервис распределения бюджета накоплений между целями."""

from decimal import Decimal

from loguru import logger

from app.models.database import Goal, GoalStatus
from app.schema.goals import AllocationResult, AllocationSummary

# Множители для режимов накоплений
SAVINGS_MODE_MULTIPLIERS: dict[str, Decimal] = {
    "free": Decimal("1.0"),  # 100% — минимальные взносы
    "medium": Decimal("1.15"),  # 115% — буфер для страховки
    "strict": Decimal("1.5"),  # 150% — максимизация накоплений
}


class AllocationService:
    """Сервис распределения бюджета накоплений между целями.

    Использует жадный алгоритм: цели обрабатываются в порядке priority (1, 2, 3...),
    каждая получает минимум из (needed, remaining_budget).
    """

    def calculate_allocation(
        self,
        goals: list[Goal],
        monthly_budget: Decimal,
        savings_mode: str = "free",
    ) -> AllocationSummary:
        """Распределяет бюджет между целями по приоритету с учетом режима накоплений.

        Args:
            goals: Список целей для распределения.
            monthly_budget: Месячный бюджет на накопления.
            savings_mode: Режим накоплений ("free", "medium", "strict").
                - "free" (1.0x) — минимальные взносы точно по графику
                - "medium" (1.15x) — +15% буфер для страховки
                - "strict" (1.5x) — максимизация накоплений

        Returns:
            AllocationSummary: Сводка распределения с детализацией по целям.

        Algorithm:
            1. Получение множителя для savings_mode.
            2. Сортировка целей по priority ASC (1, 2, 3...).
            3. Для каждой цели:
               - Если COMPLETED → skipped (completed).
               - Если PAUSED → skipped (paused).
               - Если monthly_contribution <= 0 → skipped (zero_contribution).
               - Иначе: monthly_needed = base * multiplier,
                        allocated = min(monthly_needed, remaining_budget).
            4. Подсчет totals (allocated, needed, shortfall).
            5. Формирование AllocationSummary.
        """
        # Получаем множитель для режима накоплений
        multiplier = SAVINGS_MODE_MULTIPLIERS.get(savings_mode, Decimal("1.0"))
        if savings_mode not in SAVINGS_MODE_MULTIPLIERS:
            logger.warning(
                f"Неизвестный режим накоплений: {savings_mode}, используется 1.0"
            )

        # Guard: пустой список целей
        if not goals:
            return AllocationSummary(
                total_budget=monthly_budget,
                total_allocated=Decimal("0"),
                total_needed=Decimal("0"),
                total_shortfall=Decimal("0"),
                results=[],
                all_goals_funded=True,
                budget_not_set=(monthly_budget == Decimal("0")),
            )

        # Сортировка по приоритету (1 = highest)
        sorted_goals = sorted(goals, key=lambda g: g.priority)

        # Инициализация
        remaining_budget = monthly_budget
        results: list[AllocationResult] = []
        total_allocated = Decimal("0")
        total_needed = Decimal("0")
        total_shortfall = Decimal("0")

        # Жадный алгоритм
        for goal in sorted_goals:
            # Применяем множитель к базовому monthly_contribution
            base_monthly = goal.monthly_contribution
            monthly_needed = base_monthly * multiplier

            # Определяем причину пропуска (если есть)
            skipped_reason = None
            allocated = Decimal("0")

            if goal.status == GoalStatus.COMPLETED:
                skipped_reason = "completed"
            elif goal.status == GoalStatus.PAUSED:
                skipped_reason = "paused"
            elif monthly_needed <= Decimal("0"):
                skipped_reason = "zero_contribution"
            else:
                # Активная цель с положительным needed
                allocated = min(monthly_needed, remaining_budget)
                remaining_budget -= allocated
                total_allocated += allocated
                total_needed += monthly_needed
                total_shortfall += max(Decimal("0"), monthly_needed - allocated)

            # Подсчет shortfall для результата
            result_shortfall = max(Decimal("0"), monthly_needed - allocated)

            # Формирование результата для цели
            result = AllocationResult(
                goal_id=goal.id,
                goal_name=goal.name,
                priority=goal.priority,
                monthly_contribution_needed=monthly_needed,
                allocated_amount=allocated,
                is_fully_funded=(
                    allocated >= monthly_needed if monthly_needed > 0 else False
                ),
                shortfall=result_shortfall,
                skipped_reason=skipped_reason,
            )
            results.append(result)

        # Формирование итоговой сводки
        return AllocationSummary(
            total_budget=monthly_budget,
            total_allocated=total_allocated,
            total_needed=total_needed,
            total_shortfall=total_shortfall,
            results=results,
            all_goals_funded=(total_shortfall == Decimal("0")),
            budget_not_set=(monthly_budget == Decimal("0")),
        )
