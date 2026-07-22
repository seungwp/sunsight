<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSubstationStore } from '../stores/substationStore'
import RiskBadge from '../components/ui/RiskBadge.vue'
import rawEfficiency from '../data/solarEfficiency.json'

type EfficiencyData = { monthly: Record<string, number | null>; annual: number; score: number }
const solarEfficiency = rawEfficiency as Record<string, EfficiencyData>

function efficiencyScore(sido: string | undefined): number {
  if (!sido) return 0
  return solarEfficiency[sido]?.score ?? 0
}


function priorityScore(trueSpareKW: number, sido: string | undefined): number {
  const mw = trueSpareKW / 1000
  return +(mw * efficiencyScore(sido)).toFixed(1)
}

const router = useRouter()
const substStore = useSubstationStore()

const searchName = ref('')
const filterSigungu = ref('')
const filterRiskLevels = ref<string[]>(['safe', 'caution', 'danger'])
const spareRange = ref<[number, number]>([0, 500])

function calcRisk(saturation: number): 'safe' | 'caution' | 'danger' {
  if (saturation >= 85) return 'danger'
  if (saturation >= 70) return 'caution'
  return 'safe'
}

function normalizeSigungu(sigungu: string): string {
  return sigungu.split(' ')[0]
}

const sigunguOptions = computed(() =>
  [...new Set(
    substStore.mappedSubstations
      .filter((s) => s.sigungu)
      .map((s) => normalizeSigungu(s.sigungu!))
  )].sort()
)

const filteredSubstations = computed(() =>
  substStore.mappedSubstations.filter((s) => {
    const risk = calcRisk(s.saturation)
    const spareMW = s.trueSpareKW / 1000
    const nameMatch = !searchName.value || s.substNm.includes(searchName.value)
    const sigunguMatch = !filterSigungu.value ||
      (s.sigungu && normalizeSigungu(s.sigungu) === filterSigungu.value)
    return (
      nameMatch &&
      sigunguMatch &&
      filterRiskLevels.value.includes(risk) &&
      spareMW >= spareRange.value[0] &&
      spareMW <= spareRange.value[1]
    )
  }),
)

function resetAll() {
  searchName.value = ''
  filterSigungu.value = ''
  filterRiskLevels.value = ['safe', 'caution', 'danger']
  spareRange.value = [0, 500]
}

const riskOptions = [
  { label: '안전', value: 'safe' },
  { label: '주의', value: 'caution' },
  { label: '위험', value: 'danger' },
]

