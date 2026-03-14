import http from './index'
import type { ApiResponse } from '@/types/alert'
import type { SystemStatusVO, CollectResultVO } from '@/types/system'

export function getSystemStatus() {
  return http.get<ApiResponse<SystemStatusVO>>('/api/system/status')
}

export function triggerCollect() {
  return http.post<ApiResponse<CollectResultVO>>('/api/collect/trigger', null, {
    timeout: 120_000,
  })
}
