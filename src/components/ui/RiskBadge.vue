<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ level: 'safe' | 'caution' | 'danger' }>()

const config = computed(() => ({
  safe: { label: '안전', type: 'success' as const },
  caution: { label: '주의', type: 'warning' as const },
  danger: { label: '위험', type: 'danger' as const },
}[props.level]))
</script>

<template>
  <el-tag :type="config.type" size="small" effect="dark">{{ config.label }}</el-tag>
</template>
