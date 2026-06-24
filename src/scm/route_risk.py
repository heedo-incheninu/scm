"""항로별 보호 예산 집중도와 동시위험 경고를 계산한다."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

UNASSIGNED_ROUTE = "미지정"


@dataclass(frozen=True)
class RouteRiskResult:
    """항로 집중도 계산 결과."""

    by_route: pd.DataFrame
    hhi: float | None
    status: str
    message: str
    total_allocated_budget: float
    assigned_budget: float
    coverage_ratio: float
    route_count: int
    top_route: str | None
    top_share: float


def classify_route_hhi(hhi: float) -> str:
    """초기 HHI 기준에 따라 양호·주의·위험 등급을 반환한다."""

    if not 0 <= hhi <= 1:
        raise ValueError("HHI는 0과 1 사이여야 합니다.")
    if hhi > 0.50:
        return "위험"
    if hhi > 0.25:
        return "주의"
    return "양호"


def calculate_route_concentration(
    allocation: pd.DataFrame,
    *,
    budget_column: str = "service_allocated_budget",
    route_column: str = "route",
) -> RouteRiskResult:
    """보호 예산의 항로별 비중과 HHI를 계산한다.

    항로 정보가 없거나 배정 예산이 0이면 계산 불가 상태를 반환한다.
    이 함수는 입력 배정액이나 안전재고를 변경하지 않는다.
    """

    if budget_column not in allocation.columns:
        raise ValueError(f"항로 집중도 계산 필수 열 누락: {budget_column}")

    frame = allocation.copy()
    budgets = pd.to_numeric(frame[budget_column], errors="coerce")
    if budgets.isna().any():
        raise ValueError("배정 예산에 숫자가 아닌 값이 있습니다.")
    if (budgets < 0).any():
        raise ValueError("배정 예산은 0 이상이어야 합니다.")
    frame["_route_budget"] = budgets.astype(float)

    if route_column not in frame.columns:
        frame[route_column] = UNASSIGNED_ROUTE
    routes = frame[route_column].fillna(UNASSIGNED_ROUTE).astype(str).str.strip()
    frame["_route"] = routes.mask(routes.eq(""), UNASSIGNED_ROUTE)

    protected = frame[frame["_route_budget"] > 0].copy()
    total_allocated = float(protected["_route_budget"].sum())
    if total_allocated <= 0:
        return RouteRiskResult(
            by_route=pd.DataFrame(columns=["route", "allocated_budget", "budget_share"]),
            hhi=None,
            status="정보 없음",
            message="보호 예산이 0원이어서 항로 집중도를 계산하지 않았습니다.",
            total_allocated_budget=0.0,
            assigned_budget=0.0,
            coverage_ratio=0.0,
            route_count=0,
            top_route=None,
            top_share=0.0,
        )

    assigned = protected[protected["_route"] != UNASSIGNED_ROUTE]
    assigned_budget = float(assigned["_route_budget"].sum())
    coverage_ratio = assigned_budget / total_allocated
    if assigned_budget <= 0:
        return RouteRiskResult(
            by_route=pd.DataFrame(columns=["route", "allocated_budget", "budget_share"]),
            hhi=None,
            status="정보 없음",
            message=(
                "항로 정보가 없어 집중도를 계산하지 않았습니다. "
                "CSV의 선택 열 `route`에 항로명을 입력하면 분석할 수 있습니다."
            ),
            total_allocated_budget=total_allocated,
            assigned_budget=0.0,
            coverage_ratio=0.0,
            route_count=0,
            top_route=None,
            top_share=0.0,
        )

    by_route = (
        assigned.groupby("_route", as_index=False)["_route_budget"]
        .sum()
        .rename(columns={"_route": "route", "_route_budget": "allocated_budget"})
    )
    by_route["budget_share"] = by_route["allocated_budget"] / assigned_budget
    by_route = by_route.sort_values(
        ["allocated_budget", "route"], ascending=[False, True]
    ).reset_index(drop=True)

    hhi = float(by_route["budget_share"].pow(2).sum())
    status = classify_route_hhi(hhi)
    top_route = str(by_route.iloc[0]["route"])
    top_share = float(by_route.iloc[0]["budget_share"])
    coverage_note = (
        ""
        if coverage_ratio >= 0.999999
        else f" 전체 보호 예산 중 항로 확인 비율은 {coverage_ratio:.0%}입니다."
    )
    message = (
        f"{top_route} 항로에 확인 가능한 보호 예산의 {top_share:.0%}가 집중되어 있습니다."
        f"{coverage_note}"
    )
    return RouteRiskResult(
        by_route=by_route,
        hhi=hhi,
        status=status,
        message=message,
        total_allocated_budget=total_allocated,
        assigned_budget=assigned_budget,
        coverage_ratio=coverage_ratio,
        route_count=len(by_route),
        top_route=top_route,
        top_share=top_share,
    )
