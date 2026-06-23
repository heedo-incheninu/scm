# Codex 기반 배포 계획서

## 0. 목적

이 문서는 현재 SCM Streamlit 시스템을 Codex로 점검·정리한 뒤, 외부 사용자가 접속 가능한 형태로 배포하기 위한 실행 계획서이다. 목표는 단순 실행이 아니라 해커톤 발표와 심사 시연에 안정적으로 사용할 수 있는 배포 상태를 만드는 것이다.

## 1. 현재 시스템 상태

현재 프로젝트는 Streamlit 기반 단일 웹앱이며, 핵심 진입점은 `app.py`이다.

구현된 주요 기능은 다음과 같다.

- ABC-XYZ 품목 중요도 분류
- σL 포함 안전재고 계산
- 균등·비례·우선순위·서비스수준 배분 비교
- CSV 업로드 및 가상 CSV 예제 5종
- 포기 SKU와 예상손실액 표시
- GSCPI 기반 위기 시나리오 참고 추천
- OpenAI API 기반 AI 조언 및 데모 모드
- 사용자 이해 중심 8단계 화면 흐름

현재 검증 명령은 다음과 같다.

```powershell
uv run ruff check .
uv run pytest -q
uv run streamlit run app.py
```

## 2. 권장 배포 방식

### 1순위: Streamlit Community Cloud

해커톤 시연 목적에는 Streamlit Community Cloud가 가장 적합하다.

장점:

- Streamlit 앱 배포가 간단하다.
- GitHub 저장소와 바로 연결할 수 있다.
- 별도 서버 관리가 거의 필요 없다.
- 발표용 URL 공유가 쉽다.

주의사항:

- `OPENAI_API_KEY`는 코드에 저장하지 않고 Streamlit Secrets에 등록해야 한다.
- `data/scm.db`는 배포 산출물이 아니라 앱 실행 중 생성되는 로컬 파일로 취급한다.
- `csv/` 폴더의 가상 데이터는 공개 가능한 합성 데이터로 유지한다.

### 2순위: Render 또는 Railway

Streamlit Cloud 제한이 있거나 서버 실행 로그를 더 직접 관리해야 할 때 사용한다.

필요 항목:

- 시작 명령

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

- 환경변수

```text
OPENAI_API_KEY
SCM_OPENAI_MODEL
SCM_SKIP_GSCPI
```

### 3순위: Docker 배포

장기 운영 또는 팀 서버 배포가 필요할 때 사용한다. 해커톤 MVP에서는 후순위로 둔다.

## 3. Codex 작업 순서

### Phase 1. 배포 전 코드 안정화

목표:

- 배포 전 현재 코드가 깨지지 않는지 확인한다.

작업:

```powershell
uv sync --all-groups
uv run ruff check .
uv run pytest -q
uv run python scripts/init_db.py --replace
uv run streamlit run app.py
```

완료 기준:

- Ruff 통과
- 전체 테스트 통과
- 로컬 `http://127.0.0.1:8501/` 접속 성공
- 신규 페이지 전체 로딩 확인

### Phase 2. 배포용 의존성 정리

목표:

- 배포 플랫폼이 프로젝트 의존성을 정확히 설치하도록 만든다.

현재 기준 의존성은 `pyproject.toml`과 `uv.lock`에 있다. Streamlit Cloud에서 `pyproject.toml` 인식이 불안정하면 `requirements.txt`를 추가 생성한다.

필수 패키지:

```text
streamlit
pandas
numpy
plotly
openai
openpyxl
```

완료 기준:

- 새 환경에서 앱 실행 가능
- `openpyxl` 누락으로 GSCPI 기능이 실패하지 않음

### Phase 3. 환경변수와 Secrets 정리

목표:

- API 키와 운영 설정을 코드 밖에서 관리한다.

배포 환경에 등록할 값:

```text
OPENAI_API_KEY=발급받은 OpenAI API 키
SCM_OPENAI_MODEL=gpt-5.5
```

선택값:

```text
SCM_SKIP_GSCPI=1
```

`SCM_SKIP_GSCPI=1`은 외부 네트워크 조회를 끄고 수동 시나리오 선택만 사용할 때 설정한다.

보안 기준:

