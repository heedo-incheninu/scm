from __future__ import annotations

import numpy as np

from scm.classification import classify_skus
from scm.constants import DAYS_PER_MONTH
from scm.safety_stock import calculate_safety_stock


def test_safety_stock_increases_with_scenario_severity(sample_data):
    products, sales = sample_data
    classified = classify_skus(products, sales)
    normal = calculate_safety_stock(classified, "normal").set_index("sku_id")
    moderate = calculate_safety_stock(classified, "moderate").set_index("sku_id")
    high = calculate_safety_stock(classified, "high").set_index("sku_id")
    extreme = calculate_safety_stock(classified, "extreme").set_index("sku_id")

    assert (normal["recommended_stock"] <= moderate["recommended_stock"]).all()
    assert (moderate["recommended_stock"] <= high["recommended_stock"]).all()
    assert (high["recommended_stock"] <= extreme["recommended_stock"]).all()
    assert (extreme["required_budget"] >= 0).all()


def test_crisis_multiplier_applies_only_to_mean_lead_time(sample_data):
    products, sales = sample_data
    classified = classify_skus(products, sales)
    normal = calculate_safety_stock(classified, "normal").set_index("sku_id")
    high = calculate_safety_stock(classified, "high").set_index("sku_id")

    assert np.allclose(high["lead_time_months"], normal["lead_time_months"] * 1.8)
    assert np.allclose(high["lead_time_std_months"], normal["lead_time_std_months"])
    assert np.allclose(
        high["lead_time_std_months"],
        classified.set_index("sku_id")["lead_time_std_days"] / DAYS_PER_MONTH,
    )
    assert (high["lead_time_multiplier"] == 1.8).all()


def test_safety_stock_uses_crisis_mean_and_unscaled_lead_time_variability(sample_data):
    products, sales = sample_data
    classified = classify_skus(products, sales).set_index("sku_id")
    high = calculate_safety_stock(classified.reset_index(), "high").set_index("sku_id")

    expected_variance = (
        high["lead_time_months"] * classified["demand_std"].pow(2)
        + classified["demand_mean"].pow(2)
        * (classified["lead_time_std_days"] / DAYS_PER_MONTH).pow(2)
    )
    expected_safety_stock = high["z_score"] * np.sqrt(expected_variance.clip(lower=0))

    assert np.allclose(high["safety_stock"], expected_safety_stock)


def test_invalid_scenario_is_rejected(sample_data):
    products, sales = sample_data
    classified = classify_skus(products, sales)

    try:
        calculate_safety_stock(classified, "unknown")
    except ValueError as exc:
        assert "지원하지 않는 시나리오" in str(exc)
    else:
        raise AssertionError("잘못된 시나리오가 허용되었습니다.")
