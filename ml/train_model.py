"""
KIER LightGBM 다지점 학습 스크립트
- 17개 지점 2021년 데이터: 전국 시도별 대표 관측소
- 피처: ASOS 기상변수 + lat/lon (ghi/cghi 제거 — 학습/추론 소스 일치)
- 지점별 80/20 시계열 분할 후 합산 (각 지역이 학습·검증셋 모두에 포함)
"""
import glob, pickle, warnings
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import lightgbm as lgb
warnings.filterwarnings('ignore')

DATA_DIR = "data"

LOCATIONS = [
    (133, None),   # 대전: solar_power_2021_MM.csv (기존 파일명)
    (184, 184),    # 제주
    (159, 159),    # 부산
    (156, 156),    # 광주
    (108, 108),    # 서울
    (105, 105),    # 강릉
    (112, 112),    # 인천
    (119, 119),    # 경기
    (129, 129),    # 충남
    (131, 131),    # 충북
    (136, 136),    # 경북
    (143, 143),    # 대구
    (146, 146),    # 전북
    (152, 152),    # 울산
    (155, 155),    # 경남
    (165, 165),    # 전남
    (239, 239),    # 세종
]

FEATURES = ['month', 'day', 'hour', 'day_of_year',
            'lat', 'lon',
            'ghi', 'cghi',
            'ta', 'rn', 'ws', 'wd', 'hm', 'pv', 'td', 'pa', 'ps', 'ss', 'icsr']

GHI_SLOPE     = 237.6295
GHI_INTERCEPT = 14.6284

def add_ghi_from_icsr(df):
    """icsr → ghi, cghi 파생 (ASOS icsr ↔ KIER ghi r=0.95)"""
    df = df.copy()
    df['ghi'] = (GHI_SLOPE * df['icsr'] + GHI_INTERCEPT).clip(lower=0)
    df['date_key'] = df['datetime'].dt.date
    df['cghi'] = df.groupby('date_key')['ghi'].cumsum()
    df.drop(columns='date_key', inplace=True)
    return df


def load_location(stn_id, sp_id, year=2021):
    # solar_power 로드
    if sp_id is None:
        sp_files = sorted(glob.glob(f"{DATA_DIR}/solar_power_{year}_*.csv"))
    else:
        sp_files = sorted(glob.glob(f"{DATA_DIR}/solar_power_{sp_id}_{year}_*.csv"))

    if not sp_files:
        print(f"  [stn={stn_id}] solar_power 파일 없음")
        return pd.DataFrame()

    sp = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in sp_files], ignore_index=True)
    sp['datetime'] = pd.to_datetime(sp['Date'] + ' ' + sp['time'])
    sp[['lat', 'lon', 'pvAmt']] = sp[['lat', 'lon', 'pvAmt']].apply(pd.to_numeric, errors='coerce')

    # ASOS 로드
    asos_files = sorted(glob.glob(f"{DATA_DIR}/ASOS_{stn_id}_{year}_*.csv"))
    if not asos_files:
        print(f"  [stn={stn_id}] ASOS 파일 없음")
        return pd.DataFrame()

    asos = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in asos_files], ignore_index=True)
    asos['datetime'] = pd.to_datetime(asos['tm'])
    num_cols = ['ta', 'rn', 'ws', 'wd', 'hm', 'pv', 'td', 'pa', 'ps', 'ss', 'icsr']
    asos[num_cols] = asos[num_cols].apply(pd.to_numeric, errors='coerce')

    # 병합
    merged = pd.merge(
        sp[['datetime', 'lat', 'lon', 'pvAmt']],
        asos[['datetime'] + num_cols],
        on='datetime', how='inner'
    )
    merged['month'] = merged['datetime'].dt.month
    merged['day'] = merged['datetime'].dt.day
    merged['hour'] = merged['datetime'].dt.hour
    merged['day_of_year'] = merged['datetime'].dt.dayofyear

    merged = add_ghi_from_icsr(merged)
    merged = merged.dropna(subset=FEATURES + ['pvAmt'])
    print(f"  [stn={stn_id}] {len(merged)}행 병합 완료  lat={merged['lat'].iloc[0]:.3f}, lon={merged['lon'].iloc[0]:.3f}")
    return merged


print("=" * 60)
print("다지점 데이터 로딩")
print("=" * 60)

all_dfs = []
for stn_id, sp_id in LOCATIONS:
    df = load_location(stn_id, sp_id)
    if not df.empty:
        all_dfs.append(df)

if not all_dfs:
    raise SystemExit("데이터 없음")

combined = pd.concat(all_dfs, ignore_index=True).sort_values('datetime').reset_index(drop=True)
print(f"\n전체 데이터: {len(combined)}행  ({len(all_dfs)}개 지점)")
print(f"위도 범위: {combined['lat'].min():.3f} ~ {combined['lat'].max():.3f}")
print(f"경도 범위: {combined['lon'].min():.3f} ~ {combined['lon'].max():.3f}")

# 지점별 80/20 시계열 분할 — 각 지역이 학습·검증셋 모두에 포함되도록
train_parts, test_parts = [], []
for df_loc in all_dfs:
    n = len(df_loc)
    split_idx = int(n * 0.8)
    train_parts.append(df_loc.iloc[:split_idx])
    test_parts.append(df_loc.iloc[split_idx:])

train_df = pd.concat(train_parts, ignore_index=True)
test_df = pd.concat(test_parts, ignore_index=True)

print(f"학습: {len(train_df)}행 / 검증: {len(test_df)}행")
print(f"학습 지점 lat 분포: {sorted(train_df['lat'].unique().round(3).tolist())}")

X_train = train_df[FEATURES]
y_train = train_df['pvAmt']
X_test = test_df[FEATURES]
y_test = test_df['pvAmt']

print("\n" + "=" * 60)
print("LightGBM 학습")
print("=" * 60)

model = lgb.LGBMRegressor(
    n_estimators=500,
    max_depth=12,
    learning_rate=0.03,
    num_leaves=80,
    subsample=0.9,
    colsample_bytree=0.9,
    min_child_samples=20,
    random_state=42,
    verbose=-1
)
model.fit(X_train, y_train,
          eval_set=[(X_test, y_test)],
          callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(50)])

y_pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"\n=== 모델 성능 ===")
print(f"  R²   : {r2:.4f}")
print(f"  RMSE : {rmse:.6f}")
print(f"  MAE  : {mae:.6f}")

# 피처 중요도
importances = model.feature_importances_
total = importances.sum()
print(f"\n=== 피처 중요도 (상위 10) ===")
for feat, imp in sorted(zip(FEATURES, importances), key=lambda x: -x[1])[:10]:
    print(f"  {feat:15s} {imp/total*100:5.1f}%")

lat_imp = importances[FEATURES.index('lat')] / total * 100
lon_imp = importances[FEATURES.index('lon')] / total * 100
print(f"\n  lat 기여: {lat_imp:.2f}%  |  lon 기여: {lon_imp:.2f}%")

with open("trained_model.pkl", "wb") as f:
    pickle.dump({"model": model, "features": FEATURES, "r2": r2, "rmse": rmse, "mae": mae,
                 "n_locations": len(all_dfs), "n_rows": len(combined)}, f)

print(f"\n모델 저장 완료: trained_model.pkl")
print("다음 단계: predict_nationwide.py 실행")
