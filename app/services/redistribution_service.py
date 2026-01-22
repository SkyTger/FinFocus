"""Сервис перераспределения бюджета при достижении накопительной цели."""

import time
from datetime import datetime
from decimal import Decimal

from loguru import logger

from app.models.database import Goal, GoalStatus
from app.schema.goals import (
    AllocationSummary,
    RedistributionEvent,
    RedistributionPreview,
)
from app.services.allocation_service import AllocationService

# NFR-2: Порог предупреждения о времени расчета (миллисекунды)
NFR2_WARNING_THRESHOLD_MS = 50.0


class RedistributionService:
    """Сервис перераспределения бюджета при достижении накопительной цели.

    Использует "Temporary Status Pattern" для расчета OLD allocation:
    временно меняет статус завершенной цели на ACTIVE (в памяти, без DB commit),
    вычисляет old_allocation, затем восстанавливает статус.

    Attributes:
        allocation_service: Сервис для расчета распределения бюджета.
    """

    def __init__(self, allocation_service: AllocationService | None = None):
        """Инициализирует сервис с DI pattern для тестируемости.

        Args:
            allocation_service: Сервис распределения. Если None, создается новый.
        """
        self.allocation_service = allocation_service or AllocationService()

    def calculate_redistribution_preview(
        self,
        completed_goal: Goal,
        all_goals: list[Goal],
        monthly_budget: Decimal,
        savings_mode: str = "free",
    ) -> RedistributionPreview:
        """Рассчитывает preview перераспределения при достижении цели.

        Использует "Temporary Status Pattern":
        1. Сохраняет original_status = completed_goal.status
        2. Временно устанавливает status = ACTIVE
        3. Вычисляет old_allocation (как было ДО завершения)
        4. Восстанавливает original_status
        5. Вычисляет new_allocation (как будет ПОСЛЕ завершения)

        Args:
            completed_goal: Только что завершенная цель.
            all_goals: Все цели пользователя (включая completed_goal).
            monthly_budget: Месячный бюджет на накопления.
            savings_mode: Режим накоплений ("free", "medium", "strict").

        Returns:
            RedistributionPreview: Данные для отображения в модале.

        Note:
            Метод использует finally блок для гарантированного восстановления
            статуса цели даже при возникновении исключений.
        """
        start_time = time.perf_counter()

        # Сохраняем оригинальный статус для восстановления
        original_status = completed_goal.status

        old_allocation: AllocationSummary | None = None
        new_allocation: AllocationSummary | None = None

        try:
            # --- Temporary Status Pattern: расчет OLD allocation ---
            # Временно возвращаем цель в ACTIVE для расчета "как было"
            completed_goal.status = GoalStatus.ACTIVE

            old_allocation = self.allocation_service.calculate_allocation(
                goals=all_goals,
                monthly_budget=monthly_budget,
                savings_mode=savings_mode,
            )

        finally:
            # CRITICAL: Гарантированное восстановление статуса
            completed_goal.status = original_status

        # --- Расчет NEW allocation (после завершения цели) ---
        new_allocation = self.allocation_service.calculate_allocation(
            goals=all_goals,
            monthly_budget=monthly_budget,
            savings_mode=savings_mode,
        )

        # Подсчет оставшихся активных целей (исключая завершенную)
        remaining_goals = [
            g
            for g in all_goals
            if g.id != completed_goal.id and g.status == GoalStatus.ACTIVE
        ]
        remaining_goals_count = len(remaining_goals)
        has_remaining_goals = remaining_goals_count > 0

        # Определяем освободившийся бюджет и был ли goal пропущен
        freed_budget, was_skipped = self._get_freed_budget_from_allocation(
            completed_goal_id=completed_goal.id,
            old_allocation=old_allocation,
        )

        # Timing log (NFR-2)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if elapsed_ms > NFR2_WARNING_THRESHOLD_MS:
            logger.warning(
                f"RedistributionService.calculate_redistribution_preview() "
                f"заняло {elapsed_ms:.2f}ms (порог: {NFR2_WARNING_THRESHOLD_MS}ms)"
            )
        else:
            logger.debug(
                f"RedistributionService.calculate_redistribution_preview() "
                f"выполнено за {elapsed_ms:.2f}ms"
            )

        return RedistributionPreview(
            completed_goal_id=completed_goal.id,
            completed_goal_name=completed_goal.name,
            freed_budget=freed_budget,
            was_skipped_in_old_allocation=was_skipped,
            has_remaining_goals=has_remaining_goals,
            remaining_goals_count=remaining_goals_count,
            new_allocation=new_allocation if has_remaining_goals else None,
            old_allocation=old_allocation if has_remaining_goals else None,
            calculation_time_ms=elapsed_ms,
        )

    def _get_freed_budget_from_allocation(
        self,
        completed_goal_id: int,
        old_allocation: AllocationSummary,
    ) -> tuple[Decimal, bool]:
        """Определяет освободившийся бюджет из старого распределения.

        Args:
            completed_goal_id: ID завершенной цели.
            old_allocation: Старое распределение (с целью в статусе ACTIVE).

        Returns:
            tuple[Decimal, bool]: (freed_budget, was_skipped)
                - freed_budget: Сумма, которая была выделена на цель (0 если пропущена).
                - was_skipped: True если цель была пропущена в распределении.
        """
        for result in old_allocation["results"]:
            if result["goal_id"] == completed_goal_id:
                if result["skipped_reason"] is not None:
                    # Цель была пропущена (например, zero_contribution)
                    return Decimal("0"), True
                else:
                    # Цель получала финансирование
                    return result["allocated_amount"], False

        # Цель не найдена в результатах (не должно происходить)
        logger.error(
            f"Goal id={completed_goal_id} не найден в old_allocation.results. "
            "Это может указывать на ошибку в логике."
        )
        return Decimal("0"), False

    def log_redistribution_event(
        self,
        user_id: int | None = None,
        completed_goal: Goal | None = None,
        freed_budget: Decimal | None = None,
        remaining_goals_count: int | None = None,
        action: str = "",
        new_allocation: AllocationSummary | None = None,
        *,
        preview: RedistributionPreview | None = None,
    ) -> RedistributionEvent:
        """Логирует событие перераспределения для аудита (NFR-4).

        Можно вызывать двумя способами:
        1. С развернутыми параметрами (user_id, completed_goal, ...)
        2. С preview объектом (preview=..., action=...)

        Args:
            user_id: ID пользователя (если без preview).
            completed_goal: Завершенная цель (если без preview).
            freed_budget: Освободившийся бюджет (если без preview).
            remaining_goals_count: Количество оставшихся активных целей
                (если без preview).
            action: Действие пользователя ("confirmed" | "declined").
            new_allocation: Новое распределение (или None если отклонено).
            preview: RedistributionPreview объект (альтернатива развернутым параметрам).

        Returns:
            RedistributionEvent: Структура события для возможного использования.
        """
        # Если передан preview, извлекаем данные из него
        if preview is not None:
            goal_id = preview["completed_goal_id"]
            goal_name = preview["completed_goal_name"]
            freed = preview["freed_budget"]
            remaining_count = preview["remaining_goals_count"]
            alloc = preview.get("new_allocation")
        else:
            # Используем развернутые параметры
            if completed_goal is None:
                raise ValueError("completed_goal required when preview is None")
            goal_id = completed_goal.id
            goal_name = completed_goal.name
            freed = freed_budget or Decimal("0")
            remaining_count = remaining_goals_count or 0
            alloc = new_allocation

        # Конвертируем AllocationSummary в dict для JSON-совместимости
        allocation_dict: dict | None = None
        if alloc is not None:
            allocation_dict = {
                "total_budget": str(alloc["total_budget"]),
                "total_allocated": str(alloc["total_allocated"]),
                "total_needed": str(alloc["total_needed"]),
                "total_shortfall": str(alloc["total_shortfall"]),
                "all_goals_funded": alloc["all_goals_funded"],
                "results_count": len(alloc["results"]),
            }

        # user_id: используем переданный или DEFAULT_USER_ID
        effective_user_id = user_id if user_id is not None else 1

        event = RedistributionEvent(
            timestamp=datetime.now().isoformat(),
            user_id=effective_user_id,
            completed_goal_id=goal_id,
            completed_goal_name=goal_name,
            freed_budget=str(freed),
            remaining_goals_count=remaining_count,
            action=action,
            new_allocation_summary=allocation_dict,
        )

        # Аудит-лог (NFR-4)
        logger.info(
            f"REDISTRIBUTION_EVENT: user={effective_user_id}, "
            f"goal_id={goal_id}, goal_name='{goal_name}', "
            f"freed_budget={freed}, remaining_goals={remaining_count}, "
            f"action={action}"
        )

        return event
