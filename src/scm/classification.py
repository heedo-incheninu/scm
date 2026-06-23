"""SKU의 ABC-XYZ 등급과 일관된 관리 우선순위를 계산한다."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scm.constants import (
    ABC_A_LIMIT,
    ABC_B_LIMIT,
    PRIORITY_WEIGHTS,
    XYZ_X_LIMIT,
    XYZ_Y_LIMIT,
)


def classify_skus(products: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    """매출 기여도(ABC)와 수요 변동계수(XYZ)로 모든 SKU를 분류한다."""

    required_products = {"sku_id", "unit_cost"}
    required_sales = {"sku_id", "quantity"}
    if not required_products.issubset(products.columns):
        raise ValueError(f"products 필수 열 누락: {required_products - set(products.columns)}")
    if not required_sales.issubset(sales.columns):
        raise ValueError(f"sales 필수 열 누락: {required_sales - set(sales.columns)}")
    if products["sku_id"].duplicated().any():
        raise ValueError("products의 sku_id는 고유해야 합니다.")
    if sales["quantity"].isna().any() or (sales["quantity"] < 0).any():
        raise ValueError("판매량은 누락되지 않은 0 이상의 값이어야 합니다.")

    demand = sales.groupby("sku_id", as_index=False).agg(
        demand_mean=("quantity", "mean"),
        demand_std=("quantity", lambda values: values.std(ddof=0)),
        total_quantity=("quantity", "sum"),
        periods=("quantity", "count"),
    )
    metrics = products.merge(demand, on="sku_id", how="left", validate="one_to_one")
    if metrics["demand_mean"].isna().any():
        missing = metrics.loc[metrics["demand_mean"].isna(), "sku_id"].tolist()
        raise ValueError(f"판매 이력이 없는 SKU: {missing}")

    metrics["revenue"] = metrics["total_quantity"] * metrics["unit_cost"]
    total_revenue = float(metrics["revenue"].sum())
    if total_revenue <= 0:
        raise ValueError("전체 매출은 0보다 커야 합니다.")
    metrics = metrics.sort_values(["revenue", "sku_id"], ascending=[False, True]).reset_index(
        drop=True
    )
    metrics["revenue_share"] = metrics["revenue"] / total_revenue
    metrics["cumulative_share"] = metrics["revenue_share"].cumsum()
    cumulative_before = metrics["cumulative_share"] - metrics["revenue_share"]
    metrics["abc_class"] = np.select(
        [cumulative_before < ABC_A_LIMIT, cumulative_before < ABC_B_LIMIT],
        ["A", "B"],
        default="C",
    )

    metrics["coefficient_of_variation"] = np.where(
        metrics["demand_mean"] > 0,
        metrics["demand_std"] / metrics["demand_mean"],
        np.inf,
    )
    metrics["xyz_class"] = np.select(
        [
            metrics["coefficient_of_variation"] <= XYZ_X_LIMIT,
            metrics["coefficient_of_variation"] <= XYZ_Y_LIMIT,
        ],
        ["X", "Y"],
        default="Z",
    )
    metrics["abc_xyz"] = metrics["abc_class"] + metrics["xyz_class"]
    metrics["priority_weight"] = metrics["abc_xyz"].map(PRIORITY_WEIGHTS).astype(int)
    metrics["priority_rank"] = metrics["priority_weight"].rank(
        method="dense", ascending=False
    ).astype(int)
    return metrics

