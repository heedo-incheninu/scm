# 해상물류 SCM 리스크 진단 플랫폼 - 프로젝트 히스토리

## 1. 기본 정보

- **공식 주제명**: 해상 물류 리드타임 리스크 기반 AI SCM 최적화 플랫폼
- **부제(발표용)**: 위기 대응형 SKU 우선순위 재고 의사결정
- **참여 대회**: RISE 사업단 AI해커톤 (6/27 발표) + SCM론 기말 프로젝트 (6/23 제출)
  + IIOF(인천국제해양포럼) AI해커톤 추천 가능성
- **GitHub**: github.com/Shimwonseob/scm-final-exam-platform (master 브랜치)
- **개발환경**: Python 3.11+, Streamlit, SQLite

---

## 2. 주제 선정 과정 (왜 이 주제인가)

### 2-1. 초기 후보 3개 비교
처음엔 A) SCM 전략-실행 연계 진단 플랫폼(범용), B) Bullwhip 채찍효과 시뮬레이터,
C) SKU 재고 건강진단 시스템 3개를 검토. 범용성 vs 깊이의 트레이드오프를 고민.

### 2-2. 1차 확정 → 2차 전환
처음엔 A안(범용 SCM 진단)으로 확정했으나, 인천대/IIOF 맥락(항만도시, 동북아물류대학원)을
고려해 **해상물류 특화**로 전환. 코드 재사용률 95% 유지하면서 데이터·스토리만 변경.

### 2-3. 교수님 피드백으로 핵심 재정의 (가장 중요한 전환점)
교수님 피드백: "AI로 SCM 솔루션 만드는 건 좋지만, 결국 해당 산업의 근본 문제를
해결하는 솔루션이어야 한다. 기존에 널려있거나 쉽게 해결 가능한 솔루션이 아니라,
컨설턴트 입장에서 문제를 정의하고 근본원인을 해결해야 한다."

→ 기존 5모듈 구조(ABC-XYZ+재고정책+수요예측+FisherMap+시나리오)에서
**예산제약 우선순위 배분(Module 4)이 핵심 차별점**으로 재배치됨.
수요예측/FisherMap은 보조모듈로 다운그레이드(미구현 확정).

---

## 3. 문제-원인-솔루션 논리 (최종 확정본)

### 핵심 재정의
- **외부(해결 불가)**: 해상 리드타임 변동성 자체 (배경/환경)
- **내부(본 시스템이 해결)**: 위기 시 SKU별 차등 재고·예산 의사결정 체계 부재

### 8장 보고서 논리 흐름
1. 글로벌 물류 문제 → 2. 기업 내부 근본원인 → 3. 기존 대응의 한계 →
4. 솔루션 설계 → 5. 알고리즘 → 6. 시스템 구현 → 7. 검증 → 8. 차별성 및 한계

### 안전재고 핵심 공식

σL(리드타임 표준편차)을 명시적으로 반영하는 게 핵심 — 대부분 기존 도구는 무시함.

### 위기 시나리오 (전부 실측 데이터 기반)
| 시나리오 | 배수 | 근거 |
|---------|------|------|
| 평상시 | 1.0x | 기준값 |
| 중간충격(홍해위기 2024) | 1.18x | ITF/OECD: 편도+10일, 정시율62%→52% |
| 고충격(2021-22 아시아-유럽) | 1.8x | Flexport: 55-60일→108일 |
| 극단충격(2021-22 아시아-미서부) | 2.2x | Flexport: 45-50일→110일 |

---

## 4. 자료조사 전체 — 검증된 핵심 수치 (전부 출처 URL 확인 완료)

### A. 해운 대란 / 리드타임 변동성
| 수치 | 출처 |
|------|------|
| 해상 컨테이너 평균 LT 44일, σ10.5일 | World Bank, Connecting to Compete 2023 |
| 2024 정시율 50~55% | Sea-Intelligence 2024 |
| 월 이상 차질 평균 3.7년 주기 | McKinsey Global Value Chain |
| 홍해위기: 편도+10일, 정시율62→52%, 운임+130% | ITF/OECD 2024 (PDF 직접 확인) |

URL:
- https://documents1.worldbank.org/curated/en/099042123145531599/pdf/P17146804a6a570ac0a4f80895e320dda1e.pdf
- https://www.sea-intelligence.com/press-room/307-2024-schedule-reliability-largely-within-50-55
- https://www.itf-oecd.org/sites/default/files/repositories/red-sea-crisis-impacts-global-shipping.pdf

### B. 기업 대응 실태 / 비효율
| 수치 | 출처 |
|------|------|
| 71% 재고정책 변경계획(2022) | McKinsey |
| 31%만 통합운영 | Manhattan/Talking Logistics 2024 |
| 92% gut decision, 주14시간 수동추적 | LeanDNA 2024 |
| 59%→34% 재고버퍼의존감소, 46%축소계획 | McKinsey 2024 |
| 70%수동수집/68%Excel | MLC 2024 |
| SMB 38%과잉재고, 26%만계획적안전재고 | Netstock 2024 |
| 글로벌결품손실 $1.75조/년 | ToolsGroup |

URL:
- https://www.mckinsey.com/capabilities/operations/our-insights/taking-the-pulse-of-shifting-supply-chains
- https://www.mckinsey.com/capabilities/operations/our-insights/supply-chain-risk-survey-2024
- https://www.leandna.com/resource/supply-chain-executives-survey-2024/
- https://www.netstock.com/research/inventory-management-report/

