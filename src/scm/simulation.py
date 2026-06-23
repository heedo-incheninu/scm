"""재현 가능한 SCM 이론 기반 PoC 데이터를 생성한다."""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_PRODUCT_CATALOG = [
    ("산업용 리튬 배터리팩", "전기전자"),
    ("스마트폰 OLED 패널", "전기전자"),
    ("차량용 반도체 MCU", "전기전자"),
    ("의료용 니트릴 장갑", "의료소모품"),
    ("냉동 연어 필렛", "식품원료"),
    ("공기청정기 HEPA 필터", "생활가전"),
    ("전기자전거 모터 킷", "모빌리티"),
    ("에스프레소 원두 블렌드", "식품원료"),
    ("산업용 볼베어링 세트", "기계부품"),
    ("서버용 NVMe SSD 모듈", "전기전자"),
    ("자동차 브레이크 패드", "자동차부품"),
    ("스테인리스 주방용기 세트", "생활용품"),
    ("스마트워치 강화유리", "전기전자"),
    ("친환경 세탁세제 원액", "생활화학"),
    ("프리미엄 고무 패킹", "기계부품"),
    ("소형 인버터 모듈", "전기전자"),
    ("유아용 면 기저귀", "유아용품"),
    ("냉장 컨테이너 센서", "물류장비"),
    ("산업용 라벨 프린터", "사무장비"),
    ("고단백 식물성 파우더", "식품원료"),
    ("LED 조명 드라이버", "전기전자"),
    ("정수기 카본 필터", "생활가전"),
    ("전동공구 배터리 셀", "공구부품"),
    ("방수 아웃도어 재킷", "패션상품"),
    ("초음파 진단 젤", "의료소모품"),
    ("플라스틱 사출 하우징", "산업소재"),
    ("무선 공유기 안테나", "통신장비"),
    ("프리미엄 코코아 원두", "식품원료"),
    ("자동차 와이어링 하네스", "자동차부품"),
    ("스마트 물류 태그", "물류장비"),
]


def _demand_pattern(
    rng: np.random.Generator,
    base: float,
    xyz: str,
    periods: int,
    phase: float,
) -> np.ndarray:
    months = np.arange(periods)
    if xyz == "X":
        factor = rng.normal(1.0, 0.06, periods)
    elif xyz == "Y":
        seasonal = 0.42 * np.sin((2 * np.pi * months / 12) + phase)
        factor = 1.0 + seasonal + rng.normal(0.0, 0.12, periods)
    else:
        factor = rng.lognormal(mean=-0.18, sigma=0.78, size=periods)
        factor[rng.random(periods) < 0.28] = 0.0
        spike_months = rng.choice(periods, size=2, replace=False)
        factor[spike_months] *= 2.5
    return np.maximum(np.rint(base * np.clip(factor, 0, None)), 0).astype(int)


def generate_sample_data(seed: int = 20260622) -> tuple[pd.DataFrame, pd.DataFrame]:
    """30개 SKU와 24개월 판매 이력을 생성한다.

    매출 규모 A/B/C 후보군마다 X/Y/Z 수요 패턴이 최소 3개씩 포함되도록
    구성한다. 최종 등급은 생성 후 실제 매출과 변동계수로 다시 계산한다.
    """

    rng = np.random.default_rng(seed)
    months = pd.date_range("2024-01-01", periods=24, freq="MS")
    products: list[dict[str, object]] = []
    sales: list[dict[str, object]] = []
    abc_revenue = {"A": 300_000.0, "B": 55_000.0, "C": 13_000.0}
    xyz_cycle = ["X", "Y", "Z", "X", "Y", "Z", "X", "Y", "Z", "X"]

    sku_number = 1
    for abc in ("A", "B", "C"):
        for group_index, xyz in enumerate(xyz_cycle):
            sku_id = f"SKU-{sku_number:03d}"
            unit_cost = float(rng.integers(18, 145))
            target_annual_revenue = abc_revenue[abc] * rng.uniform(0.92, 1.08)
            base_monthly_demand = max(target_annual_revenue / unit_cost / 12, 3)
            quantities = _demand_pattern(
                rng,
                base_monthly_demand,
                xyz,
                len(months),
                phase=group_index * 0.45,
            )
            current_stock = int(max(round(base_monthly_demand * rng.uniform(0.05, 0.18)), 0))
            product_name, category = DEFAULT_PRODUCT_CATALOG[sku_number - 1]
            products.append(
                {
                    "sku_id": sku_id,
                    "name": product_name,
                    "category": category,
                    "unit_cost": round(unit_cost, 2),
                    "lead_time_days": round(float(rng.normal(44.0, 2.5)), 2),
                    "lead_time_std_days": round(float(rng.normal(10.5, 0.8)), 2),
                    "service_level": 0.95,
                    "current_stock": current_stock,
                }
            )
            for month, quantity in zip(months, quantities, strict=True):
                sales.append(
                    {
                        "sku_id": sku_id,
                        "month": month.strftime("%Y-%m-%d"),
                        "quantity": int(quantity),
                    }
                )
            sku_number += 1

    return pd.DataFrame(products), pd.DataFrame(sales)
