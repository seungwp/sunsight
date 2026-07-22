<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  unit?: string
  icon: string
  color?: string
  sub?: string
}>()
</script>

<template>
  <div class="kpi-card" :style="{ '--accent': color ?? '#409eff' }">
    <div class="kpi-icon-wrap">
      <el-icon class="kpi-icon"><component :is="icon" /></el-icon>
    </div>
    <div class="kpi-body">
      <div class="kpi-title">{{ title }}</div>
      <div class="kpi-value">
        {{ value }}<span v-if="unit" class="kpi-unit"> {{ unit }}</span>
      </div>
      <div v-if="sub" class="kpi-sub">{{ sub }}</div>
    </div>
  </div>
</template>

<style scoped>
.kpi-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  gap: 16px;
  align-items: center;
  box-shadow: 0 0 10.16px 0 rgba(34, 34, 34, 0.07);
}

.kpi-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-icon {
  font-size: 24px;
  color: #9ca3af;
}

.kpi-title {
  font-size: 12px;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.kpi-value {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1;
}

.kpi-unit {
  font-size: 14px;
  font-weight: 400;
  color: #6b7280;
}

.kpi-sub {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}
</style>