### C. 한국 맥락
| 수치 | 출처 |
|------|------|
| 한국 수입공급망 취약, "취약품목 재고비축+모니터링" 정책권고 | 한국은행 2022 |
| 한국 중간재 수입의존도 50.2%, 중국의존 28.3%(G7평균초과) | Korea Times 2022 |
| 2026 한국SME 운임 1,300→3,500달러 급등 사례 | Chosun Biz 2026 |

URL:
- https://www.bok.or.kr/eng/bbs/E0000828/view.do?menuNo=400214&nttId=10071956
- https://www.koreatimes.co.kr/economy/20220523/korea-relies-more-on-imports-for-intermediate-goods-than-g-7-nations-report
- https://www.chosun.com/english/industry-en/2026/03/11/6X5I2RIBWJFTHNABIMT6STLUNU/

### D. 효과검증 참고사례
| 사례 | 효과 | 출처 |
|------|------|------|
| PT XYZ(인니, 수입냉동육도매업) ABC+예측+EOQ | 2022:33%,2023:32%,2024:29% 절감 | IJOSMAS |
| SME 주문배분 최적화 사례 | 10.89% 비용절감 | Emerald 2024 |

URL:
- https://ijosmas.org/index.php/ijosmas/article/download/525/365
- https://www.emerald.com/insight/content/doi/10.1108/jgoss-06-2023-0060/full/html

### E. 시장공백/차별점 근거
- IBM 특허(US6078900, 1998, 예산제약 우선순위 안전재고배분) — **만료되어 공개기술**.
  알고리즘 자체는 25년 전부터 존재했으나 엔터프라이즈 전용이었고 SME에 내려온 적 없음.
- Netstock 서베이: SME 78%가 전용 재고관리SW 미사용, 48% 엑셀의존, 82% ROI측정불가
- 차별점 표현: "알고리즘은 기존 특허, 우리 기여는 해상리스크+ABC-XYZ+AI해석 결합 SME경량화"

---

## 5. 5가지 검증기준 교차검증 결과 (Perplexity+ChatGPT, 3-AI)

| 기준 | 점수 | 평가 |
|------|------|------|
| 1. 고객명확성 | 3.5/5 | 한국 수입SME, ICP는 잡혔으나 더 좁혀야 함 |
| 2. 중요성/고통 | 3.0/5 | 인접증거(번아웃,운임상승)는 강하나 직접증거 약함 |
| 3. 근본원인 | 3.5/5 | SME 78%미도입 등 확인됨 |
| 4. 공감대 | 2.0/5(최약점) | 고객인터뷰·구매의향 검증 전무 |
| 5. 시장크기 | 3.0/5 | TAM은 큼, 정확한 SAM/SOM 미확정 |
| **종합** | **3.0/5** | "추진가치 있음, 검증보강 필요" |

---

## 6. 데이터 전략 (중요 - 여러 번 논쟁한 부분)

- M5(Walmart) 검토 → **기각** (이전 수요예측 과제와 데이터 중복 우려 + 원산지·단가·항로 없어 부분적합)
- 관세청 무역통계 검토 → **기각** (국가 총량 데이터, SKU/기업 단위와 스케일 불일치)
- "선행연구도 시뮬레이션 쓴다" 주장 → **기각** (PT XYZ는 실제 비공개데이터 확인됨, 거짓 권위)
- **최종 결론**: SKU단위 기업 재고데이터는 영업비밀로 구조적으로 비공개됨.
  본 프로젝트는 학생 PoC로서 실제 데이터 접근 불가 → 리드타임/위기배수는 실측,
  수요패턴은 SCM이론기반 시뮬레이션으로 구성. 이 한계를 정직하게 보고서에 명시.

---

## 7. 시스템 구조 (5개 핵심 + 2개 보조)

| 우선순위 | 모듈 | 상태 |
|---------|------|------|
| 핵심1 | ABC-XYZ 분류 | ✅완료 |
| 핵심2 | σL 안전재고+시나리오 | ✅완료 |
| 핵심3 | 예산우선순위배분(최대차별점) | ✅완료+버그수정 |
| 핵심4 | AI진단(Claude API) | ✅완료(결제이슈로 데모모드 병행) |
| 보조1 | 수요예측 | ❌미구현(확정) |
| 보조2 | Fisher Map | ❌미구현(확정) |

데이터: 30 SKU, 24개월 판매이력, 9개 ABC-XYZ셀에 분산 배치.

---

## 8. 개발 진행상황 (Phase별)

- Phase 0: 프로젝트 뼈대 ✅
- Phase 1+2: DB구조+30SKU데이터+ABC-XYZ ✅
- Phase 3: σL안전재고+시나리오 ✅
- Phase 4: 예산우선순위배분 ✅
- Phase 5: AI진단(Claude API) ✅ (단, 결제 크레딧 문제로 실제 API는 아직 미확인,
  데모모드로 백업)
- Phase 6: 통합테스트+Before/After 효과검증 ✅
  - **핵심성과**: 예산 20%수준에서 기존방식 대비 69.1% 개선효과 확인
- Phase 8: UI고도화 ✅ (화이트모드, 좌측사이드바 네비게이션, 대시보드, 사용가이드 추가)
- **종단간 점검에서 발견한 중요 버그**: Module1("AZ=최우선관리")과 Module4(실제계산)이
  모순되는 걸 발견 → ABC-XYZ 셀 기반 가중치 추가로 수정 완료

---
