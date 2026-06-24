"""수요와 해상 리드타임 불확실성을 반영한 안전재고 계산."""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd

from scm.constants import DAYS_PER_MONTH, SCENARIOS


def calculate_safety_stock(metrics: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """선택한 위기 시나리오의 SKU별 권장 안전재고를 반환한다.

    공식: z × sqrt(L × σd² + d² × σL²)
    d와 σd는 월 수요, L과 σL은 월 단위 리드타임이다.
    위기배수는 평균 리드타임 L에만 적용하며 리드타임 표준편차 σL에는 적용하지 않는다.
    """

    if scenario not in SCENARIOS:
        raise ValueError(f"지원하지 않는 시나리오: {scenario}")
    required = {
        "demand_mean",
        "demand_std",
        "lead_time_days",
        "lead_time_std_days",
        "service_level",
        "current_stock",
        "unit_cost",
    }
    if not required.issubset(metrics.columns):
        raise ValueError(f"안전재고 계산 필수 열 누락: {required - set(metrics.columns)}")
    if not metrics["service_level"].between(0.5, 0.9999).all():
        raise ValueError("서비스 수준은 0.5 이상 0.9999 이하여야 합니다.")

    result = metrics.copy()
    multiplier = float(SCENARIOS[scenario]["multiplier"])
    result["scenario"] = scenario
    result["scenario_label"] = str(SCENARIOS[scenario]["label"])
    result["lead_time_multiplier"] = multiplier
    result["lead_time_months"] = result["lead_time_days"] * multiplier / DAYS_PER_MONTH
    result["lead_time_std_months"] = result["lead_time_std_days"] / DAYS_PER_MONTH
    result["z_score"] = result["service_level"].map(NormalDist().inv_cdf)
    variance = (
        result["lead_time_months"] * result["demand_std"].pow(2)
        + result["demand_mean"].pow(2) * result["lead_time_std_months"].pow(2)
    )
    result["safety_stock"] = result["z_score"] * np.sqrt(variance.clip(lower=0))
    result["recommended_stock"] = np.ceil(result["safety_stock"]).astype(int)
    result["required_quantity"] = (
        result["recommended_stock"] - result["current_stock"]
    ).clip(lower=0).astype(int)
    result["required_budget"] = result["required_quantity"] * result["unit_cost"]
    result["reorder_point"] = np.ceil(
        result["demand_mean"] * result["lead_time_months"] + result["safety_stock"]
    ).astype(int)
    return result
