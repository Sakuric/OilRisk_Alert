import http from './index'
import type { ApiResponse } from '@/types/alert'
import type { CurrentRisk, TimeseriesData, ModelSignal } from '@/types/risk'

export interface TimeseriesParams {
  start?: string
  end?: string
}

export function getCurrentRisk() {
  return http.get<ApiResponse<CurrentRisk>>('/api/risk/current')
}

export function getTimeseries(params?: TimeseriesParams) {
  return http.get<ApiResponse<TimeseriesData>>('/api/factors/timeseries', { params })
}

export function getModelSignals() {
  return http.get<ApiResponse<ModelSignal>>('/api/risk/signals')
}
