import json
from pathlib import Path
ROOT = Path(__file__).parent.parent
with open(ROOT / "src" / "data" / "solarEfficiency.json", encoding="utf-8") as f:
    eff = json.load(f)
print("시도별 score 순위 (LightGBM 11지점 재학습):")
for sido, d in sorted(eff.items(), key=lambda x: -x[1].get("score", 0)):
    score = d.get("score", 0)
    pvamt = d.get("pvamt_2025", 0)
    icsr  = d.get("icsr_2025_mean", 0)
    print(f"  {sido:<16} score={score:.4f}  pvamt={pvamt:.6f}  icsr={icsr:.4f}")
