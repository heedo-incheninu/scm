"""제한 예산을 ABC-XYZ 중요도에 따라 배분하고 기준 방식과 비교한다."""

from __future__ import annotations

import math

import pandas as pd


def allocate_budget(safety: pd.DataFrame, budget: float) -> pd.DataFrame:
    """높은 우선순위부터 필요한 추가 안전재고를 정수 단위로 확보한다."""

    if budget < 0:
        raise ValueError("예산은 0 이상이어야 합니다.")
    required = {"required_quantity", "required_budget", "unit_cost", "priority_weight", "sku_id"}
    if not required.issubset(safety.columns):
        raise ValueError(f"예산 배분 필수 열 누락: {required - set(safety.columns)}")

    result = safety.sort_values(
        ["priority_weight", "required_budget", "sku_id"],
        ascending=[False, True, True],
    ).copy()
    remaining = float(budget)
    allocated_quantities: list[int] = []
    for row in result.itertuples():
        affordable = math.floor((remaining + 1e-9) / float(row.unit_cost))
        allocated = min(int(row.required_quantity), max(affordable, 0))
        allocated_quantities.append(allocated)
        remaining -= allocated * float(row.unit_cost)
        remaining = max(remaining, 0.0)

    result["allocated_quantity"] = allocated_quantities
    result["allocated_budget"] = result["allocated_quantity"] * result["unit_cost"]
    result["unmet_quantity"] = result["required_quantity"] - result["allocated_quantity"]
    result["fulfillment_rate"] = 1.0
    needs_stock = result["required_quantity"] > 0
    result.loc[needs_stock, "fulfillment_rate"] = (
        result.loc[needs_stock, "allocated_quantity"]
        / result.loc[needs_stock, "required_quantity"]
    )
    result["remaining_budget"] = remaining
    return result.sort_values("sku_id").reset_index(drop=True)


def allocate_proportionally(safety: pd.DataFrame, budget: float) -> pd.DataFrame:
    """비교 기준: 모든 SKU에 동일 충족률로 예산을 비례 배분한다."""

    total_required = float(safety["required_budget"].sum())
    ratio = min(budget / total_required, 1.0) if total_required > 0 else 1.0
    result = safety.copy()
    result["allocated_quantity"] = (
        result["required_quantity"] * ratio
    ).apply(math.floor).astype(int)
    result["allocated_budget"] = result["allocated_quantity"] * result["unit_cost"]
    result["unmet_quantity"] = result["required_quantity"] - result["allocated_quantity"]
    result["fulfillment_rate"] = 1.0
    needs_stock = result["required_quantity"] > 0
    result.loc[needs_stock, "fulfillment_rate"] = (
        result.loc[needs_stock, "allocated_quantity"]
        / result.loc[needs_stock, "required_quantity"]
    )
    result["remaining_budget"] = max(budget - float(result["allocated_budget"].sum()), 0.0)
    return result.sort_values("sku_id").reset_index(drop=True)


def allocate_equally(safety: pd.DataFrame, budget: float) -> pd.DataFrame:
    """비교 전략: 재고가 필요한 각 SKU에 같은 금액 한도를 적용한다."""

    if budget < 0:
        raise ValueError("예산은 0 이상이어야 합니다.")
    result = safety.sort_values("sku_id").copy()
    active_count = int((result["required_quantity"] > 0).sum())
    equal_cap = budget / active_count if active_count else 0.0
    quantities: list[int] = []
    for row in result.itertuples():
        affordable = math.floor((equal_cap + 1e-9) / float(row.unit_cost))
        quantities.append(min(int(row.required_quantity), max(affordable, 0)))
    result["allocated_quantity"] = quantities
    result["allocated_budget"] = result["allocated_quantity"] * result["unit_cost"]
    result["unmet_quantity"] = result["required_quantity"] - result["allocated_quantity"]
    result["fulfillment_rate"] = 1.0
    needs_stock = result["required_quantity"] > 0
    result.loc[needs_stock, "fulfillment_rate"] = (
        result.loc[needs_stock, "allocated_quantity"]
        / result.loc[needs_stock, "required_quantity"]
    )
    result["remaining_budget"] = max(budget - float(result["allocated_budget"].sum()), 0.0)
    return result.reset_index(drop=True)


def weighted_fulfillment(frame: pd.DataFrame) -> float:
    """필요 금액과 중요도를 함께 반영한 위험가중 충족률을 계산한다."""

    weights = frame["priority_weight"].astype(float) * frame["required_budget"].astype(float)
    if float(weights.sum()) == 0:
        return 1.0
    return float((frame["fulfillment_rate"] * weights).sum() / weights.sum())


def allocation_summary(
    prioritized: pd.DataFrame,
    baseline: pd.DataFrame,
    budget: float,
) -> dict[str, float]:
    """가중 충족률을 기준으로 우선순위 배분의 개선 효과를 요약한다."""

    priority_score = weighted_fulfillment(prioritized)
    baseline_score = weighted_fulfillment(baseline)
    improvement = (
        (priority_score - baseline_score) / baseline_score if baseline_score > 0 else 0.0
    )
    return {
        "budget": float(budget),
        "allocated_budget": float(prioritized["allocated_budget"].sum()),
        "remaining_budget": float(prioritized["remaining_budget"].iloc[0]),
        "priority_weighted_fulfillment": priority_score,
        "baseline_weighted_fulfillment": baseline_score,
        "relative_improvement": improvement,
    }
