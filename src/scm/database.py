"""SQLite 초기화와 분석용 데이터 로딩."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from scm.simulation import generate_sample_data

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    sku_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_cost REAL NOT NULL CHECK (unit_cost > 0),
    lead_time_days REAL NOT NULL CHECK (lead_time_days > 0),
    lead_time_std_days REAL NOT NULL CHECK (lead_time_std_days >= 0),
    service_level REAL NOT NULL CHECK (service_level >= 0.5 AND service_level < 1),
    current_stock INTEGER NOT NULL CHECK (current_stock >= 0)
);
CREATE TABLE IF NOT EXISTS sales (
    sku_id TEXT NOT NULL,
    month TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (sku_id, month),
    FOREIGN KEY (sku_id) REFERENCES products (sku_id) ON DELETE CASCADE
);
"""


def initialize_database(
    database_path: str | Path,
    *,
    seed: int = 20260622,
    replace: bool = False,
) -> Path:
    """스키마를 만들고 비어 있는 DB에 표본 데이터를 적재한다."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    products, sales = generate_sample_data(seed)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        row_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if replace or row_count == 0:
            connection.execute("DELETE FROM sales")
            connection.execute("DELETE FROM products")
            products.to_sql("products", connection, if_exists="append", index=False)
            sales.to_sql("sales", connection, if_exists="append", index=False)
    return path


def load_data(database_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """SQLite에서 제품과 판매 이력을 읽는다."""

    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(f"데이터베이스가 없습니다: {path}")
    with sqlite3.connect(path) as connection:
        products = pd.read_sql_query("SELECT * FROM products ORDER BY sku_id", connection)
        sales = pd.read_sql_query(
            "SELECT * FROM sales ORDER BY sku_id, month", connection, parse_dates=["month"]
        )
    return products, sales

