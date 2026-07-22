import pandas as pd
import numpy as np
import json

ird = pd.read_csv('Ird_LatLon.csv')

stations = {
    '인천':  (112, 37.4776, 126.6249),
    '경기':  (119, 37.2626, 126.9874),
    '충남':  (129, 36.3281, 126.5578),
    '충북':  (131, 36.6399, 127.4412),
    '경북':  (136, 36.5729, 128.7074),
    '대구':  (143, 35.8894, 128.6181),
    '전북':  (146, 35.8207, 127.1543),
    '울산':  (152, 35.5601, 129.3218),
    '경남':  (155, 35.1717, 128.5689),
    '전남':  (165, 34.8172, 126.4053),
    '세종':  (239, 36.4802, 127.2892),
}

result = {}
for name, (stn_id, lat, lon) in stations.items():
    dist = np.sqrt((ird['Lat']-lat)**2 + (ird['Lon']-lon)**2)
    idx = dist.idxmin()
    best_lat = float(ird.iloc[idx]['Lat'])
    best_lon = float(ird.iloc[idx]['Lon'])
    result[name] = (stn_id, best_lat, best_lon)
    print(name, stn_id, best_lat, best_lon, round(dist[idx], 4))

with open('remaining_coords.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('saved')
