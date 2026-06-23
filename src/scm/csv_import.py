"""사용자 업로드용 단일 CSV 형식을 검증하고 분석 데이터로 변환한다."""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

PRODUCT_COLUMNS = [
    "sku_id",
    "name",
    "category",
    "unit_cost",
    "lead_time_days",
    "lead_time_std_days",
    "service_level",
    "current_stock",
]
SALES_COLUMNS = ["sku_id", "month", "quantity"]
CSV_COLUMNS = [*PRODUCT_COLUMNS, "month", "quantity"]


def load_inventory_csv(source: str | Path | IO[bytes]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """제품 정보가 판매 이력 행마다 반복되는 업로드 CSV를 읽는다."""

    frame = pd.read_csv(source)
    missing = set(CSV_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"CSV 필수 열 누락: {', '.join(sorted(missing))}")
    frame = frame.loc[:, CSV_COLUMNS].copy()
    if frame.empty:
        raise ValueError("CSV에 데이터가 없습니다.")
    frame["sku_id"] = frame["sku_id"].astype(str).str.strip()
    frame["month"] = pd.to_datetime(frame["month"], errors="coerce")
    numeric_columns = [
        "unit_cost",
        "lead_time_days",
        "lead_time_std_days",
        "service_level",
        "current_stock",
        "quantity",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[CSV_COLUMNS].isna().any().any() or (frame["sku_id"] == "").any():
        raise ValueError("빈 값 또는 변환할 수 없는 날짜·숫자가 있습니다.")
    if frame[["sku_id", "month"]].duplicated().any():
        raise ValueError("같은 SKU와 월이 중복되어 있습니다.")
    if (frame[["quantity", "current_stock", "lead_time_std_days"]] < 0).any().any():
        raise ValueError("판매량, 현재고, 리드타임 표준편차는 0 이상이어야 합니다.")
    if (frame[["unit_cost", "lead_time_days"]] <= 0).any().any():
        raise ValueError("단가와 리드타임은 0보다 커야 합니다.")
    if not frame["service_level"].between(0.5, 0.9999).all():
        raise ValueError("서비스 수준은 0.5 이상 0.9999 이하여야 합니다.")
    metadata_counts = frame.groupby("sku_id")[PRODUCT_COLUMNS[1:]].nunique(dropna=False)
    if (metadata_counts > 1).any().any():
        raise ValueError("같은 SKU의 제품 정보가 행마다 다릅니다.")
    period_counts = frame.groupby("sku_id")["month"].nunique()
    if (period_counts < 2).any():
        raise ValueError("각 SKU에는 최소 2개월의 판매 이력이 필요합니다.")

    products = frame[PRODUCT_COLUMNS].drop_duplicates("sku_id").sort_values("sku_id")
    products["current_stock"] = products["current_stock"].astype(int)
    sales = frame[SALES_COLUMNS].sort_values(["sku_id", "month"])
    sales["quantity"] = sales["quantity"].astype(int)
    return products.reset_index(drop=True), sales.reset_index(drop=True)


def flatten_inventory_data(products: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    """제품과 판매 이력을 업로드 가능한 단일 CSV 형태로 결합한다."""

    frame = sales.merge(products, on="sku_id", validate="many_to_one")
    return frame.loc[:, CSV_COLUMNS].sort_values(["sku_id", "month"]).reset_index(drop=True)

