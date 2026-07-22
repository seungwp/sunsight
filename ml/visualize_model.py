"""LightGBM 모델 검증 시각화 — 모든 수치를 테스트셋에서 직접 재계산"""
import glob, pickle, warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy import stats
warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = "data"

LOCATIONS = [
    (133, None, "대전"),
    (184, 184,  "제주"),
    (159, 159,  "부산"),
    (156, 156,  "광주"),
    (108, 108,  "서울"),
    (105, 105,  "강릉"),
    (112, 112,  "인천"),
    (119, 119,  "경기"),
    (129, 129,  "충남"),
    (131, 131,  "충북"),
    (136, 136,  "경북"),
    (143, 143,  "대구"),
    (146, 146,  "전북"),
    (152, 152,  "울산"),
    (155, 155,  "경남"),
    (165, 165,  "전남"),
    (239, 239,  "세종"),
]

FEATURES = ['month', 'day', 'hour', 'day_of_year',
            'lat', 'lon', 'ghi', 'cghi',
            'ta', 'rn', 'ws', 'wd', 'hm', 'pv', 'td', 'pa', 'ps', 'ss', 'icsr']

GHI_SLOPE, GHI_INTERCEPT = 237.6295, 14.6284

def add_ghi(df):
    df = df.copy()
    df['ghi'] = (GHI_SLOPE * df['icsr'] + GHI_INTERCEPT).clip(lower=0)
    df['date_key'] = df['datetime'].dt.date
    df['cghi'] = df.groupby('date_key')['ghi'].cumsum()
    df.drop(columns='date_key', inplace=True)
    return df

def load_location(stn_id, sp_id, year=2021):
    sp_files = sorted(glob.glob(f"{DATA_DIR}/solar_power_{year}_*.csv")) if sp_id is None \
               else sorted(glob.glob(f"{DATA_DIR}/solar_power_{sp_id}_{year}_*.csv"))
    if not sp_files: return pd.DataFrame()
    sp = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in sp_files], ignore_index=True)
    sp['datetime'] = pd.to_datetime(sp['Date'] + ' ' + sp['time'])
    sp[['lat','lon','pvAmt']] = sp[['lat','lon','pvAmt']].apply(pd.to_numeric, errors='coerce')

    asos_files = sorted(glob.glob(f"{DATA_DIR}/ASOS_{stn_id}_{year}_*.csv"))
    if not asos_files: return pd.DataFrame()
    asos = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in asos_files], ignore_index=True)
    asos['datetime'] = pd.to_datetime(asos['tm'])
    num_cols = ['ta','rn','ws','wd','hm','pv','td','pa','ps','ss','icsr']
    asos[num_cols] = asos[num_cols].apply(pd.to_numeric, errors='coerce')

    merged = pd.merge(sp[['datetime','lat','lon','pvAmt']],
                      asos[['datetime']+num_cols], on='datetime', how='inner')
    merged['month']      = merged['datetime'].dt.month
    merged['day']        = merged['datetime'].dt.day
    merged['hour']       = merged['datetime'].dt.hour
    merged['day_of_year']= merged['datetime'].dt.dayofyear
    merged = add_ghi(merged)
    return merged.dropna(subset=FEATURES + ['pvAmt'])

# ── 데이터 로드 ─────────────────────────────────────────────
print("데이터 로딩 중...")
all_dfs, labels = [], []
for stn_id, sp_id, name in LOCATIONS:
    df = load_location(stn_id, sp_id)
    if not df.empty:
        all_dfs.append(df)
        labels.append(name)
        print(f"  [{name}] {len(df)}행")

with open("trained_model.pkl", "rb") as f:
    saved = pickle.load(f)
model = saved["model"]

# ── 테스트셋 구성 (지점별 80/20) ────────────────────────────
test_parts = []
for df_loc in all_dfs:
    n = len(df_loc)
    test_parts.append(df_loc.iloc[int(n*0.8):].copy())
test_df = pd.concat(test_parts, ignore_index=True)

y_true = test_df['pvAmt'].values
y_pred = np.clip(model.predict(test_df[FEATURES]), 0, None)
residuals = y_true - y_pred

