<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/', icon: 'DataBoard', label: '종합 현황' },
  { path: '/grid-map', icon: 'MapLocation', label: '계통 지도' },
  { path: '/simulation', icon: 'Histogram', label: '시뮬레이션' },
  { path: '/feasibility', icon: 'Grid', label: '설비 가능 지역' },
]
</script>

<template>
  <aside class="sidebar">
    <RouterLink to="/" class="sidebar-logo">
      <img src="../../assets/2.png" class="logo-img" alt="SunSight" />
    </RouterLink>

    <nav class="sidebar-nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: route.path === item.path }"
      >
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <span>계통포화 방지 대시보드</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  min-width: 220px;
  background: #1a1a2e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 16px 20px 16px 0px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  text-decoration: none;
}

.logo-img {
  width: 100%;
  max-height: 35px;
  object-fit: contain;
}

.sidebar-nav {
  flex: 1;
  padding: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  border-radius: 0;
  color: #a0a8c0;
  transition: all 0.2s;
  text-decoration: none;
  font-size: 16px;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
}

.nav-item.active {
  background: #32324C;
  color: #ffffff;
  border-left-color: transparent;
  font-weight: 900;
  -webkit-text-stroke: 0.5px #ffffff;
  margin: 0 8px;
  border-radius: 7px;
}

.nav-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.nav-label {
  font-size: 14px;
  line-height: 1.4;
}

.nav-item.active .nav-label {
  font-size: 14.5px;
}

.sidebar-footer {
  padding: 16px 20px;
  font-size: 11px;
  color: #505878;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
