from __future__ import annotations

import pytest

from scm.classification import classify_skus
from scm.safety_stock import calculate_safety_stock
from scm.service_level_allocation import (
    allocate_service_levels,
    build_service_level_options,
    calculate_unprotected_losses,
    service_level_full_budget,
    weighted_service_level,
)


@pytest.fixture
def safety_frame(sample_data):
    products, sales = sample_data
    return calculate_safety_stock(classify_skus(products, sales), "moderate")


def test_service_level_options_reuse_sigma_l_safety_stock_formula(safety_frame):
    options = build_service_level_options(safety_frame)
    service_95 = options[options["service_level"] == 0.95].set_index("sku_id")
    safety = safety_frame.set_index("sku_id")

    assert (service_95["service_recommended_stock"] == safety["recommended_stock"]).all()


def test_service_level_allocation_selects_one_option_per_sku_and_stays_in_budget(
    safety_frame,
):
    budget = service_level_full_budget(safety_frame) * 0.2
    allocation = allocate_service_levels(safety_frame, budget)

    assert allocation["sku_id"].is_unique
    assert len(allocation) == len(safety_frame)
    assert float(allocation["service_allocated_budget"].sum()) <= budget + 1e-6
    assert allocation["service_level"].between(0, 0.99).all()


def test_zero_budget_leaves_all_skus_unprotected(safety_frame):
    allocation = allocate_service_levels(safety_frame, 0)
    with_loss = calculate_unprotected_losses(allocation)

    assert (with_loss["service_level"] == 0).all()
    assert float(with_loss["service_allocated_budget"].sum()) == 0.0
    assert float(with_loss["expected_loss"].sum()) > 0


def test_weighted_service_level_improves_when_budget_increases(safety_frame):
    full_budget = service_level_full_budget(safety_frame)
    low = allocate_service_levels(safety_frame, full_budget * 0.1)
    high = allocate_service_levels(safety_frame, full_budget * 0.5)

    assert weighted_service_level(high) >= weighted_service_level(low)

