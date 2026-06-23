from __future__ import annotations

import pandas as pd

from scm.simulation import generate_sample_data


def test_sample_data_is_deterministic_and_valid():
    products, sales = generate_sample_data(seed=42)
    products_again, sales_again = generate_sample_data(seed=42)

    pd.testing.assert_frame_equal(products, products_again)
    pd.testing.assert_frame_equal(sales, sales_again)
    assert len(products) == 30
    assert len(sales) == 30 * 24
    assert products["sku_id"].is_unique
    assert "산업용 리튬 배터리팩" in products["name"].tolist()
    assert not products["name"].str.contains("수입품목|카테고리", regex=True).any()
    assert not sales[["sku_id", "month"]].duplicated().any()
    assert (sales["quantity"] >= 0).all()
