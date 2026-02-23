export interface TopFactor {
  name: string
  nameZh: string
  shap: number
  category: 'Supply-Demand' | 'Macro' | 'Financial' | 'Geopolitical' | 'Sentiment'
}

export interface CurrentRisk {
  riskIndex: number
  riskLevel: 'Low' | 'Medium' | 'High'
  date: string
  topFactors: TopFactor[]
}

export interface TimeseriesPoint {
  date: string
  level: string
  riskIndex: number
}

export interface TimeseriesData {
  dates: string[]
  oilPrice: number[]
  riskIndex: number[]
  alerts: TimeseriesPoint[]
}

export type RiskLevel = 'Low' | 'Medium' | 'High'

export const RISK_COLORS: Record<RiskLevel, string> = {
  Low: '#3fb950',
  Medium: '#d29922',
  High: '#f85149',
}

export const RISK_THRESHOLDS: Array<{ level: RiskLevel; min: number; max: number }> = [
  { level: 'Low', min: 0, max: 40 },
  { level: 'Medium', min: 40, max: 70 },
  { level: 'High', min: 70, max: 100 },
]
