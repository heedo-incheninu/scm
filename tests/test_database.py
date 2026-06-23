from __future__ import annotations

from scm.database import initialize_database, load_data


def test_database_round_trip(tmp_path):
    database = initialize_database(tmp_path / "scm.db")
    products, sales = load_data(database)

    assert len(products) == 30
    assert len(sales) == 720
    assert products["sku_id"].is_unique
    assert not sales[["sku_id", "month"]].duplicated().any()


def test_initialization_is_idempotent(tmp_path):
    database = tmp_path / "scm.db"
    initialize_database(database)
    initialize_database(database)
    products, sales = load_data(database)

    assert len(products) == 30
    assert len(sales) == 720

