"""
전국 시도별 태양광 발전량 예측 데이터 수집 스크립트
KIER API (태양광 발전량 예측정보 서비스)를 사용하여
시도별 대표 좌표에서 pvAmt 데이터를 수집하고 solarEfficiency.json을 업데이트합니다.

사전 준비:
  .env 파일에 KIER_SERVICE_KEY 설정 필요 (data.go.kr에서 발급)

실행:
  python scripts/collect_kier_nationwide.py --year 2024
  python scripts/collect_kier_nationwide.py --year 2024 --sido 경기도  # 특정 시도만
"""

import os
import sys
import json
import time
import argparse
import calendar
import csv
import requests
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 기준 경로 설정
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def load_env():
    env_path = ROOT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                # 인라인 주석 제거 (공백+# 이후)
                v = v.split(" #")[0].split("\t#")[0].strip()
                env[k.strip()] = v
    return env


SIDO_BBOX = {
    "강원특별자치도":   (37.1, 38.6, 127.7, 129.4),
    "경기도":          (36.9, 37.9, 126.4, 127.9),
    "경상남도":        (34.7, 35.8, 127.6, 129.4),
    "경상북도":        (35.7, 37.1, 128.0, 129.6),
    "광주광역시":      (35.0, 35.3, 126.7, 127.1),
    "대구광역시":      (35.7, 36.1, 128.4, 128.8),
    "대전광역시":      (36.2, 36.5, 127.2, 127.6),
    "부산광역시":      (35.0, 35.4, 128.8, 129.4),
    "서울특별시":      (37.4, 37.7, 126.7, 127.2),
    "세종특별자치시":  (36.4, 36.6, 127.1, 127.4),
    "울산광역시":      (35.4, 35.7, 129.0, 129.5),
    "인천광역시":      (37.2, 37.7, 126.3, 126.8),
    "전라남도":        (34.1, 35.0, 126.1, 127.9),
    "전북특별자치도":  (35.3, 36.1, 126.4, 127.8),
    "제주특별자치도":  (33.1, 33.6, 126.1, 126.9),
    "충청남도":        (36.0, 37.0, 126.0, 127.4),
    "충청북도":        (36.2, 37.3, 127.4, 128.5),
}


