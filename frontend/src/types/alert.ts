export type TriggerType = 'THRESHOLD' | 'TREND' | 'ANOMALY'

export interface AlertRecord {
  id: number
  date: string
  level: 'Low' | 'Medium' | 'High'
  riskIndex: number
  triggerType: TriggerType
  triggerFactor: string
  triggerFactorZh: string
  summary: string
  summaryEn: string
  aiReport?: string
}

export interface AlertPage {
  total: number
  page: number
  size: number
  records: AlertRecord[]
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface TriggerRule {
  ruleType: 'THRESHOLD' | 'TREND' | 'ANOMALY'
  factor: string
  factorZh: string
  currentValue: number
  threshold: number
  description: string
}

export interface AlertDetail extends AlertRecord {
  triggerRules: TriggerRule[]
}
