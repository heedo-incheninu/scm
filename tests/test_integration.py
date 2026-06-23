from __future__ import annotations

import pytest

from scm.analysis import analyze_inventory


def test_end_to_end_analysis(sample_data):
    products, sales = sample_data
    result = analyze_inventory(products, sales, scenario="moderate", budget_ratio=0.2)

    assert len(result.classification) == 30
    assert len(result.safety_stock) == 30
    assert len(result.allocation) == 30
    assert result.summary["allocated_budget"] <= result.summary["budget"] + 1e-6
    assert result.summary["priority_weighted_fulfillment"] > 0


@pytest.mark.parametrize("ratio", [-0.01, 1.01])
def test_invalid_budget_ratio_is_rejected(sample_data, ratio):
    products, sales = sample_data
    with pytest.raises(ValueError, match="budget_ratio"):
        analyze_inventory(products, sales, budget_ratio=ratio)

