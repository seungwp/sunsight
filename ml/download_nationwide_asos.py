"""
전국 17개 시도 대표 KMA ASOS 지점 2025년 데이터 다운로드
"""
import sys
sys.path.insert(0, '.')
from download_asos_data_KMA import download_asos_data_by_station

# 시도별 대표 KMA ASOS 지점 (지점번호)
SIDO_STATIONS = {
    "서울특별시":      108,   # 서울
    "경기도":          119,   # 수원
    "인천광역시":      112,   # 인천
    "강원특별자치도":  105,   # 강릉
    "충청북도":        131,   # 청주
    "충청남도":        129,   # 서산
    "세종특별자치시":  239,   # 세종
    "대전광역시":      133,   # 대전
    "전북특별자치도":  146,   # 전주
    "전라남도":        165,   # 목포
    "광주광역시":      156,   # 광주
    "경상북도":        136,   # 안동
    "대구광역시":      143,   # 대구
    "경상남도":        155,   # 창원
    "울산광역시":      152,   # 울산
    "부산광역시":      159,   # 부산
    "제주특별자치도":  184,   # 제주
}

print(f"총 {len(SIDO_STATIONS)}개 지점 2025년 데이터 다운로드 시작")
for sido, stn_id in SIDO_STATIONS.items():
    print(f"\n[{sido}] 지점번호: {stn_id}")
    download_asos_data_by_station(stn_id=stn_id, years=[2025])
print("\n전국 ASOS 다운로드 완료")
