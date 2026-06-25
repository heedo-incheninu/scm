"""물류 리드타임 입력값을 앱 시나리오로 변환하는 규칙."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

BASE_LEAD_TIME_DAYS: Final = 44.0


@dataclass(frozen=True)
class LeadTimeScenarioDiagnosis:
    """실제 예상 납기 기반 시나리오 진단 결과."""

    expected_lead_time_days: float
    base_lead_time_days: float
    multiplier: float
    scenario: str
    message: str


def diagnose_lead_time_scenario(
    expected_lead_time_days: float,
    *,
    base_lead_time_days: float = BASE_LEAD_TIME_DAYS,
) -> LeadTimeScenarioDiagnosis:
    """실제 예상 납기를 기준 리드타임과 비교해 충격 수준을 판정한다."""

    if expected_lead_time_days <= 0:
        raise ValueError("예상 납기는 0보다 커야 합니다.")
    if base_lead_time_days <= 0:
        raise ValueError("기준 리드타임은 0보다 커야 합니다.")

    multiplier = expected_lead_time_days / base_lead_time_days
    if multiplier <= 1.1:
        scenario = "normal"
        message = "평상시 수준으로 계산합니다"
    elif multiplier <= 1.3:
        scenario = "moderate"
        message = "중간 충격 수준으로 계산합니다"
    elif multiplier <= 2.0:
        scenario = "high"
        message = "고충격 수준으로 계산합니다"
    else:
        scenario = "extreme"
        message = "극단 충격 수준으로 계산합니다"

    return LeadTimeScenarioDiagnosis(
        expected_lead_time_days=float(expected_lead_time_days),
        base_lead_time_days=float(base_lead_time_days),
        multiplier=float(multiplier),
        scenario=scenario,
        message=message,
    )
