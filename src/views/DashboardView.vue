<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSubstationStore } from '../stores/substationStore'
import type { GridZone } from '../types/grid'
import KpiCard from '../components/ui/KpiCard.vue'
import RiskBadge from '../components/ui/RiskBadge.vue'
import GridMap from '../components/map/GridMap.vue'
import rawEfficiency from '../data/solarEfficiency.json'

type EfficiencyData = { monthly: Record<string, number | null>; annual: number; score: number }
const solarEfficiency = rawEfficiency as Record<string, EfficiencyData>

function efficiencyScore(sido: string): number {
  return solarEfficiency[sido]?.score ?? 0
}

function priorityScore(trueSpareKW: number, sido: string): number {
  return (trueSpareKW / 1000) * efficiencyScore(sido)
}

const router = useRouter()
const substStore = useSubstationStore()

const totalTrueSpareMW = computed(() =>
  +(substStore.mappedSubstations.reduce((s, x) => s + x.trueSpareKW, 0) / 1000).toFixed(0),
)

const totalLinkedGW = computed(() =>
  +(substStore.mappedSubstations.reduce((s, x) => s + x.linkedKW, 0) / 1_000_000).toFixed(2),
)

const totalCapacityKW = computed(() =>
  substStore.mappedSubstations.reduce((s, x) => s + x.totalKW, 0),
)

const totalLinkedKW = computed(() =>
  substStore.mappedSubstations.reduce((s, x) => s + x.linkedKW, 0),
)

const nationalSaturation = computed(() =>
  totalCapacityKW.value > 0
    ? +((totalLinkedKW.value / totalCapacityKW.value) * 100).toFixed(1)
    : 0,
)

function calcRisk(saturation: number): 'safe' | 'caution' | 'danger' {
  if (saturation >= 85) return 'danger'
  if (saturation >= 70) return 'caution'
  return 'safe'
}

interface RegionGroup {
  key: string       // 시군구 또는 substNm (미분류)
  sido: string
  sigungu: string
  count: number
  maxSaturation: number
  totalTrueSpareMW: number
  worstSubstCd: string
}

function normalizeSigungu(sigungu: string): string {
  return sigungu.split(' ')[0]
}

// 미니맵용 시/군 집계 zones (gridCapacity = count * 1000 → 반경 크기 proxy)
const dashboardMapZones = computed<GridZone[]>(() => {
  const map = new Map<string, {
    lats: number[], lngs: number[]
    maxSat: number, totalSpare: number, count: number
    sido: string, sigungu: string
  }>()

  for (const s of substStore.mappedSubstations) {
    if (!s.sigungu || s.lat === null || s.lng === null) continue
    const sigungu = normalizeSigungu(s.sigungu)
    const sido = s.sido || ''
    const key = `${sido}_${sigungu}`
    if (!map.has(key)) {
      map.set(key, { lats: [], lngs: [], maxSat: 0, totalSpare: 0, count: 0, sido, sigungu })
    }
    const g = map.get(key)!
    g.lats.push(s.lat as number)
    g.lngs.push(s.lng as number)
    g.maxSat = Math.max(g.maxSat, s.saturation)
    g.totalSpare += s.trueSpareKW / 1000
    g.count++
  }

  return [...map.values()].map((g, i) => {
    const avgLat = g.lats.reduce((a, b) => a + b, 0) / g.lats.length
    const avgLng = g.lngs.reduce((a, b) => a + b, 0) / g.lngs.length
    return {
      id: `rg-${i}`,
      regionName: g.sigungu,
      province: g.sido,
      lat: avgLat,
      lng: avgLng,
      gridCapacity: g.count * 1000,  // 반경 크기 proxy
      currentLoad: g.count * 1000 * g.maxSat / 100,
      spareCapacity: Math.round(g.totalSpare),
      saturationRate: g.maxSat,
      riskLevel: calcRisk(g.maxSat),
      riskStars: 1 as const,
      maxNewInstall: Math.round(g.totalSpare * 1000),
      peakHour: 14,
      curtailmentMWh: 0,
      solarIrradiance: 1000,
      hcThermal: 0,
      hcVoltage: 0,
      hcProtection: 0,
    }
  })
})

