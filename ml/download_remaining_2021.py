"""
나머지 11개 지점 KIER solar_power + ASOS 2021 다운로드
대상: 인천, 경기, 충남, 충북, 경북, 대구, 전북, 울산, 경남, 전남, 세종
"""
import os, calendar, time
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
    ("인천", 37.4781258072,  126.6230739194,  112),
    ("경기", 37.2627846845,  126.9849142132,  119),
    ("충남", 36.3298401473,  126.5551088094,  129),
    ("충북", 36.6389699591,  127.438825219,   131),
    ("경북", 36.5710016475,  128.7064005095,  136),
    ("대구", 35.8914331137,  128.6159421777,  143),
    ("전북", 35.8227890941,  127.1552875228,  146),
    ("울산", 35.5616338018,  129.32345437820, 152),
    ("경남", 35.1705010153,  128.5704840212,  155),
    ("전남", 34.8179377047,  126.4033392585,  165),
    ("세종", 36.4797056582,  127.2868886898,  239),
]


def download_solar(name, lat, lon, stn_id, year=2021):
    print(f"\n[{name}] KIER solar_power {year}...")
    for month in range(1, 13):
        out = f"{DATA_DIR}/solar_power_{stn_id}_{year}_{month:02d}.csv"
        if os.path.exists(out):
            print(f"  {month:02d}월 이미 존재")
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
                    item['year'] = year
                    item['month'] = month
                    item['day'] = day
                rows.extend(items)
            except Exception:
                pass
        if rows:
            pd.DataFrame(rows).to_csv(out, index=False, encoding='utf-8-sig')
            print(f"  {month:02d}월 {len(rows)}행")
        else:
            print(f"  {month:02d}월 데이터 없음")


def download_asos(name, stn_id, year=2021):
    print(f"\n[{name}] ASOS {year}...")
    for month in range(1, 13):
        out = f"{DATA_DIR}/ASOS_{stn_id}_{year}_{month:02d}.csv"
        if os.path.exists(out):
            print(f"  ASOS {month:02d}월 이미 존재")
            continue
        nm = month + 1 if month < 12 else 1
        ny = year if month < 12 else year + 1
        params = {
            'serviceKey': KMA_KEY, 'pageNo': '1', 'numOfRows': '999',
            'dataType': 'json', 'dataCd': 'ASOS', 'dateCd': 'HR',
            'startDt': f'{year}{month:02d}01', 'startHh': '00',
            'endDt': f'{ny}{nm:02d}01',        'endHh': '23',
            'stnIds': str(stn_id)
        }
        try:
            r = requests.get(ASOS_URL, params=params, timeout=30)
            items = r.json()['response']['body']['items']['item']
            if not isinstance(items, list):
                items = [items]
            pd.DataFrame(items).to_csv(out, index=False, encoding='utf-8-sig')
            print(f"  ASOS {month:02d}월 {len(items)}행")
        except Exception as e:
            print(f"  ASOS {month:02d}월 실패: {e}")
        time.sleep(0.3)


print(f"총 {len(LOCATIONS)}개 지점 다운로드 시작")
for name, lat, lon, stn_id in LOCATIONS:
    print(f"\n{'='*50}")
    print(f" {name}  (stn={stn_id}  lat={lat:.4f}  lon={lon:.4f})")
    print(f"{'='*50}")
    download_solar(name, lat, lon, stn_id)
    download_asos(name, stn_id)

print("\n모든 지점 다운로드 완료")
