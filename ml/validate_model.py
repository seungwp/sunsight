"""
모델 검증 스크립트
1. 피처 중요도 분석 (ghi 의존도)
2. 예측 vs 실제 산점도 (과적합 체크)
3. 시도별 ML 점수 vs 물리적 기준 비교
4. 스피어만 순위 상관계수
"""
import json, pickle, glob, warnings
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
warnings.filterwarnings('ignore')

DATA_DIR = "data"
ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────
# 1. 모델 로드
# ─────────────────────────────────────────
with open("trained_model.pkl", "rb") as f:
    saved = pickle.load(f)
model = saved["model"]
FEATURES = saved["features"]
print(f"모델 R²={saved['r2']:.4f}  RMSE={saved['rmse']:.6f}")

# ─────────────────────────────────────────
# 2. 피처 중요도
# ─────────────────────────────────────────
importances = model.feature_importances_
total = importances.sum()
print("\n=== 피처 중요도 (gain 기반) ===")
for feat, imp in sorted(zip(FEATURES, importances), key=lambda x: -x[1]):
    bar = "#" * int(imp / total * 40)
    print(f"  {feat:15s} {imp/total*100:5.1f}%  {bar}")

icsr_share = importances[FEATURES.index('icsr')] / total
print(f"\n  icsr(지표면 일사량) 기여: {icsr_share*100:.1f}%")

# ─────────────────────────────────────────
# 3. 테스트셋 재현 (대전 2021 20% 구간)
# ─────────────────────────────────────────
def load_dataset():
    se_files = sorted(glob.glob(f"{DATA_DIR}/solar_energy_2021_*.csv"))
    sp_files = sorted(glob.glob(f"{DATA_DIR}/solar_power_2021_*.csv"))
    as_files = sorted(glob.glob(f"{DATA_DIR}/ASOS_133_2021_*.csv"))
    if not se_files or not sp_files or not as_files:
        return pd.DataFrame()
    se = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in se_files], ignore_index=True)
    sp = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in sp_files], ignore_index=True)
    asos = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in as_files], ignore_index=True)
    se['datetime'] = pd.to_datetime(se['Date'] + ' ' + se['time'])
    sp['datetime'] = pd.to_datetime(sp['Date'] + ' ' + sp['time'])
    asos['datetime'] = pd.to_datetime(asos['tm'])
    se[['ghi','cghi','lat','lon']] = se[['ghi','cghi','lat','lon']].apply(pd.to_numeric, errors='coerce')
    se['month'] = se['datetime'].dt.month
    se['day'] = se['datetime'].dt.day
    se['hour'] = se['datetime'].dt.hour
    se['day_of_year'] = se['datetime'].dt.dayofyear
    asos['hour'] = asos['datetime'].dt.hour
    asos['day_of_year'] = asos['datetime'].dt.dayofyear
    merged = pd.merge(se[['datetime','month','day','hour','day_of_year','lat','lon','ghi','cghi']],
                      asos[['datetime','ta','rn','ws','wd','hm','pv','td','pa','ps','ss','icsr']], on='datetime', how='inner')
    merged = pd.merge(merged, sp[['datetime','pvAmt']], on='datetime', how='inner')
    for c in ['ta','rn','ws','wd','hm','pv','td','pa','ps','ss','icsr','pvAmt']:
        merged[c] = pd.to_numeric(merged[c], errors='coerce')
    return merged.dropna(subset=FEATURES+['pvAmt'])

