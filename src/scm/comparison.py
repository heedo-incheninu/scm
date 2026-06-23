"""여러 예산 조건에서 재고 예산 배분 전략을 비교한다."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from scm.allocation import (
    allocate_budget,
    allocate_equally,
    allocate_proportionally,
    weighted_fulfillment,
)
from scm.service_level_allocation import (
    DEFAULT_CARRYING_COST_RATE,
    allocate_service_levels,
    calculate_unprotected_losses,
    service_level_full_budget,
    weighted_service_level,
)

STRATEGIES = {
    "equal": ("균등 배분", allocate_equally),
    "proportional": ("비례 배분", allocate_proportionally),
    "priority": ("우선순위 배분", allocate_budget),
}


def compare_strategies(
    safety: pd.DataFrame,
    budget_ratios: Iterable[float] = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0),
    *,
    carrying_cost_rate: float = DEFAULT_CARRYING_COST_RATE,
) -> pd.DataFrame:
    """예산 비율별 배분 전략의 사용액과 위험가중 충족률을 반환한다."""

    total_required = float(safety["required_budget"].sum())
    total_service_budget = service_level_full_budget(
        safety, carrying_cost_rate=carrying_cost_rate
    )
    rows: list[dict[str, float | int | str]] = []
    for ratio in budget_ratios:
        if not 0 <= ratio <= 1:
            raise ValueError("모든 예산 비율은 0과 1 사이여야 합니다.")
        budget = total_required * ratio
        for strategy_key, (strategy_label, allocator) in STRATEGIES.items():
            allocation = allocator(safety, budget)
            rows.append(
                {
                    "budget_ratio": float(ratio),
                    "budget": budget,
                    "strategy": strategy_key,
                    "strategy_label": strategy_label,
                    "weighted_fulfillment": weighted_fulfillment(allocation),
                    "allocated_budget": float(allocation["allocated_budget"].sum()),
                    "remaining_budget": float(allocation["remaining_budget"].iloc[0]),
                    "fully_funded_skus": int((allocation["fulfillment_rate"] >= 1).sum()),
                    "unmet_quantity": int(allocation["unmet_quantity"].sum()),
                    "unprotected_skus": int((allocation["unmet_quantity"] > 0).sum()),
                    "expected_loss": 0.0,
                }
            )
        service_budget = total_service_budget * ratio
        service_allocation = allocate_service_levels(
            safety,
            service_budget,
            carrying_cost_rate=carrying_cost_rate,
        )
        service_allocation = calculate_unprotected_losses(service_allocation)
        service_allocated_budget = float(service_allocation["service_allocated_budget"].sum())
        rows.append(
            {
                "budget_ratio": float(ratio),
                "budget": service_budget,
                "strategy": "service_level",
                "strategy_label": "서비스수준 배분",
                "weighted_fulfillment": weighted_service_level(service_allocation),
                "allocated_budget": service_allocated_budget,
                "remaining_budget": max(service_budget - service_allocated_budget, 0.0),
                "fully_funded_skus": int((service_allocation["service_level"] >= 0.99).sum()),
                "unmet_quantity": int(
                    service_allocation["service_unmet_to_99_quantity"].sum()
                ),
                "unprotected_skus": int((service_allocation["service_level"] <= 0).sum()),
                "expected_loss": float(service_allocation["expected_loss"].sum()),
            }
        )
    return pd.DataFrame(rows)
