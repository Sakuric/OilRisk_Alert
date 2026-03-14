import http from './index'
import type { ApiResponse } from '@/types/alert'
import type { FactorDetail, RadarScore, WeightConfig, WeightUpdateResult } from '@/types/factor'
import type { WeightDataPoint } from '@/components/charts/WeightAreaChart.vue'

export function getFactorExplanation(date: string) {
  return http.get<ApiResponse<FactorDetail[]>>(`/api/explain/${date}`)
}

export function getRadarScores() {
  return http.get<ApiResponse<RadarScore[]>>('/api/risk/radar')
}

export function updateWeights(weights: WeightConfig, signal?: AbortSignal) {
  return http.put<ApiResponse<WeightUpdateResult>>('/api/config/weights', weights, { signal })
}

export function getWeightHistory(months = 24) {
  return http.get<ApiResponse<WeightDataPoint[]>>('/api/factor/weight-history', { params: { months } })
}
