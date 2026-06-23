"""AI 코파일럿 화면에 표시할 의사결정 요약과 효과 지표."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StrategyEffects:
    priority_protection: float
    equal_delta_pp: float
    proportional_delta_pp: float
    extra_full_vs_equal: int
    extra_full_vs_proportional: int


@dataclass(frozen=True)
class CopilotBrief:
    headline: str
    risk_summary: str
    actions: tuple[str, ...]
    evidence: tuple[str, ...]


def calculate_strategy_effects(comparison: pd.DataFrame) -> StrategyEffects:
    """현재 예산에서 우선순위 배분이 기준 방식 대비 얼마나 나은지 계산한다."""

    required = {"strategy", "weighted_fulfillment", "fully_funded_skus"}
    if not required.issubset(comparison.columns):
        raise ValueError(f"효과 계산 필수 열 누락: {required - set(comparison.columns)}")
    indexed = comparison.set_index("strategy")
    for strategy in ("equal", "proportional", "priority"):
        if strategy not in indexed.index:
            raise ValueError(f"비교 결과에 {strategy} 전략이 없습니다.")

    priority = indexed.loc["priority"]
    equal = indexed.loc["equal"]
    proportional = indexed.loc["proportional"]
    return StrategyEffects(
        priority_protection=float(priority["weighted_fulfillment"]),
        equal_delta_pp=(
            float(priority["weighted_fulfillment"]) - float(equal["weighted_fulfillment"])
        )
        * 100,
        proportional_delta_pp=(
            float(priority["weighted_fulfillment"])
            - float(proportional["weighted_fulfillment"])
        )
        * 100,
        extra_full_vs_equal=int(priority["fully_funded_skus"]) - int(equal["fully_funded_skus"]),
        extra_full_vs_proportional=int(priority["fully_funded_skus"])
        - int(proportional["fully_funded_skus"]),
    )


def build_copilot_brief(
    allocation: pd.DataFrame,
    effects: StrategyEffects,
    *,
    scenario_label: str,
    budget_ratio: float,
    service_allocation: pd.DataFrame | None = None,
) -> CopilotBrief:
    """계산 결과를 실행 가능한 한국어 코파일럿 브리프로 바꾼다."""

    required = {
        "sku_id",
        "name",
        "abc_xyz",
        "priority_weight",
        "required_quantity",
        "allocated_quantity",
        "unmet_quantity",
        "fulfillment_rate",
        "unit_cost",
    }
    if not required.issubset(allocation.columns):
        raise ValueError(f"코파일럿 필수 열 누락: {required - set(allocation.columns)}")

    frame = allocation.copy()
    frame["unmet_budget"] = frame["unmet_quantity"] * frame["unit_cost"]
    at_risk = frame[frame["unmet_quantity"] > 0].sort_values(
        ["priority_weight", "unmet_budget"], ascending=[False, False]
    )
    top_rows = at_risk.head(3)
    high_risk_count = int(
        (
            (frame["unmet_quantity"] > 0)
            & ((frame["priority_weight"] >= 6) | (frame["fulfillment_rate"] < 0.5))
        ).sum()
    )
    headline = (
        f"{scenario_label} · 예산 {budget_ratio:.0%}: 우선순위 배분으로 중요 품목 보호 수준 "
        f"{effects.priority_protection:.1%}를 확보했습니다."
    )
    risk_summary = (
        f"현재 미충족 SKU는 {len(at_risk)}개이며, 그중 즉시 조치가 필요한 고위험 SKU는 "
        f"{high_risk_count}개입니다. 비례 배분 대비 보호 수준은 "
        f"{effects.proportional_delta_pp:+.1f}%p 개선됩니다."
    )
    service_evidence: tuple[str, ...] = ()
    if service_allocation is not None and {"service_level", "expected_loss"}.issubset(
        service_allocation.columns
    ):
        unprotected = service_allocation[service_allocation["service_level"] <= 0]
        expected_loss = float(service_allocation["expected_loss"].sum())
        risk_summary += (
            f" 서비스수준 배분 기준 미보호 SKU는 {len(unprotected)}개이며, "
            f"예상손실액은 약 ₩{expected_loss:,.0f}입니다."
        )
        if not unprotected.empty:
            service_evidence = tuple(
                (
                    f"미보호 {row['name']}({row['sku_id']}) · "
                    f"예상손실 ₩{float(row['expected_loss']):,.0f}"
                )
                for _, row in unprotected.sort_values("expected_loss", ascending=False)
                .head(2)
                .iterrows()
            )
    if top_rows.empty:
        actions = (
            "현재 예산에서는 미충족 SKU가 없습니다. 시나리오 악화 조건을 먼저 점검하세요.",
            "고충격 시나리오에서 추가 예산이 필요한지 What-if 화면으로 확인하세요.",
            "실제 발주 전 운송 중 재고와 최소주문수량을 반영하세요.",
        )
        evidence = ("모든 SKU가 현재 조건에서 필요한 안전재고를 확보했습니다.",)
    else:
        first = top_rows.iloc[0]
        actions = (
            f"{first['name']}({first['sku_id']})의 발주 가능 수량과 공급사 납기를 즉시 확인하세요.",
            "A등급 또는 Z등급 SKU의 배정 예산을 먼저 확정하고 저우선 품목 발주는 보류하세요.",
            "예산을 10%p 단위로 올렸을 때 고위험 SKU가 줄어드는 구간을 What-if에서 확인하세요.",
        )
        evidence = tuple(
            (
                f"{row['name']}({row['sku_id']}) · {row['abc_xyz']}: "
                f"부족 {int(row['unmet_quantity']):,}개, "
                f"확보율 {float(row['fulfillment_rate']):.1%}"
            )
            for _, row in top_rows.iterrows()
        )
    return CopilotBrief(headline, risk_summary, actions, evidence + service_evidence)
