"""
icsr 기반 태양광 잠재력 점수 검증 시각화
출력: validation_report.png
"""
import json, glob, warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from scipy import stats
from pathlib import Path
warnings.filterwarnings('ignore')

# ── 한글 폰트 ────────────────────────────────────────────
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).parent.parent
DATA_DIR = "data"

SIDO_STATIONS = {
    "서울":   (108, 37.57),  "경기":   (119, 37.26),
    "인천":   (112, 37.48),  "강원":   (105, 37.75),
    "충북":   (131, 36.64),  "충남":   (129, 36.78),
    "세종":   (239, 36.48),  "대전":   (133, 36.35),
    "전북":   (146, 35.82),  "전남":   (165, 34.82),
    "광주":   (156, 35.17),  "경북":   (136, 36.57),
    "대구":   (143, 35.89),  "경남":   (155, 35.17),
    "울산":   (152, 35.56),  "부산":   (159, 35.10),
    "제주":   (184, 33.51),
}

SIDO_FULL = {
    "서울": "서울특별시", "경기": "경기도", "인천": "인천광역시",
    "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
    "세종": "세종특별자치시", "대전": "대전광역시", "전북": "전북특별자치도",
    "전남": "전라남도", "광주": "광주광역시", "경북": "경상북도",
    "대구": "대구광역시", "경남": "경상남도", "울산": "울산광역시",
    "부산": "부산광역시", "제주": "제주특별자치도",
}

# ── 데이터 로드 ───────────────────────────────────────────
with open(ROOT / "src" / "data" / "solarEfficiency.json", encoding="utf-8") as f:
    eff_raw = json.load(f)

rows = []
for short, full in SIDO_FULL.items():
    if full not in eff_raw:
        continue
    d = eff_raw[full]
    stn_id, lat = SIDO_STATIONS[short]
    rows.append({
        "sido": short, "full": full,
        "score": d.get("score", 0),
        "icsr": d.get("icsr_2025_mean", np.nan),
        "dsr": d.get("dsr_wm2", np.nan),
        "annual": d.get("annual", np.nan),
        "lat": lat,
        "stn": stn_id,
    })

df = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
df["rank"] = df.index + 1

# ── 월별 icsr 로드 ────────────────────────────────────────
monthly = {}
for short, full in SIDO_FULL.items():
    stn_id, _ = SIDO_STATIONS[short]
    files = sorted(glob.glob(f"{DATA_DIR}/ASOS_{stn_id}_2025_*.csv"))
    if not files:
        continue
    dfs = [pd.read_csv(f, encoding='utf-8-sig') for f in files]
    raw = pd.concat(dfs, ignore_index=True)
    raw['icsr'] = pd.to_numeric(raw['icsr'], errors='coerce')
    raw['month'] = pd.to_datetime(raw['tm']).dt.month
    m = raw[raw['icsr'] > 0].groupby('month')['icsr'].mean()
    monthly[short] = m

# ── 상관계수 ──────────────────────────────────────────────
valid = df.dropna(subset=["dsr", "annual"])
rho_dsr, p_dsr   = stats.spearmanr(valid["score"], valid["dsr"])
rho_ann, p_ann   = stats.spearmanr(valid["score"], valid["annual"])
rho_lat, p_lat   = stats.spearmanr(df["score"],  df["lat"])

# ═════════════════════════════════════════════════════════
#  레이아웃
# ═════════════════════════════════════════════════════════
fig = plt.figure(figsize=(20, 14), facecolor="#f8fafc")
fig.suptitle(
    "태양광 잠재력 점수 검증 보고서\n"
    "KMA ASOS 지표면 일사량(icsr) 2025년 기반",
    fontsize=16, fontweight='bold', color="#1a1a2e", y=0.98
)

gs = gridspec.GridSpec(2, 3, figure=fig,
                        left=0.06, right=0.97,
                        top=0.90, bottom=0.07,
                        hspace=0.42, wspace=0.38)

# 색상 팔레트
def score_color(s):
    if s >= 0.7:  return "#10b981"
    if s >= 0.4:  return "#f59e0b"
    return "#ef4444"

colors = [score_color(s) for s in df["score"]]

# ─────────────────────────────────────────────────────────
# (1) 시도별 점수 순위  [0,0]
# ─────────────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
bars = ax1.barh(df["sido"][::-1], df["score"][::-1], color=colors[::-1],
                edgecolor='white', linewidth=0.5, height=0.7)

for bar, score in zip(bars, df["score"][::-1]):
    ax1.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
             f'{score:.2f}', va='center', ha='left', fontsize=8, color='#374151')

