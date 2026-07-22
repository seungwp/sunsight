<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GaugeChart, LineChart, BarChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { useSubstationStore } from '../stores/substationStore'
import type { SubstationData } from '../stores/substationStore'
import RiskBadge from '../components/ui/RiskBadge.vue'
import rawSolarPattern from '../data/solarPattern.json'
import rawEfficiency from '../data/solarEfficiency.json'
import rawTrend from '../data/solarTrend.json'

use([CanvasRenderer, GaugeChart, LineChart, BarChart, TooltipComponent, GridComponent, LegendComponent])

const solarPattern = rawSolarPattern as Record<string, Record<string, number[]>>
type EfficiencyData = { monthly: Record<string, number | null>; annual: number; score: number; icsr_2025_mean?: number; pvamt_2025?: number }
const solarEfficiency = rawEfficiency as Record<string, EfficiencyData>
type TrendData = { years: Record<string, number>; cagr: number; yoy2425: number }
const solarTrend = rawTrend as Record<string, TrendData>


const route = useRoute()
const substStore = useSubstationStore()

const selectedSubstCd = ref<string>('')
const unitCapacity = ref<number>(100)
type InstallType = 'ground' | 'building'
const installType = ref<InstallType>('ground')

onMounted(() => {
  if (route.query.subst) {
    selectedSubstCd.value = route.query.subst as string
  } else if (substStore.mappedSubstations.length > 0) {
    selectedSubstCd.value = substStore.mappedSubstations[0].substCd
  }
})

const selectedSubst = computed<SubstationData | null>(() =>
  substStore.mappedSubstations.find((s) => s.substCd === selectedSubstCd.value) ?? null,
)

function calcRisk(rate: number): 'safe' | 'caution' | 'danger' {
  if (rate >= 85) return 'danger'
  if (rate >= 70) return 'caution'
  return 'safe'
}

const installableCount = computed(() => {
  if (!selectedSubst.value || unitCapacity.value <= 0) return 0
  return Math.floor(selectedSubst.value.trueSpareKW / unitCapacity.value)
})

const afterSaturation = computed(() => {
  if (!selectedSubst.value) return 0
  const s = selectedSubst.value
  const newLinked = s.linkedKW + s.trueSpareKW
  const total = s.totalKW
  if (total <= 0) return 100
  return +((newLinked / total) * 100).toFixed(1)
})

const substOptions = computed(() =>
  substStore.mappedSubstations.map((s) => ({
    label: `${s.substNm}변전소`,
    value: s.substCd,
  })),
)

const unitPresets = [
  { label: '3kW', value: 3, desc: '가정용 주택' },
  { label: '100kW', value: 100, desc: '소형 상업용 (공장·창고 지붕)' },
  { label: '1MW', value: 1000, desc: '영농형·대형 상업용' },
  { label: '10MW', value: 10000, desc: '태양광 발전단지' },
]

const selectedPreset = computed(() =>
  unitPresets.find((p) => p.value === unitCapacity.value) ?? null,
)

function gaugeOption(value: number, title: string) {
  const color = value >= 85 ? '#f56c6c' : value >= 70 ? '#e6a23c' : '#67c23a'
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        splitNumber: 5,
        radius: '85%',
        axisLine: {
          lineStyle: {
            width: 5,
            color: [
              [0.7, '#67c23a'],
              [0.85, '#e6a23c'],
              [1, '#f56c6c'],
            ],
          },
        },
        pointer: { itemStyle: { color } },
        axisTick: { distance: -18, length: 6, lineStyle: { color: '#fff', width: 1 } },
        splitLine: { distance: -24, length: 14, lineStyle: { color: '#fff', width: 2 } },
        axisLabel: { color: '#999', fontSize: 10, distance: -40 },
        detail: {
          valueAnimation: true,
          formatter: '{value}%',
          color,
          fontSize: 22,
          fontWeight: 'bold',
          offsetCenter: [0, '60%'],
        },
        title: { show: false },
        data: [{ value, name: '' }],
      },
    ],
  }
}

