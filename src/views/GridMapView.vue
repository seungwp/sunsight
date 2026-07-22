<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSubstationStore } from '../stores/substationStore'
import GridMap from '../components/map/GridMap.vue'
import MapLegend from '../components/map/MapLegend.vue'

const route = useRoute()
const router = useRouter()
const substStore = useSubstationStore()

const initialCenter = ref<[number, number] | null>(null)
const initialZoom = ref<number | null>(null)

onMounted(() => {
  const lat = parseFloat(route.query.lat as string)
  const lng = parseFloat(route.query.lng as string)
  const zoom = parseInt(route.query.zoom as string)
  if (!isNaN(lat) && !isNaN(lng)) {
    initialCenter.value = [lat, lng]
    initialZoom.value = isNaN(zoom) ? 11 : zoom
  }
})

type LayerMode = 'spare' | 'saturation' | 'feasibility'
const layerMode = ref<LayerMode>('saturation')
const showSubstations = ref(true)

const layerOptions = [
  { label: '포화 위험도', value: 'saturation' },
  { label: '여유 용량', value: 'spare' },
  { label: '설비 가능 여부', value: 'feasibility' },
]

function onSelectSubst(substCd: string) {
  router.push({ path: '/simulation', query: { subst: substCd } })
}
</script>

<template>
  <div class="map-page">
    <div class="map-toolbar">
      <el-radio-group v-model="layerMode" size="small">
        <el-radio-button v-for="opt in layerOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </el-radio-button>
      </el-radio-group>

      <el-divider direction="vertical" />

      <el-tag size="small" type="danger" effect="plain">
        실측 변전소 {{ substStore.stats.total }}개
      </el-tag>
      <el-tag size="small" type="danger">위험 {{ substStore.stats.danger }}개</el-tag>
      <el-tag size="small" type="warning">주의 {{ substStore.stats.caution }}개</el-tag>
      <el-tag size="small" type="success">안전 {{ substStore.stats.safe }}개</el-tag>
    </div>

    <div class="map-body">
      <div class="map-wrap">
        <GridMap
          :zones="[]"
          :layer-mode="layerMode"
          :selected-zone-id="null"
          :substations="substStore.mappedSubstations"
          :show-substations="true"
          :initial-center="initialCenter"
          :initial-zoom="initialZoom"
          @select-subst="onSelectSubst"
        />
        <div class="legend-overlay">
          <MapLegend :layer-mode="layerMode" />
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.map-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.map-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.toolbar-hint {
  font-size: 12px;
  color: #9ca3af;
}

.map-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.map-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.legend-overlay {
  position: absolute;
  bottom: 20px;
  left: 16px;
  z-index: 1000;
}
</style>
