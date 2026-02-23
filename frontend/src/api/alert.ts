import http from './index'
import type { ApiResponse, AlertPage, AlertDetail } from '@/types/alert'

export interface AlertParams {
  page?: number
  size?: number
  level?: string
  sort?: string
}

export function getAlerts(params?: AlertParams) {
  return http.get<ApiResponse<AlertPage>>('/api/alerts', { params })
}

export function getAlertDetail(id: number) {
  return http.get<ApiResponse<AlertDetail>>(`/api/alerts/${id}`)
}
