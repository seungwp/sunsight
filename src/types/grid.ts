export interface GridZone {
  id: string
  regionName: string
  province: string
  lat: number
  lng: number
  gridCapacity: number
  currentLoad: number
  spareCapacity: number
  saturationRate: number
  riskLevel: 'safe' | 'caution' | 'danger'
  riskStars: 1 | 2 | 3
  maxNewInstall: number
  peakHour: number
  curtailmentMWh: number
  solarIrradiance: number
  hcThermal: number
  hcVoltage: number
  hcProtection: number
}