const regionGroups = computed<RegionGroup[]>(() => {
  const map = new Map<string, RegionGroup>()

  for (const s of substStore.mappedSubstations) {
    const rawSigungu = s.sigungu || ''
    const sido = s.sido || ''
    const sigungu = rawSigungu ? normalizeSigungu(rawSigungu) : ''
    const key = sigungu ? `${sido}_${sigungu}` : `__${s.substCd}`

    if (!map.has(key)) {
      map.set(key, {
        key,
        sido,
        sigungu: sigungu || s.substNm + '변전소',
        count: 0,
        maxSaturation: 0,
        totalTrueSpareMW: 0,
        worstSubstCd: s.substCd,
      })
    }
    const g = map.get(key)!
    g.count++
    g.totalTrueSpareMW += s.trueSpareKW / 1000
    if (s.saturation > g.maxSaturation) {
      g.maxSaturation = s.saturation
      g.worstSubstCd = s.substCd
    }
  }

  return [...map.values()]
    .sort((a, b) => b.maxSaturation - a.maxSaturation)
    .slice(0, 8)
})

interface PriorityGroup {
  key: string
  sido: string
  sigungu: string
  count: number
  totalPriority: number
  totalTrueSpareMW: number
  topSubstCd: string
}

const priorityGroups = computed<PriorityGroup[]>(() => {
  const map = new Map<string, PriorityGroup & { maxPriority: number }>()

  for (const s of substStore.mappedSubstations) {
    const rawSigungu = s.sigungu || ''
    const sido = s.sido || ''
    const sigungu = rawSigungu ? normalizeSigungu(rawSigungu) : ''
    const key = sigungu ? `${sido}_${sigungu}` : `__${s.substCd}`
    const ps = priorityScore(s.trueSpareKW, sido)

    if (!map.has(key)) {
      map.set(key, { key, sido, sigungu: sigungu || s.substNm, count: 0, totalPriority: 0, totalTrueSpareMW: 0, topSubstCd: s.substCd, maxPriority: 0 })
    }
    const g = map.get(key)!
    g.count++
    g.totalPriority += ps
    g.totalTrueSpareMW += s.trueSpareKW / 1000
    if (ps > g.maxPriority) { g.maxPriority = ps; g.topSubstCd = s.substCd }
  }

  return [...map.values()]
    .sort((a, b) => {
      const aTop = efficiencyScore(a.sido) >= 0.7 ? 1 : 0
      const bTop = efficiencyScore(b.sido) >= 0.7 ? 1 : 0
      if (bTop !== aTop) return bTop - aTop
      return b.totalPriority - a.totalPriority
    })
    .slice(0, 8)
})

function goMap() {
  router.push('/grid-map')
}

function goMapAt(lat: number, lng: number) {
  router.push({ path: '/grid-map', query: { lat: lat.toFixed(4), lng: lng.toFixed(4), zoom: 11 } })
}

function goSimulation(substCd: string) {
  router.push({ path: '/simulation', query: { subst: substCd } })
}
</script>

