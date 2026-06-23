from __future__ import annotations

import pytest

from scm.whatif import simulate_what_if


def test_what_if_simulates_scenarios_and_budget_ratios(sample_data):
    products, sales = sample_data
    frame = simulate_what_if(
        products,
        sales,
        scenarios=["normal", "moderate"],
        budget_ratios=[0.1, 0.2],
    )

    assert len(frame) == 4
    assert set(frame["scenario"]) == {"normal", "moderate"}
    assert set(frame["budget_ratio"]) == {0.1, 0.2}
    assert frame["priority_weighted_fulfillment"].between(0, 1).all()
    assert (frame["high_risk_skus"] >= 0).all()


def test_what_if_uses_fixed_budget_so_scenarios_differ(sample_data):
    products, sales = sample_data
    frame = simulate_what_if(
        products,
        sales,
        scenarios=["normal", "extreme"],
        budget_ratios=[0.2],
    )

    normal = frame.loc[frame["scenario"] == "normal", "priority_weighted_fulfillment"].iloc[0]
    extreme = frame.loc[frame["scenario"] == "extreme", "priority_weighted_fulfillment"].iloc[0]

    assert normal > extreme


def test_what_if_rejects_invalid_budget_ratio(sample_data):
    products, sales = sample_data

    with pytest.raises(ValueError, match="예산 비율"):
        simulate_what_if(products, sales, budget_ratios=[1.2])