def get_sido_coords(substations_path: Path, ird_path: Path) -> dict:
    """
    시도별 후보 좌표 목록 반환.
    Ird_LatLon.csv(천리안2 위성 격자)에서 시도 바운딩박스 내 좌표를 샘플링.
    """
    with open(substations_path, encoding="utf-8") as f:
        sub_data = json.load(f)

    # 변전소 centroid 계산 (참고용)
    sido_points = {}
    for sub in sub_data.values():
        sido = sub.get("sido")
        lat, lng = sub.get("lat"), sub.get("lng")
        if not sido or lat is None or lng is None:
            continue
        sido_points.setdefault(sido, []).append((float(lat), float(lng)))

    # Ird_LatLon.csv 로드 (약 38만개)
    ird_coords = []
    with open(ird_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ird_coords.append((float(row["Lat"]), float(row["Lon"])))

    coords = {}
    for sido, bbox in SIDO_BBOX.items():
        lat_min, lat_max, lon_min, lon_max = bbox
        # bbox 내 Ird 좌표 필터링 후 균등 샘플링 (최대 30개)
        filtered = [(la, lo) for la, lo in ird_coords
                    if lat_min <= la <= lat_max and lon_min <= lo <= lon_max]
        step = max(1, len(filtered) // 30)
        candidates = filtered[::step][:30]
        n = len(sido_points.get(sido, []))
        coords[sido] = {"candidates": candidates, "n": n}
        print(f"  {sido}: bbox 내 Ird좌표 {len(filtered)}개 → 후보 {len(candidates)}개")

    return coords


def fetch_pvamt_daily(service_key: str, date: str, lat: float, lon: float) -> float | None:
    """
    특정 날짜/좌표의 pvAmt 일평균을 반환합니다.
    API: KIER 태양광 발전량 예측정보 서비스 (getSolarPvHrInfo)
    """
    url = "https://apis.data.go.kr/B551184/SolarPvService/getSolarPvHrInfo"
    params = {
        "serviceKey": service_key,
        "date": date,
        "lat": lat,
        "lon": lon,
        "pageNo": 1,
        "numOfRows": 24,
        "type": "json",
    }
    try:
        resp = requests.get(url, params=params, timeout=30, verify=True)
        resp.raise_for_status()
        body = resp.json().get("response", {}).get("body", {})
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            return None
        values = [float(i["pvAmt"]) for i in items if i.get("pvAmt") not in (None, "")]
        return sum(values) / len(values) if values else None
    except Exception as e:
        print(f"    API 오류 ({date}): {e}")
        return None


def fetch_pvamt_monthly(service_key: str, year: int, month: int, lat: float, lon: float,
                        sample_days: int = 3, delay: float = 0.3) -> float | None:
    """
    월 내 sample_days 일을 샘플링해 pvAmt 평균 반환.
    API 호출 수를 줄이기 위해 월의 1일, 중간일, 말일을 대표로 사용.
    """
    last_day = calendar.monthrange(year, month)[1]
    mid_day = last_day // 2
    days = sorted(set([1, mid_day, last_day]))[:sample_days]

    values = []
    for day in days:
        date_str = f"{year}{month:02d}{day:02d}"
        val = fetch_pvamt_daily(service_key, date_str, lat, lon)
        if val is not None:
            values.append(val)
        time.sleep(delay)

    return sum(values) / len(values) if values else None


def find_valid_coord(service_key: str, candidates: list, year: int) -> tuple | None:
    """데이터가 있는 첫 번째 좌표를 반환 (6월 중순으로 빠른 확인)"""
    test_date = f"{year}0615"
    for lat, lon in candidates:
        url = "https://apis.data.go.kr/B551184/SolarPvService/getSolarPvHrInfo"
        params = {"serviceKey": service_key, "date": test_date, "lat": lat, "lon": lon,
                  "pageNo": 1, "numOfRows": 3, "type": "json"}
        try:
            resp = requests.get(url, params=params, timeout=15, verify=True)
            body = resp.json().get("response", {}).get("body", {})
            if int(body.get("totalCount", 0)) > 0:
                return (lat, lon)
        except Exception:
            pass
        time.sleep(0.2)
    return None


def collect_sido_annual_pvamt(service_key: str, sido: str, candidates: list,
                               year: int) -> float | None:
    """시도 좌표 후보 중 데이터 있는 좌표로 연간 pvAmt 평균 수집"""
    print(f"  유효 좌표 탐색 중...", end=" ", flush=True)
    coord = find_valid_coord(service_key, candidates, year)
    if coord is None:
        print("없음")
        return None
    lat, lon = coord
    print(f"lat={lat}, lon={lon}")

    monthly_values = []
    for month in range(1, 13):
        print(f"  {sido} {year}-{month:02d}...", end=" ", flush=True)
        val = fetch_pvamt_monthly(service_key, year, month, lat, lon)
        if val is not None:
            monthly_values.append(val)
            print(f"{val:.4f}")
        else:
            print("데이터 없음")
    return sum(monthly_values) / len(monthly_values) if monthly_values else None


def update_solar_efficiency(pvamt_scores: dict, efficiency_path: Path):
    """solarEfficiency.json의 score를 pvAmt 기반 0~1 정규화 점수로 업데이트"""
    with open(efficiency_path, encoding="utf-8") as f:
        efficiency = json.load(f)

    valid = {k: v for k, v in pvamt_scores.items() if v is not None}
    if not valid:
        print("업데이트할 데이터가 없습니다.")
        return

    min_v = min(valid.values())
    max_v = max(valid.values())
    rng = max_v - min_v if max_v != min_v else 1.0

    updated, missing = [], []
    for sido in efficiency:
        if sido in valid:
            score = round((valid[sido] - min_v) / rng, 4)
            efficiency[sido]["score"] = score
            efficiency[sido]["pvamt_annual"] = round(valid[sido], 4)
            updated.append(sido)
        else:
            missing.append(sido)

    with open(efficiency_path, "w", encoding="utf-8") as f:
        json.dump(efficiency, f, ensure_ascii=False, indent=2)

    print(f"\n=== 업데이트 완료 ({len(updated)}개 시도) ===")
    for s in sorted(updated):
        print(f"  {s}: score={round((valid[s]-min_v)/rng,4):.4f}  pvAmt={valid[s]:.4f}")
    if missing:
        print(f"\n미매칭 (데이터 없음): {missing}")


def main():
    parser = argparse.ArgumentParser(description="전국 시도별 KIER pvAmt 수집")
    parser.add_argument("--year", type=int, default=2021, help="수집 연도 (기본: 2021, KIER 제공 기간: 2020~2021)")
    parser.add_argument("--sido", type=str, default=None, help="특정 시도만 수집 (기본: 전체)")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 좌표만 출력")
    args = parser.parse_args()

    env = load_env()
    service_key = env.get("KIER_SOLAR_PV_KEY", "")
    if not args.dry_run and (not service_key or service_key.startswith("your_key")):
        print("오류: .env 파일에 KIER_SERVICE_KEY를 설정해 주세요.")
        print("  data.go.kr → '한국에너지기술연구원 태양에너지' 검색 → 활용신청 → Decoding 인증키")
        sys.exit(1)

    substations_path = ROOT / "src" / "data" / "substationCoords.json"
    efficiency_path = ROOT / "src" / "data" / "solarEfficiency.json"

    print("시도별 대표 좌표 계산 중...")
    coords = get_sido_coords(substations_path)

    # 세종특별자치시 수동 추가 (substations 없음)
    if "세종특별자치시" not in coords:
        coords["세종특별자치시"] = {
            "candidates": [(36.4800, 127.2890), (36.5, 127.3), (36.47, 127.26)],
            "n": 0,
        }

    target_sidos = [args.sido] if args.sido else sorted(coords.keys())

    print(f"\n수집 대상: {len(target_sidos)}개 시도, 연도: {args.year}")
    for sido in target_sidos:
        c = coords.get(sido, {})
        print(f"  {sido}: 변전소 수={c.get('n', 0)}, 후보 좌표 {len(c.get('candidates', []))}개")

    if args.dry_run:
        print("\n[dry-run] API 호출 없이 종료합니다.")
        return

    print("\n데이터 수집 시작...")
    pvamt_scores = {}
    for sido in target_sidos:
        if sido not in coords:
            print(f"[경고] {sido} 좌표 없음, 건너뜀")
            continue
        c = coords[sido]
        print(f"\n[{sido}] 변전소 {c['n']}개")
        val = collect_sido_annual_pvamt(service_key, sido, c["candidates"], args.year)
        pvamt_scores[sido] = val
        print(f"  → 연간 pvAmt 평균: {val:.4f}" if val else "  → 수집 실패")

    # 중간 결과 저장 (JSON)
    output_dir = ROOT / "scripts" / "output"
    output_dir.mkdir(exist_ok=True)
    result_path = output_dir / f"pvamt_{args.year}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(pvamt_scores, f, ensure_ascii=False, indent=2)
    print(f"\n중간 결과 저장: {result_path}")

    update_solar_efficiency(pvamt_scores, efficiency_path)


if __name__ == "__main__":
    main()
