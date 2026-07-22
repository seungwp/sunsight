import fs from 'fs'
import { createRequire } from 'module'
const require = createRequire(import.meta.url)
const iconv = require('iconv-lite')

const REGION_MAP = {
  '강원도': '강원특별자치도', '강원특별자치도': '강원특별자치도',
  '경기도': '경기도',
  '경상남도': '경상남도',
  '경상북도': '경상북도',
  '광주시': '광주광역시', '광주광역시': '광주광역시',
  '대구시': '대구광역시', '대구광역시': '대구광역시',
  '대전시': '대전광역시', '대전광역시': '대전광역시',
  '부산시': '부산광역시', '부산광역시': '부산광역시',
  '서울시': '서울특별시', '서울특별시': '서울특별시',
  '세종시': '세종특별자치시', '세종특별자치시': '세종특별자치시',
  '울산시': '울산광역시', '울산광역시': '울산광역시',
  '인천시': '인천광역시', '인천광역시': '인천광역시',
  '전라남도': '전라남도',
  '전라북도': '전북특별자치도', '전북특별자치도': '전북특별자치도',
  '제주도': '제주특별자치도', '제주특별자치도': '제주특별자치도', '제주': '제주특별자치도',
  '충청남도': '충청남도',
  '충청북도': '충청북도',
}

// sido → year → month → MWh
const acc = {}

function addMWh(region, dateStr, mwh) {
  if (!region || isNaN(mwh) || mwh < 0) return
  const sido = REGION_MAP[region.trim()]
  if (!sido) return
  const year = parseInt(dateStr.slice(0, 4))
  const month = parseInt(dateStr.slice(5, 7))
  if (!acc[sido]) acc[sido] = {}
  if (!acc[sido][year]) acc[sido][year] = {}
  if (!acc[sido][year][month]) acc[sido][year][month] = 0
  acc[sido][year][month] += mwh
}

function readCsv(path) {
  const buf = fs.readFileSync(path)
  return iconv.decode(buf, 'euc-kr').trim().split('\n')
}

// ── 포맷 A: 거래일자,거래시간,지역,태양광발전량(MWh),풍력발전량(MWh)
function parseFormatA(lines) {
  for (const line of lines.slice(1)) {
    const parts = line.split(',')
    const date = parts[0]?.trim()
    const region = parts[2]?.trim()
    const mwh = parseFloat(parts[3])
    addMWh(region, date, mwh)
  }
}

// ── 포맷 B: 거래일자,거래시간,지역명,태양광발전량(Mwh),풍력발전량(Mwh)
function parseFormatB(lines) {
  for (const line of lines.slice(1)) {
    const parts = line.split(',')
    const date = parts[0]?.trim()
    const region = parts[2]?.trim()
    const mwh = parseFloat(parts[3])
    addMWh(region, date, mwh)
  }
}

// ── 포맷 C: 거래일자,거래시간,지역,연료원,전력거래량(MWh)
function parseFormatC(lines) {
  for (const line of lines.slice(1)) {
    const parts = line.split(',')
    const date = parts[0]?.trim()
    const region = parts[2]?.trim()
    const fuel = parts[3]?.trim()
    const mwh = parseFloat(parts[4])
    if (fuel !== '태양광') continue
    addMWh(region, date, mwh)
  }
}

// 파일별 처리
const FILES = [
  { path: 'scripts/230403_지역별 시간별 태양광 발전량.csv', format: 'A' },
  { path: 'scripts/한국전력거래소_지역별 시간별 태양광 발전량_20230301_20230531.csv', format: 'A' },
  { path: 'scripts/지역별 시간별 태양광 및 풍력 발전량_20230601_20230831.csv', format: 'A' },
  { path: 'scripts/지역별 시간대별 태양광 및 풍력 발전량(2309_2311).csv', format: 'B' },
  { path: 'scripts/한국전력거래소_지역별 시간별 태양광 및 풍력 발전량_20231231.csv', format: 'C' },
  { path: 'scripts/한국전력거래소_지역별 시간대별 태양광 풍력 발전량_20241231.csv', format: 'C' },
  { path: 'scripts/한국전력거래소_지역별 시간별 태양광 및 풍력 발전량_20251231.csv', format: 'C' },
]

for (const { path, format } of FILES) {
  console.log(`처리 중: ${path.split('/').pop()}`)
  const lines = readCsv(path)
  if (format === 'A') parseFormatA(lines)
  else if (format === 'B') parseFormatB(lines)
  else parseFormatC(lines)
}

// 연도별 합계
const result = {}
for (const [sido, years] of Object.entries(acc)) {
  result[sido] = {}
  for (const [year, months] of Object.entries(years)) {
    const total = Object.values(months).reduce((a, b) => a + b, 0)
    result[sido][year] = Math.round(total)
  }
}

// 성장률 계산
const summary = {}
for (const [sido, years] of Object.entries(result)) {
  const yrs = Object.keys(years).map(Number).sort()
  const first = years[yrs[0]] ?? 0
  const last = years[yrs[yrs.length - 1]] ?? 0
  const n = yrs[yrs.length - 1] - yrs[0]
  const cagr = n > 0 ? Math.pow(last / Math.max(first, 1), 1 / n) - 1 : 0

  const y2024 = years[2024] ?? 0
  const y2025 = years[2025] ?? 0
  const yoy = y2024 > 0 ? (y2025 - y2024) / y2024 : 0

  summary[sido] = {
    years,
    cagr: +cagr.toFixed(4),
    yoy2425: +yoy.toFixed(4),
  }
}

fs.writeFileSync('src/data/solarTrend.json', JSON.stringify(summary, null, 2))
console.log('\n완료: src/data/solarTrend.json')
console.log('\n── 지역별 CAGR 및 최근 발전량 ──')
for (const [sido, d] of Object.entries(summary).sort((a, b) => b[1].yoy2425 - a[1].yoy2425)) {
  const y2025 = (d.years[2025] / 1e6).toFixed(2)
  console.log(`${sido}: CAGR ${(d.cagr*100).toFixed(1)}%  YoY(24→25) ${(d.yoy2425*100).toFixed(1)}%  2025발전량 ${y2025}억MWh`)
}