# ── 전체 지표 (테스트셋 직접 계산) ────────────────────────────
R2   = r2_score(y_true, y_pred)
RMSE = np.sqrt(mean_squared_error(y_true, y_pred))
MAE  = mean_absolute_error(y_true, y_pred)
print(f"\n테스트셋 직접 계산 → R²={R2:.4f}  RMSE={RMSE:.4f}  MAE={MAE:.4f}")
print(f"저장된 모델 메타값 → R²={saved['r2']:.4f}  RMSE={saved['rmse']:.4f}")

# ── 지점별 지표 ──────────────────────────────────────────────
loc_rows = []
for df_loc, name in zip(all_dfs, labels):
    n = len(df_loc)
    df_te = df_loc.iloc[int(n*0.8):]
    yt = df_te['pvAmt'].values
    yp = np.clip(model.predict(df_te[FEATURES]), 0, None)
    loc_rows.append({
        "name": name,
        "r2":   r2_score(yt, yp),
        "rmse": np.sqrt(mean_squared_error(yt, yp)),
        "n":    len(yt),
    })
loc_df = pd.DataFrame(loc_rows).sort_values("r2", ascending=True).reset_index(drop=True)

# ── 피처 중요도 (전체 19개) ──────────────────────────────────
importances = model.feature_importances_
total = importances.sum()
feat_df = pd.DataFrame({
    "feature": FEATURES,
    "imp": importances / total * 100
}).sort_values("imp", ascending=True)   # 19개 전부

print("\n피처 중요도 합계:", feat_df['imp'].sum().round(1), "%")

# ── 시각화 ───────────────────────────────────────────────────
fig = plt.figure(figsize=(20, 15))
fig.suptitle(
    f"LightGBM 모델 검증  ·  테스트셋 R²={R2:.4f}  |  RMSE={RMSE:.4f}  |  MAE={MAE:.4f}"
    f"  |  학습 지점 {len(all_dfs)}개  |  검증 샘플 {len(test_df):,}행",
    fontsize=13, fontweight='bold', y=0.99
)
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.50, wspace=0.38)

# ① 실제 vs 예측 ─────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, :2])
sc = ax1.scatter(y_true, y_pred, alpha=0.2, s=5,
                 c=test_df['month'].values, cmap='RdYlGn', vmin=1, vmax=12)
lim_lo = min(y_true.min(), y_pred.min())
lim_hi = max(y_true.max(), y_pred.max())
ax1.plot([lim_lo, lim_hi], [lim_lo, lim_hi], 'r--', lw=1.5, label='완벽 예측 (y=x)')
sl, ic, rv, pv, _ = stats.linregress(y_true, y_pred)
xs = np.array([lim_lo, lim_hi])
ax1.plot(xs, sl*xs+ic, 'b-', lw=1.3, alpha=0.8,
         label=f'회귀선  (기울기={sl:.3f}, 절편={ic:.3f})')
cb = fig.colorbar(sc, ax=ax1, shrink=0.85)
cb.set_label('월', fontsize=10)
ax1.set_xlabel('실제 pvAmt (kWh/kWp)', fontsize=10)
ax1.set_ylabel('예측 pvAmt (kWh/kWp)', fontsize=10)
ax1.set_title(f'실제 vs 예측  (R²={R2:.4f})', fontsize=12)
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)

# ② 잔차 분포 ──────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 2])
ax2.hist(residuals, bins=70, color='#409eff', edgecolor='white', linewidth=0.2, alpha=0.85)
ax2.axvline(0,               color='red',    lw=1.8, linestyle='--', label='0 기준선')
ax2.axvline(residuals.mean(),color='orange', lw=1.4, linestyle='-',
            label=f'평균={residuals.mean():.5f}')
ax2.set_xlabel('잔차 (실제 - 예측)', fontsize=10)
ax2.set_ylabel('빈도', fontsize=10)
ax2.set_title(f'잔차 분포  (표준편차={residuals.std():.4f})', fontsize=12)
ax2.legend(fontsize=9)
ax2.grid(alpha=0.3)

# ③ 피처 중요도 (19개 전체) ───────────────────────────────────
ax3 = fig.add_subplot(gs[1, 0])
colors3 = ['#f56c6c' if f in ('ghi','cghi','icsr') else
           '#409eff' if f in ('lat','lon') else '#67c23a'
           for f in feat_df['feature']]