const beforeGauge = computed(() => gaugeOption(selectedSubst.value?.saturation ?? 0, '현재'))
const afterGauge = computed(() => gaugeOption(afterSaturation.value, '설치 후'))

const isFullySaturated = computed(() => (selectedSubst.value?.saturation ?? 0) >= 100)

// 지역 발전량 예측 점수
const regionEfficiency = computed<EfficiencyData | null>(() => {
  const sido = selectedSubst.value?.sido
  if (!sido) return null
  return solarEfficiency[sido] ?? null
})

const displayScore = computed(() => isFullySaturated.value ? 0 : (regionEfficiency.value?.score ?? 0))

const priorityScore = computed(() => {
  if (!selectedSubst.value || !regionEfficiency.value) return null
  const mw = selectedSubst.value.trueSpareKW / 1000
  return +(mw * regionEfficiency.value.score).toFixed(1)
})

const regionGrowth = computed(() => {
  const sido = selectedSubst.value?.sido
  if (!sido) return null
  return solarTrend[sido] ?? null
})

const irradianceBarOption = computed(() => {
  const eff = regionEfficiency.value
  if (!eff) return {}
  const months = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']
  const values = months.map((_, i) => eff.monthly[String(i + 1)] ?? 0)
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${p[0].value} MJ/m²` },
    grid: { left: 40, right: 10, top: 16, bottom: 30 },
    xAxis: { type: 'category', data: months, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: 'MJ/m²', nameTextStyle: { fontSize: 10 } },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: { color: '#FFB68D', borderRadius: [3, 3, 0, 0] },
    }],
  }
})

// 월별 발전량 합계 (solarPattern 24시간 합산)
const MONTH_LABELS = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']

const monthlyGeneration = computed(() => {
  const sido = selectedSubst.value?.sido
  if (!sido) return null
  const pattern = solarPattern[sido]
  if (!pattern) return null
  return MONTH_LABELS.map((_, i) => {
    const hours = pattern[String(i + 1)]
    return hours ? +hours.reduce((a, b) => a + b, 0).toFixed(0) : 0
  })
})

const peakMonth = computed(() => {
  const m = monthlyGeneration.value
  if (!m) return null
  const max = Math.max(...m)
  return { month: MONTH_LABELS[m.indexOf(max)], mwh: max }
})

const monthlyChartOption = computed(() => {
  const m = monthlyGeneration.value
  if (!m) return {}
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${p[0].value.toLocaleString()} MWh` },
    grid: { left: 55, right: 10, top: 16, bottom: 30 },
    xAxis: { type: 'category', data: MONTH_LABELS, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: 'MWh', nameTextStyle: { fontSize: 10 } },
    series: [{
      type: 'bar',
      data: m,
      itemStyle: { color: '#9ED8F3', borderRadius: [3, 3, 0, 0] },
    }],
  }
})

function barWidth(val: number, s: SubstationData): string {
  const max = Math.max(1, s.spareKW, s.vol2Sum, s.vol3Sum)
  return Math.min(100, (val / max) * 100).toFixed(1) + '%'
}

// ── 수익 계산 ───────────────────────────────────────────
const SMP_WON_KWH = 110.76
const REC_WON     = 71_000

function recWeight(kw: number, type: InstallType): number {
  if (type === 'building') return kw <= 3000 ? 1.5 : 1.0
  if (kw < 100)  return 1.2
  if (kw <= 3000) return 1.0
  return 0.8
}

function formatWon(won: number): string {
  if (won >= 1_0000_0000) return (won / 1_0000_0000).toFixed(1) + '억원'
  if (won >= 1_0000)      return Math.round(won / 1_0000).toLocaleString() + '만원'
  return won.toLocaleString() + '원'
}