df = load_dataset()
if not df.empty:
    split = int(len(df) * 0.8)
    test = df.iloc[split:]
    y_true = test['pvAmt'].values
    y_pred = model.predict(test[FEATURES])

    # 낮 시간대만 (pvAmt > 0)
    mask = y_true > 0.001
    y_t, y_p = y_true[mask], y_pred[mask]

    bias = np.mean(y_p - y_t)
    rel_err = np.mean(np.abs(y_p - y_t) / y_t) * 100

    print(f"\n=== 테스트셋 상세 분석 (낮 시간 {mask.sum()}행) ===")
    print(f"  평균 편향(Bias)       : {bias:+.6f}  ({'과대' if bias > 0 else '과소'}추정)")
    print(f"  평균 상대오차(MAPE)   : {rel_err:.2f}%")
    print(f"  상관계수              : {np.corrcoef(y_t, y_p)[0,1]:.6f}")

    # 분위수별 오차
    q25, q75 = np.percentile(y_t, 25), np.percentile(y_t, 75)
    for label, m in [("하위 25%", y_t < q25), ("중간 50%", (y_t >= q25) & (y_t < q75)), ("상위 25%", y_t >= q75)]:
        err = np.mean(np.abs(y_p[m] - y_t[m]) / y_t[m]) * 100 if m.sum() else 0
        print(f"  {label} MAPE           : {err:.1f}%")

    # ── icsr 없이 예측했을 때 성능 ──────────────────────
    print("\n=== icsr을 0으로 대체했을 때 성능 저하 ===")
    from sklearn.metrics import r2_score
    test_noicsr = test[FEATURES].copy()
    test_noicsr['icsr'] = 0
    y_noicsr = model.predict(test_noicsr)
    r2_noicsr = r2_score(y_true, y_noicsr)
    print(f"  icsr 제거 후 R² : {r2_noicsr:.4f}  (원래 {saved['r2']:.4f})")
    print(f"  → icsr의 실제 기여: R² {saved['r2']-r2_noicsr:.4f} 감소")

# ─────────────────────────────────────────
# 4. 시도별 순위 비교 (ML vs DSR vs Annual)
# ─────────────────────────────────────────
eff_path = ROOT / "src" / "data" / "solarEfficiency.json"
with open(eff_path, encoding="utf-8") as f:
    eff = json.load(f)

rows = []
for sido, d in eff.items():
    rows.append({
        "sido": sido,
        "ml_score": d.get("score", 0),
        "pvamt_2025": d.get("pvamt_2025", 0),
        "dsr_wm2": d.get("dsr_wm2", None),
        "annual": d.get("annual", 0),
    })
df_comp = pd.DataFrame(rows).dropna(subset=["dsr_wm2"])

print("\n=== 시도별 순위 비교 ===")
print(f"{'시도':<14} {'ML순위':>6} {'DSR순위':>7} {'Annual순위':>10} {'pvamt':>10} {'dsr_wm2':>8} {'annual':>7}")
print("-" * 70)

df_comp['ml_rank'] = df_comp['pvamt_2025'].rank(ascending=False).astype(int)
df_comp['dsr_rank'] = df_comp['dsr_wm2'].rank(ascending=False).astype(int)
df_comp['ann_rank'] = df_comp['annual'].rank(ascending=False).astype(int)

for _, r in df_comp.sort_values('ml_rank').iterrows():
    flag = ""
    rank_diff = abs(r['ml_rank'] - r['dsr_rank'])
    if rank_diff >= 5:
        flag = " ← 괴리"
    print(f"{r['sido']:<14} {r['ml_rank']:>6} {r['dsr_rank']:>7} {r['ann_rank']:>10}  "
          f"{r['pvamt_2025']:>9.4f}  {r['dsr_wm2']:>7.1f}  {r['annual']:>6.2f}{flag}")

# 스피어만 상관
rho_dsr, p_dsr = stats.spearmanr(df_comp['pvamt_2025'], df_comp['dsr_wm2'])
rho_ann, p_ann = stats.spearmanr(df_comp['pvamt_2025'], df_comp['annual'])

print(f"\n=== 순위 일관성 (스피어만 상관) ===")
sig_dsr = "유의" if p_dsr < 0.05 else "비유의"
sig_ann = "유의" if p_ann < 0.05 else "비유의"
print(f"  ML점수 vs DSR(위성 직달 일사량) : rho={rho_dsr:+.3f}  p={p_dsr:.3f}  {sig_dsr}")
print(f"  ML점수 vs ASOS Annual avg      : rho={rho_ann:+.3f}  p={p_ann:.3f}  {sig_ann}")

if abs(rho_dsr) < 0.5:
    print("\n  경고: ML 점수와 직달 일사량 순위가 크게 다릅니다.")
    print("  → 단일 지점(대전) 학습의 지역 외삽 오차일 가능성이 높습니다.")
elif rho_dsr < 0:
    print("\n  경고: 역상관 — ML이 일사량 많은 지역을 오히려 낮게 평가하고 있습니다.")
else:
    print("\n  순위가 물리적 기준과 일치합니다.")


print("\n검증 완료")
