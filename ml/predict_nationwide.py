"""
전국 17개 시도 2025년 태양광 발전량 예측
학습된 LightGBM 모델로 각 시도 대표 지점의 pvAmt 예측 후
solarEfficiency.json score 업데이트
"""
import sys, json, glob, pickle, warnings
import pandas as pd
import numpy as np
from pathlib import Path
warnings.filterwarnings('ignore')

DATA_DIR = "data"
ROOT = Path(__file__).parent.parent

SIDO_STATIONS = {
    "서울특별시":      (108, 37.5714, 126.9658),
    "경기도":          (119, 37.2636, 127.0286),
    "인천광역시":      (112, 37.4772, 126.6247),
    "강원특별자치도":  (105, 37.7514, 128.8761),
    "충청북도":        (131, 36.6390, 127.4420),
    "충청남도":        (129, 36.7769, 126.4953),
    "세종특별자치시":  (239, 36.4800, 127.2890),
    "대전광역시":      (133, 36.3493, 127.3868),
    "전북특별자치도":  (146, 35.8242, 127.1489),
    "전라남도":        (165, 34.8167, 126.3814),
    "광주광역시":      (156, 35.1728, 126.8917),
    "경상북도":        (136, 36.5728, 128.7058),
    "대구광역시":      (143, 35.8853, 128.6181),
    "경상남도":        (155, 35.1689, 128.5644),
    "울산광역시":      (152, 35.5581, 129.3200),
    "부산광역시":      (159, 35.1042, 129.0320),
    "제주특별자치도":  (184, 33.5147, 126.5297),
}

FEATURES = ['month', 'day', 'hour', 'day_of_year',
            'lat', 'lon',
            'ghi', 'cghi',
            'ta', 'rn', 'ws', 'wd', 'hm', 'pv', 'td', 'pa', 'ps', 'ss', 'icsr']

GHI_SLOPE     = 237.6295
GHI_INTERCEPT = 14.6284

def add_ghi_from_icsr(df):
    df = df.copy()
    df['ghi'] = (GHI_SLOPE * df['icsr'] + GHI_INTERCEPT).clip(lower=0)
    df['date_key'] = df['datetime'].dt.date
    df['cghi'] = df.groupby('date_key')['ghi'].cumsum()
    df.drop(columns='date_key', inplace=True)
    return df

# 모델 로드
with open("trained_model.pkl", "rb") as f:
    saved = pickle.load(f)
model = saved["model"]
print(f"모델 로드 완료 (R²={saved['r2']:.4f})")

def load_asos_2025(stn_id):
    files = sorted(glob.glob(f"{DATA_DIR}/ASOS_{stn_id}_2025_*.csv"))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_csv(f, encoding='utf-8-sig') for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df['datetime'] = pd.to_datetime(df['tm'])
    df['month'] = df['datetime'].dt.month
    df['day'] = df['datetime'].dt.day
    df['hour'] = df['datetime'].dt.hour
    df['day_of_year'] = df['datetime'].dt.dayofyear
    num_cols = ['ta','rn','ws','wd','hm','pv','td','pa','ps','ss','icsr']
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce')
    return df

print("\n전국 시도별 pvAmt 예측 시작...")
pvamt_results = {}

for sido, (stn_id, lat, lon) in SIDO_STATIONS.items():
    asos = load_asos_2025(stn_id)
    if asos.empty:
        print(f"  [{sido}] ASOS 데이터 없음 - 건너뜀")
        continue

    asos = asos.sort_values('datetime')
    asos['lat'] = lat
    asos['lon'] = lon
    asos = add_ghi_from_icsr(asos)

    df_feat = asos[FEATURES].dropna()
    if df_feat.empty:
        print(f"  [{sido}] 유효 feature 없음")
        continue

    preds = model.predict(df_feat)
    preds = np.clip(preds, 0, None)  # 음수 제거
    annual_mean = float(np.mean(preds))
    pvamt_results[sido] = annual_mean
    print(f"  [{sido}] pvAmt 평균={annual_mean:.6f}  ({len(df_feat)}시간)")

# 0~1 정규화
print(f"\n수집된 시도: {len(pvamt_results)}개")
if len(pvamt_results) < 2:
    print("데이터 부족으로 종료")
    sys.exit(1)

min_v = min(pvamt_results.values())
max_v = max(pvamt_results.values())
rng = max_v - min_v

print("\n=== 시도별 예측 결과 ===")
scores = {}
for sido, val in sorted(pvamt_results.items(), key=lambda x: -x[1]):
    score = round((val - min_v) / rng, 4)
    scores[sido] = score
    print(f"  {sido}: pvAmt={val:.6f}  score={score:.4f}")

# solarEfficiency.json 업데이트
eff_path = ROOT / "src" / "data" / "solarEfficiency.json"
with open(eff_path, encoding="utf-8") as f:
    efficiency = json.load(f)

updated, missing = [], []
for sido in efficiency:
    if sido in scores:
        efficiency[sido]["score"] = scores[sido]
        efficiency[sido]["pvamt_2025"] = round(pvamt_results[sido], 6)
        updated.append(sido)
    else:
        missing.append(sido)

with open(eff_path, "w", encoding="utf-8") as f:
    json.dump(efficiency, f, ensure_ascii=False, indent=2)

print(f"\n solarEfficiency.json 업데이트: {len(updated)}개 시도")
if missing:
    print(f"  미업데이트: {missing}")
print("완료!")
