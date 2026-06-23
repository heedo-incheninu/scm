"""서비스수준 차등 선택형 예산 배분과 포기 SKU 손실 계산."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

SERVICE_LEVELS: tuple[float, ...] = (0.90, 0.95, 0.99)
MAX_SERVICE_LEVEL = max(SERVICE_LEVELS)
DEFAULT_CARRYING_COST_RATE = 0.20


@dataclass(frozen=True)
class ServiceLevelSummary:
    """서비스수준 배분 결과 요약."""

    budget: float
    allocated_budget: float
    remaining_budget: float
    weighted_service_level: float
    protected_skus: int
    unprotected_skus: int
    expected_loss: float


def _required_columns() -> set[str]:
    return {
        "sku_id",
        "name",
        "demand_mean",
        "demand_std",
        "lead_time_months",
        "lead_time_std_months",
        "current_stock",
        "unit_cost",
        "priority_weight",
        "abc_xyz",
    }


def _validate_safety_frame(safety: pd.DataFrame) -> None:
    missing = _required_columns() - set(safety.columns)
    if missing:
        raise ValueError(f"서비스수준 배분 필수 열 누락: {missing}")


def service_level_z_score(service_level: float) -> float:
    """서비스수준을 정규분포 안전계수 z로 변환한다."""

    if not 0.5 <= service_level < 1:
        raise ValueError("서비스수준은 0.5 이상 1 미만이어야 합니다.")
    return float(NormalDist().inv_cdf(service_level))


def build_service_level_options(
    safety: pd.DataFrame,
    *,
    carrying_cost_rate: float = DEFAULT_CARRYING_COST_RATE,
    service_levels: tuple[float, ...] = SERVICE_LEVELS,
) -> pd.DataFrame:
    """SKU별 미선택·90%·95%·99% 서비스수준 후보를 만든다.

    안전재고 공식은 기존 시스템의 σL 포함 공식을 그대로 사용한다.
    후보 비용은 현재고를 제외한 추가 필요 수량에 단가와 재고보유비율을 곱한다.
    """

    if not 0 <= carrying_cost_rate <= 1:
        raise ValueError("재고보유비율은 0과 1 사이여야 합니다.")
    _validate_safety_frame(safety)

    rows: list[dict[str, float | int | str | bool]] = []
    ordered_levels = (0.0, *service_levels)
    for sku in safety.itertuples(index=False):
        variance = (
            float(sku.lead_time_months) * float(sku.demand_std) ** 2
            + float(sku.demand_mean) ** 2 * float(sku.lead_time_std_months) ** 2
        )
        variance = max(variance, 0.0)
        for level in ordered_levels:
            z_score = service_level_z_score(level) if level > 0 else 0.0
            safety_stock = z_score * math.sqrt(variance)
            recommended_stock = int(math.ceil(safety_stock))
            additional_quantity = max(recommended_stock - int(sku.current_stock), 0)
            protection_cost = additional_quantity * float(sku.unit_cost) * carrying_cost_rate
            protected_value = (
                additional_quantity
                * float(sku.unit_cost)
                * float(sku.priority_weight)
                * (level / MAX_SERVICE_LEVEL if level > 0 else 0.0)
            )
            rows.append(
                {
                    "sku_id": str(sku.sku_id),
                    "name": str(sku.name),
                    "abc_xyz": str(sku.abc_xyz),
                    "priority_weight": int(sku.priority_weight),
                    "service_level": float(level),
                    "service_level_label": "미선택" if level == 0 else f"{level:.0%}",
                    "z_score": z_score,
                    "service_safety_stock": safety_stock,
                    "service_recommended_stock": recommended_stock,
                    "service_required_quantity": additional_quantity,
                    "service_required_budget": protection_cost,
                    "service_value": protected_value,
                    "is_unprotected_option": level == 0,
                }
            )
    return pd.DataFrame(rows)


def _scaled_costs(
    costs: pd.Series,
    budget: float,
    max_budget_units: int,
) -> tuple[pd.Series, float]:
    if budget <= 0:
        scaled = costs.astype(float).gt(0).astype(int)
        return scaled, 1.0
    granularity = max(1.0, budget / max_budget_units)
    scaled = np.ceil(costs.astype(float) / granularity).astype(int)
    return scaled, granularity


def allocate_service_levels(
    safety: pd.DataFrame,
    budget: float,
    *,
    carrying_cost_rate: float = DEFAULT_CARRYING_COST_RATE,
    max_budget_units: int = 3_000,
) -> pd.DataFrame:
    """예산 안에서 SKU별 하나의 서비스수준을 선택한다."""

    if budget < 0:
        raise ValueError("예산은 0 이상이어야 합니다.")
    if max_budget_units <= 0:
        raise ValueError("max_budget_units는 0보다 커야 합니다.")

    options = build_service_level_options(safety, carrying_cost_rate=carrying_cost_rate)
    scaled_costs, granularity = _scaled_costs(
        options["service_required_budget"], budget, max_budget_units
    )
    options = options.assign(scaled_cost=scaled_costs)
    capacity = int(math.floor(budget / granularity)) if budget > 0 else 0

    groups = [
        group.sort_values("service_level").reset_index(drop=True)
        for _, group in options.groupby("sku_id", sort=False)
    ]
    group_options = [
        [
            (int(row.scaled_cost), float(row.service_value), option_idx)
            for option_idx, row in enumerate(group.itertuples())
        ]
        for group in groups
    ]
    dp = [-math.inf] * (capacity + 1)
    dp[0] = 0.0
    backtrack: list[list[tuple[int, int] | None]] = []

    for options_for_sku in group_options:
        next_dp = [-math.inf] * (capacity + 1)
        choices: list[tuple[int, int] | None] = [None] * (capacity + 1)
        for current_cost, current_value in enumerate(dp):
            if current_value == -math.inf:
                continue
            for scaled_cost, service_value, option_idx in options_for_sku:
                next_cost = current_cost + scaled_cost
                if next_cost > capacity:
                    continue
                next_value = current_value + service_value
                if next_value > next_dp[next_cost]:
                    next_dp[next_cost] = next_value
                    choices[next_cost] = (current_cost, option_idx)
        dp = next_dp
        backtrack.append(choices)

    best_cost = max(range(capacity + 1), key=lambda index: dp[index])
    selected_indices: list[int] = []
    cost_cursor = best_cost
    for group_index in range(len(groups) - 1, -1, -1):
        choice = backtrack[group_index][cost_cursor]
        if choice is None:
            option_idx = 0
            previous_cost = cost_cursor
        else:
            previous_cost, option_idx = choice
        selected_indices.append(option_idx)
        cost_cursor = previous_cost
    selected_indices.reverse()

    selected_rows = [
        groups[group_index].iloc[option_idx]
        for group_index, option_idx in enumerate(selected_indices)
    ]
    selected = pd.DataFrame(selected_rows).drop(columns=["scaled_cost"]).reset_index(drop=True)
    original = safety.drop(
        columns=[
            column
            for column in selected.columns
            if column in safety.columns and column not in {"sku_id", "name", "abc_xyz"}
        ],
        errors="ignore",
    )
    max_stock = options.loc[
        options["service_level"] == MAX_SERVICE_LEVEL,
        ["sku_id", "service_recommended_stock"],
    ].rename(columns={"service_recommended_stock": "max_service_recommended_stock"})
    result = original.merge(
        selected,
        on=["sku_id", "name", "abc_xyz"],
        how="left",
        validate="one_to_one",
    ).merge(max_stock, on="sku_id", how="left", validate="one_to_one")
    result["service_allocated_budget"] = result["service_required_budget"]
    result["service_unmet_to_99_quantity"] = (
        result["max_service_recommended_stock"] - result["service_recommended_stock"]
    ).clip(lower=0)
    result["service_status"] = np.select(
        [
            result["service_level"] >= MAX_SERVICE_LEVEL,
            result["service_level"] > 0,
        ],
        ["최고 보호", "부분 보호"],
        default="미보호",
    )
    result["selection_reason"] = np.select(
        [
            result["service_level"] >= MAX_SERVICE_LEVEL,
            result["service_level"] > 0,
        ],
        [
            "중요도와 예산 효율이 높아 99% 보호를 추천합니다.",
            "예산 제약을 고려해 부분 보호를 추천합니다.",
        ],
        default="예산 대비 우선순위가 낮아 이번 배분에서는 보류합니다.",
    )
    remaining = max(budget - float(result["service_allocated_budget"].sum()), 0.0)
    result["service_remaining_budget"] = remaining
    return result.sort_values(
        ["service_level", "priority_weight", "service_value", "sku_id"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def service_level_full_budget(
    safety: pd.DataFrame,
    *,
    carrying_cost_rate: float = DEFAULT_CARRYING_COST_RATE,
) -> float:
    """모든 SKU를 99%로 보호할 때 필요한 서비스수준 기준 예산을 계산한다."""

    options = build_service_level_options(safety, carrying_cost_rate=carrying_cost_rate)
    max_options = options.loc[options["service_level"] == MAX_SERVICE_LEVEL]
    return float(max_options["service_required_budget"].sum())


def calculate_unprotected_losses(
    service_allocation: pd.DataFrame,
    *,
    stockout_period_months: float = 1.0,
    loss_factor: float = 1.0,
) -> pd.DataFrame:
    """미보호 SKU의 예상손실액을 계산한다."""

    if stockout_period_months < 0 or loss_factor < 0:
        raise ValueError("결품기간과 손실계수는 0 이상이어야 합니다.")
    required = {"demand_mean", "unit_cost", "service_level"}
    if not required.issubset(service_allocation.columns):
        missing = required - set(service_allocation.columns)
        raise ValueError(f"예상손실 계산 필수 열 누락: {missing}")

    result = service_allocation.copy()
    unprotected = result["service_level"] <= 0
    result["expected_loss"] = 0.0
    result.loc[unprotected, "expected_loss"] = (
        result.loc[unprotected, "demand_mean"].astype(float)
        * result.loc[unprotected, "unit_cost"].astype(float)
        * stockout_period_months
        * loss_factor
    )
    result["loss_reason"] = np.where(
        unprotected,
        "서비스수준 미선택으로 결품 위험을 감수하는 품목입니다.",
        "이번 예산에서 최소 서비스수준 이상 보호됩니다.",
    )
    return result


def weighted_service_level(service_allocation: pd.DataFrame) -> float:
    """중요도와 품목 가치를 반영한 평균 서비스수준 점수를 계산한다."""

    required = {"priority_weight", "demand_mean", "unit_cost", "service_level"}
    if not required.issubset(service_allocation.columns):
        missing = required - set(service_allocation.columns)
        raise ValueError(f"서비스수준 점수 필수 열 누락: {missing}")
    weights = (
        service_allocation["priority_weight"].astype(float)
        * service_allocation["demand_mean"].astype(float)
        * service_allocation["unit_cost"].astype(float)
    )
    if float(weights.sum()) <= 0:
        return 1.0
    level_ratio = service_allocation["service_level"].astype(float) / MAX_SERVICE_LEVEL
    return float((level_ratio.clip(0, 1) * weights).sum() / weights.sum())


def summarize_service_level_allocation(
    service_allocation: pd.DataFrame,
    budget: float,
) -> dict[str, float]:
    """서비스수준 배분 결과를 KPI용 dict로 요약한다."""

    allocated_budget = float(service_allocation["service_allocated_budget"].sum())
    expected_loss = (
        float(service_allocation["expected_loss"].sum())
        if "expected_loss" in service_allocation.columns
        else 0.0
    )
    return {
        "budget": float(budget),
        "allocated_budget": allocated_budget,
        "remaining_budget": max(float(budget) - allocated_budget, 0.0),
        "weighted_service_level": weighted_service_level(service_allocation),
        "protected_skus": int((service_allocation["service_level"] > 0).sum()),
        "unprotected_skus": int((service_allocation["service_level"] <= 0).sum()),
        "expected_loss": expected_loss,
    }