bars3 = ax3.barh(feat_df['feature'], feat_df['imp'], color=colors3, height=0.65)
ax3.set_xlabel('중요도 (%)', fontsize=10)
ax3.set_title('피처 중요도 (전체 19개)', fontsize=12)
ax3.set_xlim(0, feat_df['imp'].max() * 1.22)
for bar, v in zip(bars3, feat_df['imp']):
    ax3.text(v + 0.1, bar.get_y() + bar.get_height()/2,
             f'{v:.1f}%', va='center', fontsize=8)
from matplotlib.patches import Patch
ax3.legend(handles=[Patch(color='#f56c6c', label='일사량 관련'),
                    Patch(color='#409eff', label='위치 (위·경도)'),
                    Patch(color='#67c23a', label='기상 변수')],
           fontsize=8, loc='lower right')
ax3.grid(alpha=0.3, axis='x')

# ④ 지점별 R² ──────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 1:])
bar_colors4 = ['#f56c6c' if r < 0.5 else '#e6a23c' if r < 0.7 else '#67c23a'
               for r in loc_df['r2']]
ylabels = [f"{row['name']} (n={row['n']})" for _, row in loc_df.iterrows()]
bars4 = ax4.barh(ylabels, loc_df['r2'], color=bar_colors4, height=0.6)
ax4.axvline(R2, color='#1a1a2e', lw=1.8, linestyle='--', label=f'전체 R²={R2:.4f}')
ax4.set_xlim(0, 1.12)
ax4.set_xlabel('R²', fontsize=10)
ax4.set_title('지점별 검증 R²  (테스트셋 재계산)', fontsize=12)
for bar, row in zip(bars4, loc_df.itertuples()):
    ax4.text(row.r2 + 0.01, bar.get_y() + bar.get_height()/2,
             f'{row.r2:.3f}', va='center', fontsize=9, fontweight='bold')
ax4.legend(fontsize=9)
ax4.grid(alpha=0.3, axis='x')

# ⑤ 잔차 vs 예측값 ─────────────────────────────────────────
ax5 = fig.add_subplot(gs[2, :2])
ax5.scatter(y_pred, residuals, alpha=0.15, s=4, color='#6366f1')
ax5.axhline(0, color='red', lw=1.8, linestyle='--', label='0 기준선')
sigma = residuals.std()
ax5.axhline( sigma, color='orange', lw=1.2, linestyle=':', label=f'+1σ = +{sigma:.4f}')
ax5.axhline(-sigma, color='orange', lw=1.2, linestyle=':', label=f'-1σ = -{sigma:.4f}')
ax5.set_xlabel('예측 pvAmt (kWh/kWp)', fontsize=10)
ax5.set_ylabel('잔차', fontsize=10)
ax5.set_title('잔차 vs 예측값  (등분산 확인)', fontsize=12)
ax5.legend(fontsize=9)
ax5.grid(alpha=0.3)

# ⑥ 지점별 평균 발전량 실제 vs 예측 ─────────────────────────
ax6 = fig.add_subplot(gs[2, 2])
act_means, prd_means = [], []
for df_loc in all_dfs:
    n = len(df_loc)
    df_te = df_loc.iloc[int(n*0.8):]
    act_means.append(df_te['pvAmt'].mean())
    prd_means.append(np.clip(model.predict(df_te[FEATURES]), 0, None).mean())

x = np.arange(len(labels))
w = 0.35
ax6.bar(x - w/2, act_means, w, label='실제', color='#409eff', alpha=0.9)
ax6.bar(x + w/2, prd_means, w, label='예측', color='#f59e0b', alpha=0.9)
ax6.set_xticks(x)
ax6.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
ax6.set_ylabel('평균 pvAmt (kWh/kWp)', fontsize=10)
ax6.set_title('지점별 평균 발전량  실제 vs 예측', fontsize=12)
ax6.legend(fontsize=9)
ax6.grid(alpha=0.3, axis='y')

# 수치 표시
for i, (a, p) in enumerate(zip(act_means, prd_means)):
    ax6.text(i - w/2, a + 0.001, f'{a:.3f}', ha='center', va='bottom', fontsize=6, color='#1d4ed8')
    ax6.text(i + w/2, p + 0.001, f'{p:.3f}', ha='center', va='bottom', fontsize=6, color='#92400e')

plt.savefig("model_validation.png", dpi=150, bbox_inches='tight')
print("\n저장 완료: model_validation.png")
plt.show()
