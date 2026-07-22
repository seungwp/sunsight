import os
import requests
import csv

with open(os.path.join(os.path.dirname(__file__), '..', '.env'), encoding='utf-8') as _f:
    for _line in _f:
        if _line.strip().startswith('KIER_SERVICE_KEY='):
            KEY = _line.strip().split('=', 1)[1].split(' #')[0].strip()
URL_PV = 'https://apis.data.go.kr/B551184/SolarPvService/getSolarPvHrInfo'
URL_GHI = 'https://apis.data.go.kr/B551184/SolarGhiService/getSolarGhiHrInfo'

# Ird_LatLon.csv에서 전국 대표 좌표 샘플링 (100개마다 1개)
coords = []
with open('src/data/KIER_NationalCoreData_DataAPI/Ird_LatLon.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i % 5000 == 0:
            coords.append((float(row['Lat']), float(row['Lon'])))

print(f'테스트 좌표 {len(coords)}개:')
hit = 0
for lat, lon in coords:
    params = {'serviceKey': KEY, 'date': '20210615', 'lat': lat, 'lon': lon,
              'pageNo': 1, 'numOfRows': 3, 'type': 'json'}
    resp = requests.get(URL_PV, params=params, timeout=10)
    total = resp.json().get('response', {}).get('body', {}).get('totalCount', 0)
    status = 'OK' if int(total) > 0 else '-'
    if int(total) > 0:
        hit += 1
    print(f'  lat={lat:.3f}, lon={lon:.3f} -> {status} (count={total})')

print(f'\n결과: {hit}/{len(coords)} 좌표에서 데이터 있음')
