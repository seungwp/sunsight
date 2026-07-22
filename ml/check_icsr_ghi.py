"""icsr(ASOS)와 ghi(KIER) 상관관계 확인"""
import glob
import pandas as pd
import numpy as np
from scipy import stats

# 대전 2021 solar_energy + ASOS 병합
se_files = sorted(glob.glob("data/solar_energy_2021_*.csv"))
se = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in se_files], ignore_index=True)
se['datetime'] = pd.to_datetime(se['Date'] + ' ' + se['time'])

asos_files = sorted(glob.glob("data/ASOS_133_2021_*.csv"))
asos = pd.concat([pd.read_csv(f, encoding='utf-8-sig') for f in asos_files], ignore_index=True)
asos['datetime'] = pd.to_datetime(asos['tm'])
asos['icsr'] = pd.to_numeric(asos['icsr'], errors='coerce')

merged = pd.merge(se[['datetime','ghi','cghi']], asos[['datetime','icsr']], on='datetime')
merged = merged[(merged['ghi'] > 0) & (merged['icsr'] > 0)].dropna()

r, p = stats.pearsonr(merged['icsr'], merged['ghi'])
slope, intercept, rv, pv, _ = stats.linregress(merged['icsr'], merged['ghi'])

print(f"샘플 수: {len(merged)}")
print(f"icsr vs ghi  Pearson r={r:.4f}  p={p:.4e}")
print(f"선형 회귀: ghi = {slope:.4f} * icsr + {intercept:.4f}  (R²={rv**2:.4f})")
print(f"\nicsr 범위: {merged['icsr'].min():.4f} ~ {merged['icsr'].max():.4f}")
print(f"ghi  범위: {merged['ghi'].min():.4f} ~ {merged['ghi'].max():.4f}")
print(f"\n단위 비교 (icsr 1.0 → ghi {slope:.2f})")
