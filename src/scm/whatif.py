"""물류 시나리오와 예산 조건을 바꿔 보는 What-if 시뮬레이션."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from scm.allocation import allocate_budget, allocate_proportionally, allocation_summary
from scm.classification import classify_skus
from scm.constants import SCENARIOS
from scm.safety_stock import calculate_safety_stock

DEFAULT_BUDGET_RATIOS = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0)


def simulate_what_if(
    products: pd.DataFrame,
    sales: pd.DataFrame,
    *,
    scenarios: Iterable[str] | None = None,
    budget_ratios: Iterable[float] = DEFAULT_BUDGET_RATIOS,
    budget_anchor_scenario: str = "normal",
) -> pd.DataFrame:
    """여러 위기 시나리오와 예산 조건의 우선순위 배분 결과를 반환한다.

    예산 비율은 각 시나리오의 필요 금액이 아니라 기준 시나리오의 필요 금액에
    곱한다. 이렇게 해야 같은 금액을 투입했을 때 물류 충격 강도별 차이가 드러난다.
    """

    scenario_keys = list(scenarios or SCENARIOS.keys())
    ratios = list(budget_ratios)
    if budget_anchor_scenario not in SCENARIOS:
        raise ValueError(f"지원하지 않는 기준 시나리오: {budget_anchor_scenario}")
    classification = classify_skus(products, sales)
    anchor_safety = calculate_safety_stock(classification, budget_anchor_scenario)
    anchor_required_budget = float(anchor_safety["required_budget"].sum())
    rows: list[dict[str, float | int | str]] = []
    for scenario_order, scenario_key in enumerate(scenario_keys):
        if scenario_key not in SCENARIOS:
            raise ValueError(f"지원하지 않는 시나리오: {scenario_key}")
        scenario_details = SCENARIOS[scenario_key]
        safety = calculate_safety_stock(classification, scenario_key)
        scenario_required_budget = float(safety["required_budget"].sum())
        for ratio in ratios:
            if not 0 <= ratio <= 1:
                raise ValueError("모든 예산 비율은 0과 1 사이여야 합니다.")
            budget = anchor_required_budget * ratio
            allocation = allocate_budget(safety, budget)
            baseline = allocate_proportionally(safety, budget)
            summary = allocation_summary(allocation, baseline, budget)
            unmet_budget = allocation["unmet_quantity"] * allocation["unit_cost"]
            high_risk_mask = (allocation["unmet_quantity"] > 0) & (
                (allocation["priority_weight"] >= 6) | (allocation["fulfillment_rate"] < 0.5)
            )
            rows.append(
                {
                    "scenario": scenario_key,
                    "scenario_label": str(scenario_details["label"]),
                    "scenario_order": scenario_order,
                    "lead_time_multiplier": float(scenario_details["multiplier"]),
                    "budget_ratio": float(ratio),
                    "budget_anchor_scenario": budget_anchor_scenario,
                    "budget": budget,
                    "required_budget": scenario_required_budget,
                    "allocated_budget": float(summary["allocated_budget"]),
                    "unmet_budget": float(unmet_budget.sum()),
                    "priority_weighted_fulfillment": float(
                        summary["priority_weighted_fulfillment"]
                    ),
                    "baseline_weighted_fulfillment": float(
                        summary["baseline_weighted_fulfillment"]
                    ),
                    "relative_improvement": float(summary["relative_improvement"]),
                    "fully_funded_skus": int((allocation["fulfillment_rate"] >= 1).sum()),
                    "shortage_skus": int((safety["required_quantity"] > 0).sum()),
                    "high_risk_skus": int(high_risk_mask.sum()),
                }
            )
    return pd.DataFrame(rows)
