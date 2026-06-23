from __future__ import annotations

import pytest

from scm.classification import classify_skus
from scm.comparison import compare_strategies
from scm.safety_stock import calculate_safety_stock


@pytest.fixture
def safety_frame(sample_data):
    products, sales = sample_data
    return calculate_safety_stock(classify_skus(products, sales), "moderate")


def test_four_strategies_are_compared_at_every_budget(safety_frame):
    comparison = compare_strategies(safety_frame, [0.1, 0.2, 0.5, 1.0])

    assert len(comparison) == 16
    assert set(comparison["strategy"]) == {
        "equal",
        "proportional",
        "priority",
        "service_level",
    }
    assert comparison.groupby("budget_ratio")["strategy"].nunique().eq(4).all()
    assert comparison["weighted_fulfillment"].between(0, 1).all()
    assert {"unprotected_skus", "expected_loss"}.issubset(comparison.columns)


def test_priority_strategy_beats_proportional_at_twenty_percent(safety_frame):
    comparison = compare_strategies(safety_frame, [0.2]).set_index("strategy")

    assert (
        comparison.loc["priority", "weighted_fulfillment"]
        > comparison.loc["proportional", "weighted_fulfillment"]
    )


def test_invalid_comparison_ratio_is_rejected(safety_frame):
    with pytest.raises(ValueError, match="예산 비율"):
        compare_strategies(safety_frame, [1.1])
