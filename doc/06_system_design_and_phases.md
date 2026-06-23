06번 통합 문서가 더 빠르다. 한 번에 준다.



cmd에서:

cd docs

notepad 06\_system\_design\_and\_phases.md

아래 내용 전부 복사해서 붙여넣고 저장.

markdown# 시스템 설계 및 개발단계 (v6 기준 - 01\~03 통합/대체)



본 문서는 05\_solution\_logic\_and\_validation.md(v6)를 기준으로

01\~03번 문서를 대체한다. 01\~03은 구버전(5모듈+FisherMap중심)

아카이브로 보존.



\---



\## 1. 시스템 한줄소개



해상 리드타임 위기 시나리오 하에서, ABC-XYZ로 분류된 SKU별

σL포함 안전재고를 계산하고, 한정된 예산을 결품손실/추가비용

효율 순으로 배분하여 우선순위를 처방하며, AI가 그 결과를

해석한다.



\---



\## 2. 핵심 컴포넌트 (우선순위 순)



| 순위 | 컴포넌트 | 분류 |

|------|---------|------|

| 1 | ABC-XYZ 분류 | 핵심 |

| 2 | σL포함 안전재고 + 시나리오(1.0/1.18/1.8/2.2x) | 핵심 |

| 3 | 예산제약 우선순위 배분 (fractional knapsack) | 핵심 - 최대차별점 |

| 4 | AI 해석/처방 (Claude API) | 핵심 |

| 5 | 수요예측 (CV기반 모델선택) | 보조 |

| 6 | Fisher Map 포지셔닝 | 보조 |



\---



\## 3. DB 구조



\### sku\_master

| 컬럼 | 타입 | 설명 |

|------|------|------|

| sku\_id | TEXT PK | 품목코드 |

| sku\_name | TEXT | 품목명 |

| category | TEXT | 카테고리 |

| unit\_price | REAL | 단가 |

| origin\_country | TEXT | 원산지 |

| route | TEXT | 항로 (예: 아시아-유럽, 아시아-미서부, 동남아 등) |

| maritime\_dependency | TEXT | High/Mid/Low |



\### lead\_time\_info

| 컬럼 | 타입 | 설명 |

|------|------|------|

| sku\_id | TEXT | 품목코드 |

| avg\_lead\_time | REAL | 평균 리드타임(일), 평상시 기준 |

| std\_lead\_time | REAL | 리드타임 표준편차(일), 평상시 기준 |



(시나리오 배수 1.0/1.18/1.8/2.2는 route별로 avg/std에

곱해서 계산. route="아시아-유럽"이면 1.18x/1.8x 적용 가능,

route="아시아-미서부"면 2.2x 적용 등)



\### sales\_history

| 컬럼 | 타입 | 설명 |

|------|------|------|

| sku\_id | TEXT | 품목코드 |

| year | INTEGER | 연도 |

| month | INTEGER | 월 |

| quantity | REAL | 판매량 |



\### budget\_config (신규)

| 컬럼 | 타입 | 설명 |

|------|------|------|

| total\_budget | REAL | 총 예산 |

| holding\_cost\_rate | REAL | 보유비용률 (0.15\~0.25) |

| service\_level\_target | REAL | 목표 서비스수준 (0.80\~0.99) |



\---



\## 4. 화면(탭) 구조

탭0: 기준정보



CSV 업로드 → DB 저장

SKU/리드타임/판매이력/예산설정



탭1: 수요진단 (ABC-XYZ)



매트릭스 히트맵, 파레토차트, CV히스토그램



탭2: 재고정책 + 시나리오 \[핵심]



시나리오 선택: 평상시(1.0x)/홍해위기(1.18x)/

고충격(1.8x)/극단충격(2.2x)

SKU별 σL포함 안전재고/ROP 재계산

route별 배수 차등 적용 결과 비교



탭3: 예산우선순위 \[핵심-최대차별점]



예산 입력

SKU별 효율(결품손실/추가비용) 계산

효율순 배분 결과 (우선순위 액션보드:

🔴즉시조치/🟡모니터링/🟢정상)

시나리오 전환 시 실시간 재배열



탭4: AI 진단 \[핵심]



탭1\~3 결과를 Claude API로 전달

자연어 해석/처방 출력



탭5: 수요예측 (보조, 시간남으면)

탭6: Fisher Map (보조, 시간남으면)



\---



\## 5. 핵심 알고리즘



\### 5.1 안전재고/ROP (시나리오 적용)

SS = z × sqrt(L\_scenario × σD² + D² × σL\_scenario²)

ROP = D × L\_scenario + SS

L\_scenario = L\_base × scenario\_multiplier

σL\_scenario = σL\_base × scenario\_multiplier

scenario\_multiplier ∈ {1.0, 1.18, 1.8, 2.2}

(route에 따라 적용가능한 multiplier 제한 가능:

예) 아시아-미서부 SKU만 2.2x 시나리오 적용)