const revenueCalc = computed(() => {
  const eff = regionEfficiency.value
  const kw  = unitCapacity.value
  if (!eff?.pvamt_2025 || kw <= 0) return null

  const annualKwh    = eff.pvamt_2025 * 8760 * kw        // 단위 1기 연간 발전량 kWh
  const annualMwh    = annualKwh / 1000
  const weight       = recWeight(kw, installType.value)
  const smpRev       = annualKwh * SMP_WON_KWH
  const recRev       = annualMwh * weight * REC_WON
  const unitTotal    = smpRev + recRev

  const count        = installableCount.value
  return {
    annualMwh:     +annualMwh.toFixed(1),
    annualMwhAll:  +(annualMwh * count).toFixed(1),
    weight,
    smpUnit:    Math.round(smpRev),
    recUnit:    Math.round(recRev),
    unitTotal:  Math.round(unitTotal),
    totalAll:   Math.round(unitTotal * count),
    smpAll:     Math.round(smpRev * count),
    recAll:     Math.round(recRev * count),
    count,
  }
})
</script>

<template>
  <div class="simulation-page">
    <!-- Input Panel -->
    <div class="input-panel">
      <div class="panel-title">설비 가능 규모 분석</div>

      <div class="form-group">
        <label>변전소 선택</label>
        <el-select v-model="selectedSubstCd" filterable style="width: 100%" placeholder="이름으로 검색...">
          <el-option
            v-for="opt in substOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>

      <div v-if="selectedSubst" class="zone-info-box">
        <div class="info-row">
          <span>현재 포화도</span>
          <span class="info-val">{{ selectedSubst.saturation }}%</span>
        </div>
        <div class="info-row">
          <span>누적 연계용량</span>
          <span class="info-val">{{ (selectedSubst.linkedKW / 1000).toFixed(1) }} MW</span>
        </div>
        <div class="info-row">
          <span>위험도</span>
          <RiskBadge :level="calcRisk(selectedSubst.saturation)" />
        </div>
        <el-divider style="margin: 6px 0" />
        <div class="info-row">
          <span>변전소 여유</span>
          <span class="info-val">{{ (selectedSubst.spareKW / 1000).toFixed(1) }} MW</span>
        </div>
        <div class="info-row">
          <span>변압기 여유</span>
          <span class="info-val">{{ (selectedSubst.vol2Sum / 1000).toFixed(1) }} MW</span>
        </div>
        <div class="info-row">
          <span>배전선로 여유</span>
          <span class="info-val">{{ (selectedSubst.vol3Sum / 1000).toFixed(1) }} MW</span>
        </div>
        <div class="info-row bottleneck-row">
          <span>보수적 추정치</span>
          <span class="info-val">{{ (selectedSubst.trueSpareKW / 1000).toFixed(1) }} MW</span>
        </div>
      </div>

      <!-- 태양광 잠재력 점수 -->
      <div v-if="regionEfficiency" class="ai-box">
        <div class="ai-box-label">AI 분석 태양광 발전 적합도</div>
        <div class="eff-score-big">
          <span class="eff-score-num" :style="{ color: displayScore === 0 ? '#ef4444' : displayScore >= 0.7 ? '#10b981' : displayScore >= 0.4 ? '#f59e0b' : '#ef4444' }">
            {{ (displayScore * 100).toFixed(0) }}
          </span>
          <span class="eff-score-unit">점</span>
        </div>
        <div class="eff-score-sub">
          <span class="eff-score-comment" :style="{ color: displayScore === 0 ? '#ef4444' : displayScore >= 0.7 ? '#10b981' : displayScore >= 0.4 ? '#f59e0b' : '#ef4444' }">
            {{ displayScore === 0 ? '불가능해요' : displayScore >= 0.7 ? '최고예요!' : displayScore >= 0.4 ? '그냥 그래요' : '별로예요!' }}
          </span>
          <span v-if="displayScore === 0" class="eff-score-suggest">포화도가 가득 찬 지역이에요</span>
          <span v-else-if="displayScore < 0.4" class="eff-score-suggest">다른 지역을 찾아 볼까요?</span>
        </div>
      </div>

      <div class="form-group">
        <label>단위 설비 용량 (kW)</label>
        <div class="preset-buttons">
          <el-tooltip
            v-for="p in unitPresets"
            :key="p.value"
            :content="p.desc"
            placement="top"
          >
            <el-button
              size="small"
              :type="unitCapacity === p.value ? 'primary' : 'default'"
              @click="unitCapacity = p.value"
            >
              {{ p.label }}
            </el-button>
          </el-tooltip>
        </div>
        <div class="preset-hint">
          <span v-if="selectedPreset">{{ selectedPreset.label }} — {{ selectedPreset.desc }}</span>
          <span v-else>직접 입력 중</span>
        </div>
        <el-slider
          v-model="unitCapacity"
          :min="1"
          :max="50000"
          :step="1"
          show-input
          input-size="small"
        />
      </div>

      <div class="form-group">
        <label>설치 유형</label>
        <el-radio-group v-model="installType" size="small" style="width:100%; display:flex; gap:0">
          <el-radio-button value="ground" style="width:50%">일반부지</el-radio-button>
          <el-radio-button value="building" style="width:50%">건물 위</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- Result Panel -->
    <div class="result-panel">
      <template v-if="selectedSubst">
        <!-- Summary Row -->
        <div class="summary-row">
          <div class="summary-card primary-card">
            <div class="sum-label">최대 설치 가능 개수</div>
            <div class="sum-value big">{{ installableCount.toLocaleString() }} <span>개</span></div>
          </div>
          <div class="summary-card">
            <div class="sum-label">보수적 설치가능 추정치</div>
            <div class="sum-value">{{ (selectedSubst.trueSpareKW / 1000).toFixed(1) }} <span>MW</span></div>
          </div>
          <div class="summary-card">
            <div class="sum-label">전량 설치 후 포화도</div>
            <div class="sum-value">{{ afterSaturation }} <span>%</span></div>
          </div>
        </div>

        <!-- Gauges -->
        <div class="gauge-row">
          <div class="chart-card">
            <div class="chart-title">현재 포화도</div>
            <VChart :option="beforeGauge" autoresize style="height: 200px" />
          </div>
          <div class="chart-card">
            <div class="chart-title">설치 후 포화도</div>
            <VChart :option="afterGauge" autoresize style="height: 200px" />
          </div>
        </div>

        <!-- 예상 수익 -->
        <div v-if="revenueCalc" class="revenue-card">
          <div class="revenue-header">
            <span class="chart-title">연간 예상 수익</span>
            <span class="revenue-basis">SMP {{ SMP_WON_KWH }}원/kWh · REC {{ REC_WON.toLocaleString() }}원/REC · 가중치 {{ revenueCalc.weight }}</span>
          </div>

          <div class="revenue-cols">
            <!-- 단위 1기 -->
            <div class="revenue-col">
              <div class="revenue-section-label">단위 설비 1기 ({{ unitCapacity.toLocaleString() }}kW) 연간</div>
              <div class="revenue-row-group">
                <div class="revenue-row">
                  <span class="rev-label">연간 발전량</span>
                  <span class="rev-val">{{ revenueCalc.annualMwh.toLocaleString() }} MWh</span>
                </div>
                <div class="revenue-row">
                  <span class="rev-label">SMP 수익</span>
                  <span class="rev-val">{{ formatWon(revenueCalc.smpUnit) }}</span>
                </div>
                <div class="revenue-row">
                  <span class="rev-label">REC 수익</span>
                  <span class="rev-val">{{ formatWon(revenueCalc.recUnit) }}</span>
                </div>
                <div class="revenue-row total-row">
                  <span class="rev-label">합계</span>
                  <span class="rev-val highlight">{{ formatWon(revenueCalc.unitTotal) }}</span>
                </div>
              </div>
            </div>

            <!-- 전체 설치 -->
            <div class="revenue-col">
              <div class="revenue-section-label">
                전체 {{ revenueCalc.count.toLocaleString() }}기 설치 시 연간
              </div>
              <div class="revenue-row-group">
                <div class="revenue-row">
                  <span class="rev-label">연간 발전량</span>
                  <span class="rev-val">{{ revenueCalc.annualMwhAll.toLocaleString() }} MWh</span>
                </div>
                <div class="revenue-row">
                  <span class="rev-label">SMP 수익</span>
                  <span class="rev-val">{{ formatWon(revenueCalc.smpAll) }}</span>
                </div>
                <div class="revenue-row">
                  <span class="rev-label">REC 수익</span>
                  <span class="rev-val">{{ formatWon(revenueCalc.recAll) }}</span>
                </div>
                <div class="revenue-row total-row">
                  <span class="rev-label">합계</span>
                  <span class="rev-val highlight">{{ formatWon(revenueCalc.totalAll) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 월별 발전량 -->
        <div v-if="monthlyGeneration" class="chart-card">
          <div class="pattern-header">
            <div class="chart-title">
              {{ selectedSubst.sido }} 월별 태양광 발전량
              <span class="pattern-source">2025년 기준</span>
            </div>
            <div class="pattern-meta" v-if="peakMonth">
              피크: <b>{{ peakMonth.month }}</b> · {{ peakMonth.mwh.toLocaleString() }} MWh
            </div>
          </div>
          <VChart :option="monthlyChartOption" autoresize style="height: 200px" />
        </div>

        <!-- 월별 일사량 -->
        <div v-if="regionEfficiency" class="chart-card">
          <div class="chart-title">
            {{ selectedSubst!.sido }} 월별 평균 일사량
            <span class="pattern-source">2025년 기준</span>
          </div>
          <VChart :option="irradianceBarOption" autoresize style="height: 180px" />
        </div>

        <!-- Breakdown -->
        <div class="breakdown-card">
          <div class="chart-title">여유용량 상세 분해</div>
          <div class="breakdown-list">
            <div class="bk-item">
              <div class="bk-label">변전소 여유</div>
              <div class="bk-bar-wrap">
                <div class="bk-bar" :style="{ width: barWidth(selectedSubst.spareKW, selectedSubst), background: '#6b7280' }" />
              </div>
              <div class="bk-val">{{ (selectedSubst.spareKW / 1000).toFixed(1) }} MW</div>
            </div>
            <div class="bk-item">
              <div class="bk-label">변압기 여유</div>
              <div class="bk-bar-wrap">
                <div class="bk-bar" :style="{ width: barWidth(selectedSubst.vol2Sum, selectedSubst), background: '#6b7280' }" />
              </div>
              <div class="bk-val">{{ (selectedSubst.vol2Sum / 1000).toFixed(1) }} MW</div>
            </div>
            <div class="bk-item">
              <div class="bk-label">배전선로 여유</div>
              <div class="bk-bar-wrap">
                <div class="bk-bar" :style="{ width: barWidth(selectedSubst.vol3Sum, selectedSubst), background: '#6b7280' }" />
              </div>
              <div class="bk-val">{{ (selectedSubst.vol3Sum / 1000).toFixed(1) }} MW</div>
            </div>
            <div class="bk-item bottleneck-item">
              <div class="bk-label">보수적 추정치</div>
              <div class="bk-bar-wrap">
                <div class="bk-bar" :style="{ width: barWidth(selectedSubst.trueSpareKW, selectedSubst), background: '#6b7280' }" />
              </div>
              <div class="bk-val">{{ (selectedSubst.trueSpareKW / 1000).toFixed(1) }} MW</div>
            </div>
          </div>
        </div>
      </template>

      <div v-else class="no-result">
        <el-icon style="font-size: 48px; color: #d1d5db"><TrendCharts /></el-icon>
        <p>좌측에서 변전소를 선택하면<br>설비 가능 규모가 표시됩니다.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.simulation-page {
  display: flex;
  gap: 20px;
  height: 100%;
  overflow: hidden;
}

.input-panel {
  width: 300px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
}

.preset-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preset-hint {
  font-size: 11px;
  color: #9ca3af;
  min-height: 16px;
}

.zone-info-box {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #6b7280;
}

.info-val {
  font-weight: 700;
  color: #1a1a2e;
}

.info-val.highlight {
  color: #f56c6c;
}

.bottleneck-row {
  border-radius: 6px;
  padding: 4px 0;
}

.result-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  min-width: 0;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  flex-shrink: 0;
}

.summary-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: none;
}