ax1.set_xlim(0, 1.18)
ax1.set_xlabel("잠재력 점수 (0–1)", fontsize=9)
ax1.set_title("① 17개 시도 태양광 잠재력 점수", fontsize=11, fontweight='bold', pad=8)
ax1.axvline(0.7, color='#10b981', ls='--', lw=0.8, alpha=0.5)
ax1.axvline(0.4, color='#f59e0b', ls='--', lw=0.8, alpha=0.5)
ax1.tick_params(labelsize=9)
ax1.set_facecolor('#ffffff')
for spine in ax1.spines.values():
    spine.set_edgecolor('#e5e7eb')

# 범례
from matplotlib.patches import Patch
legend_elem = [Patch(facecolor='#10b981', label='상위 (≥0.7)'),
               Patch(facecolor='#f59e0b', label='중위 (0.4–0.7)'),
               Patch(facecolor='#ef4444', label='하위 (<0.4)')]
ax1.legend(handles=legend_elem, fontsize=7.5, loc='lower right',
           framealpha=0.8, edgecolor='#e5e7eb')

# ─────────────────────────────────────────────────────────
# (2) icsr vs Annual ASOS 산점도  [0,1]
# ─────────────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
sc = ax2.scatter(valid["annual"], valid["score"],
                 c=[score_color(s) for s in valid["score"]],
                 s=80, zorder=3, edgecolors='white', linewidths=0.5)

# 회귀선
m, b = np.polyfit(valid["annual"], valid["score"], 1)
x_line = np.linspace(valid["annual"].min(), valid["annual"].max(), 100)
ax2.plot(x_line, m*x_line+b, color='#6366f1', lw=1.5, alpha=0.7, zorder=2)

for _, row in valid.iterrows():
    ax2.annotate(row["sido"], (row["annual"], row["score"]),
                 textcoords="offset points", xytext=(5, 3),
                 fontsize=7, color='#374151')

sig = "★ 유의" if p_ann < 0.05 else "비유의"
ax2.set_xlabel("연간 일조량 평균 (ASOS annual)", fontsize=9)
ax2.set_ylabel("잠재력 점수", fontsize=9)
ax2.set_title(f"② icsr 점수 vs 연간 일조량\nSpearman ρ = {rho_ann:+.3f}  p = {p_ann:.3f}  {sig}",
              fontsize=10, fontweight='bold', pad=8)
ax2.set_facecolor('#ffffff')
for spine in ax2.spines.values():
    spine.set_edgecolor('#e5e7eb')
ax2.tick_params(labelsize=8)

# ─────────────────────────────────────────────────────────
# (3) icsr vs 위도  [0,2]
# ─────────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax3.scatter(df["lat"], df["score"],
            c=colors, s=80, zorder=3, edgecolors='white', linewidths=0.5)

m2, b2 = np.polyfit(df["lat"], df["score"], 1)
x2 = np.linspace(df["lat"].min(), df["lat"].max(), 100)
ax3.plot(x2, m2*x2+b2, color='#6366f1', lw=1.5, alpha=0.7)

for _, row in df.iterrows():
    ax3.annotate(row["sido"], (row["lat"], row["score"]),
                 textcoords="offset points", xytext=(4, 3),
                 fontsize=7, color='#374151')

sig3 = "★ 유의" if p_lat < 0.05 else "비유의"
ax3.set_xlabel("위도 (°N)  ← 남쪽     북쪽 →", fontsize=9)
ax3.set_ylabel("잠재력 점수", fontsize=9)
ax3.set_title(f"③ icsr 점수 vs 위도 (남쪽 = 일사량↑)\nSpearman ρ = {rho_lat:+.3f}  p = {p_lat:.3f}  {sig3}",
              fontsize=10, fontweight='bold', pad=8)
# 제주 이상치 표시
jeju = df[df['sido'] == '제주']
if not jeju.empty:
    ax3.annotate('제주 (섬, 구름 많음)', (jeju['lat'].values[0], jeju['score'].values[0]),
                 textcoords="offset points", xytext=(6, -14),
                 fontsize=7, color='#6b7280',
                 arrowprops=dict(arrowstyle='->', color='#9ca3af', lw=0.8))
ax3.set_facecolor('#ffffff')
for spine in ax3.spines.values():
    spine.set_edgecolor('#e5e7eb')
ax3.tick_params(labelsize=8)

# ─────────────────────────────────────────────────────────
# (4) 월별 icsr 패턴 — 상위 3 / 하위 3  [1,0:2]
# ─────────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, :2])

