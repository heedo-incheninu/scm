"""프로젝트 전체에서 공유하는 기준값과 우선순위 규칙."""

from typing import Final

SCENARIOS: Final[dict[str, dict[str, float | str]]] = {
    "normal": {
        "label": "평상시",
        "multiplier": 1.0,
        "description": "평균적인 해상 운송 환경",
        "source": "World Bank, Connecting to Compete 2023",
        "source_url": (
            "https://documents1.worldbank.org/curated/en/099042123145531599/"
            "pdf/P17146804a6a570ac0a4f80895e320dda1e.pdf"
        ),
    },
    "moderate": {
        "label": "중간 충격",
        "multiplier": 1.18,
        "description": "홍해 우회처럼 납기가 약 18% 늘어난 상황",
        "source": "ITF/OECD, Red Sea Crisis 2024",
        "source_url": (
            "https://www.itf-oecd.org/sites/default/files/repositories/"
            "red-sea-crisis-impacts-global-shipping.pdf"
        ),
    },
    "high": {
        "label": "고충격",
        "multiplier": 1.8,
        "description": "2021~2022년 아시아-유럽 운송 지연 수준",
        "source": "Flexport 공개 리드타임 사례(Plan.md 조사 기록)",
        "source_url": "",
    },
    "extreme": {
        "label": "극단 충격",
        "multiplier": 2.2,
        "description": "2021~2022년 아시아-미서부 최악 지연 수준",
        "source": "Flexport 공개 리드타임 사례(Plan.md 조사 기록)",
        "source_url": "",
    },
}

# 변동성이 큰 핵심 매출 SKU(AZ)를 가장 먼저 보호한다.
PRIORITY_WEIGHTS: Final[dict[str, int]] = {
    "AZ": 10,
    "AX": 9,
    "AY": 8,
    "BZ": 7,
    "BX": 6,
    "BY": 5,
    "CZ": 4,
    "CX": 3,
    "CY": 2,
}

ABC_A_LIMIT: Final = 0.80
ABC_B_LIMIT: Final = 0.95
XYZ_X_LIMIT: Final = 0.20
XYZ_Y_LIMIT: Final = 0.50
DAYS_PER_MONTH: Final = 365.25 / 12
