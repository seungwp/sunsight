# SunSight — 태양광 잠재력 예측 모델

시·도별 태양광 발전 잠재력 점수(0~1)를 산출하는 LightGBM 회귀 파이프라인입니다.
산출된 점수는 대시보드의 우선순위 계산(`trueSpareKW(MW) × 잠재력 점수`)에 사용됩니다.

## 실행 순서

```sh
# 1. 기상 관측 데이터 수집 (전국 17개 시·도 ASOS)
python download_nationwide_asos.py

# 2. LightGBM 학습 — 11개 지점 병합, 피처 19개
python train_model.py            # → trained_model.pkl

# 3. 성능 검증
python validate_model.py         # R² · RMSE · MAE
python check_r2.py               # 위도 상관 검증
python check_icsr_ghi.py         # icsr → ghi 선형관계 검증

# 4. 17개 시·도 잠재력 점수 예측
python predict_nationwide.py

# 5. 시각화 (선택)
python visualize_model.py        # → model_validation.png
```

이후 프로젝트 루트에서 `node scripts/buildSolarEfficiency.mjs`를 실행하면
예측 결과가 대시보드용 JSON(`src/data/solarEfficiency.json`)으로 변환됩니다.

## 모델 개요

| 항목 | 값 |
|---|---|
| 알고리즘 | LightGBM 회귀 (`LGBMRegressor`) |
| 목표 변수 | `pvAmt` — 단위용량당 발전량 (kWh/kWp) |
| 피처 | 19개 — 시간(4) · 좌표(2) · 일사량(2) · 기상(11) |
| 학습 데이터 | 11개 시·도 × 2021년 시간자료 (유효 7,474행) |
| 검증 분할 | 지점별 시계열 80/20 — 11개 지점이 학습·검증셋에 모두 포함 |
| 성능 | **R² = 0.745** (RMSE 0.0516 · MAE 0.0303) |
| 피처 중요도 | ghi 12.7% · cghi 9.6% · ta 7.6% · hour 7.1% |

### 파생 피처

예측 대상 지역에는 전일사량(`ghi`)이 없어, 전국에서 수집 가능한
ASOS 지표면 일사량(`icsr`)에서 파생했습니다.

```
ghi = 237.6295 × icsr + 14.6284      (Pearson r = 0.95)
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `train_model.py` | LightGBM 학습 · 피처 정의 · 중요도 출력 |
| `predict_nationwide.py` | 학습 모델로 17개 시·도 잠재력 점수 예측 |
| `validate_model.py` · `check_r2.py` | 성능 검증 (R² · Spearman) |
| `check_icsr_ghi.py` | icsr→ghi 선형관계 검증 |
| `score_from_icsr.py` | 회귀 이전 임시 스코어링 방식 (개선 이력 참고용) |
| `download_nationwide_asos.py` | 전국 ASOS 기상 데이터 수집 |
| `download_multiloc_2021.py` · `download_remaining_2021.py` | 학습용 다지점 데이터 수집 |
| `find_coords.py` · `remaining_coords.json` | 관측 지점 좌표 매핑 |
| `show_scores.py` | 산출된 점수 확인 |
| `trained_model.pkl` | 학습 완료 모델 (R² 0.745) |

## 데이터

`data/` — ASOS 원본 CSV(지점 × 월, 약 68MB)는 용량 문제로 저장소에 포함하지 않았습니다.
`download_nationwide_asos.py` 실행 시 재수집됩니다. 공공데이터포털 API 키가 필요합니다.

## 출처 및 라이선스

원본 데이터 수집에는 한국에너지기술연구원(KIER)이 공개한 예제 스크립트를 참고했습니다.

- **KIER 국가핵심데이터 API 저장소** — https://github.com/KIERREBD/KIER_NationalCoreData_DataAPI (Apache License 2.0)
  - 태양광 발전량 수집: `download_solar_data_KIER.py`
  - 기상 관측 수집: `download_asos_data_KMA.py`

위 두 스크립트는 KIER 저장소의 것을 그대로 사용했으므로 이 폴더에 포함하지 않았습니다.
학습 데이터를 처음부터 재현하려면 해당 저장소를 별도로 받아 실행해야 합니다.

**이 폴더의 코드는 전부 SunSight 프로젝트에서 직접 작성한 것입니다.**

### 데이터 출처

| 데이터 | 제공 | API |
|---|---|---|
| 태양광 시간별 발전량 | 한국에너지기술연구원(KIER) | `apis.data.go.kr/B551184/SolarPvService` |
| 종관기상관측(ASOS) | 기상청 기상자료개방포털 | `apis.data.go.kr/1360000/AsosHourlyInfoService` |