function exportCsv() {
  const header = '변전소명,누적연계용량(MW),변전소여유(MW),변압기여유(MW),배전선로여유(MW),보수적추정치(MW),포화도(%),위험등급,태양광잠재력점수,우선순위점수'
  const rows = filteredSubstations.value.map((s) =>
    [
      s.substNm + '변전소',
      (s.linkedKW / 1000).toFixed(1),
      (s.spareKW / 1000).toFixed(1),
      (s.vol2Sum / 1000).toFixed(1),
      (s.vol3Sum / 1000).toFixed(1),
      (s.trueSpareKW / 1000).toFixed(1),
      s.saturation,
      calcRisk(s.saturation),
      efficiencyScore(s.sido).toFixed(3),
      priorityScore(s.trueSpareKW, s.sido),
    ].join(','),
  )
  const blob = new Blob(['﻿' + [header, ...rows].join('\n')], {
    type: 'text/csv;charset=utf-8;',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '태양광_설비가능변전소.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function goSimulation(substCd: string) {
  router.push({ path: '/simulation', query: { subst: substCd } })
}

const sortColumn = ref('priorityScore')
const sortOrder = ref<'ascending' | 'descending'>('descending')

function handleSort({ prop, order }: { prop: string; order: 'ascending' | 'descending' }) {
  sortColumn.value = prop
  sortOrder.value = order
}

const sortedSubstations = computed(() => {
  const list = [...filteredSubstations.value]
  list.sort((a, b) => {
    let av: number, bv: number
    if (sortColumn.value === 'priorityScore') {
      av = priorityScore(a.trueSpareKW, a.sido)
      bv = priorityScore(b.trueSpareKW, b.sido)
    } else if (sortColumn.value === 'efficiencyScore') {
      av = efficiencyScore(a.sido)
      bv = efficiencyScore(b.sido)
    } else {
      av = (a as Record<string, unknown>)[sortColumn.value] as number
      bv = (b as Record<string, unknown>)[sortColumn.value] as number
    }
    return sortOrder.value === 'ascending' ? av - bv : bv - av
  })
  return list
})
</script>

<template>
  <div class="feasibility-page">
    <!-- Filter Panel -->
    <div class="filter-panel">
      <div class="filter-title">
        <el-icon><Filter /></el-icon>
        필터
      </div>

      <div class="filter-section">
        <div class="filter-label">변전소 검색</div>
        <el-input v-model="searchName" placeholder="변전소명 입력" size="small" clearable />
      </div>

      <div class="filter-section">
        <div class="filter-label">시/군/구</div>
        <el-select
          v-model="filterSigungu"
          placeholder="전체 지역"
          clearable
          filterable
          size="small"
          style="width: 100%"
        >
          <el-option v-for="s in sigunguOptions" :key="s" :label="s" :value="s" />
        </el-select>
      </div>

      <div class="filter-section">
        <div class="filter-label">위험 등급</div>
        <el-checkbox-group v-model="filterRiskLevels">
          <el-checkbox v-for="opt in riskOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </el-checkbox>
        </el-checkbox-group>
      </div>

      <div class="filter-section">
        <div class="filter-label">보수적 추정치 범위 (MW)</div>
        <el-slider
          v-model="spareRange"
          range
          :min="0"
          :max="500"
          :step="5"
          size="small"
        />
        <div class="range-labels">
          <span>{{ spareRange[0] }} MW</span>
          <span>{{ spareRange[1] }} MW</span>
        </div>
      </div>

      <el-button size="small" style="width: 100%" @click="resetAll">필터 초기화</el-button>

      <div class="filter-count">
        <el-tag type="info" size="small">{{ filteredSubstations.length }}개 변전소 검색됨</el-tag>
      </div>
    </div>

    <!-- Table Area -->
    <div class="table-area">
      <div class="table-header">
        <span class="table-title">태양광 설비 가능 변전소 목록</span>
        <el-button size="small" type="success" @click="exportCsv">
          <el-icon><Download /></el-icon>
          CSV 내보내기
        </el-button>
      </div>

      <el-table
        :data="sortedSubstations"
        style="width: 100%; flex: 1"
        height="100%"
        stripe
        @sort-change="handleSort"
      >
        <el-table-column prop="substNm" label="변전소명" width="130" fixed>
          <template #default="{ row }">{{ row.substNm }}변전소</template>
        </el-table-column>

        <el-table-column prop="linkedKW" label="누적 연계용량 (MW)" width="160" sortable="custom" align="right">
          <template #default="{ row }">{{ (row.linkedKW / 1000).toFixed(1) }}</template>
        </el-table-column>

        <el-table-column prop="spareKW" label="변전소 여유 (MW)" width="150" sortable="custom" align="right">
          <template #default="{ row }">{{ (row.spareKW / 1000).toFixed(1) }}</template>
        </el-table-column>

        <el-table-column prop="vol2Sum" label="변압기 여유 (MW)" width="150" sortable="custom" align="right">
          <template #default="{ row }">{{ (row.vol2Sum / 1000).toFixed(1) }}</template>
        </el-table-column>

        <el-table-column prop="vol3Sum" label="배전선로 여유 (MW)" width="160" sortable="custom" align="right">
          <template #default="{ row }">{{ (row.vol3Sum / 1000).toFixed(1) }}</template>
        </el-table-column>

        <el-table-column prop="trueSpareKW" label="보수적 추정치 (MW)" width="160" sortable="custom" align="right">
          <template #default="{ row }">
            <span :style="{ color: '#f56c6c', fontWeight: 700 }">
              {{ (row.trueSpareKW / 1000).toFixed(1) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="efficiencyScore" label="태양광 잠재력 점수" width="150" sortable="custom" align="right">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="efficiencyScore(row.sido) >= 0.7 ? 'success' : efficiencyScore(row.sido) >= 0.4 ? 'warning' : 'danger'"
            >
              {{ (efficiencyScore(row.sido) * 100).toFixed(0) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="priorityScore" label="우선순위 점수" width="140" sortable="custom" align="right">
          <template #default="{ row }">
            <span :style="{ fontWeight: 700, color: '#1a1a2e' }">
              {{ priorityScore(row.trueSpareKW, row.sido).toFixed(1) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="saturation" label="포화도 (%)" width="140" sortable="custom" align="right">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(row.saturation, 100)"
              :color="row.saturation >= 85 ? '#FF494C' : row.saturation >= 70 ? '#fdae61' : '#9ED8F3'"
              :stroke-width="8"
              :show-text="false"
            />
            <span :style="{ fontSize: '12px', color: row.saturation >= 85 ? '#FF494C' : row.saturation >= 70 ? '#fdae61' : '#9ED8F3', fontWeight: 600 }">{{ row.saturation }}%</span>
          </template>
        </el-table-column>

        <el-table-column label="위험 등급" width="100" align="center">
          <template #default="{ row }">
            <RiskBadge :level="calcRisk(row.saturation)" />
          </template>
        </el-table-column>

        <el-table-column label="" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="goSimulation(row.substCd)">
              시뮬레이션
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.feasibility-page {
  display: flex;
  gap: 20px;
  height: 100%;
  overflow: hidden;
}

.filter-panel {
  width: 220px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.filter-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 6px;
}

.filter-section {
  display: flex;
  flex-direction: column;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

.filter-count {
  margin-top: auto;
}

.table-area {
  flex: 1;
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}
</style>
