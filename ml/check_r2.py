import json, numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).parent.parent
with open(ROOT / "src/data/solarEfficiency.json", encoding="utf-8") as f:
    eff = json.load(f)

SIDO_LAT = {
    "서울특별시": 37.57, "경기도": 37.26, "인천광역시": 37.48,
    "강원특별자치도": 37.75, "충청북도": 36.64, "충청남도": 36.78,
    "세종특별자치시": 36.48, "대전광역시": 36.35, "전북특별자치도": 35.82,
    "전라남도": 34.82, "광주광역시": 35.17, "경상북도": 36.57,
    "대구광역시": 35.89, "경상남도": 35.17, "울산광역시": 35.56,
    "부산광역시": 35.10, "제주특별자치도": 33.51,
}

rows = []
for sido, d in eff.items():
    if sido not in SIDO_LAT: continue
    rows.append({
        "sido": sido,
        "score": d.get("score", 0),
        "annual": d.get("annual", 0),
        "dsr": d.get("dsr_wm2", 0),
        "icsr": d.get("icsr_2025_mean", 0),
        "lat": SIDO_LAT[sido],
    })

scores  = np.array([r["score"]  for r in rows])
annual  = np.array([r["annual"] for r in rows])
lat_arr = np.array([r["lat"]    for r in rows])
dsr_arr = np.array([r["dsr"]    for r in rows])
icsr_arr= np.array([r["icsr"]   for r in rows])

def reg(x, y, label):
    sl, ic, r, p, _ = stats.linregress(x, y)
    rho, ps = stats.spearmanr(x, y)
    sig = "유의" if p < 0.05 else "-"
    print(f"  {label:<28}  R2={r**2:.4f}  rho={rho:+.3f}  p={p:.3f}  {sig}")

print("=== LightGBM score 결정계수 ===")
reg(scores, annual,  "score vs 연간 일조량(Annual)")
reg(scores, lat_arr, "score vs 위도(Lat)")
reg(scores, dsr_arr, "score vs DSR")
reg(scores, icsr_arr,"score vs icsr 실측")

print("\n=== 학습 모델 자체 R² ===")
import pickle
with open("trained_model.pkl", "rb") as f:
    saved = pickle.load(f)
print(f"  LightGBM test R² = {saved['r2']:.4f}  (11개 지점 2021 학습/검증)")
