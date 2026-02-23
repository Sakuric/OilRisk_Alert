import http from './index'
import type { ApiResponse } from '@/types/alert'
import type { FactorDetail, RadarScore, WeightConfig } from '@/types/factor'

export function getFactorExplanation(date: string) {
  return http.get<ApiResponse<FactorDetail[]>>(`/api/explain/${date}`)
}

export function getRadarScores() {
  return http.get<ApiResponse<RadarScore[]>>('/api/risk/radar')
}

export function updateWeights(weights: WeightConfig, signal?: AbortSignal) {
  return http.put<ApiResponse<unknown>>('/api/config/weights', weights, { signal })
}
