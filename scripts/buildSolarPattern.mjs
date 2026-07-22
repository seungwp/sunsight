import fs from 'fs'
import { createRequire } from 'module'
const require = createRequire(import.meta.url)
const iconv = require('iconv-lite')

// EPSIS 지역명 → 변전소 sido명 매핑
const REGION_MAP = {
  '강원도': '강원특별자치도',
  '경기도': '경기도',
  '경상남도': '경상남도',
  '경상북도': '경상북도',
  '광주시': '광주광역시',
  '대구시': '대구광역시',
  '대전시': '대전광역시',
  '부산시': '부산광역시',
  '서울시': '서울특별시',
  '세종시': '세종특별자치시',
  '울산시': '울산광역시',
  '인천시': '인천광역시',
  '전라남도': '전라남도',
  '전라북도': '전북특별자치도',
  '제주도': '제주특별자치도',
  '충청남도': '충청남도',
  '충청북도': '충청북도',
}

const CSV_PATH = 'scripts/한국전력거래소_지역별 시간별 태양광 및 풍력 발전량_20251231.csv'

const buf = fs.readFileSync(CSV_PATH)
const text = iconv.decode(buf, 'euc-kr')
const lines = text.trim().split('\n').slice(1) // 헤더 제거

// sido → month(1~12) → hour(0~23) → [sum, count]
const acc = {}

for (const line of lines) {
  const parts = line.split(',')
  const dateStr = parts[0]        // 2025-01-01
  const hourStr = parts[1]        // 01~24
  const region = parts[2]         // 강원도 등
  const fuel = parts[3]           // 태양광 / 풍력
  const mwh = parseFloat(parts[4])

  if (fuel !== '태양광') continue
  if (!REGION_MAP[region]) continue
  if (isNaN(mwh)) continue

  const sido = REGION_MAP[region]
  const month = parseInt(dateStr.slice(5, 7))  // 1~12
  const hour = parseInt(hourStr) - 1           // 0~23 (거래시간 1 = 0시~1시)

  if (!acc[sido]) acc[sido] = {}
  if (!acc[sido][month]) {
    acc[sido][month] = Array.from({ length: 24 }, () => ({ sum: 0, count: 0 }))
  }
  acc[sido][month][hour].sum += mwh
  acc[sido][month][hour].count += 1
}

// 평균으로 변환
const result = {}
for (const [sido, months] of Object.entries(acc)) {
  result[sido] = {}
  for (const [month, hours] of Object.entries(months)) {
    result[sido][month] = hours.map(({ sum, count }) =>
      count > 0 ? Math.round((sum / count) * 1000) / 1000 : 0
    )
  }
}

// 연간 평균도 추가 (월 구분 없이)
for (const [sido, months] of Object.entries(acc)) {
  const annual = Array.from({ length: 24 }, () => ({ sum: 0, count: 0 }))
  for (const hours of Object.values(months)) {
    for (let h = 0; h < 24; h++) {
      annual[h].sum += hours[h].sum
      annual[h].count += hours[h].count
    }
  }
  result[sido]['annual'] = annual.map(({ sum, count }) =>
    count > 0 ? Math.round((sum / count) * 1000) / 1000 : 0
  )
}

const outPath = 'src/data/solarPattern.json'
fs.writeFileSync(outPath, JSON.stringify(result, null, 2))

console.log(`완료: ${outPath}`)
console.log(`지역 수: ${Object.keys(result).length}`)
for (const sido of Object.keys(result).sort()) {
  const annual = result[sido]['annual']
  const peak = Math.max(...annual)
  const peakHour = annual.indexOf(peak)
  console.log(`  ${sido}: 연평균 피크 ${peakHour}시 (${peak.toFixed(1)} MWh)`)
}
