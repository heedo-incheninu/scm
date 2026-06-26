from scm.constants import SCENARIOS


def test_high_and_extreme_scenario_sources_are_adjustable_inputs() -> None:
    expected_source = "업계 맥락 기반 시나리오 입력값. 사용자가 상황에 따라 조정 가능"

    assert SCENARIOS["high"]["source"] == expected_source
    assert SCENARIOS["extreme"]["source"] == expected_source
    assert "Plan.md" not in SCENARIOS["high"]["source"]
    assert "Plan.md" not in SCENARIOS["extreme"]["source"]
    assert "Flexport" not in SCENARIOS["high"]["source"]
    assert "Flexport" not in SCENARIOS["extreme"]["source"]
