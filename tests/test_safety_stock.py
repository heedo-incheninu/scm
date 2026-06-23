from __future__ import annotations

from scm.classification import classify_skus
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


def test_invalid_scenario_is_rejected(sample_data):
    products, sales = sample_data
    classified = classify_skus(products, sales)

    try:
        calculate_safety_stock(classified, "unknown")
    except ValueError as exc:
        assert "지원하지 않는 시나리오" in str(exc)
    else:
        raise AssertionError("잘못된 시나리오가 허용되었습니다.")

