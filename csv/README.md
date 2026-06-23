# CSV 예제 데이터

이 폴더의 파일은 업로드 기능과 발표 시연을 위한 가상 기업 데이터입니다. 실제 기업 또는 제품을 나타내지 않습니다.

| 파일 | 가상 데이터 특성 |
|---|---|
| `01_electronics_stable.csv` | 고단가 전자부품 중심 |
| `02_food_seasonal.csv` | 계절성이 있는 식품원료 |
| `03_auto_parts_volatile.csv` | 수요 변동이 큰 자동차부품 |
| `04_medical_high_service.csv` | 서비스 수준 99% 의료소모품 |
| `05_fashion_peak.csv` | 연말 성수기가 강한 패션상품 |

각 파일은 30개 SKU와 SKU별 24개월 판매 이력으로 구성됩니다. 제품 정보는 판매 이력 행마다 반복되며 앱이 이를 제품·판매 테이블로 분리합니다.

필수 열:

```text
sku_id,name,category,unit_cost,lead_time_days,lead_time_std_days,
service_level,current_stock,month,quantity
```

가상 데이터를 다시 만들려면 프로젝트 루트에서 실행합니다.

```powershell
uv run python scripts/generate_csv_samples.py
```
