import pytest

from scm.scenario import diagnose_lead_time_scenario


@pytest.mark.parametrize(
    ("lead_time_days", "expected_scenario", "expected_message"),
    [
        (44, "normal", "평상시 수준으로 계산합니다"),
        (52, "moderate", "중간 충격 수준으로 계산합니다"),
        (80, "high", "고충격 수준으로 계산합니다"),
        (100, "extreme", "극단 충격 수준으로 계산합니다"),
    ],
)
def test_diagnose_lead_time_scenario_maps_demo_inputs(
    lead_time_days: float,
    expected_scenario: str,
    expected_message: str,
) -> None:
    diagnosis = diagnose_lead_time_scenario(lead_time_days)

    assert diagnosis.scenario == expected_scenario
    assert diagnosis.message == expected_message


@pytest.mark.parametrize(
    ("lead_time_days", "expected_scenario"),
    [
        (48.4, "normal"),
        (57.2, "moderate"),
        (88.0, "high"),
    ],
)
def test_diagnose_lead_time_scenario_includes_upper_boundaries(
    lead_time_days: float,
    expected_scenario: str,
) -> None:
    assert diagnose_lead_time_scenario(lead_time_days).scenario == expected_scenario


def test_diagnose_lead_time_scenario_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError):
        diagnose_lead_time_scenario(0)