.primary-card {
}

.sum-label {
  font-size: 12px;
  color: #1a1a2e;
  margin-bottom: 6px;
}

.sum-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

.sum-value.big {
  font-size: 22px;
}

.sum-value span {
  font-size: 12px;
  font-weight: 400;
  color: #6b7280;
}

.sum-hint {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

.breakdown-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: none;
  flex-shrink: 0;
}

.breakdown-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.bk-item {
  display: grid;
  grid-template-columns: 160px 1fr 80px;
  align-items: center;
  gap: 10px;
}

.bk-label {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.bk-bar-wrap {
  background: #f3f4f6;
  border-radius: 4px;
  height: 10px;
  overflow: hidden;
}

.bk-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.bk-val {
  font-size: 13px;
  font-weight: 700;
  color: #1a1a2e;
  text-align: right;
}

.bottleneck-item .bk-label {
  font-size: 12px;
  font-weight: 400;
  color: #6b7280;
}

.bottleneck-item .bk-val {
  font-size: 13px;
  font-weight: 700;
  color: #1a1a2e;
}

.gauge-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex-shrink: 0;
}

.chart-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: none;
}

.chart-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.pattern-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.pattern-source {
  font-size: 10px;
  color: #9ca3af;
  font-weight: 400;
  margin-left: 6px;
}

