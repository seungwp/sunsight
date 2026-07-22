import fs from 'fs'
import { createRequire } from 'module'
const require = createRequire(import.meta.url)
const iconv = require('iconv-lite')

// Station ID → 시·도 mapping (97 ASOS stations)
const STATION_SIDO = {
  // 서울특별시
  108: '서울특별시',
  // 부산광역시
  159: '부산광역시', 296: '부산광역시',
  // 대구광역시
  143: '대구광역시',
  // 인천광역시
  112: '인천광역시', 102: '인천광역시', 201: '인천광역시',
  // 광주광역시
  156: '광주광역시',
  // 대전광역시
  133: '대전광역시',
  // 울산광역시
  152: '울산광역시',
  // 세종특별자치시
  239: '세종특별자치시',
  // 경기도
  98: '경기도', 99: '경기도', 119: '경기도', 202: '경기도', 203: '경기도',
  // 강원특별자치도
  90: '강원특별자치도', 93: '강원특별자치도', 95: '강원특별자치도',
  100: '강원특별자치도', 101: '강원특별자치도', 104: '강원특별자치도',
  105: '강원특별자치도', 106: '강원특별자치도', 114: '강원특별자치도',
  115: '강원특별자치도', 121: '강원특별자치도', 211: '강원특별자치도',
  212: '강원특별자치도', 216: '강원특별자치도', 217: '강원특별자치도',
  // 충청북도
  127: '충청북도', 131: '충청북도', 135: '충청북도', 181: '충청북도',
  221: '충청북도', 226: '충청북도',
  // 충청남도
  129: '충청남도', 177: '충청남도', 232: '충청남도',
  235: '충청남도', 236: '충청남도', 238: '충청남도',
  // 전북특별자치도
  140: '전북특별자치도', 146: '전북특별자치도', 172: '전북특별자치도',
  243: '전북특별자치도', 244: '전북특별자치도', 245: '전북특별자치도',
  247: '전북특별자치도', 248: '전북특별자치도', 251: '전북특별자치도',
  254: '전북특별자치도',
  // 전라남도
  165: '전라남도', 168: '전라남도', 169: '전라남도', 170: '전라남도',
  174: '전라남도', 252: '전라남도', 258: '전라남도', 259: '전라남도',
  260: '전라남도', 261: '전라남도', 262: '전라남도', 266: '전라남도',
  268: '전라남도',
  // 경상북도
  130: '경상북도', 136: '경상북도', 137: '경상북도', 138: '경상북도',
  271: '경상북도', 272: '경상북도', 273: '경상북도', 276: '경상북도',
  277: '경상북도', 278: '경상북도', 279: '경상북도', 281: '경상북도',
  283: '경상북도',
  // 경상남도
  155: '경상남도', 162: '경상남도', 192: '경상남도', 253: '경상남도',
  255: '경상남도', 257: '경상남도', 263: '경상남도', 264: '경상남도',
  284: '경상남도', 285: '경상남도', 288: '경상남도', 289: '경상남도',
  294: '경상남도', 295: '경상남도',
  // 제주특별자치도
  184: '제주특별자치도', 185: '제주특별자치도', 188: '제주특별자치도',
  189: '제주특별자치도',
}

function readCsv(path) {
  const buf = fs.readFileSync(path)
  return iconv.decode(buf, 'euc-kr').trim().split('\n')
}

// ── Step 1: Load ASOS data
// { stationId → { date → { sun, rad } } }
const stationDays = {}

const lines = readCsv('scripts/OBS_ASOS_DD_20260521105348.csv')
for (const line of lines.slice(1)) {
  const p = line.split(',')
  const id = parseInt(p[0]?.trim())
  const date = p[2]?.trim()          // YYYY-MM-DD
  const tmp = parseFloat(p[3])
  const sun = parseFloat(p[4])       // 합계 일조시간 (hr)
  const rad = parseFloat(p[5])       // 합계 일사량 (MJ/m²)

  if (!STATION_SIDO[id]) continue
  if (!date || date.length < 10) continue

  if (!stationDays[id]) stationDays[id] = {}
  stationDays[id][date] = {
    sun: isNaN(sun) ? null : sun,
    rad: isNaN(rad) ? null : rad,
    tmp: isNaN(tmp) ? null : tmp,
  }
}

// ── Step 2: Per-station irradiance/sunshine ratio for imputation
const stationRatio = {}
for (const [id, days] of Object.entries(stationDays)) {
  const ratios = []
  for (const { sun, rad } of Object.values(days)) {
    if (sun !== null && sun > 0 && rad !== null && rad > 0) {
      ratios.push(rad / sun)
    }
  }
  if (ratios.length > 0) {
    ratios.sort((a, b) => a - b)
    stationRatio[id] = ratios[Math.floor(ratios.length / 2)]  // median
  }
}

// ── Step 3: Fill missing irradiance using ratio × sunshine
for (const [id, days] of Object.entries(stationDays)) {
  const ratio = stationRatio[id]
  for (const day of Object.values(days)) {
    if (day.rad === null && day.sun !== null && ratio) {
      day.rad = day.sun * ratio
    }
  }
}

// ── Step 4: Aggregate daily irradiance by 시·도 × month
// sidoMonthly[sido][month] = [irradiance values]
const sidoMonthly = {}

for (const [id, days] of Object.entries(stationDays)) {
  const sido = STATION_SIDO[parseInt(id)]
  if (!sido) continue
  if (!sidoMonthly[sido]) sidoMonthly[sido] = {}

  for (const [date, { rad }] of Object.entries(days)) {
    if (rad === null || rad < 0) continue
    const month = parseInt(date.slice(5, 7))
    if (!sidoMonthly[sido][month]) sidoMonthly[sido][month] = []
    sidoMonthly[sido][month].push(rad)
  }
}

// ── Step 5: Compute monthly and annual averages per 시·도
const result = {}
const allAnnual = []

for (const [sido, months] of Object.entries(sidoMonthly)) {
  const monthly = {}
  let totalSum = 0, totalCnt = 0

  for (let m = 1; m <= 12; m++) {
    const vals = months[m] || []
    if (vals.length === 0) {
      monthly[m] = null
      continue
    }
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length
    monthly[m] = +avg.toFixed(2)
    totalSum += avg
    totalCnt++
  }

  const annual = totalCnt > 0 ? +(totalSum / totalCnt).toFixed(2) : 0
  result[sido] = { monthly, annual }
  allAnnual.push(annual)
}

// ── Step 6: Normalize to 0–1 score
const minA = Math.min(...allAnnual)
const maxA = Math.max(...allAnnual)

for (const sido of Object.keys(result)) {
  const a = result[sido].annual
  result[sido].score = maxA > minA ? +((a - minA) / (maxA - minA)).toFixed(3) : 0.5
}

// ── Output
fs.writeFileSync('src/data/solarEfficiency.json', JSON.stringify(result, null, 2))
console.log('완료: src/data/solarEfficiency.json\n')
console.log('── 지역별 연평균 일사량 (MJ/m²/일) ──')
const sorted = Object.entries(result).sort((a, b) => b[1].annual - a[1].annual)
for (const [sido, d] of sorted) {
  console.log(`${sido.padEnd(12)} ${d.annual.toFixed(2)} MJ/m²/일  score: ${d.score.toFixed(3)}`)
}
