export interface BacktestParams {
  startDate: string
  endDate: string
  model: 'XGBoost' | 'ARIMA' | 'LSTM'
}

export interface BacktestResult {
  dates: string[]
  actual: number[]
  predicted: number[]
  hitRate: number
  falseAlarmRate: number
  mae: number
  directionAccuracy: number
}
