<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppSidebar from './components/layout/AppSidebar.vue'
import AppHeader from './components/layout/AppHeader.vue'
</script>

<template>
  <AppSidebar />
  <div class="main-content">
    <AppHeader />
    <div class="page-body">
      <RouterView />
    </div>
  </div>
</template>
