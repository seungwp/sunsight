<script setup lang="ts">
defineProps<{ layerMode: string }>()
</script>

<template>
  <div class="map-legend">
    <div class="legend-title">
      {{ layerMode === 'spare' ? '여유용량 (MW)' : layerMode === 'saturation' ? '포화도 (%)' : '설비 가능 여부' }}
    </div>

    <template v-if="layerMode === 'spare'">
      <div class="legend-item"><span class="swatch" style="background:#9ED8F3"></span>50 MW 이상</div>
      <div class="legend-item"><span class="swatch" style="background:#fee08b"></span>10 ~ 50 MW</div>
      <div class="legend-item"><span class="swatch" style="background:#f46d43"></span>10 MW 미만</div>
      <div class="legend-item"><span class="swatch" style="background:#FF494C"></span>여유 없음</div>
    </template>

    <template v-else-if="layerMode === 'saturation'">
      <div class="legend-item"><span class="swatch" style="background:#9ED8F3"></span>70% 미만 (안전)</div>
      <div class="legend-item"><span class="swatch" style="background:#fdae61"></span>70 ~ 85% (주의)</div>
      <div class="legend-item"><span class="swatch" style="background:#FF494C"></span>85% 이상 (위험)</div>
    </template>

    <template v-else>
      <div class="legend-item"><span class="swatch" style="background:#9ED8F3"></span>설치 가능</div>
      <div class="legend-item"><span class="swatch" style="background:#fdae61"></span>주의 — 소규모 가능</div>
      <div class="legend-item"><span class="swatch" style="background:#FF494C"></span>설치 불가 (포화)</div>
    </template>
  </div>
</template>

<style scoped>
.map-legend {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 12px 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  min-width: 160px;
}

.legend-title {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #4b5563;
  margin-bottom: 4px;
}

.swatch {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  flex-shrink: 0;
}
</style>
