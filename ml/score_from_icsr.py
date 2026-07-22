"""
2025 ASOS icsr(지표면 일사량) 기반 시도별 발전 잠재력 점수 산출
- icsr 단위: MJ/m²/h
- 낮 시간대(icsr > 0) 평균값 → 지역별 태양광 잠재력 대리 지표
- 0~1 min-max 정규화 → solarEfficiency.json score 업데이트
"""
import json, glob, warnings
import pandas as pd
import numpy as np
from pathlib import Path
warnings.filterwarnings('ignore')

DATA_DIR = "data"
ROOT = Path(__file__).parent.parent

SIDO_STATIONS = {
    "서울특별시":      108,
    "경기도":          119,
    "인천광역시":      112,
    "강원특별자치도":  105,
    "충청북도":        131,
    "충청남도":        129,
    "세종특별자치시":  239,
    "대전광역시":      133,
    "전북특별자치도":  146,
    "전라남도":        165,
    "광주광역시":      156,
    "경상북도":        136,
    "대구광역시":      143,
    "경상남도":        155,
    "울산광역시":      152,
    "부산광역시":      159,
    "제주특별자치도":  184,
}

print("시도별 2025 ASOS icsr 집계...")
results = {}

for sido, stn_id in SIDO_STATIONS.items():
    files = sorted(glob.glob(f"{DATA_DIR}/ASOS_{stn_id}_2025_*.csv"))
    if not files:
        print(f"  [{sido}] 파일 없음")
        continue

    dfs = [pd.read_csv(f, encoding='utf-8-sig') for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df['icsr'] = pd.to_numeric(df['icsr'], errors='coerce')
    df['datetime'] = pd.to_datetime(df['tm'])
    df['month'] = df['datetime'].dt.month

    # 낮 시간대만 (icsr > 0)
    day = df[df['icsr'] > 0]
    if day.empty:
        print(f"  [{sido}] icsr 데이터 없음")
        continue

    annual_mean = float(day['icsr'].mean())
    annual_sum = float(df['icsr'].fillna(0).sum())  # 연간 누적
    data_months = df['month'].nunique()

    results[sido] = {
        'mean': annual_mean,
        'annual_sum': annual_sum,
        'n_daytime': len(day),
        'months': data_months,
    }
    print(f"  [{sido}] 낮평균={annual_mean:.4f} MJ/m²  누적={annual_sum:.1f}  낮시간={len(day)}h  ({data_months}개월)")

# 0~1 정규화 (낮 평균 기준)
print(f"\n집계 완료: {len(results)}개 시도")
vals = {s: d['mean'] for s, d in results.items()}
min_v, max_v = min(vals.values()), max(vals.values())
rng = max_v - min_v

print(f"\n=== 시도별 icsr 기반 점수 ===")
scores = {}
for sido, val in sorted(vals.items(), key=lambda x: -x[1]):
    score = round((val - min_v) / rng, 4)
    scores[sido] = score
    months = results[sido]['months']
    note = f" ← {months}개월만" if months < 12 else ""
    print(f"  {sido:<14} icsr={val:.4f}  score={score:.4f}{note}")

# solarEfficiency.json 업데이트
eff_path = ROOT / "src" / "data" / "solarEfficiency.json"
with open(eff_path, encoding="utf-8") as f:
    efficiency = json.load(f)

updated, missing = [], []
for sido in efficiency:
    if sido in scores:
        efficiency[sido]["score"] = scores[sido]
        efficiency[sido]["icsr_2025_mean"] = round(results[sido]['mean'], 6)
        efficiency[sido].pop("pvamt_2025", None)  # 이전 ML 필드 제거
        updated.append(sido)
    else:
        missing.append(sido)

with open(eff_path, "w", encoding="utf-8") as f:
    json.dump(efficiency, f, ensure_ascii=False, indent=2)

print(f"\nsolarEfficiency.json 업데이트: {len(updated)}개 시도")
if missing:
    print(f"  미업데이트: {missing}")
print("완료!")