months = list(range(1, 13))
month_labels = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']

top3    = df.head(3)["sido"].tolist()
bottom3 = df.tail(3)["sido"].tolist()

palette_top    = ["#10b981", "#34d399", "#6ee7b7"]
palette_bottom = ["#ef4444", "#f87171", "#fca5a5"]

for i, sido in enumerate(top3):
    if sido not in monthly:
        continue
    vals = [monthly[sido].get(m, np.nan) for m in months]
    ax4.plot(months, vals, color=palette_top[i], lw=2, marker='o', ms=5,
             label=f"{sido} (상위 {i+1}위, {df[df.sido==sido].score.values[0]:.2f})")

for i, sido in enumerate(bottom3):
    if sido not in monthly:
        continue
    vals = [monthly[sido].get(m, np.nan) for m in months]
    ax4.plot(months, vals, color=palette_bottom[i], lw=2, marker='s', ms=5,
             ls='--', label=f"{sido} (하위 {i+1}위, {df[df.sido==sido].score.values[0]:.2f})")

ax4.set_xticks(months)
ax4.set_xticklabels(month_labels, fontsize=9)
ax4.set_ylabel("icsr 평균 (MJ/m²)", fontsize=9)
ax4.set_title("④ 월별 icsr 패턴 비교 — 상위 3 / 하위 3 지역 (2025년)", fontsize=11, fontweight='bold', pad=8)
ax4.legend(fontsize=8, ncol=2, framealpha=0.8, edgecolor='#e5e7eb', loc='upper left')
ax4.set_facecolor('#ffffff')
ax4.grid(axis='y', color='#f3f4f6', lw=0.8)
for spine in ax4.spines.values():
    spine.set_edgecolor('#e5e7eb')
ax4.tick_params(labelsize=8)

# ─────────────────────────────────────────────────────────
# (5) 검증 요약 카드  [1,2]
# ─────────────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 2])
ax5.axis('off')

summary_lines = [
    ("데이터 출처", "KMA ASOS 종관기상관측 2025"),
    ("측정 지표", "지표면 일사량 icsr (MJ/m²/h)"),
    ("대상 시도", "전국 17개 시/도"),
    ("", ""),
    ("─── 상관 검증 ───", ""),
    ("vs 연간 일조량", f"ρ = {rho_ann:+.3f}  p = {p_ann:.3f}  {'★ 유의' if p_ann < 0.05 else '—'}"),
    ("vs 위도",       f"ρ = {rho_lat:+.3f}  p = {p_lat:.3f}  {'★ 유의' if p_lat < 0.05 else '—'}"),
    ("vs DSR(직달)",  f"ρ = {rho_dsr:+.3f}  p = {p_dsr:.3f}  {'★ 유의' if p_dsr < 0.05 else '—'}"),
    ("", ""),
    ("─── 순위 상위 3 ───", ""),
]
for s, _ in df.head(3).iterrows():
    r = df.iloc[s]
    summary_lines.append((f"{r['rank']}위 {r['sido']}", f"icsr {r['icsr']:.4f} / 점수 {r['score']:.3f}"))

summary_lines += [
    ("", ""),
    ("─── 순위 하위 3 ───", ""),
]
for s in range(len(df)-3, len(df)):
    r = df.iloc[s]
    summary_lines.append((f"{r['rank']}위 {r['sido']}", f"icsr {r['icsr']:.4f} / 점수 {r['score']:.3f}"))

y = 0.98
for key, val in summary_lines:
    if key.startswith("───"):
        ax5.text(0.0, y, key, fontsize=8.5, color='#6366f1', fontweight='bold',
                 transform=ax5.transAxes, va='top')
    elif key == "":
        pass
    else:
        ax5.text(0.0, y, key, fontsize=8, color='#6b7280',
                 transform=ax5.transAxes, va='top')
        ax5.text(1.0, y, val, fontsize=8, color='#1a1a2e',
                 transform=ax5.transAxes, va='top', ha='right')
    y -= 0.067

ax5.set_title("⑤ 검증 요약", fontsize=11, fontweight='bold', pad=8)

# 배경 카드
rect = FancyBboxPatch((0, 0), 1, 1, transform=ax5.transAxes,
                       boxstyle="round,pad=0.02", linewidth=1,
                       edgecolor='#e5e7eb', facecolor='#ffffff', zorder=0)
ax5.add_patch(rect)

# ─────────────────────────────────────────────────────────
out_path = Path("validation_report.png")
fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close()
print(f"저장 완료: {out_path.resolve()}")