<template>
  <div class="dashboard">
    <!-- KPI Row -->
    <div class="kpi-row">
      <KpiCard
        title="포화 위험 변전소 수"
        :value="substStore.stats.danger"
        unit="개소"
        icon="Warning"
        color="#f56c6c"
      />
      <KpiCard
        title="전국 보수적 설치가능 추정치"
        :value="totalTrueSpareMW.toLocaleString()"
        unit="MW"
        icon="Lightning"
        color="#409eff"
      />
      <KpiCard
        title="전국 가중 평균 포화도"
        :value="nationalSaturation"
        unit="%"
        icon="Odometer"
        :color="nationalSaturation >= 85 ? '#f56c6c' : nationalSaturation >= 70 ? '#e6a23c' : '#67c23a'"
      />
      <KpiCard
        title="전국 누적 연계용량"
        :value="totalLinkedGW"
        unit="GW"
        icon="Sunny"
        color="#67c23a"
      />
    </div>

    <!-- Main Content -->
    <div class="main-row">
      <!-- Mini Map -->
      <div class="mini-map-card" @click="goMap" title="지도 페이지로 이동">
        <div class="card-header">
          <span class="card-title">계통 포화도 지도</span>
          <span class="view-all-link" @click.stop="goMap">전체 보기 <el-icon><ArrowRight /></el-icon></span>
        </div>
        <div class="mini-map-body" @click.stop>
          <GridMap
            :zones="dashboardMapZones"
            layer-mode="saturation"
            :selected-zone-id="null"
            :mini="true"
            :substations="[]"
            :show-substations="false"
            @mini-click="goMapAt"
          />
        </div>
      </div>

      <!-- Right column: saturation + priority lists -->
      <div class="right-col">
        <!-- Top Priority Regions -->
        <div class="list-card">
          <div class="card-header">
            <span class="card-title">태양광 투자 추천 지역</span>
            <el-tooltip content="계통여유(MW) × LightGBM 태양광잠재력 점수" placement="top">
              <el-icon style="color:#9ca3af;cursor:default"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          <div class="danger-list">
            <div
              v-for="(g, i) in priorityGroups"
              :key="g.key"
              class="danger-item"
            >
              <span class="rank priority-rank">{{ i + 1 }}</span>
              <div class="zone-info">
                <div class="zone-name">{{ g.sigungu }}</div>
                <div class="zone-sub">{{ g.sido }} · 여유 {{ g.totalTrueSpareMW.toFixed(0) }}MW</div>
              </div>
              <div class="zone-stats">
                <span class="priority-score">{{ g.totalPriority.toFixed(1) }}</span>
              </div>
              <el-icon class="arrow-btn" @click="goSimulation(g.topSubstCd)" title="시뮬레이션"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>

        <!-- Top Danger Regions -->
        <div class="list-card">
          <div class="card-header">
            <span class="card-title">포화도 상위 지역</span>
          </div>
          <div class="danger-list">
            <div
              v-for="(g, i) in regionGroups"
              :key="g.key"
              class="danger-item"
            >
              <span class="rank">{{ i + 1 }}</span>
              <div class="zone-info">
                <div class="zone-name">{{ g.sigungu }}</div>
                <div class="zone-sub">{{ g.sido }}</div>
              </div>
              <div class="zone-stats">
                <RiskBadge :level="calcRisk(g.maxSaturation)" />
                <span class="saturation-pct">{{ g.maxSaturation }}%</span>
              </div>
              <el-icon class="arrow-btn" @click="goSimulation(g.worstSubstCd)" title="시뮬레이션"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  background: #F9F9F9;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  flex-shrink: 0;
}

.main-row {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.right-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.mini-map-card,
.list-card,
.history-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 0 10.16px 0 rgba(34, 34, 34, 0.07);
  display: flex;
  flex-direction: column;
}

.list-card {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.mini-map-card {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.mini-map-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-shrink: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.view-all-link {
  font-size: 13px;
  color: #555555;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  line-height: 1;
  vertical-align: middle;
}

.view-all-link .el-icon {
  font-size: 13px;
  vertical-align: middle;
}

.mini-map-body {
  flex: 1;
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
}

.danger-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  overflow-y: auto;
}

.danger-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #FAFAFA;
  border-radius: 8px;
}

.rank {
  width: 22px;
  color: #1a1a2e;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
  line-height: 1;
  margin-top: -3px;
}

.zone-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.zone-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  line-height: 1;
  white-space: nowrap;
}

.zone-sub {
  font-size: 11px;
  color: #6b7280;
  white-space: nowrap;
}

.zone-stats {
  display: flex;
  align-items: center;
  gap: 8px;
}

.saturation-pct {
  font-size: 14px;
  font-weight: 700;
  color: #374151;
  min-width: 40px;
  text-align: right;
}

.history-card {
  flex-shrink: 0;
}

.priority-rank {
}

.priority-score {
  font-size: 14px;
  font-weight: 700;
  color: #409eff;
  min-width: 48px;
  text-align: right;
}

.arrow-btn {
  font-size: 16px;
  color: #9ca3af;
  cursor: pointer;
  flex-shrink: 0;
  align-self: center;
}

.arrow-btn:hover {
  color: #1a1a2e;
}
</style>
