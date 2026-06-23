from __future__ import annotations

from scm.classification import classify_skus


def test_all_skus_receive_one_class_and_all_cells_are_represented(sample_data):
    products, sales = sample_data
    classified = classify_skus(products, sales)

    assert len(classified) == 30
    assert classified["sku_id"].is_unique
    assert set(classified["abc_class"]) == {"A", "B", "C"}
    assert set(classified["xyz_class"]) == {"X", "Y", "Z"}
    assert set(classified["abc_xyz"]) == {
        "AX",
        "AY",
        "AZ",
        "BX",
        "BY",
        "BZ",
        "CX",
        "CY",
        "CZ",
    }
    assert classified["priority_weight"].notna().all()


def test_az_uses_the_highest_priority_weight(sample_data):
    products, sales = sample_data
    classified = classify_skus(products, sales)
    weights = classified.groupby("abc_xyz")["priority_weight"].first()

    assert weights["AZ"] == weights.max()

