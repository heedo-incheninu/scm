"""분류부터 예산 배분까지의 전체 계산 파이프라인."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from scm.allocation import allocate_budget, allocate_proportionally, allocation_summary
from scm.classification import classify_skus
from scm.safety_stock import calculate_safety_stock


@dataclass(frozen=True)
class AnalysisResult:
    classification: pd.DataFrame
    safety_stock: pd.DataFrame
    allocation: pd.DataFrame
    baseline_allocation: pd.DataFrame
    summary: dict[str, float]


def analyze_inventory(
    products: pd.DataFrame,
    sales: pd.DataFrame,
    scenario: str = "moderate",
    budget_ratio: float = 0.20,
) -> AnalysisResult:
    """입력 데이터를 분석하고 제한 예산 배분 결과를 반환한다."""

    if not 0 <= budget_ratio <= 1:
        raise ValueError("budget_ratio는 0과 1 사이여야 합니다.")
    classification = classify_skus(products, sales)
    safety = calculate_safety_stock(classification, scenario)
    budget = float(safety["required_budget"].sum()) * budget_ratio
    allocation = allocate_budget(safety, budget)
    baseline = allocate_proportionally(safety, budget)
    summary = allocation_summary(allocation, baseline, budget)
    return AnalysisResult(classification, safety, allocation, baseline, summary)

