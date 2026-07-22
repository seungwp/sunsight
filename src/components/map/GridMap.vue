<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import type { GridZone } from '../../types/grid'
import type { SubstationData } from '../../stores/substationStore'

const props = defineProps<{
  zones: GridZone[]
  layerMode: 'spare' | 'saturation' | 'feasibility'
  selectedZoneId: string | null
  mini?: boolean
  substations?: SubstationData[]
  showSubstations?: boolean
  initialCenter?: [number, number] | null
  initialZoom?: number | null
}>()

const emit = defineEmits<{
  selectZone: [id: string]
  selectSubst: [substCd: string]
  miniClick: [lat: number, lng: number]
}>()

const mapContainer = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
const markers: L.CircleMarker[] = []
const substMarkers: L.CircleMarker[] = []

function getColor(zone: GridZone): string {
  if (props.layerMode === 'spare') {
    const s = zone.spareCapacity
    if (s >= 500) return '#9ED8F3'
    if (s >= 300) return '#9ED8F3'
    if (s >= 100) return '#fee08b'
    if (s >= 50) return '#f46d43'
    return '#FF494C'
  }
  if (props.layerMode === 'saturation') {
    if (zone.saturationRate >= 85) return '#FF494C'
    if (zone.saturationRate >= 70) return '#fdae61'
    return '#9ED8F3'
  }
  // feasibility
  if (zone.maxNewInstall >= 500) return '#9ED8F3'
  if (zone.maxNewInstall > 0) return '#fdae61'
  return '#FF494C'
}

function getRadius(zone: GridZone): number {
  if (props.mini) {
    // gridCapacity를 그룹 크기 proxy로 사용 (count * 1000 단위)
    const base = Math.sqrt(zone.gridCapacity / 1000) * 5
    return Math.max(6, Math.min(base, 22))
  }
  const base = Math.sqrt(zone.gridCapacity / 3200) * 22
  return Math.max(10, Math.min(base, 35))
}

function substColor(s: SubstationData): string {
  if (props.layerMode === 'spare') {
    const mw = s.trueSpareKW / 1000
    if (mw >= 100) return '#9ED8F3'
    if (mw >= 50)  return '#9ED8F3'
    if (mw >= 10)  return '#fee08b'
    if (mw > 0)    return '#f46d43'
    return '#FF494C'
  }
  if (props.layerMode === 'feasibility') {
    if (s.trueSpareKW <= 0 || s.saturation >= 85) return '#FF494C'
    if (s.saturation >= 70) return '#fdae61'
    return '#9ED8F3'
  }
  // saturation
  if (s.saturation >= 85) return '#FF494C'
  if (s.saturation >= 70) return '#fdae61'
  return '#9ED8F3'
}

function substTooltip(s: SubstationData, color: string): string {
  const trueMW = (s.trueSpareKW / 1000).toFixed(1)
  const base = `<b>${s.substNm}변전소</b> <span style="color:${color}">●</span><br>`
  if (props.layerMode === 'spare') {
    return base +
      `보수적 설치가능 추정치: <b>${trueMW} MW</b><br>` +
      `변전소 여유: ${(s.spareKW / 1000).toFixed(1)} MW<br>` +
      `변압기 여유: ${(s.vol2Sum / 1000).toFixed(1)} MW<br>` +
      `배전선로 여유: ${(s.vol3Sum / 1000).toFixed(1)} MW`
  }
  if (props.layerMode === 'feasibility') {
    const status = s.trueSpareKW <= 0 ? '설치 불가' : s.saturation >= 85 ? '포화 — 설치 불가' : s.saturation >= 70 ? '주의 — 소규모 가능' : '설치 가능'
    return base +
      `설비 가능 여부: <b>${status}</b><br>` +
      `포화도: <span style="color:${color};font-weight:700">${s.saturation}%</span> · 여유: ${trueMW} MW`
  }
  return base +
    `포화도: <b style="color:${color}">${s.saturation}%</b><br>` +
    `연계용량: ${(s.linkedKW / 1000).toFixed(1)} MW<br>` +
    `─────────────────<br>` +
    `변전소 여유: ${(s.spareKW / 1000).toFixed(1)} MW<br>` +
    `변압기 여유: ${(s.vol2Sum / 1000).toFixed(1)} MW<br>` +
    `배전선로 여유: ${(s.vol3Sum / 1000).toFixed(1)} MW<br>` +
    `<b>보수적 설치가능 추정치: ${trueMW} MW</b>`
}

function buildSubstMarkers() {
  substMarkers.forEach((m) => m.remove())
  substMarkers.length = 0
  if (!map || !props.showSubstations || !props.substations) return

  props.substations.forEach((s) => {
    if (s.lat === null || s.lng === null) return
    const color = substColor(s)
    const marker = L.circleMarker([s.lat!, s.lng!], {
      radius: 5,
      fillColor: color,
      color: '#ffffff',
      weight: 1,
      opacity: 1,
      fillOpacity: 0.9,
    })

    marker.bindTooltip(substTooltip(s, color), { direction: 'top', offset: [0, -6] })

    if (!props.mini) {
      marker.on('click', () => emit('selectSubst', s.substCd))
      marker.getElement()?.classList.add('subst-clickable')
    }

    marker.addTo(map!)
    substMarkers.push(marker)
  })
}

function buildMarkers() {
  markers.forEach((m) => m.remove())
  markers.length = 0
  if (!map) return

  props.zones.forEach((zone) => {
    const isSelected = zone.id === props.selectedZoneId
    const color = getColor(zone)
    const marker = L.circleMarker([zone.lat, zone.lng], {
      radius: getRadius(zone),
      fillColor: color,
      color: isSelected ? '#1a1a2e' : '#ffffff',
      weight: isSelected ? 2 : 0.25,
      opacity: 1,
      fillOpacity: isSelected ? 0.95 : 0.78,
    })

    marker.bindTooltip(
      `<b>${zone.regionName}</b><br>포화도: ${zone.saturationRate}%<br>여유용량: ${zone.spareCapacity} MW`,
      { direction: 'top', offset: [0, -8] },
    )

    if (props.mini) {
      marker.on('click', () => emit('miniClick', zone.lat, zone.lng))
    } else {
      marker.on('click', () => emit('selectZone', zone.id))
    }

    marker.addTo(map!)
    markers.push(marker)
  })

  buildSubstMarkers()
}

onMounted(() => {
  if (!mapContainer.value) return
  map = L.map(mapContainer.value, {
    center: [36.5, 127.8],
    zoom: props.mini ? 6 : 7,
    zoomControl: !props.mini,
    scrollWheelZoom: !props.mini,
    dragging: !props.mini,
    touchZoom: !props.mini,
    doubleClickZoom: !props.mini,
    attributionControl: false,
  })

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap contributors © CARTO',
  }).addTo(map)

  buildMarkers()

  if (props.initialCenter && props.initialZoom) {
    map.setView(props.initialCenter, props.initialZoom)
  }
})

watch(() => [props.layerMode, props.zones, props.selectedZoneId, props.showSubstations], buildMarkers)

onUnmounted(() => {
  map?.remove()
  map = null
})
</script>

<template>
  <div ref="mapContainer" class="grid-map" :class="{ mini }"></div>
</template>

<style scoped>
.grid-map {
  width: 100%;
  height: 100%;
  border-radius: 12px;
  z-index: 0;
}

.grid-map.mini {
  border-radius: 8px;
}
</style>
