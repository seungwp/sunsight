import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import rawData from '../data/substationCoords.json'

export interface SubstationData {
  substCd: string
  substNm: string
  linkedKW: number
  spareKW: number    // vol1 변전소 여유
  vol2Sum: number    // 변압기 여유 합계
  vol2Min: number    // 가장 여유 없는 변압기
  vol3Sum: number    // DL 여유 합계
  vol3Min: number    // 가장 여유 없는 DL
  trueSpareKW: number // 실제 설치 가능 용량 (병목 기준)
  totalKW: number
  saturation: number
  lat: number | null
  lng: number | null
  sido?: string      // 시/도
  sigungu?: string   // 시/군/구
}

function calcRisk(rate: number): 'safe' | 'caution' | 'danger' {
  if (rate >= 85) return 'danger'
  if (rate >= 70) return 'caution'
  return 'safe'
}

export const useSubstationStore = defineStore('substation', () => {
  const allSubstations = ref<SubstationData[]>(
    Object.values(rawData as Record<string, SubstationData>)
  )

  // 좌표 있는 변전소만
  const mappedSubstations = computed(() =>
    allSubstations.value.filter((s) => s.lat !== null && s.lng !== null)
  )

  const dangerSubstations = computed(() =>
    mappedSubstations.value.filter((s) => s.saturation >= 85)
  )

  const stats = computed(() => ({
    total: mappedSubstations.value.length,
    danger: mappedSubstations.value.filter((s) => s.saturation >= 85).length,
    caution: mappedSubstations.value.filter((s) => s.saturation >= 70 && s.saturation < 85).length,
    safe: mappedSubstations.value.filter((s) => s.saturation < 70).length,
  }))

  function getRisk(s: SubstationData) {
    return calcRisk(s.saturation)
  }

  const sigunguList = computed(() =>
    [...new Set(
      mappedSubstations.value
        .filter((s) => s.sigungu)
        .map((s) => s.sigungu as string)
    )].sort()
  )

  return { allSubstations, mappedSubstations, dangerSubstations, stats, sigunguList, getRisk }
})
