from __future__ import annotations

import pandas as pd
import pytest

from scm.route_risk import calculate_route_concentration, classify_route_hhi


def test_single_route_is_full_concentration():
    allocation = pd.DataFrame(
        {
            "route": ["상하이-부산", "상하이-부산"],
            "service_allocated_budget": [60.0, 40.0],
        }
    )

    result = calculate_route_concentration(allocation)

    assert result.hhi == pytest.approx(1.0)
    assert result.status == "위험"
    assert result.top_route == "상하이-부산"
    assert result.top_share == pytest.approx(1.0)


def test_equal_budget_across_four_routes_is_low_concentration():
    allocation = pd.DataFrame(
        {
            "route": ["A", "B", "C", "D"],
            "service_allocated_budget": [25.0, 25.0, 25.0, 25.0],
        }
    )

    result = calculate_route_concentration(allocation)

    assert result.hhi == pytest.approx(0.25)
    assert result.status == "양호"
    assert result.route_count == 4


def test_missing_route_information_returns_unavailable_without_mutating_input():
    allocation = pd.DataFrame({"service_allocated_budget": [70.0, 30.0]})
    original = allocation.copy(deep=True)

    result = calculate_route_concentration(allocation)

    assert result.hhi is None
    assert result.status == "정보 없음"
    assert result.coverage_ratio == 0
    pd.testing.assert_frame_equal(allocation, original)


def test_partial_route_information_reports_coverage():
    allocation = pd.DataFrame(
        {
            "route": ["상하이-부산", "미지정", "호치민-부산"],
            "service_allocated_budget": [40.0, 20.0, 40.0],
        }
    )

    result = calculate_route_concentration(allocation)

    assert result.coverage_ratio == pytest.approx(0.8)
    assert result.hhi == pytest.approx(0.5)
    assert result.status == "주의"


def test_invalid_hhi_and_negative_budget_are_rejected():
    with pytest.raises(ValueError, match="HHI"):
        classify_route_hhi(1.1)

    allocation = pd.DataFrame(
        {"route": ["상하이-부산"], "service_allocated_budget": [-1.0]}
    )
    with pytest.raises(ValueError, match="0 이상"):
        calculate_route_concentration(allocation)
