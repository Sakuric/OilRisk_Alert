import http from './index'
import type { ApiResponse } from '@/types/alert'
import type { BacktestParams, BacktestResult } from '@/types/backtest'

export function runBacktest(params: BacktestParams) {
  return http.post<ApiResponse<BacktestResult>>('/api/predict/backtest', params)
}
