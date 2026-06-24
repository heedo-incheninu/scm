from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

from scm.csv_import import CSV_COLUMNS, flatten_inventory_data, load_inventory_csv


def test_flat_csv_round_trip(sample_data):
    products, sales = sample_data
    content = flatten_inventory_data(products, sales).to_csv(index=False).encode("utf-8")
    loaded_products, loaded_sales = load_inventory_csv(io.BytesIO(content))

    assert len(loaded_products) == 30
    assert len(loaded_sales) == 720
    assert loaded_products["sku_id"].is_unique
    assert loaded_products["route"].notna().all()
    assert loaded_products["route"].nunique() > 1


def test_legacy_csv_without_route_is_still_supported(sample_data):
    products, sales = sample_data
    frame = flatten_inventory_data(products, sales).drop(columns=["route"])

    loaded_products, loaded_sales = load_inventory_csv(
        io.BytesIO(frame.to_csv(index=False).encode("utf-8"))
    )

    assert len(loaded_sales) == 720
    assert loaded_products["route"].eq("미지정").all()


def test_all_five_example_csv_files_are_valid():
    paths = sorted(Path("csv").glob("*.csv"))
    assert len(paths) == 5

    for path in paths:
        products, sales = load_inventory_csv(path)
        assert len(products) == 30, path
        assert len(sales) == 720, path
        assert products["route"].notna().all(), path
        assert not products["name"].str.contains(r"\d{2}$|수입품목|카테고리", regex=True).any()


def test_missing_column_is_rejected():
    frame = pd.DataFrame([{column: 1 for column in CSV_COLUMNS if column != "quantity"}])

    with pytest.raises(ValueError, match="필수 열"):
        load_inventory_csv(io.BytesIO(frame.to_csv(index=False).encode("utf-8")))


def test_duplicate_sku_month_is_rejected(sample_data):
    products, sales = sample_data
    frame = flatten_inventory_data(products, sales)
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="중복"):
        load_inventory_csv(io.BytesIO(frame.to_csv(index=False).encode("utf-8")))
