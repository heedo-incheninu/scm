\# 시스템 설계서



\## 기술 스택



| 항목 | 내용 |

|------|------|

| 언어 | Python 3.14 |

| 웹 프레임워크 | Streamlit |

| DB | SQLite |

| 데이터 처리 | pandas, numpy |

| 통계/예측 | scipy, statsmodels |

| 시각화 | plotly |

| AI 진단 | anthropic (Claude API) |

| 실행 명령어 | py -m streamlit run app.py |



\## 파일 구조

scm-platform/

├── app.py

├── requirements.txt

├── .env                          # API 키 (GitHub 비공개)

├── .gitignore

├── data/

│   └── sku\_data.csv

├── database/

│   └── scm.db                    # 자동 생성

├── modules/

│   ├── module1\_demand.py

│   ├── module2\_inventory.py

│   ├── module3\_forecast.py

│   ├── module4\_strategy.py

│   └── module5\_scenario.py

├── utils/

│   ├── db\_manager.py

│   └── ai\_diagnosis.py

└── docs/                         # 기획/설계 문서



\## 시스템 흐름

\[기준정보 탭] 최초 1회 데이터 등록

│

▼

\[Module 1] 수입 품목 수요 진단

ABC-XYZ 분류 + 해상 의존도 분류

│

▼

\[Module 2] 해상 LT 리스크 기반 재고 정책

σL 포함 안전재고 + 현재 정책 비교

│

▼

\[Module 3] 수요 예측

CV 기반 모델 자동선택 + MAPE-재고 연결

│

▼

\[Module 4] 전략 포지셔닝 맵

Fisher Map + 해상 물류 기업 오버레이

│

▼

\[Module 5] 해운 리스크 시나리오 + AI 진단

3개 시나리오 시뮬레이션 + Claude API 처방



\## DB 테이블 구조



\### sku\_master

| 컬럼 | 타입 | 설명 |

|------|------|------|

| sku\_id | TEXT PK | 품목 코드 |

| sku\_name | TEXT | 품목명 |

| category | TEXT | 카테고리 |

| unit\_price | REAL | 단가 |

| origin\_country | TEXT | 원산지 |

| maritime\_dependency | TEXT | 해상의존도 High/Mid/Low |



\### lead\_time\_info

| 컬럼 | 타입 | 설명 |

|------|------|------|

| sku\_id | TEXT | 품목 코드 |

| avg\_lead\_time | REAL | 평균 리드타임 (일) |

| std\_lead\_time | REAL | 리드타임 표준편차 (일) |

| route | TEXT | 해운 구간 |



\### sales\_history

| 컬럼 | 타입 | 설명 |

|------|------|------|

| sku\_id | TEXT | 품목 코드 |

| year | INTEGER | 연도 |

| month | INTEGER | 월 |

| quantity | REAL | 판매량 |



\## 모듈별 핵심 로직



\### Module 2 핵심 공식

안전재고 = z × √(µL × σ²D + µ²D × σ²L)

ROP = µD × µL + 안전재고

\- µL: 평균 리드타임

\- σL: 리드타임 표준편차

\- µD: 평균 수요

\- σD: 수요 표준편차



\### Module 3 모델 선택 기준

| CV | 모델 | 이유 |

|----|------|------|

| <0.5 | Holt-Winters | 안정적 계절성 |

| 0.5\~1.0 | 지수평활 | 트렌드 추적 |

| ≥1.0 | Croston's Method | 간헐 수요 |



\### Module 5 시나리오 기준값

| 시나리오 | 평균 LT | σL | 근거 |

|---------|---------|-----|------|

| 평상시 | 기준값 100% | 기준값 | 2019년 수준 |

| 경미한 차질 | +50% | +80% | 2020년 수준 |

| 해운 대란 | +150% | +200% | 2022년 실제 수준 |

