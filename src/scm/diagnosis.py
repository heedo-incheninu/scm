"""분석 결과를 OpenAI Responses API 또는 결정론적 데모 진단으로 설명한다."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DiagnosisResult:
    text: str
    mode: str
    warning: str | None = None


def _risk_rows(allocation: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    return allocation.sort_values(
        ["priority_weight", "unmet_quantity"], ascending=[False, False]
    ).head(limit)


def build_prompt(allocation: pd.DataFrame, scenario_label: str, budget_ratio: float) -> str:
    """원시 판매 이력 없이 집계된 의사결정 결과만 포함한 프롬프트를 만든다."""

    rows = _risk_rows(allocation)
    items = "\n".join(
        (
            f"- {row.sku_id}: 등급 {row.abc_xyz}, 필요 {row.required_quantity}개, "
            f"배정 {row.allocated_quantity}개, 미충족 {row.unmet_quantity}개"
        )
        for row in rows.itertuples()
    )
    return f"""당신은 수입 중소기업의 SCM 의사결정 지원 분석가입니다.
시나리오: {scenario_label}
가용 예산: 전체 필요 예산의 {budget_ratio:.0%}
우선 검토 SKU:
{items}

다음 형식으로 한국어로 간결하게 답하세요.
1. 위험 요약
2. 즉시 실행할 조치 3개
3. 판단의 한계
마크다운 문법을 사용하지 말고 plain text로만 출력하세요.
수치를 과장하거나 입력에 없는 원인을 단정하지 마세요.
"""


def demo_diagnosis(
    allocation: pd.DataFrame,
    scenario_label: str,
    budget_ratio: float,
) -> str:
    """네트워크나 API 키 없이도 재현되는 규칙 기반 진단을 반환한다."""

    rows = _risk_rows(allocation)
    at_risk = rows[rows["unmet_quantity"] > 0]
    top = at_risk.iloc[0] if not at_risk.empty else rows.iloc[0]
    fully_funded = int((allocation["fulfillment_rate"] >= 1).sum())
    return f"""위험 요약
{scenario_label}에서 전체 필요 예산의 {budget_ratio:.0%}만 사용할 수 있습니다.
우선순위 배분 결과 {fully_funded}개 SKU가 필요 안전재고를 모두 확보했습니다.
가장 먼저 확인할 품목은 {top['sku_id']}({top['abc_xyz']})이며
미충족 수량은 {int(top['unmet_quantity']):,}개입니다.

즉시 실행할 조치
1. {top['sku_id']}의 발주 가능 수량과 공급사 납기를 우선 확인합니다.
2. A등급 중 충족률이 낮은 SKU의 배정 예산을 확정하고 저우선 품목 발주를 보류합니다.
3. 실제 리드타임과 판매 실적을 갱신한 뒤 같은 시나리오로 다시 계산합니다.

판단의 한계
이 결과는 시뮬레이션 수요와 공개 리드타임 근거를 사용한 PoC 분석입니다.
실제 발주 전 최소주문수량, 운송 중 재고, 공급사 제약을 추가로 확인해야 합니다.
"""


def generate_diagnosis(
    allocation: pd.DataFrame,
    scenario_label: str,
    budget_ratio: float,
    *,
    api_key: str | None = None,
    model: str = "gpt-5.5",
    force_demo: bool = False,
) -> DiagnosisResult:
    """OpenAI 진단을 요청하고 실패 시 안전하게 데모 진단으로 전환한다."""

    fallback = demo_diagnosis(allocation, scenario_label, budget_ratio)
    if force_demo or not api_key:
        warning = None if force_demo else "API 키가 없어 데모 진단을 표시합니다."
        return DiagnosisResult(fallback, "demo", warning)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            reasoning={"effort": "low"},
            input=build_prompt(allocation, scenario_label, budget_ratio),
        )
        text = response.output_text.strip()
        if not text:
            raise ValueError("OpenAI API가 텍스트를 반환하지 않았습니다.")
        return DiagnosisResult(text, "openai")
    except Exception as exc:  # API 오류가 핵심 계산 결과를 가리지 않게 한다.
        return DiagnosisResult(fallback, "demo", f"OpenAI 호출 실패로 데모 모드 전환: {exc}")