.pattern-meta {
  font-size: 12px;
  color: #6b7280;
  margin-left: auto;
}

.pattern-missing {
  font-size: 12px;
  color: #9ca3af;
  padding: 12px;
  text-align: center;
}

.efficiency-box {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.eff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.eff-title {
  font-size: 12px;
  font-weight: 600;
  color: #1a1a2e;
}

.ai-box {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-box-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 500;
}

.eff-score-big {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.eff-score-num {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}

.eff-score-unit {
  font-size: 14px;
  color: #6b7280;
}

.eff-score-sub {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}

.eff-score-comment {
  font-size: 13px;
  font-weight: 600;
}

.eff-score-suggest {
  font-size: 12px;
  color: #6b7280;
}

.eff-detail {
  font-size: 10px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eff-priority {
  font-size: 11px;
  font-weight: 400;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eff-hint {
  font-size: 10px;
  color: #9ca3af;
  margin-left: 4px;
}

.eff-title-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.eff-data-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1px 6px;
  background: linear-gradient(135deg, #0ea5e9, #0284c7);
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.eff-score-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 2px 0;
}

.eff-score-bar {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.eff-score-label {
  font-size: 12px;
  font-weight: 700;
  color: #1a1a2e;
  min-width: 36px;
  text-align: right;
}

.eff-score-desc {
  font-size: 10px;
  color: #6b7280;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eff-model-info {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.eff-model-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.eff-model-key {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
  flex-shrink: 0;
}

.eff-model-val {
  font-size: 11px;
  color: #374151;
  text-align: right;
}

.revenue-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: none;
}

.revenue-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.revenue-basis {
  font-size: 11px;
  color: #9ca3af;
}

.revenue-section-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 6px;
}

.revenue-cols {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.revenue-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.revenue-row-group {
  background: #f9fafb;
  border-radius: 8px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.revenue-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #374151;
}

.total-row {
  border-top: 1px solid #e5e7eb;
  padding-top: 6px;
  font-weight: 700;
}

.rev-label {
  color: #6b7280;
  width: 110px;
  flex-shrink: 0;
  text-align: left;
}

.rev-val {
  font-weight: 600;
  color: #1a1a2e;
  margin-left: auto;
  text-align: right;
}

.rev-val.highlight {
  color: #67c23a;
  font-size: 15px;
}

.no-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #9ca3af;
  font-size: 14px;
  text-align: center;
  line-height: 1.8;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: none;
}
</style>