- `.env` 파일 커밋 금지
- API 키 코드 삽입 금지
- 실제 기업 데이터 커밋 금지
- `data/scm.db` 커밋 금지

### Phase 4. GitHub 저장소 정리

목표:

- 배포 플랫폼이 읽을 저장소 상태를 정리한다.

확인 항목:

- `app.py`가 루트에 존재
- `pyproject.toml` 또는 `requirements.txt` 존재
- `csv/` 예제 파일 포함
- `readme.md` 실행 방법 최신화
- `checklist.md` 진행 상태 최신화
- 불필요한 로컬 DB와 캐시 제외

권장 `.gitignore` 항목:

```text
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
data/scm.db
.env
```

### Phase 5. Streamlit Cloud 배포

목표:

- GitHub 저장소를 Streamlit Cloud에 연결해 공개 URL을 만든다.

작업 순서:

1. GitHub에 최신 코드 push
2. Streamlit Cloud에서 New app 생성
3. Repository 선택
4. Main file path를 `app.py`로 설정
5. Python 버전은 3.11 이상 사용
6. Secrets에 `OPENAI_API_KEY`, `SCM_OPENAI_MODEL` 등록
7. Deploy 실행

완료 기준:

- 외부 URL 접속 가능
- 기본 예제 데이터로 홈 화면 로딩
- 데이터 확인, 위험 시나리오, 예산 추천, 포기 SKU, 전략 비교, AI 조언 페이지 진입 가능

### Phase 6. 배포 후 시연 검증

목표:

- 심사위원 앞에서 끊기지 않는 발표 흐름을 만든다.

시연 순서:

1. 한눈에 보기에서 전체 위험 요약
2. 데이터 확인에서 합성 데이터와 한계 설명
3. 위험 시나리오에서 GSCPI와 사용자 선택 구분 설명
4. 품목 중요도에서 ABC-XYZ 해석
5. 필요 재고에서 σL 포함 안전재고 산식 설명
6. 예산 추천에서 90%·95%·99% 서비스수준 배분 설명
7. 포기 SKU에서 예상손실액 설명
8. 전략 비교에서 기존 방식과 신규 방식 비교
9. AI 조언에서 실행 항목 요약

완료 기준:

- 3분 발표 흐름으로 설명 가능
- API 키가 없어도 데모 모드로 시연 가능
- GSCPI 조회 실패 시에도 앱이 중단되지 않음

## 4. 배포 전 필수 점검표

- [ ] `uv run ruff check .` 통과
- [ ] `uv run pytest -q` 통과
- [ ] 로컬 Streamlit 실행 확인
- [ ] 신규 페이지 전체 클릭 확인
- [ ] API 키 미설정 데모 모드 확인
- [ ] API 키 설정 상태 AI 조언 확인
- [ ] GSCPI 조회 실패 fallback 확인
- [ ] CSV 예제 로딩 확인
- [ ] 업로드 CSV 오류 안내 확인
- [ ] README 실행 명령 확인
- [ ] `data/scm.db`, `.env`, API 키 미커밋 확인

## 5. 배포 리스크와 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| OpenAI API 키 없음 | AI 조언 생성 제한 | 데모 모드 유지 |
| GSCPI 외부 조회 실패 | 위험 시나리오 추천 제한 | `SCM_SKIP_GSCPI=1` 또는 fallback 표시 |
| Streamlit Cloud 의존성 설치 실패 | 앱 배포 실패 | `requirements.txt` 추가 |
| DB 파일 없음 | 기본 데이터 로딩 실패 가능 | `scripts/init_db.py` 또는 앱 초기화 로직 확인 |
| 실제 데이터 오해 | 심사 신뢰도 하락 | 합성 데이터와 한계 문구 표시 |

## 6. 최종 완료 기준

배포가 완료되었다고 판단하려면 다음 조건을 만족해야 한다.

- 공개 URL에서 앱이 정상 접속된다.
- 기본 예제 데이터로 모든 페이지가 로딩된다.
- 서비스수준 배분, 포기 SKU, 전략 비교가 정상 표시된다.
- API 키가 없어도 앱이 중단되지 않는다.
- 배포 환경에서 비밀키가 코드나 저장소에 노출되지 않는다.
- 발표자가 8단계 사용자 흐름을 끊김 없이 시연할 수 있다.

