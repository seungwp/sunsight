<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()

const pageTitles: Record<string, string> = {
  '/': '종합 현황',
  '/grid-map': '계통 지도',
  '/location': '입지 추천',
  '/simulation': '시뮬레이션',
  '/forecast': '예측 분석',
  '/feasibility': '데이터 내보내기',
}

const pageTitle = computed(() => pageTitles[route.path] ?? '대시보드')

const now = new Date()
const dateStr = now.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })
</script>

<template>
  <header class="app-header">
    <div class="header-right">
      <span class="date-label">{{ dateStr }}</span>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 67px;
  background: #F9F9F9;
  border-bottom: none;
  flex-shrink: 0;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.date-label {
  font-size: 13px;
  color: #6b7280;
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