\### 5.2 예산 우선순위 배분 (fractional knapsack)

for each SKU:

additional\_SS = SS\_scenario - SS\_normal  (시나리오 전환시 추가필요량)

additional\_cost = additional\_SS \* unit\_price \* holding\_cost\_rate

expected\_shortage\_loss = (시나리오 적용시 결품 발생확률) \* unit\_price \* 예상판매량

efficiency = expected\_shortage\_loss / additional\_cost

sort SKUs by efficiency DESC

allocate budget sequentially (fractional - 마지막 SKU는 부분배분 가능)

output: 배분결과 + 우선순위 순위 + 잔여예산



\### 5.3 AI 해석 (Claude API)

input: 탭1\~3 계산결과 (JSON)

prompt: "다음은 SCM 시스템의 계산결과입니다.

새로운 수치를 계산하지 말고, 아래 결과를

한국어로 해석하여 SKU별 우선순위와 그 이유를

설명하세요."

output: 자연어 진단 텍스트



\---



\## 6. 개발 Phase (핵심 우선 배치)



\### PHASE 0 — 뼈대

| 단계 | 작업 | 산출물 |

|------|------|--------|

| 0-1 | 폴더구조+requirements.txt+.env+.gitignore | 구조생성 확인 |

| 0-2 | app.py 7개탭 스켈레톤 | 탭7개 렌더링 확인 |



\### PHASE 1 — 기준정보 DB

| 단계 | 작업 | 산출물 |

|------|------|--------|

| 1-1 | db\_manager.py - 4테이블 생성 | scm.db 생성확인 |

| 1-2 | sku\_data.csv - 30SKU (origin/route 포함) | CSV생성 |

| 1-3 | 탭0 UI - 업로드+로딩 | DB저장 확인 |



\### PHASE 2 — ABC-XYZ (핵심1)

| 단계 | 작업 | 산출물 |

|------|------|--------|

| 2-1 | ABC/XYZ 분류함수 | 분류테이블 |

| 2-2 | 매트릭스+히트맵+파레토 | 탭1 렌더링 |



\### PHASE 3 — σL안전재고+시나리오 (핵심2)

| 단계 | 작업 | 산출물 |

|------|------|--------|

| 3-1 | 안전재고/ROP 계산함수 (시나리오 multiplier 포함) | 계산값 수동검증 |

| 3-2 | 시나리오 선택UI + route별 적용 | 탭2 렌더링, 시나리오 전환시 재계산 확인 |



\### PHASE 4 — 예산우선순위배분 (핵심3, 최대차별점)

| 단계 | 작업 | 산출물 |

|------|------|--------|

| 4-1 | 효율계산+fractional knapsack배분 함수 | 배분결과 수동검증 |

| 4-2 | 우선순위 액션보드 UI (🔴🟡🟢) | 탭3 렌더링, 시나리오전환시 재배열 확인 |



\### PHASE 5 — AI진단 (핵심4)

| 단계 | 작업 | 산출물 |

|------|------|--------|

| 5-1 | ai\_diagnosis.py - Claude API 호출 (계산안함,해석만) | API응답 확인 |

| 5-2 | 탭4 AI진단 패널 | 진단텍스트 렌더링 |



\### PHASE 6 — 통합테스트

| 단계 | 작업 | 산출물 |

|------|------|--------|

| 6-1 | 탭0→4 전체흐름 (session\_state 연결) | 전체 오류없음 확인 |

| 6-2 | Before/After 시뮬레이션 실행+결과기록 | 효과검증 수치 확보 |



\### PHASE 7 — 보조모듈 (시간남으면)

| 단계 | 작업 |

|------|------|

| 7-1 | 수요예측 (탭5) |

| 7-2 | Fisher Map (탭6) |



\### PHASE 8 — UI고도화

| 단계 | 작업 |

|------|------|

| 8-1 | 색상/레이아웃 정리 |

| 8-2 | 발표용 데모시나리오 준비 |



\### PHASE 9 — 보고서

| 단계 | 작업 |

|------|------|

| 9-1 | 8장구조(05번 섹션7) 기반 보고서 작성 |

| 9-2 | 발표자료 |



\---



\## 7. 일정 (남은 기간 기준)



| 작업 | Phase |

|------|-------|

| Day1 | Phase0+1 |

| Day2 | Phase2 |

| Day3-4 | Phase3 |

| Day5-6 | Phase4 (최우선 - 최대차별점) |

| Day7 | Phase5 |

| Day8 | Phase6 (Before/After 실행) |

| Day9-10 | Phase7 (시간남으면) |

| Day11 | Phase8 |

| Day12-13 | Phase9 보고서 |

| Day14 | 제출 |



\*\*Phase4(예산우선순위)가 가장 중요. Phase4 완성 전까지는

Phase7(보조모듈) 절대 손대지 않음.\*\*

