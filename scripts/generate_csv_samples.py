"""CSV 업로드 데모용 가상 기업 데이터 5종을 생성한다."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scm.csv_import import flatten_inventory_data
from scm.simulation import generate_sample_data

OUTPUT_DIR = Path("csv")
PROFILES = [
    {
        "filename": "01_electronics_stable.csv",
        "seed": 1101,
        "prefix": "전자부품",
        "cost_factor": 1.35,
        "lead_factor": 1.15,
        "service_level": 0.95,
        "demand": "base",
    },
    {
        "filename": "02_food_seasonal.csv",
        "seed": 2202,
        "prefix": "식품원료",
        "cost_factor": 0.65,
        "lead_factor": 0.85,
        "service_level": 0.96,
        "demand": "seasonal",
    },
    {
        "filename": "03_auto_parts_volatile.csv",
        "seed": 3303,
        "prefix": "자동차부품",
        "cost_factor": 1.8,
        "lead_factor": 1.25,
        "service_level": 0.95,
        "demand": "volatile",
    },
    {
        "filename": "04_medical_high_service.csv",
        "seed": 4404,
        "prefix": "의료소모품",
        "cost_factor": 1.1,
        "lead_factor": 1.0,
        "service_level": 0.99,
        "demand": "base",
    },
    {
        "filename": "05_fashion_peak.csv",
        "seed": 5505,
        "prefix": "패션상품",
        "cost_factor": 0.9,
        "lead_factor": 1.05,
        "service_level": 0.94,
        "demand": "peak",
    },
]

PROFILE_PRODUCT_NAMES = {
    "전자부품": [
        "차량용 전력관리 IC",
        "스마트폰 OLED 구동칩",
        "서버용 NVMe 컨트롤러",
        "산업용 온도 센서",
        "고속 충전 USB-C 포트",
        "리튬 배터리 보호회로",
        "와이파이 6 안테나 모듈",
        "전기차 BMS 커넥터",
        "소형 카메라 이미지센서",
        "LED 조명 드라이버",
        "로봇 제어용 MCU",
        "태블릿 터치 컨트롤러",
        "스마트워치 진동 모터",
        "산업용 릴레이 보드",
        "광통신 송수신 모듈",
        "전원 어댑터 코일",
        "고내열 세라믹 콘덴서",
        "차량용 레이더 보드",
        "디스플레이 FPCB",
        "블루투스 오디오 칩셋",
        "서버 냉각 팬 모듈",
        "전류 감지 저항",
        "의료기기 전원 모듈",
        "스마트미터 통신 보드",
        "산업용 터치 패널",
        "드론 GPS 모듈",
        "모터 제어 인버터",
        "임베디드 메모리 카드",
        "방수 원형 커넥터",
        "고속 데이터 케이블",
    ],
    "식품원료": [
        "냉동 연어 필렛",
        "프리미엄 코코아 원두",
        "아라비카 커피 생두",
        "비건 단백질 파우더",
        "유기농 귀리 플레이크",
        "냉동 망고 다이스",
        "천연 바닐라 익스트랙트",
        "토마토 페이스트 드럼",
        "고올레산 해바라기유",
        "무수 구연산",
        "그릭요거트 스타터",
        "분말 치즈 시즈닝",
        "건조 양파 플레이크",
        "볶음 참깨 원료",
        "냉동 새우살",
        "농축 레몬 주스",
        "사탕수수 원당",
        "아몬드 슬라이스",
        "천일염 플레이크",
        "말차 파우더",
        "냉동 블루베리",
        "코코넛 밀크 파우더",
        "비프 엑기스 베이스",
        "옥수수 전분",
        "바질 페스토 원료",
        "캐슈넛 분태",
        "고추장 베이스",
        "감자 플레이크",
        "해조 칼슘 분말",
        "냉동 아보카도 퓨레",
    ],
    "자동차부품": [
        "전기차 배터리 하우징",
        "차량용 반도체 MCU",
        "브레이크 패드 세트",
        "와이어링 하네스",
        "전동식 워터펌프",
        "타이어 공기압 센서",
        "LED 헤드램프 모듈",
        "ABS 유압 밸브",
        "스티어링 조인트",
        "에어컨 컴프레서",
        "차량용 카메라 렌즈",
        "파워윈도우 모터",
        "고전압 커넥터",
        "연료 펌프 어셈블리",
        "인포테인먼트 보드",
        "도어 래치 모듈",
        "서스펜션 부싱",
        "라디에이터 팬",
        "시트 히터 패드",
        "자동변속기 솔레노이드",
        "촉매 컨버터 센서",
        "차량용 무선충전 코일",
        "트렁크 쇼크 업소버",
        "전방 레이더 브래킷",
        "냉각수 호스 세트",
        "후방 주차 센서",
        "배터리 셀 버스바",
        "클러치 베어링",
        "엔진 마운트",
        "차량용 이더넷 케이블",
    ],
    "의료소모품": [
        "의료용 니트릴 장갑",
        "멸균 주사기",
        "수술용 드레이프",
        "초음파 진단 젤",
        "혈당 시험지",
        "일회용 산소 마스크",
        "멸균 거즈 패드",
        "IV 카테터",
        "검체 채취 튜브",
        "수액 세트",
        "의료용 알코올 솜",
        "멸균 봉합사",
        "치과용 석션 팁",
        "체온계 프로브 커버",
        "일회용 내시경 밸브",
        "감염관리 가운",
        "투석 라인 세트",
        "의료용 흡수 패드",
        "산소 캐뉼라",
        "멸균 시험 장갑",
        "주사침 안전캡",
        "소독용 포비돈 스틱",
        "검사 키트 버퍼액",
        "혈액백 튜브",
        "정형외과 캐스트 패드",
        "수술용 흡인 튜브",
        "일회용 샤프 컨테이너",
        "창상 드레싱 필름",
        "의료용 실리콘 튜브",
        "무균 포장 파우치",
    ],
    "패션상품": [
        "방수 아웃도어 재킷",
        "코튼 오버핏 셔츠",
        "울 블렌드 코트",
        "러닝 압박 레깅스",
        "친환경 데님 팬츠",
        "캐시미어 니트",
        "캔버스 토트백",
        "비건 레더 스니커즈",
        "경량 패딩 베스트",
        "기능성 골프 장갑",
        "리넨 와이드 팬츠",
        "실크 스카프",
        "플리스 후드 집업",
        "아동용 레인부츠",
        "스트레치 요가 탑",
        "메리노 울 양말",
        "여행용 크로스백",
        "발수 트렌치코트",
        "쿨링 스포츠 티셔츠",
        "가죽 벨트",
        "패딩 머플러",
        "에코 퍼 재킷",
        "니트 비니",
        "방한 부츠",
        "비치웨어 래시가드",
        "슬림핏 슬랙스",
        "소프트 브라렛",
        "캠핑 방풍 팬츠",
        "새틴 파자마 세트",
        "클래식 로퍼",
    ],
}

PROFILE_CATEGORIES = {
    "전자부품": ["반도체", "센서", "전원부품", "통신모듈", "케이블"],
    "식품원료": ["냉동식품", "분말원료", "오일·소스", "견과·곡물", "조미원료"],
    "자동차부품": ["전장부품", "구동부품", "차체부품", "냉각부품", "안전부품"],
    "의료소모품": ["멸균소모품", "검사소모품", "감염관리", "수술소모품", "튜브·라인"],
    "패션상품": ["아우터", "상의", "하의", "액세서리", "신발"],
}


def _adjust_demand(sales: pd.DataFrame, mode: str, seed: int) -> pd.DataFrame:
    result = sales.copy()
    months = pd.to_datetime(result["month"]).dt.month
    if mode == "seasonal":
        factors = 1 + 0.35 * np.sin(2 * np.pi * (months - 2) / 12)
        result["quantity"] = np.rint(result["quantity"] * factors.clip(lower=0.4)).astype(int)
    elif mode == "volatile":
        rng = np.random.default_rng(seed)
        factors = rng.lognormal(mean=-0.05, sigma=0.35, size=len(result))
        result["quantity"] = np.rint(result["quantity"] * factors).astype(int)
    elif mode == "peak":
        factors = months.map({10: 1.35, 11: 1.8, 12: 2.1}).fillna(0.85)
        result["quantity"] = np.rint(result["quantity"] * factors).astype(int)
    return result


def generate_files(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for profile in PROFILES:
        products, sales = generate_sample_data(seed=int(profile["seed"]))
        prefix = str(profile["prefix"])
        products["name"] = PROFILE_PRODUCT_NAMES[prefix]
        categories = PROFILE_CATEGORIES[prefix]
        products["category"] = [categories[index % len(categories)] for index in range(30)]
        products["unit_cost"] = (products["unit_cost"] * float(profile["cost_factor"])).round(2)
        products["lead_time_days"] = (
            products["lead_time_days"] * float(profile["lead_factor"])
        ).round(2)
        products["lead_time_std_days"] = (
            products["lead_time_std_days"] * float(profile["lead_factor"])
        ).round(2)
        products["service_level"] = float(profile["service_level"])
        sales = _adjust_demand(sales, str(profile["demand"]), int(profile["seed"]))
        path = output_dir / str(profile["filename"])
        flatten_inventory_data(products, sales).to_csv(path, index=False, encoding="utf-8-sig")
        generated.append(path)
    return generated


if __name__ == "__main__":
    for generated_path in generate_files():
        print(generated_path)
