"""
다지점 학습용 데이터 다운로드
- KIER solar_power 2021 (pvAmt 정답값) → solar_power_{stn_id}_2021_MM.csv
- ASOS 2021 기상 데이터              → ASOS_{stn_id}_2021_MM.csv (기존 형식 동일)
5개 추가 지점: 제주, 부산, 광주, 서울, 강릉
"""
import sys, os, calendar, time
sys.path.insert(0, '.')
import requests
import pandas as pd

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(os.path.dirname(__file__), '..', '.env'), encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('KIER_SOLAR_PV_KEY='):
            KIER_KEY = line.split('=', 1)[1].split(' #')[0].strip()
        if line.startswith('KMA_SERVICE_KEY='):
            KMA_KEY = line.split('=', 1)[1].split(' #')[0].strip()

SOLAR_PV_URL = "https://apis.data.go.kr/B551184/SolarPvService/getSolarPvHrInfo"
ASOS_URL = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"

LOCATIONS = [
    ("제주",  33.5168425493, 126.531920715,  184),
    ("부산",  35.1020946418, 129.0318422193, 159),
    ("광주",  35.1727449827, 126.8921528618, 156),
    ("서울",  37.5724271096, 126.9664820861, 108),
    ("강릉",  37.7533294507, 128.8733191481, 105),
]

def download_solar_power_year(name, lat, lon, stn_id, year=2021):
    print(f"\n[{name}] KIER solar_power {year} 다운로드...")
    for month in range(1, 13):
        out = f"{DATA_DIR}/solar_power_{stn_id}_{year}_{month:02d}.csv"
        if os.path.exists(out):
            print(f"  {month:02d}월 이미 존재, 건너뜀")
            continue
        rows = []
        last_day = calendar.monthrange(year, month)[1]
        for day in range(1, last_day + 1):
            params = {
                "serviceKey": KIER_KEY,
                "date": f"{year}{month:02d}{day:02d}",
                "lat": lat, "lon": lon,
                "pageNo": 1, "numOfRows": 24, "type": "json"
            }
            try:
                r = requests.get(SOLAR_PV_URL, params=params, timeout=30)
                items = r.json()['response']['body']['items']['item']
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    item['year'] = year; item['month'] = month; item['day'] = day
                rows.extend(items)
            except Exception:
                pass
        if rows:
            pd.DataFrame(rows).to_csv(out, index=False, encoding='utf-8-sig')
            print(f"  {month:02d}월 저장 ({len(rows)}행)")
        else:
            print(f"  {month:02d}월 데이터 없음")

def download_asos_year(name, stn_id, year=2021):
    print(f"\n[{name}] ASOS {year} 다운로드...")
    for month in range(1, 13):
        out = f"{DATA_DIR}/ASOS_{stn_id}_{year}_{month:02d}.csv"
        if os.path.exists(out):
            print(f"  ASOS {month:02d}월 이미 존재, 건너뜀")
            continue
        nm = month + 1 if month < 12 else 1
        ny = year if month < 12 else year + 1
        params = {
            'serviceKey': KMA_KEY, 'pageNo': '1', 'numOfRows': '999',
            'dataType': 'json', 'dataCd': 'ASOS', 'dateCd': 'HR',
            'startDt': f'{year}{month:02d}01', 'startHh': '00',
            'endDt': f'{ny}{nm:02d}01', 'endHh': '23',
            'stnIds': str(stn_id)
        }
        try:
            r = requests.get(ASOS_URL, params=params, timeout=30)
            items = r.json()['response']['body']['items']['item']
            if not isinstance(items, list):
                items = [items]
            pd.DataFrame(items).to_csv(out, index=False, encoding='utf-8-sig')
            print(f"  ASOS {month:02d}월 저장 ({len(items)}행)")
        except Exception as e:
            print(f"  ASOS {month:02d}월 실패: {e}")
        time.sleep(0.3)

print(f"총 {len(LOCATIONS)}개 지점 다운로드 시작")
for name, lat, lon, stn_id in LOCATIONS:
    print(f"\n{'='*50}")
    print(f" {name}  (lat={lat}, lon={lon}, stn={stn_id})")
    print(f"{'='*50}")
    download_solar_power_year(name, lat, lon, stn_id)
    download_asos_year(name, stn_id)

print("\n모든 지점 다운로드 완료")
