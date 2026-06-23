from __future__ import annotations

import pytest

from scm.allocation import (
    allocate_budget,
    allocate_equally,
    allocate_proportionally,
    allocation_summary,
)
from scm.classification import classify_skus
from scm.safety_stock import calculate_safety_stock


@pytest.fixture
def safety_frame(sample_data):
    products, sales = sample_data
    return calculate_safety_stock(classify_skus(products, sales), "moderate")


@pytest.mark.parametrize("ratio", [0.0, 0.2, 1.0])
def test_allocation_never_exceeds_budget_or_need(safety_frame, ratio):
    budget = float(safety_frame["required_budget"].sum()) * ratio
    allocated = allocate_budget(safety_frame, budget)

    assert float(allocated["allocated_budget"].sum()) <= budget + 1e-6
    assert (allocated["allocated_quantity"] <= allocated["required_quantity"]).all()
    assert (allocated["allocated_quantity"] >= 0).all()


def test_priority_allocation_improves_weighted_fulfillment(safety_frame):
    budget = float(safety_frame["required_budget"].sum()) * 0.2
    prioritized = allocate_budget(safety_frame, budget)
    baseline = allocate_proportionally(safety_frame, budget)
    summary = allocation_summary(prioritized, baseline, budget)

    assert summary["priority_weighted_fulfillment"] > summary["baseline_weighted_fulfillment"]
    assert summary["relative_improvement"] > 0


def test_negative_budget_is_rejected(safety_frame):
    with pytest.raises(ValueError, match="예산"):
        allocate_budget(safety_frame, -1)


def test_equal_allocation_uses_same_budget_cap_per_sku(safety_frame):
    budget = float(safety_frame["required_budget"].sum()) * 0.2
    allocated = allocate_equally(safety_frame, budget)

    assert float(allocated["allocated_budget"].sum()) <= budget + 1e-6
    assert (allocated["allocated_quantity"] <= allocated["required_quantity"]).all()

